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
from src.signals_api import router as signals_router
from tickers_api import router as tickers_router  # ✅ Ticker management
from simulated_trades_api import router as simulated_trades_router  # ✅ NEW: Simulated Trades (Trackback)
from optimizer_api import router as optimizer_router  # ✅ Self-Tuning Engine
from bcd_api import router as bcd_router              # ✅ BCD Optimizer
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

# Import daily simulate+migrate job
from src.backtest_service import BacktestService
from src.models import SimulatedTrade, Signal
from src.live_to_archive_migrator import (
    migrate_closed_trade_to_archive,
    migrate_signal_without_trade,
)


def run_daily_simulate_and_migrate():
    """
    Napi 09:08 CET: live backtest futtatása, majd teljes migráció:
      1. Lezárt trade-ek → archive_signals + archive_simulated_trades
      2. Trade nélküli expired/archived signalok → archive_signals
         (recalc-ready: a következő recalculate-and-resimulate fut rájuk)
    Manuális trigger-től függetlenül minden nap lefut.
    """
    logger.info("⏰ [DailyJob] Napi szimuláció + migráció indul...")
    try:
        from src.database import get_db as _get_db
        db = next(_get_db())
        try:
            # Orphan lista BACKTEST ELŐTT: csak az eleve nem-live státuszú
            # signalok kerülnek migrálásra, a backtest által frissen
            # no_data/parallel_skip/stb. státuszra állított BUY/SELL signalok
            # nem vesznek el azonnal (következő szimulációs körben újra próbálhatók).
            _MIGRATABLE = ['expired', 'archived',
                           'skip_hours', 'parallel_skip', 'no_sl_tp',
                           'no_data', 'invalid_levels']
            orphan_ids = [
                s.id for s in db.query(Signal).filter(
                    (Signal.status.in_(_MIGRATABLE)) |
                    ((Signal.status == 'active') & (Signal.decision == 'HOLD'))
                ).all()
            ]

            service = BacktestService(db)
            result = service.run_backtest()
            stats = result.get('stats', {})
            logger.info(f"[DailyJob] Backtest kész: {stats}")
            closed_ids = [
                t.id for t in db.query(SimulatedTrade)
                .filter(SimulatedTrade.status == 'CLOSED').all()
            ]
        finally:
            db.close()

        # 1. Lezárt trade-ek migrálása
        migrated = errors = 0
        for tid in closed_ids:
            try:
                if migrate_closed_trade_to_archive(tid):
                    migrated += 1
            except Exception as e:
                errors += 1
                logger.warning(f"[DailyJob] Trade migráció hiba {tid}: {e}")
        logger.info(
            f"[DailyJob] Trade migráció: {migrated}/{len(closed_ids)}"
            + (f" ({errors} hiba)" if errors else "")
        )

        # 2. Trade nélküli expired/archived signalok migrálása
        migrated_s = errors_s = 0
        for sid in orphan_ids:
            try:
                if migrate_signal_without_trade(sid):
                    migrated_s += 1
            except Exception as e:
                errors_s += 1
                logger.warning(f"[DailyJob] Signal migráció hiba {sid}: {e}")
        logger.info(
            f"[DailyJob] Signal migráció (trade nélkül): {migrated_s}/{len(orphan_ids)}"
            + (f" ({errors_s} hiba)" if errors_s else "")
        )

    except Exception as e:
        logger.error(f"[DailyJob] Fatális hiba: {e}", exc_info=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database imports
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

    # Ensure all tables exist (idempotent: skips already existing tables)
    try:
        from src.database import init_db
        init_db()
        logger.info("✅ Database tables verified/created")
    except Exception as e:
        logger.warning(f"⚠️ init_db failed: {e}")


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

    # Napi 09:08 CET: live backtest + archive migráció
    scheduler.add_job(
        run_daily_simulate_and_migrate,
        trigger=CronTrigger(hour=9, minute=8, timezone="Europe/Budapest"),
        id='daily_simulate_migrate',
        name='Daily Simulate + Archive Migration',
        replace_existing=True,
        max_instances=1,
    )

    # Start scheduler
    scheduler.start()
    logger.info(f"⏰ Scheduler started - Signal refresh every {config.signal_refresh_interval} minutes")
    logger.info(f"   BÉT Hours: {config.bet_market_open}-{config.bet_market_close} {config.bet_timezone}")
    logger.info(f"   US Hours:  {config.us_market_open}-{config.us_market_close} {config.us_timezone}")
    logger.info(f"   Daily Simulate+Migrate: 09:08 CET (minden nap, manuális triggertől függetlenül)")
    
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
app.include_router(optimizer_router)  # ✅ Self-Tuning Engine
app.include_router(bcd_router)        # ✅ BCD Optimizer

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
        from src.models import NewsCategory
        query = db.query(NewsItem)

        # Filter by ticker if specified
        if ticker_symbol:
            query = query.join(NewsTicker, NewsTicker.news_id == NewsItem.id).join(Ticker, Ticker.id == NewsTicker.ticker_id).filter(
                Ticker.symbol == ticker_symbol.upper()
            )

        # Filter by sentiment if specified
        if sentiment and sentiment != 'all':
            query = query.filter(NewsItem.sentiment_label == sentiment)

        # Order by published date and limit
        news_items = query.order_by(NewsItem.published_at.desc()).limit(limit).all()

        # Pre-fetch sources and categories to avoid N+1 and missing relationship issues
        news_ids = [item.id for item in news_items]
        source_ids = list({item.source_id for item in news_items if item.source_id})

        sources_by_id = {}
        if source_ids:
            sources = db.query(NewsSource).filter(NewsSource.id.in_(source_ids)).all()
            sources_by_id = {s.id: s.name for s in sources}

        categories_by_news_id = {}
        if news_ids:
            cats = db.query(NewsCategory).filter(NewsCategory.news_id.in_(news_ids)).all()
            for cat in cats:
                categories_by_news_id.setdefault(cat.news_id, []).append(cat.category)

        # Format response
        news_list = []
        for item in news_items:
            news_list.append({
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "url": item.url,
                "source": sources_by_id.get(item.source_id, "Unknown"),
                "published_at": item.published_at.isoformat() + "Z" if item.published_at else None,
                "sentiment_score": float(item.sentiment_score) if item.sentiment_score else 0.0,
                "sentiment_confidence": float(item.sentiment_confidence) if item.sentiment_confidence else 0.0,
                "sentiment_label": item.sentiment_label,
                "categories": categories_by_news_id.get(item.id, [])
            })

        return {"news": news_list, "total": len(news_list)}

    except Exception as e:
        logger.error(f"❌ Error getting news: {e}")
        import traceback
        traceback.print_exc()
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
