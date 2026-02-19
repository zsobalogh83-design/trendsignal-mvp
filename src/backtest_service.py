"""
TrendSignal - Backtest Service (v2 - All Signals)
Processes ALL non-neutral signals, creates trade for each

LOGIC:
- Every NON-NEUTRAL signal (|score| >= 25) gets a trade
- First run: All trades are new
- Subsequent runs: Skip already processed signals
- Development: DROP TABLE before each run

Version: 2.0 - Process all signals
Date: 2026-02-17
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
import time

from src.models import Signal, SimulatedTrade
from src.trade_manager import TradeManager
from src.exceptions import InsufficientDataError, InvalidSignalError

logger = logging.getLogger(__name__)


class BacktestService:
    """Backtest service - ensures every signal has a trade"""
    
    def __init__(self, db: Session):
        self.db = db
        self.trade_manager = TradeManager(db)
    
    def run_backtest(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        symbols: Optional[List[str]] = None,
        reprocess_closed: bool = False
    ) -> Dict:
        """
        Run backtest ensuring every signal has a trade.
        
        Args:
            date_from: Start date (UTC)
            date_to: End date (UTC)
            symbols: Filter symbols
            reprocess_closed: Reprocess closed trades
        
        Returns:
            Stats dict
        """
        start_time = time.time()
        
        logger.info("=" * 70)
        logger.info("🔄 Backtest Start")
        logger.info("=" * 70)
        
        # Get signals
        signals = self._get_signals(date_from, date_to, symbols)
        
        logger.info(f"📊 Processing {len(signals)} NON-NEUTRAL signals")
        if date_from or date_to:
            logger.info(f"   Range: {date_from or 'earliest'} → {date_to or 'now'} UTC")
        if symbols:
            logger.info(f"   Symbols: {', '.join(symbols)}")
        
        # Stats
        stats = {
            'total_signals': len(signals),
            'already_closed': 0,
            'newly_closed': 0,
            'still_open': 0,
            'newly_opened': 0,
            'skipped_no_data': 0,
            'skipped_invalid': 0,
            'errors': []
        }
        
        # Process each signal
        for i, signal in enumerate(signals, 1):
            if i % 50 == 0:
                logger.info(f"   Progress: {i}/{len(signals)}...")
            
            try:
                result = self._process_signal(signal, reprocess_closed)
                stats[result] += 1
                
            except Exception as e:
                logger.error(f"❌ Signal {signal.id} ({signal.ticker_symbol}): {e}")
                stats['errors'].append({
                    'signal_id': signal.id,
                    'symbol': signal.ticker_symbol,
                    'error': str(e)
                })
        
        # Commit
        self.db.commit()
        
        execution_time = time.time() - start_time
        
        logger.info("=" * 70)
        logger.info("✅ Backtest Complete")
        logger.info("=" * 70)
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info(f"Already closed: {stats['already_closed']}")
        logger.info(f"Newly closed:   {stats['newly_closed']}")
        logger.info(f"Still open:     {stats['still_open']}")
        logger.info(f"Newly opened:   {stats['newly_opened']}")
        logger.info(f"Skipped (no data): {stats['skipped_no_data']}")
        logger.info(f"Skipped (invalid): {stats['skipped_invalid']}")
        logger.info(f"Errors:         {len(stats['errors'])}")
        logger.info("=" * 70)
        
        return {
            'execution_time_seconds': round(execution_time, 2),
            'stats': stats
        }
    
    def _process_signal(self, signal: Signal, reprocess_closed: bool) -> str:
        """
        Process single signal - ensure it has a trade.
        
        Returns:
            Status string for stats
        """
        # Check existing trade
        trade = self.db.query(SimulatedTrade).filter(
            SimulatedTrade.entry_signal_id == signal.id
        ).first()
        
        # Case 1: Already closed
        if trade and trade.status == 'CLOSED':
            if reprocess_closed:
                logger.debug(f"   Reprocessing {signal.ticker_symbol} signal {signal.id}")
                self.db.delete(trade)
                self.db.flush()
                trade = None
            else:
                return 'already_closed'
        
        # Case 2: Open trade - check exit triggers
        if trade and trade.status == 'OPEN':
            was_closed = self._check_and_close_trade(trade)
            return 'newly_closed' if was_closed else 'still_open'
        
        # Case 3: No trade - create new
        try:
            logger.debug(f"   Creating trade for {signal.ticker_symbol} signal {signal.id}")
            
            trade = self.trade_manager.open_position(signal)
            
            if not trade:
                return 'skipped_invalid'
            
            self.db.flush()
            
            # Immediately check exit triggers
            was_closed = self._check_and_close_trade(trade)
            
            return 'newly_opened' if not was_closed else 'newly_closed'
        
        except InsufficientDataError as e:
            logger.debug(f"   Skip {signal.ticker_symbol}: No price data")
            return 'skipped_no_data'
        
        except InvalidSignalError as e:
            logger.debug(f"   Skip {signal.ticker_symbol}: {e}")
            return 'skipped_invalid'
        
        except Exception as e:
            logger.error(f"   Error {signal.ticker_symbol}: {e}")
            raise
    
    def _check_and_close_trade(self, trade: SimulatedTrade) -> bool:
        """
        Check exit triggers from entry to now.
        
        Returns:
            True if closed, False if still open
        """
        if trade.status != 'OPEN':
            return False
        
        # Start checking from entry + 15 min
        check_time_utc = trade.entry_signal_generated_at + timedelta(minutes=30)
        now_utc = datetime.utcnow()
        
        # Check every 15 minutes
        while check_time_utc <= now_utc:
            trigger = self._check_exit_triggers_at_time(trade, check_time_utc)
            
            if trigger:
                logger.debug(
                    f"      Exit: {trade.symbol} {trigger['exit_reason']} "
                    f"@ {check_time_utc} UTC"
                )
                
                self.trade_manager.close_position(
                    trade,
                    exit_reason=trigger['exit_reason'],
                    exit_signal=trigger.get('exit_signal'),
                    trigger_time_utc=check_time_utc
                )
                
                return True
            
            check_time_utc += timedelta(minutes=15)
        
        # Still open
        return False
    
    def _check_exit_triggers_at_time(self, trade: SimulatedTrade, check_time_utc: datetime) -> Optional[Dict]:
        """Check all exit triggers at specific UTC time"""
        
        # Priority 1: SL/TP
        price_trigger = self.trade_manager.price_service.check_price_triggers(
            trade.symbol,
            trade.stop_loss_price,
            trade.take_profit_price,
            trade.direction,
            check_time_utc,
            tolerance_minutes=15
        )
        
        if price_trigger and price_trigger['triggered']:
            return {
                'exit_reason': price_trigger['trigger_type'],
                'exit_signal': None
            }
        
        # Priority 2: Opposing signal
        opposing = self._find_opposing_signal(trade, check_time_utc)
        if opposing:
            return {
                'exit_reason': 'OPPOSING_SIGNAL',
                'exit_signal': opposing
            }
        
        # Priority 3: EOD (SHORT only)
        if trade.direction == 'SHORT':
            market_time = self.trade_manager.price_service._utc_to_market_time(
                check_time_utc, 
                trade.symbol
            )
            if self.trade_manager._is_eod_time(market_time):
                return {
                    'exit_reason': 'EOD_AUTO_LIQUIDATION',
                    'exit_signal': None
                }
        
        return None
    
    def _find_opposing_signal(self, trade: SimulatedTrade, check_time_utc: datetime) -> Optional[Signal]:
        """Find opposing signal near check time"""
        time_start = check_time_utc - timedelta(minutes=15)
        time_end = check_time_utc + timedelta(minutes=15)
        
        signals = self.db.query(Signal).filter(
            and_(
                Signal.ticker_symbol == trade.symbol,
                Signal.created_at >= time_start,
                Signal.created_at <= time_end,
                Signal.id != trade.entry_signal_id
            )
        ).all()
        
        for signal in signals:
            if abs(signal.combined_score) < 25:
                continue
            
            if trade.direction == 'LONG' and signal.combined_score <= -25:
                return signal
            elif trade.direction == 'SHORT' and signal.combined_score >= 25:
                return signal
        
        return None
    
    def _get_signals(
        self,
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        symbols: Optional[List[str]]
    ) -> List[Signal]:
        """Get NON-NEUTRAL signals to process"""
        query = self.db.query(Signal)
        
        if date_from:
            query = query.filter(Signal.created_at >= date_from)
        
        if date_to:
            query = query.filter(Signal.created_at <= date_to)
        
        if symbols:
            query = query.filter(Signal.ticker_symbol.in_(symbols))
        
        # Only non-neutral
        query = query.filter(
            or_(
                Signal.combined_score >= 25,
                Signal.combined_score <= -25
            )
        )
        
        query = query.order_by(Signal.created_at.asc())
        
        return query.all()
