# 🛡️ AlphaSentinel — Multi-Agent AI Trade Risk Filter

**AlphaSentinel** is a real-time financial risk-management system that bridges **Algorithmic Trading** and **Large Language Models (LLMs)**.

Before entering a trade on Crypto or Equities, AlphaSentinel deploys a **3-Agent Pipeline** to evaluate market conditions:
1. **Technical Analyst Agent:** Evaluates live price action, `RSI(14)`, `SMA-20`, and `SMA-50`.
2. **News & Sentiment Agent:** Uses live **Web Search** to scan breaking news and regulatory risks.
3. **Chief Risk Manager Agent:** Weighs both reports and outputs a structured trade decision (`True/False`), risk score (`1-10`), and concise reasoning.

## 🛠️ Tech Stack
- **Language:** Python
- **AI & Agents:** OpenAI Responses API, Structured Outputs (`Pydantic`), Live Web Search Tool
- **Market Data & Quant:** `ccxt` (Crypto), `yfinance` (Stocks), `pandas` (Technical Indicators)
- **Frontend UI:** `Gradio`

## 🚀 How to Run Locally

1. **Clone the repository:**
   ```bash
   git clone https://github.com
   cd alphasentinel
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key:**
   Create a `.env` file in the root directory and add:
   ```text
   OPENAI_API_KEY=your-openai-api-key
   ```

4. **Launch the app:**
   ```bash
   python app.py
   ```
