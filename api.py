"""
TrendSignal MVP - Complete Working API with Database Integration
All endpoints functional with SQLite persistence
"""

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from config_api import router as config_router
from signals_api import router as signals_router
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import datetime, timedelta
import sys
import os
import numpy as np
import json

sys.path.insert(0, os.path.dirname(__file__))
from main import run_analysis, run_batch_analysis, get_config

# Database imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from src.database import get_db, SessionLocal
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

# Config API endpoints
app.include_router(config_router)
app.include_router(signals_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def to_python(val):
    """Convert numpy types to Python native types"""
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    return val

def save_signal_to_db(signal, db: Session):
    """Save generated signal to database"""
    try:
        # Get ticker from database
        ticker = db.query(Ticker).filter(Ticker.symbol == signal.ticker_symbol).first()
        if not ticker:
            # Create ticker if doesn't exist
            ticker = Ticker(
                symbol=signal.ticker_symbol,
                name=signal.ticker_name if hasattr(signal, 'ticker_name') else signal.ticker_symbol,
                is_active=True
            )
            db.add(ticker)
            db.commit()
            db.refresh(ticker)
        
        # Create reasoning JSON
        reasoning = {
            "sentiment": {
                "summary": f"Sentiment score: {signal.sentiment_score:.1f}",
                "score": to_python(signal.sentiment_score)
            },
            "technical": {
                "summary": f"Technical score: {signal.technical_score:.1f}",
                "score": to_python(signal.technical_score)
            },
            "risk": {
                "summary": f"Risk score: {signal.risk_score:.1f}",
                "score": to_python(signal.risk_score)
            }
        }
        
        # Create signal record
        db_signal = Signal(
            ticker_id=ticker.id,
            ticker_symbol=signal.ticker_symbol,
            decision=str(signal.decision),
            strength=str(signal.strength),
            combined_score=to_python(signal.combined_score),
            sentiment_score=to_python(signal.sentiment_score),
            technical_score=to_python(signal.technical_score),
            risk_score=to_python(signal.risk_score),
            overall_confidence=to_python(signal.overall_confidence),
            sentiment_confidence=to_python(getattr(signal, 'sentiment_confidence', 0.5)),
            technical_confidence=to_python(getattr(signal, 'technical_confidence', 0.5)),
            entry_price=to_python(signal.entry_price) if signal.entry_price else None,
            stop_loss=to_python(signal.stop_loss) if signal.stop_loss else None,
            take_profit=to_python(signal.take_profit) if signal.take_profit else None,
            risk_reward_ratio=to_python(signal.risk_reward_ratio) if signal.risk_reward_ratio else None,
            reasoning_json=json.dumps(reasoning),
            status='active',
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        db.add(db_signal)
        db.commit()
        db.refresh(db_signal)
        
        return db_signal
        
    except Exception as e:
        print(f"❌ Error saving signal to DB: {e}")
        db.rollback()
        return None

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
    """Get all tickers from database"""
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

@app.get("/api/v1/signals")
async def get_signals(
    status: Optional[str] = "active",
    limit: Optional[int] = 50,
    db: Session = Depends(get_db)
):
    """Get signals - from database if available, otherwise generate"""
    try:
        # Try to get signals from database
        query = db.query(Signal)
        
        if status and status != "all":
            query = query.filter(Signal.status == status)
        
        db_signals = query.order_by(Signal.created_at.desc()).limit(limit).all()
        
        # If no signals in DB, generate them
        if not db_signals:
            print("📊 No signals in DB, generating new ones...")
            tickers = db.query(Ticker).filter(Ticker.is_active == True).limit(limit).all()
            ticker_list = [{'symbol': t.symbol, 'name': t.name} for t in tickers]
            
            signals_data = run_batch_analysis(ticker_list)
            
            # Save to database
            for signal in signals_data:
                save_signal_to_db(signal, db)
            
            # Fetch from DB
            db_signals = query.order_by(Signal.created_at.desc()).limit(limit).all()
        
        # Format response
        signals_list = []
        for signal in db_signals:
            reasoning = json.loads(signal.reasoning_json) if signal.reasoning_json else {}
            
            api_signal = {
                "id": signal.id,
                "ticker_symbol": signal.ticker_symbol,
                "decision": signal.decision,
                "strength": signal.strength,
                "combined_score": float(signal.combined_score),
                "overall_confidence": float(signal.overall_confidence),
                "sentiment_score": float(signal.sentiment_score),
                "technical_score": float(signal.technical_score),
                "risk_score": float(signal.risk_score),
                "entry_price": float(signal.entry_price) if signal.entry_price else 0.0,
                "stop_loss": float(signal.stop_loss) if signal.stop_loss else 0.0,
                "take_profit": float(signal.take_profit) if signal.take_profit else 0.0,
                "risk_reward_ratio": float(signal.risk_reward_ratio) if signal.risk_reward_ratio else 1.0,
                "reasoning": reasoning,
                "created_at": signal.created_at.isoformat() + "Z",
                "expires_at": signal.expires_at.isoformat() + "Z" if signal.expires_at else None,
                "status": signal.status
            }
            signals_list.append(api_signal)
        
        return {"signals": signals_list, "total": len(signals_list)}
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/signals/{ticker_symbol}")
async def get_signal_by_ticker(
    ticker_symbol: str,
    db: Session = Depends(get_db)
):
    """Get latest signal for specific ticker"""
    try:
        # Try database first
        db_signal = db.query(Signal).filter(
            Signal.ticker_symbol == ticker_symbol.upper(),
            Signal.status == 'active'
        ).order_by(Signal.created_at.desc()).first()
        
        # If not in DB, generate new signal
        if not db_signal:
            print(f"📊 Generating new signal for {ticker_symbol}...")
            ticker = db.query(Ticker).filter(Ticker.symbol == ticker_symbol.upper()).first()
            
            if not ticker:
                raise HTTPException(status_code=404, detail="Ticker not found")
            
            signal = run_analysis(
                ticker_symbol=ticker.symbol,
                ticker_name=ticker.name
            )
            
            # Save to DB
            db_signal = save_signal_to_db(signal, db)
            
            if not db_signal:
                raise HTTPException(status_code=500, detail="Failed to save signal")
        
        # Format response
        reasoning = json.loads(db_signal.reasoning_json) if db_signal.reasoning_json else {}
        
        return {
            "id": db_signal.id,
            "ticker_symbol": db_signal.ticker_symbol,
            "decision": db_signal.decision,
            "strength": db_signal.strength,
            "combined_score": float(db_signal.combined_score),
            "overall_confidence": float(db_signal.overall_confidence),
            "sentiment_score": float(db_signal.sentiment_score),
            "technical_score": float(db_signal.technical_score),
            "risk_score": float(db_signal.risk_score),
            "entry_price": float(db_signal.entry_price) if db_signal.entry_price else 0.0,
            "stop_loss": float(db_signal.stop_loss) if db_signal.stop_loss else 0.0,
            "take_profit": float(db_signal.take_profit) if db_signal.take_profit else 0.0,
            "risk_reward_ratio": float(db_signal.risk_reward_ratio) if db_signal.risk_reward_ratio else 1.0,
            "reasoning": reasoning,
            "created_at": db_signal.created_at.isoformat() + "Z",
            "expires_at": db_signal.expires_at.isoformat() + "Z" if db_signal.expires_at else None,
            "status": db_signal.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/signals/generate")
async def generate_signals(db: Session = Depends(get_db)):
    """Generate fresh signals for all active tickers"""
    try:
        tickers = db.query(Ticker).filter(Ticker.is_active == True).all()
        ticker_list = [{'symbol': t.symbol, 'name': t.name} for t in tickers]
        
        print(f"📊 Generating signals for {len(ticker_list)} tickers...")
        signals_data = run_batch_analysis(ticker_list)
        
        saved_count = 0
        for signal in signals_data:
            if save_signal_to_db(signal, db):
                saved_count += 1
        
        return {
            "message": f"Generated {len(signals_data)} signals",
            "saved": saved_count,
            "tickers": [s.ticker_symbol for s in signals_data]
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
