"""
TrendSignal - Simulated Trades API
FastAPI endpoints for trade simulation and backtest

Version: 1.0
Date: 2026-02-17
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

from src.database import get_db
from src.models import SimulatedTrade, Signal
from src.backtest_service import BacktestService
from src.price_service import PriceService
from src.archive_backtest_service import ArchiveBacktestService
from src.live_to_archive_migrator import (
    migrate_closed_trade_to_archive,
    migrate_signal_without_trade,
)
import sqlite3
import os
import logging
import threading
import time

logger = logging.getLogger(__name__)

# ── Háttérfeladat állapot ────────────────────────────────────────────────────
# Egyetlen globális state — egyszerre csak egy recalc futhat
_task_lock = threading.Lock()
_task: dict = {
    "running": False,
    "phase": None,          # "recalc" | "backtest" | "done" | "error"
    "current_ticker": None,
    "ticker_index": 0,
    "ticker_total": 0,
    "recalc_stats": None,
    "backtest_stats": None,
    "error": None,
    "started_at": None,
    "finished_at": None,
    "elapsed_seconds": None,
}

router = APIRouter(prefix="/api/v1/simulated-trades", tags=["Simulated Trades"])


# ==========================================
# REQUEST/RESPONSE MODELS
# ==========================================

class BacktestRequest(BaseModel):
    """Request model for backtest"""
    date_from: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    symbols: Optional[List[str]] = Field(None, description="Ticker symbols to filter")


class BacktestResponse(BaseModel):
    """Response model for backtest"""
    status: str
    execution_time_seconds: float
    stats: dict


class TradeResponse(BaseModel):
    """Response model for single trade"""
    id: int
    symbol: str
    direction: str
    status: str
    entry_price: float
    entry_execution_time: str
    entry_score: float
    entry_confidence: float
    stop_loss_price: float
    take_profit_price: float
    exit_price: Optional[float]
    exit_execution_time: Optional[str]
    exit_reason: Optional[str]
    pnl_percent: Optional[float]
    pnl_amount_huf: Optional[float]
    duration_minutes: Optional[int]
    created_at: str


class TradeListResponse(BaseModel):
    """Response model for trade list"""
    trades: List[TradeResponse]
    total: int
    offset: int
    limit: int


class TradeStatsResponse(BaseModel):
    """Response model for trade statistics"""
    total_trades: int
    open_trades: int
    closed_trades: int
    profitable_trades: int
    loss_trades: int
    win_rate: float
    total_pnl_huf: float
    avg_pnl_percent: float
    avg_duration_minutes: float


# ==========================================
# ENDPOINTS
# ==========================================

@router.post("/backtest", response_model=BacktestResponse)
def run_backtest(
    request: BacktestRequest,
    db: Session = Depends(get_db)
):
    """
    Run incremental backtest on historical signals.

    - Already CLOSED trades: skipped (never modified)
    - OPEN trades: exit triggers checked, SL/TP updated
    - Missing trades: created fresh

    **Example:**
    ```json
    {
      "date_from": "2026-02-01",
      "date_to": "2026-02-17",
      "symbols": ["AAPL", "TSLA"]
    }
    ```
    """
    try:
        # Parse dates
        date_from = None
        date_to = None

        if request.date_from:
            date_from = datetime.strptime(request.date_from, "%Y-%m-%d")

        if request.date_to:
            # Include the full day: parse to end-of-day (23:59:59)
            date_to = datetime.strptime(request.date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )

        # ── Orphan signal lista BACKTEST ELŐTT összeállítva ─────────────────
        # Fontos: csak a már eleve nem-live státuszú signalokat migráljuk.
        # Ha a lista a backtest UTÁN kerülne összeállításra, a backtest által
        # frissen no_data / parallel_skip / no_sl_tp státuszra állított
        # aktív BUY/SELL signalok is belekerülnének és azonnal archive-ba
        # kerülnének (elveszítenék a következő szimulációs újrapróbálkozás
        # lehetőségét).
        _MIGRATABLE = ['expired', 'archived',
                       'skip_hours', 'parallel_skip', 'no_sl_tp',
                       'no_data', 'invalid_levels']
        orphan_ids = [
            s.id for s in db.query(Signal).filter(
                (Signal.status.in_(_MIGRATABLE)) |
                ((Signal.status == 'active') & (Signal.decision == 'HOLD'))
            ).all()
        ]

        # Run backtest
        service = BacktestService(db)
        result = service.run_backtest(
            date_from=date_from,
            date_to=date_to,
            symbols=request.symbols,
        )

        # Lezárt trade-ek migrálása archive táblákba
        closed_ids = [
            t.id for t in db.query(SimulatedTrade)
            .filter(SimulatedTrade.status == 'CLOSED').all()
        ]
        migrated = migration_errors = 0
        for tid in closed_ids:
            try:
                if migrate_closed_trade_to_archive(tid):
                    migrated += 1
            except Exception as mig_err:
                migration_errors += 1
                logger.debug(f"[Migration] Trade {tid} error: {mig_err}")
        if migrated > 0 or migration_errors > 0:
            logger.info(
                f"[Migration] {migrated}/{len(closed_ids)} trade áthelyezve archive-ba"
                + (f" ({migration_errors} hiba)" if migration_errors else "")
            )
        migrated_signals = signal_errors = 0
        for sid in orphan_ids:
            try:
                if migrate_signal_without_trade(sid):
                    migrated_signals += 1
            except Exception as sig_err:
                signal_errors += 1
                logger.debug(f"[Migration] Signal {sid} error: {sig_err}")
        if migrated_signals > 0 or signal_errors > 0:
            logger.info(
                f"[Migration] {migrated_signals}/{len(orphan_ids)} signal (trade nélkül) → archive"
                + (f" ({signal_errors} hiba)" if signal_errors else "")
            )

        return {
            "status": "completed",
            "execution_time_seconds": result['execution_time_seconds'],
            "stats": result['stats']
        }

    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=TradeListResponse)
def get_trades(
    symbol: Optional[str] = Query(None, description="Filter by ticker symbol"),
    status: Optional[str] = Query(None, description="Filter by status (OPEN/CLOSED)"),
    direction: Optional[str] = Query(None, description="Filter by direction (LONG/SHORT)"),
    exit_reason: Optional[str] = Query(None, description="Filter by exit reason"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db)
):
    """
    Get list of simulated trades with filters and pagination.
    
    **Filters:**
    - `symbol`: AAPL, TSLA, etc.
    - `status`: OPEN, CLOSED
    - `direction`: LONG, SHORT
    - `exit_reason`: SL_HIT, TP_HIT, OPPOSING_SIGNAL, EOD_AUTO_LIQUIDATION
    """
    query = db.query(SimulatedTrade)
    
    # Apply filters
    if symbol:
        query = query.filter(SimulatedTrade.symbol == symbol)
    
    if status:
        query = query.filter(SimulatedTrade.status == status)
    
    if direction:
        query = query.filter(SimulatedTrade.direction == direction)
    
    if exit_reason:
        query = query.filter(SimulatedTrade.exit_reason == exit_reason)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and order
    trades = query.order_by(
        SimulatedTrade.entry_execution_time.desc()
    ).offset(offset).limit(limit).all()
    
    # Convert to response model
    trade_list = []
    for trade in trades:
        trade_list.append({
            "id": trade.id,
            "symbol": trade.symbol,
            "direction": trade.direction,
            "status": trade.status,
            "entry_price": trade.entry_price,
            "entry_execution_time": trade.entry_execution_time.isoformat(),
            "entry_score": trade.entry_score,
            "entry_confidence": trade.entry_confidence,
            "stop_loss_price": trade.stop_loss_price,
            "take_profit_price": trade.take_profit_price,
            "exit_price": trade.exit_price,
            "exit_execution_time": trade.exit_execution_time.isoformat() if trade.exit_execution_time else None,
            "exit_reason": trade.exit_reason,
            "pnl_percent": trade.pnl_percent,
            "pnl_amount_huf": trade.pnl_amount_huf,
            "duration_minutes": trade.duration_minutes,
            "created_at": trade.created_at.isoformat()
        })
    
    return {
        "trades": trade_list,
        "total": total,
        "offset": offset,
        "limit": limit
    }


@router.get("/stats/summary", response_model=TradeStatsResponse)
def get_trade_stats(
    symbol: Optional[str] = Query(None, description="Filter by ticker symbol"),
    db: Session = Depends(get_db)
):
    """
    Get aggregate statistics for simulated trades.

    Returns win rate, total P&L, average duration, etc.
    """
    query = db.query(SimulatedTrade)

    if symbol:
        query = query.filter(SimulatedTrade.symbol == symbol)

    all_trades = query.all()

    if not all_trades:
        return {
            "total_trades": 0,
            "open_trades": 0,
            "closed_trades": 0,
            "profitable_trades": 0,
            "loss_trades": 0,
            "win_rate": 0.0,
            "total_pnl_huf": 0.0,
            "avg_pnl_percent": 0.0,
            "avg_duration_minutes": 0.0
        }

    # Calculate statistics
    total_trades = len(all_trades)
    open_trades = sum(1 for t in all_trades if t.status == 'OPEN')
    closed_trades = sum(1 for t in all_trades if t.status == 'CLOSED')

    closed_list = [t for t in all_trades if t.status == 'CLOSED']

    if closed_list:
        profitable_trades = sum(1 for t in closed_list if t.pnl_percent and t.pnl_percent > 0)
        loss_trades = sum(1 for t in closed_list if t.pnl_percent and t.pnl_percent <= 0)
        win_rate = (profitable_trades / closed_trades) * 100 if closed_trades > 0 else 0

        total_pnl_huf = sum(t.pnl_amount_huf for t in closed_list if t.pnl_amount_huf)
        avg_pnl_percent = sum(t.pnl_percent for t in closed_list if t.pnl_percent) / closed_trades
        avg_duration = sum(t.duration_minutes for t in closed_list if t.duration_minutes) / closed_trades
    else:
        profitable_trades = 0
        loss_trades = 0
        win_rate = 0.0
        total_pnl_huf = 0.0
        avg_pnl_percent = 0.0
        avg_duration = 0.0

    return {
        "total_trades": total_trades,
        "open_trades": open_trades,
        "closed_trades": closed_trades,
        "profitable_trades": profitable_trades,
        "loss_trades": loss_trades,
        "win_rate": round(win_rate, 2),
        "total_pnl_huf": round(total_pnl_huf, 2),
        "avg_pnl_percent": round(avg_pnl_percent, 2),
        "avg_duration_minutes": round(avg_duration, 2)
    }


@router.get("/open-pnl")
def get_open_pnl(
    db: Session = Depends(get_db)
):
    """
    Get unrealized P&L for all currently OPEN simulated trades.

    Fetches the current market price for each open position and calculates
    the unrealized P&L percent relative to the entry price.

    Returns a dict keyed by trade_id:
        { trade_id: { current_price, unrealized_pnl_percent } }
    """
    open_trades = db.query(SimulatedTrade).filter(
        SimulatedTrade.status == 'OPEN'
    ).all()

    if not open_trades:
        return {}

    price_service = PriceService()
    result = {}

    # Fetch prices per unique symbol (avoid duplicate yfinance calls)
    prices: dict = {}
    for trade in open_trades:
        if trade.symbol not in prices:
            try:
                price = price_service.get_current_price(trade.symbol)
                prices[trade.symbol] = price
            except Exception as e:
                logger.warning(f"Could not fetch price for {trade.symbol}: {e}")
                prices[trade.symbol] = None

    for trade in open_trades:
        current_price = prices.get(trade.symbol)
        if current_price is None:
            result[trade.id] = {"current_price": None, "unrealized_pnl_percent": None, "unrealized_pnl_huf": None}
            continue

        if trade.direction == 'LONG':
            pnl_pct = (current_price - trade.entry_price) / trade.entry_price * 100
            pnl_per_share = current_price - trade.entry_price
        else:  # SHORT
            pnl_pct = (trade.entry_price - current_price) / trade.entry_price * 100
            pnl_per_share = trade.entry_price - current_price

        shares = trade.position_size_shares or 0
        usd_huf = trade.usd_huf_rate
        pnl_amount = pnl_per_share * shares
        pnl_huf = round(pnl_amount * usd_huf if usd_huf else pnl_amount, 0)

        result[trade.id] = {
            "current_price": round(current_price, 4),
            "unrealized_pnl_percent": round(pnl_pct, 4),
            "unrealized_pnl_huf": pnl_huf,
        }

    return result


# ==========================================
# ARCHIVE BACKTEST ENDPOINTS
# ==========================================

class ArchiveBacktestRequest(BaseModel):
    symbols: Optional[List[str]] = Field(None, description="Ticker symbols (None = összes)")
    score_threshold: float = Field(15.0, description="Minimum |combined_score|")


@router.post("/archive-backtest")
def run_archive_backtest(request: ArchiveBacktestRequest):
    """
    Futtatja a visszamenőleges szimulációt az archive_signals adatain.
    Eredmény az archive_simulated_trades táblába kerül.
    Korábbi eredmények törlődnek (teljes újrafuttatás).
    """
    import time
    try:
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trendsignal.db")
        service = ArchiveBacktestService(db_path)
        t0 = time.time()
        stats = service.run(
            symbols=request.symbols,
            score_threshold=request.score_threshold,
        )
        elapsed = round(time.time() - t0, 2)
        return {"status": "ok", "execution_time_seconds": elapsed, "stats": stats}
    except Exception as e:
        logger.error(f"Archive backtest error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recalculate-and-resimulate")
def recalculate_and_resimulate(request: ArchiveBacktestRequest):
    """
    Kétlépéses pipeline (háttérszálon fut, azonnal visszatér):
    1. archive_signals score-ok újraszámolása az aktuális config alapján
    2. archive_simulated_trades újragenerálása a frissített score-okból

    Progress követéshez: GET /recalculate-status
    """
    global _task
    with _task_lock:
        if _task["running"]:
            raise HTTPException(
                status_code=409,
                detail="Már fut egy recalculate folyamat. Várj amíg befejezi, vagy kövesd: GET /recalculate-status"
            )
        _task = {
            "running": True,
            "phase": "recalc",
            "current_ticker": None,
            "ticker_index": 0,
            "ticker_total": 0,
            "recalc_stats": None,
            "backtest_stats": None,
            "error": None,
            "started_at": datetime.utcnow().isoformat(),
            "finished_at": None,
            "elapsed_seconds": None,
        }

    def _run():
        global _task
        t0 = time.time()
        try:
            from src.signal_recalculator import SignalRecalculator
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trendsignal.db")

            # ── Step 1: recalculate component scores ────────────────────────
            def recalc_progress(ticker, idx, total):
                with _task_lock:
                    _task["phase"] = "recalc"
                    _task["current_ticker"] = ticker
                    _task["ticker_index"] = idx
                    _task["ticker_total"] = total

            recalc = SignalRecalculator(db_path)
            recalc_stats = recalc.run(
                symbols=request.symbols,
                progress_callback=recalc_progress,
            )
            with _task_lock:
                _task["recalc_stats"] = recalc_stats
                _task["phase"] = "backtest"
                _task["current_ticker"] = None
                _task["ticker_index"] = 0
                _task["ticker_total"] = 0

            # ── Step 2: re-simulate trades ───────────────────────────────────
            def backtest_progress(ticker, idx, total):
                with _task_lock:
                    _task["phase"] = "backtest"
                    _task["current_ticker"] = ticker
                    _task["ticker_index"] = idx
                    _task["ticker_total"] = total

            backtest = ArchiveBacktestService(db_path)
            backtest_stats = backtest.run(
                symbols=request.symbols,
                score_threshold=request.score_threshold,
                progress_callback=backtest_progress,
            )

            elapsed = round(time.time() - t0, 2)
            with _task_lock:
                _task["running"] = False
                _task["phase"] = "done"
                _task["backtest_stats"] = backtest_stats
                _task["finished_at"] = datetime.utcnow().isoformat()
                _task["elapsed_seconds"] = elapsed
                _task["current_ticker"] = None

        except Exception as e:
            logger.error(f"Recalculate+resimulate error: {e}", exc_info=True)
            with _task_lock:
                _task["running"] = False
                _task["phase"] = "error"
                _task["error"] = str(e)
                _task["finished_at"] = datetime.utcnow().isoformat()
                _task["elapsed_seconds"] = round(time.time() - t0, 2)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {"status": "started", "message": "Recalculate+resimulate elindult. Kövesd: GET /recalculate-status"}


@router.get("/recalculate-status")
def get_recalculate_status():
    """
    Visszaadja az aktuálisan futó (vagy utoljára befejezett) recalculate folyamat állapotát.

    phase értékek:
    - "recalc"   → archive_signals score-ok újraszámolása
    - "backtest" → archive_simulated_trades újragenerálása
    - "done"     → sikeresen befejezett
    - "error"    → hiba (error mező tartalmazza)
    - null       → még nem indult el semmi
    """
    with _task_lock:
        return dict(_task)


@router.get("/archive/stats")
def get_archive_stats(
    symbol: Optional[str] = Query(None),
    real_only: bool = Query(False, description="Csak is_real_trade=1 eredmények"),
):
    """Archive szimulációs statisztikák."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trendsignal.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        where = ["status = 'CLOSED'"]
        params: list = []
        if symbol:
            where.append("ticker_symbol = ?")
            params.append(symbol)
        if real_only:
            where.append("is_real_trade = 1")
        w = " AND ".join(where)

        row = conn.execute(f"""
            SELECT
                COUNT(*)                                          AS total,
                SUM(CASE WHEN pnl_percent > 0 THEN 1 ELSE 0 END) AS wins,
                SUM(CASE WHEN pnl_percent <= 0 THEN 1 ELSE 0 END) AS losses,
                AVG(pnl_percent)                                  AS avg_pnl,
                SUM(CASE WHEN exit_reason='TP_HIT'   THEN 1 ELSE 0 END) AS tp_hit,
                SUM(CASE WHEN exit_reason='SL_HIT'   THEN 1 ELSE 0 END) AS sl_hit,
                SUM(CASE WHEN exit_reason='OPPOSING_SIGNAL' THEN 1 ELSE 0 END) AS opposing,
                SUM(CASE WHEN exit_reason='MAX_HOLD_LIQUIDATION' THEN 1 ELSE 0 END) AS max_hold,
                AVG(duration_bars)                                AS avg_bars,
                COUNT(CASE WHEN direction='LONG'  THEN 1 END)    AS long_count,
                COUNT(CASE WHEN direction='SHORT' THEN 1 END)    AS short_count
            FROM archive_simulated_trades WHERE {w}
        """, params).fetchone()

        open_count = conn.execute(
            f"SELECT COUNT(*) FROM archive_simulated_trades WHERE status='OPEN'"
            + (f" AND ticker_symbol=?" if symbol else ""),
            ([symbol] if symbol else []),
        ).fetchone()[0]

        total = row["total"] or 0
        wins  = row["wins"]  or 0
        return {
            "total_closed": total,
            "total_open":   open_count,
            "wins":   wins,
            "losses": row["losses"] or 0,
            "win_rate": round(wins / total * 100, 1) if total else 0,
            "avg_pnl_percent": round(row["avg_pnl"] or 0, 3),
            "tp_hit":   row["tp_hit"]   or 0,
            "sl_hit":   row["sl_hit"]   or 0,
            "opposing": row["opposing"] or 0,
            "max_hold": row["max_hold"] or 0,
            "avg_duration_bars": round(row["avg_bars"] or 0, 1),
            "long_count":  row["long_count"]  or 0,
            "short_count": row["short_count"] or 0,
        }
    finally:
        conn.close()


