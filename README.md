# 📊 Market Sentiment Dashboard

A real-time options sentiment analysis dashboard built with **FastAPI** (backend) and **React.js** (frontend). It integrates **DeepSeek LLM via OpenRouter** to generate intelligent summaries and strategy suggestions based on live option chain data.

🔄 Updates every 15 seconds with actionable insights.

![WhatsApp Image 2025-07-20 at 18 38 28_f57c11ca](https://github.com/user-attachments/assets/114bd854-4d1c-4bbf-8bb6-fe4c54e63cda)

![WhatsApp Image 2025-07-20 at 18 38 51_0a9191b5](https://github.com/user-attachments/assets/ae8802ff-da2c-41f2-ac6e-2dde486dc85a)


---

## 🚀 Features

- Live Option Chain Data Visualization
- Core Market Indicators:
  - ✅ Put/Call Volume Ratio
  - ✅ Gamma Exposure (GEX)
  - ✅ Open Interest Concentration
  - ✅ Volume/OI Ratio
- Strike-wise Sentiment Table (Put & Call side)
- OI Skew Analysis (IV comparisons)
- Overall Market Sentiment with LLM Explanation
- LLM-Suggested Options Strategies (Protective Put, Bear Put Spread, etc.)
- Smooth UI with color-coded components and scroll syncing

---

## 🧠 Tech Stack

- **Backend**: FastAPI, OpenRouter (DeepSeek), DhanHQ API
- **Frontend**: React.js, Axios, TailwindCSS
- **LLM**: DeepSeek Chat (via [OpenRouter.ai](https://openrouter.ai))

---

## 📁 Folder Structure

market-sentiment-dashboard/
├── backend/
│ ├── main.py
│ ├── llm_handler.py
│ ├── sentiment_engine.py
│ ├── requirements.txt
│ └── .env.example
├── frontend/
│ └── src/
│ ├── components/
│ │ ├── OIChart.jsx
│ │ ├── SentimentTable.jsx
│ │ └── IVTable.jsx
│ ├── App.jsx
│ └── api.js
└── README.md


 .env (Create inside backend)
ini
Copy
Edit
OPENROUTER_API_KEY=your_openrouter_key
DHAN_API_KEY=your_dhan_key

 Frontend (React)
cd frontend
npm install
npm start
Runs at: http://localhost:3000


 LLM Integration
The backend uses DeepSeek Chat via OpenRouter API to:

Analyze overall sentiment from OI, GEX, PCR

Generate reasoning text

Suggest strategies like:

Protective Put

Bear Put Spread

Fully automated via OpenRouter-compatible headers.



Metric	Meaning
Put/Call Ratio > 1	Panic hedging, bearish bias
Negative GEX	Dealers short gamma, volatility amplified
OI Walls	Resistance @ 25,000, Support @ 24,500
OI+LTP Δ (Strike)	Per-strike bullish/bearish labels
Skew (CE IV > PE IV)	Bullish bias (smart money pricing)


