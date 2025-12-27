"""
TrendSignal MVP - FastAPI Backend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from main import run_analysis, run_batch_analysis, get_config

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

def to_python(val):
    """Convert numpy types to Python native types"""
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    return val

@app.on_event("startup")
async def startup_event():
    print("🚀 TrendSignal FastAPI backend started!")
    get_config()
    print("✅ Configuration loaded")

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
                        "factors": ["Volatility and risk analyzed"]
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

@app.get("/api/v1/signals/{ticker_id}")
async def get_signal(ticker_id: int):
    try:
        if ticker_id < 1 or ticker_id > len(TICKERS):
            raise HTTPException(status_code=404, detail="Ticker not found")
        
        ticker = TICKERS[ticker_id - 1]
        signal = run_analysis(ticker_symbol=ticker['symbol'], ticker_name=ticker['name'])
        
        return {
            "id": ticker_id,
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
                "sentiment": {"summary": "Sentiment analysis", "key_news": [], "score": to_python(signal.sentiment_score)},
                "technical": {"summary": "Technical analysis", "key_signals": [], "score": to_python(signal.technical_score)}
            },
            "created_at": datetime.utcnow().isoformat() + "Z",
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat() + "Z",
            "status": "active"
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting TrendSignal FastAPI backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
