"""
Signals API - Signal generation endpoints with Database Integration
Place this file in project root alongside api.py

Add to your FastAPI app (api.py):
    from signals_api import router as signals_router
    app.include_router(signals_router)
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import json
from datetime import datetime, timedelta

# Database imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from src.database import get_db
from src.models import Ticker, Signal, SignalCalculation, SimulatedTrade  # ✅ ADD SignalCalculation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/signals", tags=["Signals"])


def to_python(val):
    """Convert numpy types to Python native types"""
    import numpy as np
    if isinstance(val, (np.integer, np.int64, np.int32)):
        return int(val)
    if isinstance(val, (np.floating, np.float64, np.float32)):
        return float(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    return val


def save_signal_to_db(signal, db: Session):
    """Save generated signal to database with lifecycle management"""
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
        
        # ===== LIFECYCLE MANAGEMENT =====
        # Archive all previous ACTIVE signals for this ticker
        previous_signals = db.query(Signal).filter(
            Signal.ticker_symbol == signal.ticker_symbol,
            Signal.status == 'active'
        ).all()
        
        archived_count = 0
        for prev_signal in previous_signals:
            prev_signal.status = 'archived'
            archived_count += 1
        
        if archived_count > 0:
            db.commit()
            logger.info(f"📦 Archived {archived_count} previous signal(s) for {signal.ticker_symbol}")
        
        # Create reasoning JSON - use signal's full reasoning if available
        if signal.reasoning:
            # Use the complete reasoning from SignalGenerator (includes key_news, key_signals, etc.)
            reasoning = signal.reasoning
            
            # Also include components if available (for indicator values like RSI, MACD, etc.)
            if signal.components:
                reasoning["components"] = signal.components
        else:
            # Fallback: Create minimal reasoning
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
            technical_indicator_id=getattr(signal, 'technical_indicator_id', None),  # ✅ Link to technical snapshot
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
        
        # ===== SAVE AUDIT TRAIL =====
        # Check if signal has _audit_record attribute (created by SignalGenerator._save_audit_trail)
        if hasattr(signal, '_audit_record') and signal._audit_record:
            try:
                audit_record = signal._audit_record
                audit_record.signal_id = db_signal.id  # Link to saved signal
                db.add(audit_record)
                db.commit()
                logger.info(f"✅ Saved audit trail for signal #{db_signal.id}")
            except Exception as audit_error:
                logger.error(f"❌ Failed to save audit trail for signal #{db_signal.id}: {audit_error}")
                # Don't rollback the signal - audit trail is optional
        
        logger.info(f"✅ Saved signal for {signal.ticker_symbol} to database (ID: {db_signal.id})")
        return db_signal
        
    except Exception as e:
        logger.error(f"❌ Error saving signal to DB: {e}")
        db.rollback()
        return None


# ===== REQUEST/RESPONSE MODELS =====

class GenerateSignalsRequest(BaseModel):
    """Request model for signal generation"""
    tickers: Optional[List[str]] = None  # If None, generate for all active tickers
    force_refresh: bool = False  # Force news collection before generation

class GenerateSignalsResponse(BaseModel):
    """Response model for signal generation"""
    message: str
    signals_generated: int
    saved: int
    tickers_processed: List[str]

class SchedulerStatusResponse(BaseModel):
    """Response model for scheduler status"""
    status: str
    message: str
    signals_generated: Optional[int] = None
    tickers: Optional[List[str]] = None


# ===== ENDPOINTS =====

@router.post("/generate", response_model=GenerateSignalsResponse)
async def generate_all_signals(
    request: GenerateSignalsRequest = None,
    db: Session = Depends(get_db)
):
    """
    Generate trading signals for all active tickers and save to database
    
    This endpoint:
    1. Collects latest news (if force_refresh=True)
    2. Analyzes sentiment with decay model
    3. Calculates technical indicators
    4. Generates BUY/SELL/HOLD signals
    5. Saves to database
    6. Returns count of generated signals
    """
    try:
        from main import run_batch_analysis
        
        logger.info("🎯 Signal generation triggered via API")
        
        # Get tickers from database
        if request and request.tickers:
            # Specific tickers requested
            tickers_to_process = []
            for symbol in request.tickers:
                ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
                if ticker:
                    tickers_to_process.append({'symbol': ticker.symbol, 'name': ticker.name})
        else:
            # All active tickers
            tickers = db.query(Ticker).filter(Ticker.is_active == True).all()
            print(f"🔍 DEBUG: Query returned {len(tickers)} tickers from database")
            for t in tickers:
                print(f"   - {t.symbol}: {t.name} (active={t.is_active})")
            tickers_to_process = [{'symbol': t.symbol, 'name': t.name} for t in tickers]
            print(f"🔍 DEBUG: tickers_to_process has {len(tickers_to_process)} items")
        
        if not tickers_to_process:
            logger.warning("No tickers to process")
            return GenerateSignalsResponse(
                message="No tickers available for signal generation",
                signals_generated=0,
                saved=0,
                tickers_processed=[]
            )
        
        logger.info(f"📊 Processing {len(tickers_to_process)} tickers")
        
        # Run analysis WITH DATABASE SESSION
        signals = run_batch_analysis(tickers_to_process, config=None, use_db=True)
        
        if signals:
            logger.info(f"✅ Generated {len(signals)} signals")
            
            # Save to database
            saved_count = 0
            for signal in signals:
                if save_signal_to_db(signal, db):
                    saved_count += 1
            
            logger.info(f"💾 Saved {saved_count}/{len(signals)} signals to database")
            
            return GenerateSignalsResponse(
                message=f"Successfully generated {len(signals)} signals",
                signals_generated=len(signals),
                saved=saved_count,
                tickers_processed=[s.ticker_symbol for s in signals]
            )
        else:
            logger.warning("Signal generation completed but no signals returned")
            return GenerateSignalsResponse(
                message="Signal generation completed but no signals returned",
                signals_generated=0,
                saved=0,
                tickers_processed=[]
            )
        
    except Exception as e:
        logger.error(f"❌ Error generating signals: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate signals: {str(e)}"
        )


@router.post("/generate/{ticker_symbol}")
async def generate_single_signal(
    ticker_symbol: str,
    db: Session = Depends(get_db)
):
    """
    Generate trading signal for a single ticker
    
    Args:
        ticker_symbol: Stock ticker (e.g., AAPL, MSFT)
    """
    try:
        from main import run_analysis
        
        logger.info(f"🎯 Signal generation triggered for {ticker_symbol}")
        
        # Get ticker from database
        ticker = db.query(Ticker).filter(Ticker.symbol == ticker_symbol.upper()).first()
        
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker_symbol} not found")
        
        # Run analysis for single ticker
        signal = run_analysis(ticker.symbol, ticker.name)
        
        if signal:
            # Save to database
            db_signal = save_signal_to_db(signal, db)
            
            return GenerateSignalsResponse(
                message=f"Successfully generated signal for {ticker_symbol}",
                signals_generated=1,
                saved=1 if db_signal else 0,
                tickers_processed=[ticker_symbol]
            )
        else:
            return GenerateSignalsResponse(
                message=f"No signal generated for {ticker_symbol}",
                signals_generated=0,
                saved=0,
                tickers_processed=[]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating signal for {ticker_symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate signal: {str(e)}"
        )


@router.post("/refresh")
async def refresh_signals(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Refresh all signals (collect news + generate signals)
    Runs in background to avoid timeout
    """
    try:
        logger.info("🔄 Signal refresh triggered (with news collection)")
        
        # Add task to background
        def background_refresh():
            from main import run_batch_analysis
            tickers = db.query(Ticker).filter(Ticker.is_active == True).all()
            ticker_list = [{'symbol': t.symbol, 'name': t.name} for t in tickers]
            signals = run_batch_analysis(ticker_list)
            for signal in signals:
                save_signal_to_db(signal, db)
        
        background_tasks.add_task(background_refresh)
        
        return {
            "message": "Signal refresh started in background",
            "status": "processing"
        }
        
    except Exception as e:
        logger.error(f"❌ Error refreshing signals: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh signals: {str(e)}"
        )


