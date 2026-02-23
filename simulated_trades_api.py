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
from src.models import SimulatedTrade
from src.backtest_service import BacktestService
from src.price_service import PriceService
import logging

logger = logging.getLogger(__name__)

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

        # Run backtest
        service = BacktestService(db)
        result = service.run_backtest(
            date_from=date_from,
            date_to=date_to,
            symbols=request.symbols,
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
