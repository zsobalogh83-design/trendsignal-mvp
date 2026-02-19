"""
TrendSignal MVP - Complete Working API with Database Integration and Scheduler
All endpoints functional with SQLite persistence
No duplicate endpoints - signals handled by signals_api router

FIXED: CORS + Host settings for proper frontend connection
🆕 SCHEDULER: Automated signal generation every 15 minutes during market hours
🆕 TICKERS: Full CRUD via tickers_api router
🆕 TRACKBACK: Simulated trades backtest system
"""

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from config_api import router as config_router
from signals_api import router as signals_router
from tickers_api import router as tickers_router  # ✅ Ticker management
from simulated_trades_api import router as simulated_trades_router  # ✅ NEW: Simulated Trades (Trackback)
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import sys
import os
import json
import logging

# APScheduler imports
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

sys.path.insert(0, os.path.dirname(__file__))
from main import get_config

# Import scheduler functions
from scheduler import generate_signals_for_active_markets

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from database import get_db
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
scheduler = None  # 🆕 APScheduler instance


# ==========================================
# LIFECYCLE MANAGEMENT
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event handler
    Manages scheduler startup and shutdown
    """
    global scheduler, news_collector
    
    # STARTUP
    logger.info("🚀 TrendSignal API starting up...")
    logger.info("📊 Database connection established")
    
    config = get_config()
    
    # Initialize NewsCollector
    if HAS_NEWS_COLLECTOR:
        try:
            news_collector = NewsCollector(config)
            logger.info("✅ NewsCollector initialized (English + Hungarian)")
        except Exception as e:
            logger.warning(f"⚠️ NewsCollector init failed: {e}")
    
    # Initialize APScheduler
    scheduler = AsyncIOScheduler()
    
    # Schedule signal generation every 15 minutes
    # This runs during trading hours only (checked inside the function)
    scheduler.add_job(
        generate_signals_for_active_markets,
        trigger=CronTrigger(minute=f"*/{config.signal_refresh_interval}"),  # Every 15 minutes
        id='signal_refresh',
        name='Automated Signal Generation',
        replace_existing=True,
        max_instances=1  # Prevent overlapping runs
    )
    
    # Start scheduler
    scheduler.start()
    logger.info(f"⏰ Scheduler started - Signal refresh every {config.signal_refresh_interval} minutes")
    logger.info(f"   BÉT Hours: {config.bet_market_open}-{config.bet_market_close} {config.bet_timezone}")
    logger.info(f"   US Hours:  {config.us_market_open}-{config.us_market_close} {config.us_timezone}")
    
    yield  # Application runs here
    
    # SHUTDOWN
    logger.info("🛑 TrendSignal API shutting down...")
    
    # Shutdown scheduler
    if scheduler:
        scheduler.shutdown(wait=True)
        logger.info("⏰ Scheduler stopped")


app = FastAPI(
    title="TrendSignal API", 
    version="0.2.0",  # ✅ Bumped version for Trackback feature
    lifespan=lifespan  # 🆕 Use lifespan for startup/shutdown
)

# Include routers
app.include_router(config_router)
app.include_router(signals_router)
app.include_router(tickers_router)  # ✅ Ticker CRUD endpoints
app.include_router(simulated_trades_router)  # ✅ NEW: Trackback System

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

@app.get("/")
async def root():
    return {
        "status": "ok",
        "version": "0.2.0",
        "database": "connected",
        "scheduler_status": "active" if scheduler and scheduler.running else "inactive",
        "features": {
            "signals": "enabled",
            "tickers": "enabled",
            "trackback": "enabled"  # ✅ NEW
        }
    }

# ✅ OLD /api/v1/tickers endpoint REMOVED - now handled by tickers_router

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
        # Import SimulatedTrade for stats
        from src.models import SimulatedTrade
        
        ticker_count = db.query(Ticker).count()
        signal_count = db.query(Signal).count()
        news_count = db.query(NewsItem).count()
        source_count = db.query(NewsSource).count()
        
        active_signals = db.query(Signal).filter(Signal.status == 'active').count()
        
        # ✅ NEW: Simulated trades stats
        total_trades = db.query(SimulatedTrade).count()
        open_trades = db.query(SimulatedTrade).filter(SimulatedTrade.status == 'OPEN').count()
        closed_trades = db.query(SimulatedTrade).filter(SimulatedTrade.status == 'CLOSED').count()
        
        return {
            "status": "connected",
            "statistics": {
                "tickers": ticker_count,
                "signals": signal_count,
                "active_signals": active_signals,
                "news_items": news_count,
                "news_sources": source_count,
                "simulated_trades": {  # ✅ NEW
                    "total": total_trades,
                    "open": open_trades,
                    "closed": closed_trades
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint with scheduler status"""
    config = get_config()
    
    return {
        "status": "healthy",
        "scheduler": {
            "running": scheduler.running if scheduler else False,
            "refresh_interval": f"{config.signal_refresh_interval} minutes",
            "next_run": str(scheduler.get_jobs()[0].next_run_time) if scheduler and scheduler.get_jobs() else None
        },
        "markets": {
            "bet": {
                "hours": f"{config.bet_market_open}-{config.bet_market_close}",
                "timezone": config.bet_timezone,
                "tickers": config.bet_tickers
            },
            "us": {
                "hours": f"{config.us_market_open}-{config.us_market_close}",
                "timezone": config.us_timezone,
                "tickers": config.us_tickers
            }
        }
    }


@app.get("/scheduler/status")
async def scheduler_status():
    """Get scheduler status and next run times"""
    if not scheduler:
        return {"error": "Scheduler not initialized"}
    
    jobs = scheduler.get_jobs()
    
    return {
        "running": scheduler.running,
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time),
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    }


# ==========================================
# MAIN ENTRY POINT - FIXED HOST SETTING
# ==========================================
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting TrendSignal API server...")
    print("📊 Database: SQLite")
    print("🔗 Signals API: Integrated via signals_api router")
    print("📊 Tickers API: Integrated via tickers_api router")
    print("📈 Trackback API: Integrated via simulated_trades_api router")  # ✅ NEW
    print("⏰ Scheduler: Auto signal refresh every 15 minutes")
    print("=" * 60)
    print("🌐 Server starting on: http://127.0.0.1:8000")
    print("📖 API Documentation: http://127.0.0.1:8000/docs")
    print("✅ Frontend should connect to: http://localhost:8000")
    print("=" * 60)
    print("")
    print("🆕 NEW ENDPOINTS:")
    print("   POST /api/v1/simulated-trades/backtest")
    print("   GET  /api/v1/simulated-trades/")
    print("   GET  /api/v1/simulated-trades/{id}")
    print("   GET  /api/v1/simulated-trades/stats/summary")
    print("=" * 60)
    
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