@router.post("/trigger-scheduled", response_model=SchedulerStatusResponse)
async def trigger_scheduled_refresh():
    """
    🆕 Manual trigger for scheduled signal refresh
    
    Generates signals only for markets that are currently open:
    - BÉT tickers during Budapest market hours (9:00-17:00 CET)
    - US tickers during NYSE/NASDAQ hours (9:30-16:00 ET)
    
    Returns:
        Status and count of generated signals
    """
    try:
        from scheduler import trigger_signal_refresh_now
        
        logger.info("🔘 Manual scheduled refresh triggered via API")
        
        # Call scheduler function (checks market hours automatically)
        result = trigger_signal_refresh_now()
        
        return SchedulerStatusResponse(
            status=result['status'],
            message=result['message'],
            signals_generated=result.get('signals_generated'),
            tickers=result.get('tickers')
        )
        
    except Exception as e:
        logger.error(f"❌ Error in scheduled refresh: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger scheduled refresh: {str(e)}"
        )


# ===== GET ENDPOINTS =====

@router.get("/history")
async def get_signal_history(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    ticker_symbols: Optional[List[str]] = Query(None),
    decisions: Optional[List[str]] = Query(None),
    strengths: Optional[List[str]] = Query(None),
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get historical signals with flexible filtering
    
    Query params:
    - from_date: Start date (YYYY-MM-DD format)
    - to_date: End date (YYYY-MM-DD format)
    - ticker_symbols: List of ticker symbols to filter (can be multiple)
    - decisions: List of decisions to filter (BUY, SELL, HOLD)
    - strengths: List of strengths to filter (STRONG, MODERATE, WEAK)
    - min_score: Minimum combined score
    - max_score: Maximum combined score
    - limit: Maximum number of results (default: 100)
    - offset: Pagination offset (default: 0)
    
    Returns signals with status='expired' or 'archived'
    """
    try:
        # Start with base query - only expired or archived signals
        query = db.query(Signal).filter(
            Signal.status.in_(['expired', 'archived'])
        )
        
        # Date range filtering
        if from_date:
            try:
                from_datetime = datetime.strptime(from_date, "%Y-%m-%d")
                query = query.filter(Signal.created_at >= from_datetime)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid from_date format. Expected YYYY-MM-DD, got: {from_date}"
                )
        
        if to_date:
            try:
                # Add 1 day to include the entire to_date
                to_datetime = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
                query = query.filter(Signal.created_at < to_datetime)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid to_date format. Expected YYYY-MM-DD, got: {to_date}"
                )
        
        # Ticker symbols filtering
        if ticker_symbols:
            # Convert to uppercase and filter
            ticker_symbols_upper = [s.upper() for s in ticker_symbols]
            query = query.filter(Signal.ticker_symbol.in_(ticker_symbols_upper))
        
        # Decision filtering
        if decisions:
            valid_decisions = ['BUY', 'SELL', 'HOLD']
            decisions_upper = [d.upper() for d in decisions]
            invalid_decisions = [d for d in decisions_upper if d not in valid_decisions]
            if invalid_decisions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid decisions: {invalid_decisions}. Valid: {valid_decisions}"
                )
            query = query.filter(Signal.decision.in_(decisions_upper))
        
        # Strength filtering
        if strengths:
            valid_strengths = ['STRONG', 'MODERATE', 'WEAK']
            strengths_upper = [s.upper() for s in strengths]
            invalid_strengths = [s for s in strengths_upper if s not in valid_strengths]
            if invalid_strengths:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid strengths: {invalid_strengths}. Valid: {valid_strengths}"
                )
            query = query.filter(Signal.strength.in_(strengths_upper))
        
        # Score range filtering
        if min_score is not None:
            query = query.filter(Signal.combined_score >= min_score)
        if max_score is not None:
            query = query.filter(Signal.combined_score <= max_score)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Order by created_at descending (newest first) and apply pagination
        signals = query.order_by(Signal.created_at.desc()).limit(limit).offset(offset).all()
        
        # Fetch all simulated trades for these signals in one query
        signal_ids = [s.id for s in signals]
        trades_by_signal = {}
        if signal_ids:
            trades = db.query(SimulatedTrade).filter(
                SimulatedTrade.entry_signal_id.in_(signal_ids)
            ).all()
            for trade in trades:
                trades_by_signal[trade.entry_signal_id] = trade

        # Format response (same format as get_signals)
        signals_list = []
        for signal in signals:
            reasoning = json.loads(signal.reasoning_json) if signal.reasoning_json else {}

            trade = trades_by_signal.get(signal.id)
            simulated_trade = None
            if trade:
                simulated_trade = {
                    "id": trade.id,
                    "status": trade.status,
                    "direction": trade.direction,
                    "pnl_percent": float(trade.pnl_percent) if trade.pnl_percent is not None else None,
                    "pnl_amount_huf": float(trade.pnl_amount_huf) if trade.pnl_amount_huf is not None else None,
                    "exit_reason": trade.exit_reason,
                    "entry_price": float(trade.entry_price),
                    "exit_price": float(trade.exit_price) if trade.exit_price is not None else None,
                    "position_size_shares": int(trade.position_size_shares) if trade.position_size_shares is not None else None,
                    "usd_huf_rate": float(trade.usd_huf_rate) if trade.usd_huf_rate is not None else None,
                }

            signals_list.append({
                "id": signal.id,
                "ticker_symbol": signal.ticker_symbol,
                "technical_indicator_id": signal.technical_indicator_id,
                "decision": signal.decision,
                "strength": signal.strength,
                "combined_score": float(signal.combined_score),
                "overall_confidence": float(signal.overall_confidence),
                "sentiment_score": float(signal.sentiment_score),
                "technical_score": float(signal.technical_score),
                "risk_score": float(signal.risk_score),
                "sentiment_confidence": float(signal.sentiment_confidence) if signal.sentiment_confidence else 0.0,
                "technical_confidence": float(signal.technical_confidence) if signal.technical_confidence else 0.0,
                "entry_price": float(signal.entry_price) if signal.entry_price else 0.0,
                "stop_loss": float(signal.stop_loss) if signal.stop_loss else 0.0,
                "take_profit": float(signal.take_profit) if signal.take_profit else 0.0,
                "risk_reward_ratio": float(signal.risk_reward_ratio) if signal.risk_reward_ratio else 1.0,
                "reasoning": reasoning,
                "created_at": signal.created_at.isoformat() + "Z",
                "expires_at": signal.expires_at.isoformat() + "Z" if signal.expires_at else None,
                "status": signal.status,
                "simulated_trade": simulated_trade,
            })
        
        # Return response with applied filters info
        return {
            "signals": signals_list,
            "total": total_count,
            "filters_applied": {
                "from_date": from_date,
                "to_date": to_date,
                "ticker_symbols": ticker_symbols,
                "decisions": decisions,
                "strengths": strengths,
                "min_score": min_score,
                "max_score": max_score,
                "limit": limit,
                "offset": offset
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting signal history: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get signal history: {str(e)}"
        )


@router.get("")
async def get_signals(
    status: str = "active",
    limit: int = 50,
    ticker_symbol: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all stored signals from database
    
    Query params:
    - status: active/expired/archived (default: active)
    - limit: max results (default: 50)
    - ticker_symbol: filter by ticker (optional)
    """
    try:
        query = db.query(Signal)
        
        # Filter by status
        if status and status != "all":
            query = query.filter(Signal.status == status)
        
        # Filter by ticker if provided
        if ticker_symbol:
            query = query.filter(Signal.ticker_symbol == ticker_symbol.upper())
        
        # Order and limit
        signals = query.order_by(Signal.created_at.desc()).limit(limit).all()
        
        # Format response
        signals_list = []
        for signal in signals:
            reasoning = json.loads(signal.reasoning_json) if signal.reasoning_json else {}
            
            signals_list.append({
                "id": signal.id,
                "ticker_symbol": signal.ticker_symbol,
                "technical_indicator_id": signal.technical_indicator_id,  # ✅ Link
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
            })
        
        return {
            "signals": signals_list,
            "total": len(signals_list)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting signals: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get signals: {str(e)}"
        )


@router.get("/{signal_id}")
async def get_signal_by_id_endpoint(
    signal_id: int,
    db: Session = Depends(get_db)
):
    """
    Get single signal by ID from database
    
    Path param:
    - signal_id: Signal ID (auto-generated)
    
    Returns full signal object with components breakdown
    """
    try:
        signal = db.query(Signal).filter(Signal.id == signal_id).first()
        
        if not signal:
            raise HTTPException(
                status_code=404,
                detail=f"Signal with ID {signal_id} not found"
            )
        
        reasoning = json.loads(signal.reasoning_json) if signal.reasoning_json else {}
        
        return {
            "id": signal.id,
            "ticker_symbol": signal.ticker_symbol,
            "technical_indicator_id": signal.technical_indicator_id,  # ✅ Link
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting signal {signal_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get signal: {str(e)}"
        )


# Export router
__all__ = ['router']
