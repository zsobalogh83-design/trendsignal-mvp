"""
TrendSignal - Backtest Service (v3 - Signal-based adaptive SL/TP)
Processes ALL non-neutral signals, creates trade for each

LOGIC:
- Every NON-NEUTRAL signal (|score| >= 25) gets a trade
- First run: All trades are new
- Subsequent runs: Skip already processed signals
- Development: DROP TABLE before each run
- SL/TP updated in-flight by same-direction signals (signal-based trailing)

SL/TP UPDATE RULES:
- LONG: new SL > current SL → update (move stop up, lock in gains)
         new TP > current TP → update (raise target if market is stronger)
- SHORT: new SL < current SL → update (move stop down, lock in gains)
         new TP < current TP → update (lower target if market is weaker)
- Only non-neutral same-direction signals trigger updates (|score| >= 25)
- The entry signal itself is excluded from updates

Version: 3.0 - Signal-based adaptive SL/TP
Date: 2026-02-21
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
import time

from src.models import Signal, SimulatedTrade
from src.trade_manager import TradeManager
from src.exceptions import InsufficientDataError, InvalidSignalError, PositionAlreadyExistsError

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

        except PositionAlreadyExistsError as e:
            # Another open trade exists for this symbol - skip this signal
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

        price_service = self.trade_manager.price_service

        # Check every 15 minutes
        while check_time_utc <= now_utc:
            # Skip weekends entirely - markets are closed, no candles, no exits possible
            if price_service._is_weekend(check_time_utc):
                check_time_utc += timedelta(minutes=15)
                continue

            # Skip outside trading hours - no candles available
            # Also skip the last 15 minutes before market close to avoid
            # get_5min_candle_at_time's +15min offset pushing into after-hours
            if not price_service._is_trading_hours(check_time_utc, trade.symbol):
                check_time_utc += timedelta(minutes=15)
                continue

            # Guard: ensure check_time + 15min (execution offset) is still within trading hours
            check_plus_15 = check_time_utc + timedelta(minutes=15)
            if not price_service._is_trading_hours(check_plus_15, trade.symbol):
                # This candle would be fetched outside trading hours - skip to next day open
                check_time_utc = price_service._next_market_open_utc(check_time_utc, trade.symbol)
                continue

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
        """Check all exit triggers at specific UTC time.

        Priority order:
        1. SL_HIT / TP_HIT  (uses current SL/TP which may already be updated)
        2. Same-direction signal → update SL/TP in-place (no exit, continue loop)
        3. OPPOSING_SIGNAL → exit
        4. EOD_AUTO_LIQUIDATION (SHORT only)
        """

        # Priority 1: SL/TP check against current (possibly already updated) levels
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

        # Priority 2: Same-direction signal → adaptive SL/TP update (no exit)
        same_dir = self._find_same_direction_signal(trade, check_time_utc)
        if same_dir:
            updated = self._update_sl_tp_from_signal(trade, same_dir, check_time_utc)
            if updated:
                # After update immediately re-check SL/TP with new levels
                # (edge case: updated SL already breached by current price)
                price_trigger2 = self.trade_manager.price_service.check_price_triggers(
                    trade.symbol,
                    trade.stop_loss_price,
                    trade.take_profit_price,
                    trade.direction,
                    check_time_utc,
                    tolerance_minutes=15
                )
                if price_trigger2 and price_trigger2['triggered']:
                    return {
                        'exit_reason': price_trigger2['trigger_type'],
                        'exit_signal': None
                    }

        # Priority 3: Opposing signal → exit
        opposing = self._find_opposing_signal(trade, check_time_utc)
        if opposing:
            return {
                'exit_reason': 'OPPOSING_SIGNAL',
                'exit_signal': opposing
            }

        # Priority 4: EOD (SHORT only, weekdays only)
        if trade.direction == 'SHORT':
            price_service = self.trade_manager.price_service
            if not price_service._is_weekend(check_time_utc):
                market_time = price_service._utc_to_market_time(
                    check_time_utc,
                    trade.symbol
                )
                if self.trade_manager._is_eod_time(market_time):
                    return {
                        'exit_reason': 'EOD_AUTO_LIQUIDATION',
                        'exit_signal': None
                    }

        return None

    def _update_sl_tp_from_signal(
        self,
        trade: SimulatedTrade,
        signal: Signal,
        check_time_utc: datetime
    ) -> bool:
        """
        Update trade SL/TP from a same-direction signal if the new levels are
        more favourable (i.e. lock in more profit or raise the target).

        LONG: better SL = higher SL (closer to price from below)
              better TP = higher TP (more ambitious upside target)
        SHORT: better SL = lower SL (closer to price from above)
               better TP = lower TP (more ambitious downside target)

        Returns:
            True if at least one level was updated, False otherwise
        """
        if signal.stop_loss is None and signal.take_profit is None:
            return False

        updated = False

        if trade.direction == 'LONG':
            if signal.stop_loss is not None and signal.stop_loss > trade.stop_loss_price:
                logger.debug(
                    f"      SL updated {trade.symbol} LONG: "
                    f"{trade.stop_loss_price:.4f} → {signal.stop_loss:.4f} "
                    f"(signal {signal.id} @ {check_time_utc})"
                )
                trade.stop_loss_price = signal.stop_loss
                updated = True

            if signal.take_profit is not None and signal.take_profit > trade.take_profit_price:
                logger.debug(
                    f"      TP updated {trade.symbol} LONG: "
                    f"{trade.take_profit_price:.4f} → {signal.take_profit:.4f} "
                    f"(signal {signal.id} @ {check_time_utc})"
                )
                trade.take_profit_price = signal.take_profit
                updated = True

        else:  # SHORT
            if signal.stop_loss is not None and signal.stop_loss < trade.stop_loss_price:
                logger.debug(
                    f"      SL updated {trade.symbol} SHORT: "
                    f"{trade.stop_loss_price:.4f} → {signal.stop_loss:.4f} "
                    f"(signal {signal.id} @ {check_time_utc})"
                )
                trade.stop_loss_price = signal.stop_loss
                updated = True

            if signal.take_profit is not None and signal.take_profit < trade.take_profit_price:
                logger.debug(
                    f"      TP updated {trade.symbol} SHORT: "
                    f"{trade.take_profit_price:.4f} → {signal.take_profit:.4f} "
                    f"(signal {signal.id} @ {check_time_utc})"
                )
                trade.take_profit_price = signal.take_profit
                updated = True

        if updated:
            trade.sl_tp_update_count = (trade.sl_tp_update_count or 0) + 1
            trade.sl_tp_last_updated_at = check_time_utc

        return updated
    
    def _find_opposing_signal(self, trade: SimulatedTrade, check_time_utc: datetime) -> Optional[Signal]:
        """Find opposing signal on the same trading day up to check_time.

        An opposing signal anywhere during the current trading day is sufficient
        to trigger a position reversal - it does not need to be within ±15 min.
        We return the strongest (highest abs score) opposing signal of the day,
        so the most decisive reversal wins.
        """
        # Search from the start of the current UTC day up to check_time
        day_start = check_time_utc.replace(hour=0, minute=0, second=0, microsecond=0)

        signals = self.db.query(Signal).filter(
            and_(
                Signal.ticker_symbol == trade.symbol,
                Signal.created_at >= day_start,
                Signal.created_at <= check_time_utc,
                Signal.id != trade.entry_signal_id
            )
        ).all()

        best = None
        for signal in signals:
            if abs(signal.combined_score) < 25:
                continue
            if trade.direction == 'LONG' and signal.combined_score <= -25:
                if best is None or abs(signal.combined_score) > abs(best.combined_score):
                    best = signal
            elif trade.direction == 'SHORT' and signal.combined_score >= 25:
                if best is None or abs(signal.combined_score) > abs(best.combined_score):
                    best = signal

        return best
    
    def _find_same_direction_signal(self, trade: SimulatedTrade, check_time_utc: datetime) -> Optional[Signal]:
        """Find the strongest same-direction signal on the current trading day up to check_time.

        Used for signal-based adaptive SL/TP update:
        - LONG trade → look for signals with combined_score >= 25
        - SHORT trade → look for signals with combined_score <= -25

        The entry signal is excluded. We pick the strongest (highest abs score)
        same-direction signal so the most decisive confirmation drives the update.

        Only signals that have valid SL or TP values are considered useful.
        """
        day_start = check_time_utc.replace(hour=0, minute=0, second=0, microsecond=0)

        signals = self.db.query(Signal).filter(
            and_(
                Signal.ticker_symbol == trade.symbol,
                Signal.created_at >= day_start,
                Signal.created_at <= check_time_utc,
                Signal.id != trade.entry_signal_id
            )
        ).all()

        best = None
        for signal in signals:
            # Must have at least one of SL or TP to be useful for updating
            if signal.stop_loss is None and signal.take_profit is None:
                continue

            if trade.direction == 'LONG' and signal.combined_score >= 25:
                if best is None or abs(signal.combined_score) > abs(best.combined_score):
                    best = signal
            elif trade.direction == 'SHORT' and signal.combined_score <= -25:
                if best is None or abs(signal.combined_score) > abs(best.combined_score):
                    best = signal

        return best

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
