"""
Signals API - Signal generation endpoints with Database Integration
Place this file in project root alongside api.py

Add to your FastAPI app (api.py):
    from signals_api import router as signals_router
    app.include_router(signals_router)
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import json
import pytz
from datetime import datetime, timedelta

_ET_TZ = pytz.timezone('America/New_York')

def _us_eod_utc(dt_utc: datetime) -> datetime:
    """4:00 PM ET (DST-aware) → naive UTC. EDT: 20:00 UTC | EST: 21:00 UTC."""
    utc_aware = pytz.utc.localize(dt_utc)
    et_time   = utc_aware.astimezone(_ET_TZ)
    et_close  = _ET_TZ.localize(
        et_time.replace(hour=16, minute=0, second=0, microsecond=0, tzinfo=None)
    )
    return et_close.astimezone(pytz.utc).replace(tzinfo=None)


def _is_us_trading_hours(dt_utc: datetime) -> bool:
    """DST-aware US kereskedési óra ellenőrzés (9:30–16:00 ET → UTC)."""
    utc_aware  = pytz.utc.localize(dt_utc)
    et_time    = utc_aware.astimezone(_ET_TZ)
    et_decimal = et_time.hour + et_time.minute / 60.0
    return 9.5 <= et_decimal < 16.0

# Database imports
from src.database import get_db
from src.models import Ticker, Signal, SignalCalculation, SimulatedTrade, PriceData

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/signals", tags=["Signals"])


def _compute_direction_result(
    signal_created_at: datetime,
    ticker_symbol: str,
    decision: str,
    db: Session
) -> dict | None:
    """
    Kiszámolja, hogy egy signal helyes irányt jelzett-e a belépéstől
    számított 2 órán belül (vagy EOD zárásig, ha az közelebb van).

    Visszatérési érték:
        None  — ha a signal nem értékelhető (HOLD, after-hours, nincs adat)
        dict  — {eligible, correct, price_change_pct, window_minutes, hit_eod}

    Feltételek (azonos logika mint analyze_signal_direction.py):
        - Belépés = created_at + 15 perc
        - Csak kereskedési időben lévő belépések vizsgálhatók
        - Kilépési referencia: entry + 2h, max EOD - 5 perc
        - 5m gyertyák ±20 perces toleranciával
    """
    if decision == 'HOLD':
        return None

    entry_time = signal_created_at + timedelta(minutes=15)

    # Kereskedési idő és hétvége ellenőrzés
    def _is_weekend(t: datetime) -> bool:
        return t.weekday() >= 5

    def _is_trading(t: datetime, sym: str) -> bool:
        if sym.endswith('.BD'):
            dec = t.hour + t.minute / 60.0
            return 8.0 <= dec < 16.0
        return _is_us_trading_hours(t)   # DST-aware

    if _is_weekend(entry_time) or not _is_trading(entry_time, ticker_symbol):
        return None

    # Piacvégi időpont (UTC, DST-aware)
    if ticker_symbol.endswith('.BD'):
        eod = entry_time.replace(hour=16, minute=0, second=0, microsecond=0)
    else:
        eod = _us_eod_utc(entry_time)   # 20:00 UTC (EDT) vagy 21:00 UTC (EST)

    raw_exit_time = entry_time + timedelta(hours=2)
    exit_time     = min(raw_exit_time, eod - timedelta(minutes=5))

    if (exit_time - entry_time).total_seconds() < 300:
        return None  # Kevesebb mint 5 perc kereskedési idő maradt

    hit_eod = raw_exit_time > eod

    # Legközelebbi 5m gyertya a target időponthoz
    def _nearest_candle(t: datetime, tol_min: int = 20):
        t_low  = t - timedelta(minutes=tol_min)
        t_high = t + timedelta(minutes=tol_min)
        rows = db.query(PriceData).filter(
            PriceData.ticker_symbol == ticker_symbol,
            PriceData.interval == '5m',
            PriceData.timestamp >= t_low,
            PriceData.timestamp <= t_high,
        ).all()
        if not rows:
            return None
        return min(rows, key=lambda c: abs((c.timestamp - t).total_seconds()))

    entry_candle = _nearest_candle(entry_time)
    if not entry_candle:
        return None

    exit_candle = _nearest_candle(exit_time)
    if not exit_candle:
        return None

    entry_price  = float(entry_candle.close)
    exit_price   = float(exit_candle.close)
    pct_change   = (exit_price - entry_price) / entry_price * 100
    correct      = (exit_price > entry_price) if decision == 'BUY' else (exit_price < entry_price)
    window_min   = int((exit_time - entry_time).total_seconds() / 60)

    return {
        "eligible":          True,
        "correct":           correct,
        "price_change_pct":  round(pct_change, 3),
        "window_minutes":    window_min,
        "hit_eod":           hit_eod,
    }


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
            # Minden signal active státusszal jön létre (HOLD is),
            # így megjelenik a live nézetben a következő simulate futásig.
            # Simulate futása után a migrátor 'migrated' státuszra állítja és
            # az archive nézetbe kerül.
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
    exit_reasons: Optional[List[str]] = Query(None),
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
    
    Returns signals with status='active', 'expired' or 'archived'
    """
    try:
        # Pre-compute requested skip statuses so base query can include them
        _skip_status_map = {
            'NOGO': 'nogo', 'NO_DATA': 'no_data', 'SKIP_HRS': 'skip_hours',
            'INV_LVL': 'invalid_levels', 'PAR_SKIP': 'parallel_skip',
        }
        _requested_skip = [_skip_status_map[r] for r in (exit_reasons or []) if r in _skip_status_map]

        # Live nézetben látható signalok (állapot alapú, nem dátum alapú):
        #   1. active státuszú signal — minden döntés (BUY, SELL, HOLD egyaránt),
        #      amíg simulate nem fut rajtuk → megmarad a live nézetben
        #   2. archived státuszú BUY/SELL signal — generator által superseded,
        #      de még nem ment át a migrate pipeline-on
        #   3. Bármely státuszú signal, amelyhez OPEN trade tartozik
        #
        # migrated, nogo, expired, skip_hours, parallel_skip stb.
        # → csak explicit szűrőre látszik (archive nézetben)
        from sqlalchemy import or_, exists as sa_exists, and_
        _base_statuses = ['active'] + _requested_skip
        query = db.query(Signal).filter(
            or_(
                # active: minden fresh signal (BUY, SELL, HOLD)
                Signal.status.in_(_base_statuses),
                # archived BUY/SELL: generator superseded, de még pending migrate
                and_(
                    Signal.status == 'archived',
                    Signal.decision.in_(['BUY', 'SELL'])
                ),
                # Bármely signal, amelyhez nyitott trade tartozik
                sa_exists().where(
                    and_(
                        SimulatedTrade.entry_signal_id == Signal.id,
                        SimulatedTrade.status == 'OPEN'
                    )
                )
            )
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
        
        # Score range filtering (on absolute value, so SELL signals with negative scores are included)
        if min_score is not None:
            query = query.filter(func.abs(Signal.combined_score) >= min_score)
        if max_score is not None:
            query = query.filter(func.abs(Signal.combined_score) <= max_score)

        # Exit reason filtering (joins SimulatedTrade)
        # Frontend categories -> DB values:
        #   SL       -> SL_HIT
        #   TP       -> TP_HIT
        #   REV      -> OPPOSING_SIGNAL
        #   EOD      -> EOD_AUTO_LIQUIDATION
        #   STAG     -> STAGNATION_EXIT
        #   MAX      -> MAX_HOLD_LIQUIDATION
        #   OPEN     -> trade.status == 'OPEN'
        #   NOGO     -> signal.status == 'nogo'
        #   NO_DATA  -> signal.status == 'no_data'
        #   SKIP_HRS -> signal.status == 'skip_hours'
        #   INV_LVL  -> signal.status == 'invalid_levels'
        #   PAR_SKIP -> signal.status == 'parallel_skip'
        #   NONE     -> no trade exists
        if exit_reasons:
            exit_reason_conditions = []
            db_reason_map = {
                'SL':   'SL_HIT',
                'TP':   'TP_HIT',
                'REV':  'OPPOSING_SIGNAL',
                'EOD':  'EOD_AUTO_LIQUIDATION',
                'STAG': 'STAGNATION_EXIT',
                'MAX':  'MAX_HOLD_LIQUIDATION',
            }
            signal_status_map = {
                'NOGO':     'nogo',
                'NO_DATA':  'no_data',
                'SKIP_HRS': 'skip_hours',
                'INV_LVL':  'invalid_levels',
                'PAR_SKIP': 'parallel_skip',
            }
            db_reasons = [db_reason_map[r] for r in exit_reasons if r in db_reason_map]
            sig_statuses = [signal_status_map[r] for r in exit_reasons if r in signal_status_map]
            include_open = 'OPEN' in exit_reasons
            include_none = 'NONE' in exit_reasons

            from sqlalchemy import or_, and_, exists
            trade_alias = SimulatedTrade

            if db_reasons:
                exit_reason_conditions.append(
                    exists().where(
                        and_(trade_alias.entry_signal_id == Signal.id,
                             trade_alias.exit_reason.in_(db_reasons))
                    )
                )
            if include_open:
                exit_reason_conditions.append(
                    exists().where(
                        and_(trade_alias.entry_signal_id == Signal.id,
                             trade_alias.status == 'OPEN')
                    )
                )
            if sig_statuses:
                exit_reason_conditions.append(Signal.status.in_(sig_statuses))
            if include_none:
                exit_reason_conditions.append(
                    ~exists().where(trade_alias.entry_signal_id == Signal.id)
                )

            if exit_reason_conditions:
                query = query.filter(or_(*exit_reason_conditions))

        # Get total count before pagination
        total_count = query.count()

        # Compute P&L summary across ALL filtered signals (not just current page)
        all_signal_ids_for_summary = [s.id for s in query.all()]

        pnl_summary = {
            "closed_count": 0,
            "open_count": 0,
            "open_trade_ids": [],
            "total_pnl_huf": None,
            "total_pnl_percent": None,
            "total_net_pnl_percent": None,
            "win_rate": None,
        }
        if all_signal_ids_for_summary:
            all_trades_for_summary = db.query(SimulatedTrade).filter(
                SimulatedTrade.entry_signal_id.in_(all_signal_ids_for_summary)
            ).all()
            closed_huf_values = [
                float(t.pnl_amount_huf)
                for t in all_trades_for_summary
                if t.status == 'CLOSED' and t.pnl_amount_huf is not None
            ]
            closed_pct_values = [
                float(t.pnl_percent)
                for t in all_trades_for_summary
                if t.status == 'CLOSED' and t.pnl_percent is not None
            ]
            _TARGET_POS_HUF = 700_000
            closed_cnt = sum(1 for t in all_trades_for_summary if t.status == 'CLOSED')
            win_cnt    = sum(1 for t in all_trades_for_summary if t.status == 'CLOSED' and (t.pnl_amount_huf or 0) >= 0)
            pnl_summary["closed_count"] = closed_cnt
            pnl_summary["open_count"] = sum(1 for t in all_trades_for_summary if t.status == 'OPEN')
            pnl_summary["open_trade_ids"] = [t.id for t in all_trades_for_summary if t.status == 'OPEN']
            if closed_huf_values:
                total_huf = sum(closed_huf_values)
                pnl_summary["total_pnl_huf"] = total_huf
                # Átlagos %/trade: átlagos HUF nyereség / target pozícióméret
                pnl_summary["total_net_pnl_percent"] = (total_huf / closed_cnt) / _TARGET_POS_HUF * 100
            if closed_pct_values:
                pnl_summary["total_pnl_percent"] = sum(closed_pct_values)
            if closed_cnt > 0:
                pnl_summary["win_rate"] = win_cnt / closed_cnt * 100

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

            direction_result = _compute_direction_result(
                signal.created_at, signal.ticker_symbol, signal.decision, db
            )

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
                **({
                    "sentiment_contribution": gc["sentiment"],
                    "technical_contribution": gc["technical"],
                    "risk_contribution":      gc["risk"],
                } if (gc := reasoning.get("group_contributions")) else {}),
                "created_at": signal.created_at.isoformat() + "Z",
                "expires_at": signal.expires_at.isoformat() + "Z" if signal.expires_at else None,
                "status": signal.status,
                "simulated_trade": simulated_trade,
                "direction_result": direction_result,
            })
        
        # Return response with applied filters info
        return {
            "signals": signals_list,
            "total": total_count,
            "pnl_summary": pnl_summary,
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
    latest_per_ticker: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all stored signals from database

    Query params:
    - status: active/expired/archived/all (default: active)
    - limit: max results (default: 50)
    - ticker_symbol: filter by ticker (optional)
    - latest_per_ticker: if true, return only the most recent signal per ticker regardless of status (default: false)
    """
    try:
        if latest_per_ticker:
            # Subquery: max created_at per ticker
            subq = (
                db.query(
                    Signal.ticker_symbol,
                    func.max(Signal.created_at).label("max_created_at")
                )
                .group_by(Signal.ticker_symbol)
                .subquery()
            )
            query = db.query(Signal).join(
                subq,
                (Signal.ticker_symbol == subq.c.ticker_symbol) &
                (Signal.created_at == subq.c.max_created_at)
            )
            # Optional status filter on top of latest-per-ticker
            if status and status != "all" and status != "active":
                query = query.filter(Signal.status == status)
        else:
            query = db.query(Signal)
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


# ──────────────────────────────────────────────────────────────────────────────
# ARCHIVE SIGNALS HISTORY
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/archive/history")
async def get_archive_signal_history(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    ticker_symbols: Optional[List[str]] = Query(None),
    decisions: Optional[List[str]] = Query(None),
    strengths: Optional[List[str]] = Query(None),
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    exit_reasons: Optional[List[str]] = Query(None),
    cluster_peak_only: bool = False,
    limit: int = 100,
    offset: int = 0,
):
    """
    Archive signalok listázása szimulált trade adatokkal.
    Azonos response formátum mint a /history endpoint — így a frontend
    ugyanazt a komponenst tudja újrahasznosítani.
    """
    import sqlite3 as _sqlite3
    import os as _os

    db_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "trendsignal.db")
    db_path = _os.path.normpath(db_path)
    conn = _sqlite3.connect(db_path)
    conn.row_factory = _sqlite3.Row
    try:
        where: list[str] = ["1=1"]
        params: list = []

        if from_date:
            where.append("s.signal_timestamp >= ?")
            params.append(from_date)
        if to_date:
            where.append("s.signal_timestamp < date(?, '+1 day')")
            params.append(to_date)
        if ticker_symbols:
            ph = ",".join("?" * len(ticker_symbols))
            where.append(f"s.ticker_symbol IN ({ph})")
            params.extend([t.upper() for t in ticker_symbols])
        if decisions:
            ph = ",".join("?" * len(decisions))
            where.append(f"s.decision IN ({ph})")
            params.extend([d.upper() for d in decisions])
        if strengths:
            ph = ",".join("?" * len(strengths))
            where.append(f"s.strength IN ({ph})")
            params.extend([st.upper() for st in strengths])
        if min_score is not None:
            where.append("ABS(s.combined_score) >= ?")
            params.append(min_score)
        if max_score is not None:
            where.append("ABS(s.combined_score) <= ?")
            params.append(max_score)

        # exit_reason filter — archive_simulated_trades alapján
        if exit_reasons:
            er_map = {
                'TP':   'TP_HIT',
                'SL':   'SL_HIT',
                'REV':  'OPPOSING_SIGNAL',
                'MAX':  'MAX_HOLD_LIQUIDATION',
                'STAG': 'STAGNATION_EXIT',
                'EOD':  'EOD_AUTO_LIQUIDATION',
            }
            db_reasons = [er_map[r] for r in exit_reasons if r in er_map]
            include_open = 'OPEN' in exit_reasons
            include_none = 'NONE' in exit_reasons

            er_conds: list[str] = []
            if db_reasons:
                ph = ",".join("?" * len(db_reasons))
                er_conds.append(
                    f"EXISTS (SELECT 1 FROM archive_simulated_trades t "
                    f"WHERE t.archive_signal_id=s.id AND t.exit_reason IN ({ph}))"
                )
                params.extend(db_reasons)
            if include_open:
                er_conds.append(
                    "EXISTS (SELECT 1 FROM archive_simulated_trades t "
                    "WHERE t.archive_signal_id=s.id AND t.status='OPEN')"
                )
            if include_none:
                er_conds.append(
                    "NOT EXISTS (SELECT 1 FROM archive_simulated_trades t "
                    "WHERE t.archive_signal_id=s.id)"
                )
            if er_conds:
                where.append(f"({' OR '.join(er_conds)})")

        # Klaszter-csúcs filter: ticker+irány szerint futó maximum score alapján
        # csak azok a signalok jelennek meg, amelyek meghaladják a korábbi klaszter-csúcsot.
        # Reset: ha a score 25 alá esik, a klaszter újraindul.
        if cluster_peak_only:
            _CLUSTER_THRESHOLD = 25.0
            pre_rows = conn.execute(
                f"SELECT s.id, s.ticker_symbol, s.combined_score "
                f"FROM archive_signals s WHERE {' AND '.join(where)} "
                f"ORDER BY s.signal_timestamp ASC",
                params,
            ).fetchall()
            _cluster_max: dict = {}   # (ticker, direction) → futó max |score|
            _valid_ids: list = []
            for _r in pre_rows:
                _abs = abs(_r["combined_score"])
                _dir = "LONG" if _r["combined_score"] > 0 else "SHORT"
                _key = (_r["ticker_symbol"], _dir)
                _cur = _cluster_max.get(_key, 0.0)
                if _abs < _CLUSTER_THRESHOLD:
                    _cluster_max[_key] = 0.0          # reset
                elif _abs > _cur:
                    _valid_ids.append(_r["id"])
                    _cluster_max[_key] = _abs
                # else: skip (score >= threshold de nem haladja meg a csúcsot)
            if _valid_ids:
                _ph = ",".join("?" * len(_valid_ids))
                where.append(f"s.id IN ({_ph})")
                params = list(params) + _valid_ids
            else:
                where.append("1=0")

        w = " AND ".join(where)

        # PnL summary + total count (egyetlen JOIN-os lekérdezés a COUNT helyett)
        # USD/HUF közelítés az archive periódusra (2024-2026 átlag)
        _USD_HUF_APPROX = 380.0
        _TARGET_HUF     = 700_000
        pnl_row = conn.execute(f"""
            SELECT
                COUNT(DISTINCT s.id)                                             AS total_count,
                SUM(CASE WHEN t.status='CLOSED' THEN 1 ELSE 0 END)              AS closed_count,
                SUM(CASE WHEN t.status='OPEN'   THEN 1 ELSE 0 END)              AS open_count,
                AVG(CASE WHEN t.status='CLOSED' THEN t.pnl_net_percent END)     AS avg_net_pnl_pct,
                SUM(CASE WHEN t.status='CLOSED' THEN t.pnl_net_percent ELSE 0 END) AS sum_net_pnl_pct,
                SUM(CASE WHEN t.status='CLOSED' AND t.pnl_net_percent >= 0 THEN 1 ELSE 0 END) AS win_count,
                SUM(CASE WHEN t.status='CLOSED' AND t.entry_price > 0 AND t.pnl_net_percent IS NOT NULL
                    THEN CAST({_TARGET_HUF} / {_USD_HUF_APPROX} / t.entry_price AS INT)
                         * t.entry_price * {_USD_HUF_APPROX} * t.pnl_net_percent / 100.0
                    ELSE 0 END)                                                  AS sum_huf_adjusted
            FROM archive_signals s
            LEFT JOIN archive_simulated_trades t ON t.archive_signal_id = s.id
            WHERE {w}
        """, params).fetchone()

        total_count = pnl_row["total_count"] or 0

        closed_cnt    = pnl_row["closed_count"] or 0
        win_cnt       = pnl_row["win_count"]    or 0
        win_rate      = (win_cnt / closed_cnt * 100) if closed_cnt > 0 else None
        avg_net_pct   = float(pnl_row["avg_net_pnl_pct"])   if pnl_row["avg_net_pnl_pct"]   is not None else None
        sum_net_pct   = float(pnl_row["sum_net_pnl_pct"])   if pnl_row["sum_net_pnl_pct"]   is not None else None
        total_pnl_huf = round(float(pnl_row["sum_huf_adjusted"])) if pnl_row["sum_huf_adjusted"] is not None else None

        pnl_summary = {
            "closed_count":    closed_cnt,
            "open_count":      pnl_row["open_count"] or 0,
            "open_trade_ids":  [],
            "total_pnl_huf":   total_pnl_huf,
            # kumulatív összeg (live-stílusú megjelenítéshez)
            "total_pnl_percent":     sum_net_pct,
            # átlagos per-trade net PnL (megtartva visszafelé kompatibilitáshoz)
            "total_net_pnl_percent": avg_net_pct,
            "win_rate":              win_rate,
        }

        # Paginated signals
        rows = conn.execute(f"""
            SELECT s.*, t.id as trade_id, t.status as trade_status,
                   t.direction as trade_direction,
                   t.pnl_percent as trade_pnl_pct,
                   t.pnl_net_percent as trade_pnl_net_pct,
                   t.exit_reason as trade_exit_reason,
                   t.entry_price as trade_entry_price,
                   t.exit_price as trade_exit_price,
                   t.stop_loss_price as trade_sl,
                   t.take_profit_price as trade_tp,
                   t.is_real_trade as trade_is_real,
                   t.direction_2h_eligible as trade_2h_eligible,
                   t.direction_2h_correct as trade_2h_correct,
                   t.direction_2h_pct as trade_2h_pct
            FROM archive_signals s
            LEFT JOIN archive_simulated_trades t ON t.archive_signal_id = s.id
            WHERE {w}
            ORDER BY s.signal_timestamp DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset]).fetchall()

        signals_list = []
        for r in rows:
            trade_data = None
            if r["trade_id"]:
                trade_data = {
                    "id":              r["trade_id"],
                    "status":          r["trade_status"],
                    "direction":       r["trade_direction"],
                    "pnl_percent":     float(r["trade_pnl_pct"])     if r["trade_pnl_pct"]     is not None else None,
                    "pnl_net_percent": float(r["trade_pnl_net_pct"]) if r["trade_pnl_net_pct"] is not None else None,
                    "pnl_amount_huf":  None,
                    "exit_reason":     r["trade_exit_reason"],
                    "entry_price":     float(r["trade_entry_price"]) if r["trade_entry_price"] else None,
                    "exit_price":      float(r["trade_exit_price"])  if r["trade_exit_price"]  is not None else None,
                    "position_size_shares": None,
                    "usd_huf_rate":    None,
                    "is_real_trade":   bool(r["trade_is_real"]),
                }

            # 2H direction_result archive trade 2H mezőiből
            direction_result = None
            if r["trade_id"] and r["trade_2h_eligible"] is not None:
                if r["trade_2h_eligible"]:
                    direction_result = {
                        "eligible":         True,
                        "correct":          bool(r["trade_2h_correct"]),
                        "price_change_pct": float(r["trade_2h_pct"]) if r["trade_2h_pct"] is not None else 0.0,
                        "window_minutes":   120,
                        "hit_eod":          False,
                    }
                else:
                    direction_result = {"eligible": False}

            reasoning = {}
            if r["reasoning_json"]:
                try:
                    reasoning = json.loads(r["reasoning_json"])
                except Exception:
                    pass

            signals_list.append({
                "id":                r["id"],
                "ticker_symbol":     r["ticker_symbol"],
                "decision":          r["decision"],
                "strength":          r["strength"],
                "combined_score":    float(r["combined_score"]) if r["combined_score"] is not None else 0.0,
                "overall_confidence":float(r["overall_confidence"]) if r["overall_confidence"] is not None else 0.0,
                "sentiment_score":   float(r["sentiment_score"]) if r["sentiment_score"] is not None else 0.0,
                "technical_score":   float(r["technical_score"]) if r["technical_score"] is not None else 0.0,
                "risk_score":        float(r["risk_score"]) if r["risk_score"] is not None else 0.0,
                "sentiment_confidence": float(r["sentiment_confidence"]) if r["sentiment_confidence"] is not None else 0.0,
                "technical_confidence": float(r["technical_confidence"]) if r["technical_confidence"] is not None else 0.0,
                "entry_price":       float(r["entry_price"]) if r["entry_price"] else 0.0,
                "stop_loss":         float(r["stop_loss"]) if r["stop_loss"] else 0.0,
                "take_profit":       float(r["take_profit"]) if r["take_profit"] else 0.0,
                "risk_reward_ratio": float(r["risk_reward_ratio"]) if r["risk_reward_ratio"] else 1.0,
                "reasoning":         reasoning,
                "created_at":        r["signal_timestamp"] + "Z" if r["signal_timestamp"] else None,
                "expires_at":        None,
                "status":            "archived",
                "simulated_trade":   trade_data,
                "direction_result":  direction_result,
                "is_archive":        True,
            })

        return {
            "signals":     signals_list,
            "total":       total_count,
            "pnl_summary": pnl_summary,
            "filters_applied": {
                "from_date": from_date, "to_date": to_date,
                "ticker_symbols": ticker_symbols, "decisions": decisions,
                "strengths": strengths, "min_score": min_score,
                "max_score": max_score, "limit": limit, "offset": offset,
            },
        }

    finally:
        conn.close()


# Export router
__all__ = ['router']
