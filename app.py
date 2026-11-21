import os
import ccxt
import yfinance as yf
import pandas as pd
import gradio as gr
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import OpenAI

# 1. טעינת מפתח ה-API
load_dotenv()
client = OpenAI()

# 2. הגדרת מבני התשובה (טפסים) לכל סוכן
class AnalystReport(BaseModel):
    sentiment: str      # Bullish, Bearish, or Neutral
    summary: str        # סיכום קצר של הממצאים

class FinalDecision(BaseModel):
    allow_buy: bool     # החלטה סופית: True או False
    risk_score: int     # ציון סיכון מ-1 עד 10
    short_reason: str   # הנימוק הסופי שמשקלל את שני הסוכנים

# 3. חישוב אינדיקטורים טכניים
def calculate_indicators(closes: list[float]) -> dict:
    series = pd.Series(closes)
    sma_20 = round(series.rolling(window=20).mean().iloc[-1], 2)
    sma_50 = round(series.rolling(window=50).mean().iloc[-1], 2)
    
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi_14 = round(100 - (100 / (1 + rs.iloc[-1])), 2)
    
    current_price = round(closes[-1], 2)
    return {
        "price": current_price,
        "rsi": rsi_14,
        "sma_20": sma_20,
        "sma_50": sma_50
    }

def get_asset_technicals(symbol: str) -> tuple[str, dict]:
    if "/" in symbol:
        exchange = ccxt.coinbase()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1h", limit=60)
        closes = [candle[4] for candle in ohlcv]
        return "Crypto (1H Chart)", calculate_indicators(closes)
    else:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="3mo", interval="1d")
        if hist.empty or len(hist) < 50:
            raise ValueError(f"לא נמצאו נתונים עבור '{symbol}'.")
        closes = hist["Close"].tolist()
        return "Stock (Daily Chart)", calculate_indicators(closes)

# --- סוכן 1: אנליסט טכני בלבד ---
def run_technical_agent(symbol: str, tech: dict) -> AnalystReport:
    prompt = f"""
    Analyze ONLY the technical indicators for {symbol}:
    Price: ${tech['price']}, RSI(14): {tech['rsi']}, SMA20: ${tech['sma_20']}, SMA50: ${tech['sma_50']}.
    Ignore news. Is the technical setup Bullish, Bearish, or Neutral? Give a 2-sentence summary.
    """
    res = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": "You are a pure quantitative technical analyst."},
            {"role": "user", "content": prompt}
        ],
        text_format=AnalystReport,
    )
    return res.output_parsed

# --- סוכן 2: חוקר חדשות וסנטימנט ברשת ---
def run_news_agent(symbol: str) -> AnalystReport:
    prompt = f"""
    Search the web for today's breaking news and market sentiment for {symbol}.
    Ignore chart indicators. Based ONLY on news and events, is the sentiment Bullish, Bearish, or Neutral? Give a 2-sentence summary.
    """
    res = client.responses.parse(
        model="gpt-4o-mini",
        tools=[{"type": "web_search_preview"}],
        input=[
            {"role": "system", "content": "You are a financial news and sentiment researcher."},
            {"role": "user", "content": prompt}
        ],
        text_format=AnalystReport,
    )
    return res.output_parsed

# --- סוכן 3: מנהל הסיכונים הראשי (השופט) ---
def run_risk_manager_agent(symbol: str, tech_report: AnalystReport, news_report: AnalystReport) -> FinalDecision:
    prompt = f"""
    You are reviewing a potential BUY trade for {symbol}.
    
    Report from Technical Analyst ({tech_report.sentiment}):
    {tech_report.summary}
    
    Report from News Researcher ({news_report.sentiment}):
    {news_report.summary}
    
    Weigh both reports. If there is high news risk or weak technicals, block the trade. Make your final ruling.
    """
    res = client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": "You are the Chief Risk Officer. You make the final trading decision based on your team's reports."},
            {"role": "user", "content": prompt}
        ],
        text_format=FinalDecision,
    )
    return res.output_parsed

# הפונקציה הראשית שמפעילה את שלושת הסוכנים בזה אחר זה
def analyze_multi_agent(symbol: str):
    try:
        clean_symbol = symbol.strip().upper()
        asset_type, tech = get_asset_technicals(clean_symbol)
        
        # הפעלת סוכן 1
        tech_report = run_technical_agent(clean_symbol, tech)
        
        # הפעלת סוכן 2
        news_report = run_news_agent(clean_symbol)
        
        # הפעלת סוכן 3 שמקבל את התוצאות של 1 ו-2
        final_decision = run_risk_manager_agent(clean_symbol, tech_report, news_report)

        status_text = "✅ מאושר לקנייה (BUY)" if final_decision.allow_buy else "🛑 חסום לקנייה (HOLD / BLOCK)"
        price_display = f"${tech['price']:,.2f} ({asset_type}) | RSI: {tech['rsi']}"
        tech_display = f"[{tech_report.sentiment}] {tech_report.summary}"
        news_display = f"[{news_report.sentiment}] {news_report.summary}"
        
        return (
            price_display,
            tech_display,
            news_display,
            status_text,
            f"{final_decision.risk_score} / 10",
            final_decision.short_reason
        )
    except Exception as e:
        return "שגיאה", "-", "-", "לא ניתן לבדוק", "-", f"פירוט השגיאה: {str(e)}"

# ממשק המשתמש המעודכן שמציג את כל 3 הסוכנים
with gr.Blocks(title="AlphaSentinel Multi-Agent") as demo:
    gr.Markdown("# 🛡️ AlphaSentinel — מערכת Multi-Agent לניתוח מסחר")
    gr.Markdown("הזן זוג קריפטו (כמו `BTC/USDT`) או מניה (כמו `NVDA`). המערכת תפעיל 3 סוכנים עצמאיים שישקללו החלטה סופית.")
    
    with gr.Row():
        symbol_input = gr.Textbox(label="נכס לבדיקה", value="NVDA")
        analyze_btn = gr.Button("הפעל צוות סוכנים", variant="primary")
        
    price_out = gr.Textbox(label="נתוני שוק חיים")
    
    with gr.Row():
        tech_agent_out = gr.Textbox(label="📊 דוח סוכן 1: אנליסט טכני", lines=3)
        news_agent_out = gr.Textbox(label="📰 דוח סוכן 2: חוקר חדשות", lines=3)
        
    with gr.Row():
        decision_out = gr.Textbox(label="⚖️ החלטת סוכן 3: מנהל סיכונים")
        risk_out = gr.Textbox(label="ציון סיכון")
        
    reason_out = gr.Textbox(label="סיכום מנהל הסיכונים הראשי", lines=2)

    analyze_btn.click(
        fn=analyze_multi_agent,
        inputs=symbol_input,
        outputs=[price_out, tech_agent_out, news_agent_out, decision_out, risk_out, reason_out]
    )

    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 7860))
        demo.launch(server_name="0.0.0.0", server_port=port)


'''if __name__ == "__main__":
    demo.launch()
    #demo.launch(share=True)'''