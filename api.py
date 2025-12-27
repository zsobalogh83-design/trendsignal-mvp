"""
TrendSignal MVP - FastAPI Backend with REAL NewsCollector
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime, timedelta
import sys
import os
import numpy as np

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)
sys.path.insert(0, os.path.dirname(__file__))

from main import run_batch_analysis, get_config
from src.news_collector import NewsCollector

app = FastAPI(title="TrendSignal API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TICKERS = [
    {'symbol': 'AAPL', 'name': 'Apple Inc.'},
    {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
    {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'},
]

# Global instances
config = None
news_collector = None

def to_python(val):
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    return val

@app.on_event("startup")
async def startup_event():
    global config, news_collector
    print("🚀 TrendSignal FastAPI backend started!")
    config = get_config()
    print("✅ Configuration loaded")
    
    try:
        news_collector = NewsCollector(config)
        print("✅ NewsCollector initialized with REAL API keys")
    except Exception as e:
        print(f"⚠️ NewsCollector init failed: {e}")

@app.get("/")
async def root():
    return {"status": "ok", "service": "TrendSignal API"}

@app.get("/api/v1/signals")
async def get_signals(status: Optional[str] = "active", limit: Optional[int] = 50):
    try:
        print(f"📡 GET /api/v1/signals")
        signals_data = run_batch_analysis(TICKERS[:limit])
        signals_list = []
        
        for idx, signal in enumerate(signals_data, start=1):
            api_signal = {
                "id": idx,
                "ticker_symbol": str(signal.ticker_symbol),
                "decision": str(signal.decision),
                "strength": str(signal.strength),
                "combined_score": to_python(signal.combined_score),
                "overall_confidence": to_python(signal.overall_confidence),
                "sentiment_score": to_python(signal.sentiment_score),
                "technical_score": to_python(signal.technical_score),
                "risk_score": to_python(signal.risk_score),
                "entry_price": to_python(signal.entry_price) if signal.entry_price else 0.0,
                "stop_loss": to_python(signal.stop_loss) if signal.stop_loss else 0.0,
                "take_profit": to_python(signal.take_profit) if signal.take_profit else 0.0,
                "risk_reward_ratio": to_python(signal.risk_reward_ratio) if signal.risk_reward_ratio else 1.0,
                "reasoning": {
                    "sentiment": {
                        "summary": f"Sentiment analysis for {signal.ticker_symbol}",
                        "key_news": ["Recent news analyzed"],
                        "score": to_python(signal.sentiment_score)
                    },
                    "technical": {
                        "summary": f"Technical indicators for {signal.ticker_symbol}",
                        "key_signals": ["Technical analysis complete"],
                        "score": to_python(signal.technical_score)
                    },
                    "risk": {
                        "summary": "Risk assessment",
                        "factors": ["Volatility analyzed"]
                    }
                },
                "created_at": datetime.utcnow().isoformat() + "Z",
                "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z",
                "status": status
            }
            signals_list.append(api_signal)
        
        print(f"✅ Returning {len(signals_list)} signals")
        return {"signals": signals_list, "total": len(signals_list)}
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/news")
async def get_news(
    ticker_symbol: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: Optional[int] = 50
):
    """Get REAL news from NewsCollector"""
    try:
        print(f"📡 GET /api/v1/news (ticker={ticker_symbol}, limit={limit})")
        
        if not news_collector:
            print("⚠️ NewsCollector not initialized, using mock")
            return {"news": [], "total": 0}
        
        # Collect real news for all tickers or specific one
        all_news = []
        
        tickers_to_fetch = [ticker_symbol] if ticker_symbol else [t['symbol'] for t in TICKERS]
        
        for ticker in tickers_to_fetch:
            ticker_info = next((t for t in TICKERS if t['symbol'] == ticker), None)
            if not ticker_info:
                continue
            
            print(f"📰 Fetching news for {ticker}...")
            
            # REAL API CALL
            news_items = news_collector.collect_news(
                ticker_symbol=ticker,
                company_name=ticker_info['name'],
                lookback_hours=24
            )
            
            print(f"✅ Got {len(news_items)} news for {ticker}")
            
            # Convert NewsItem objects to dict
            for idx, news_item in enumerate(news_items):
                news_dict = {
                    "id": len(all_news) + idx + 1,
                    "title": news_item.title,
                    "description": news_item.description or news_item.title,
                    "url": news_item.url,
                    "source": news_item.source,
                    "published_at": news_item.published_at.isoformat() + "Z",
                    "sentiment_score": float(news_item.sentiment_score),
                    "sentiment_confidence": float(news_item.sentiment_confidence),
                    "sentiment_label": news_item.sentiment_label,
                    "ticker_symbol": ticker,
                    "categories": getattr(news_item, 'categories', []),
                    "credibility": float(getattr(news_item, 'credibility', 0.8))
                }
                all_news.append(news_dict)
        
        # Filter by sentiment if specified
        if sentiment and sentiment != 'all':
            all_news = [n for n in all_news if n['sentiment_label'] == sentiment]
        
        # Limit and sort
        all_news = sorted(all_news, key=lambda x: x['published_at'], reverse=True)[:limit]
        
        print(f"✅ Returning {len(all_news)} REAL news items from NewsAPI/AlphaVantage")
        
        return {
            "news": all_news,
            "total": len(all_news)
        }
        
    except Exception as e:
        print(f"❌ Error in get_news: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting TrendSignal FastAPI backend...")
    print("📊 Signals: REAL analysis")
    print("📰 News: REAL data from NewsAPI + Alpha Vantage")
    uvicorn.run(app, host="0.0.0.0", port=8000)
