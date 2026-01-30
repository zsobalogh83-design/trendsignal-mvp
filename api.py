"""
TrendSignal MVP - Complete Working API with Database Integration
All endpoints functional with SQLite persistence
No duplicate endpoints - signals handled by signals_api router

FIXED: CORS + Host settings for proper frontend connection
"""

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from config_api import router as config_router
from signals_api import router as signals_router
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import sys
import os
import json

sys.path.insert(0, os.path.dirname(__file__))
from main import get_config

# Database imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from src.database import get_db
from src.models import Ticker, Signal, NewsItem, NewsSource, NewsTicker

# Import NewsCollector with fixed datetime handling
try:
    from src.news_collector import NewsCollector
    HAS_NEWS_COLLECTOR = True
    print("✅ NewsCollector imported")
except Exception as e:
    HAS_NEWS_COLLECTOR = False
    print(f"⚠️ NewsCollector not available: {e}")

# Global
news_collector = None

app = FastAPI(title="TrendSignal API", version="0.1.0")

# Include routers (signals_api handles /api/v1/signals/*)
app.include_router(config_router)
app.include_router(signals_router)

# ==========================================
# CORS CONFIGURATION - CRITICAL FOR FRONTEND
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Vite dev server
        "http://127.0.0.1:5173",      # Alternative localhost
        "http://localhost:3000",      # Alternative port
        "http://127.0.0.1:3000",      # Alternative port
        "*"                            # Fallback (development only)
    ],
    allow_credentials=True,
    allow_methods=["*"],              # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],              # Allow all headers
)

@app.on_event("startup")
async def startup_event():
    global news_collector
    print("🚀 TrendSignal FastAPI started!")
    print("📊 Database connection established")
    
    config = get_config()
    
    if HAS_NEWS_COLLECTOR:
        try:
            news_collector = NewsCollector(config)
            print("✅ NewsCollector initialized (English + Hungarian)")
        except Exception as e:
            print(f"⚠️ NewsCollector init failed: {e}")

@app.get("/")
async def root():
    return {
        "status": "ok",
        "version": "0.1.0",
        "database": "connected"
    }

@app.get("/api/v1/tickers")
async def get_tickers(db: Session = Depends(get_db)):
    """Get all active tickers from database"""
    try:
        tickers = db.query(Ticker).filter(Ticker.is_active == True).all()
        
        return {
            "tickers": [
                {
                    "id": ticker.id,
                    "symbol": ticker.symbol,
                    "name": ticker.name,
                    "market": ticker.market,
                    "priority": ticker.priority,
                    "is_active": ticker.is_active
                }
                for ticker in tickers
            ],
            "total": len(tickers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/news")
async def get_news(
    ticker_symbol: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: Optional[int] = 50,
    db: Session = Depends(get_db)
):
    """Get news items from database"""
    try:
        query = db.query(NewsItem)
        
        # Filter by ticker if specified
        if ticker_symbol:
            query = query.join(NewsTicker).join(Ticker).filter(
                Ticker.symbol == ticker_symbol.upper()
            )
        
        # Filter by sentiment if specified
        if sentiment and sentiment != 'all':
            query = query.filter(NewsItem.sentiment_label == sentiment)
        
        # Order by published date and limit
        news_items = query.order_by(NewsItem.published_at.desc()).limit(limit).all()
        
        # Format response
        news_list = []
        for item in news_items:
            news_list.append({
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "url": item.url,
                "source": item.source.name if item.source else "Unknown",
                "published_at": item.published_at.isoformat() + "Z" if item.published_at else None,
                "sentiment_score": float(item.sentiment_score) if item.sentiment_score else 0.0,
                "sentiment_confidence": float(item.sentiment_confidence) if item.sentiment_confidence else 0.0,
                "sentiment_label": item.sentiment_label,
                "categories": [cat.category for cat in item.categories]
            })
        
        return {"news": news_list, "total": len(news_list)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/database/status")
async def database_status(db: Session = Depends(get_db)):
    """Get database status and statistics"""
    try:
        ticker_count = db.query(Ticker).count()
        signal_count = db.query(Signal).count()
        news_count = db.query(NewsItem).count()
        source_count = db.query(NewsSource).count()
        
        active_signals = db.query(Signal).filter(Signal.status == 'active').count()
        
        return {
            "status": "connected",
            "statistics": {
                "tickers": ticker_count,
                "signals": signal_count,
                "active_signals": active_signals,
                "news_items": news_count,
                "news_sources": source_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# MAIN ENTRY POINT - FIXED HOST SETTING
# ==========================================
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting TrendSignal API server...")
    print("📊 Database: SQLite")
    print("🔗 Signals API: Integrated via signals_api router")
    print("=" * 60)
    print("🌐 Server starting on: http://127.0.0.1:8000")
    print("📖 API Documentation: http://127.0.0.1:8000/docs")
    print("✅ Frontend should connect to: http://localhost:8000")
    print("=" * 60)
    
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