@router.get("/archive/signal/{signal_id}")
def get_archive_trade_by_signal(signal_id: int):
    """Visszaadja az adott archive_signal_id-hez tartozó szimulált trade-et."""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trendsignal.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM archive_simulated_trades WHERE archive_signal_id = ?",
            (signal_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Nincs szimulált trade ehhez a signalhoz")
        return dict(row)
    finally:
        conn.close()


@router.delete("/archive/clear")
def clear_archive_trades(confirm: str = Query(...)):
    """Törli az összes archive szimulált trade-et."""
    if confirm != "yes":
        raise HTTPException(status_code=400, detail="Add hozzá: ?confirm=yes")
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trendsignal.db")
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("DELETE FROM archive_simulated_trades")
        count = conn.execute("SELECT changes()").fetchone()[0]
        conn.commit()
        return {"status": "ok", "deleted": count}
    finally:
        conn.close()


@router.delete("/clear")
def clear_all_trades(
    confirm: str = Query(..., description="Must be 'yes' to confirm deletion"),
    db: Session = Depends(get_db)
):
    """
    Delete all simulated trades (DANGEROUS).
    
    Requires `confirm=yes` query parameter.
    """
    if confirm != "yes":
        raise HTTPException(
            status_code=400,
            detail="Confirmation required. Add ?confirm=yes to the request"
        )
    
    count = db.query(SimulatedTrade).count()
    db.query(SimulatedTrade).delete()
    db.commit()
    
    return {
        "status": "success",
        "deleted_trades": count,
        "message": f"Deleted {count} simulated trades"
    }


# ── FONTOS: /{trade_id} catch-all route — mindig az összes specifikus route UTÁN kell! ──
# FastAPI sorban egyezteti a route-okat; ha ez előbb lenne, a /recalculate-status és
# /archive/* URL-eket is megpróbálná trade_id (int) paraméterként értelmezni → 422.
@router.get("/{trade_id}", response_model=TradeResponse)
def get_trade(
    trade_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information for a single trade.
    """
    trade = db.query(SimulatedTrade).filter(SimulatedTrade.id == trade_id).first()

    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "direction": trade.direction,
        "status": trade.status,
        "entry_price": trade.entry_price,
        "entry_execution_time": trade.entry_execution_time.isoformat(),
        "entry_score": trade.entry_score,
        "entry_confidence": trade.entry_confidence,
        "stop_loss_price": trade.stop_loss_price,
        "take_profit_price": trade.take_profit_price,
        "exit_price": trade.exit_price,
        "exit_execution_time": trade.exit_execution_time.isoformat() if trade.exit_execution_time else None,
        "exit_reason": trade.exit_reason,
        "pnl_percent": trade.pnl_percent,
        "pnl_amount_huf": trade.pnl_amount_huf,
        "duration_minutes": trade.duration_minutes,
        "created_at": trade.created_at.isoformat()
    }
