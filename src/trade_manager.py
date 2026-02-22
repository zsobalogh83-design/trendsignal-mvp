"""
TrendSignal - Trade Manager (Timezone-Aware)
Core service for simulated trade lifecycle management

TIMEZONE HANDLING:
- All signal times are UTC
- Execution times converted to market local time
- Weekend signals → Next Monday market open + 30 min

Version: 2.0 - Timezone-aware
Date: 2026-02-17
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session
import logging
import math

from src.models import SimulatedTrade, Signal
from src.price_service import PriceService
from src.exceptions import (
    PositionAlreadyExistsError,
    InsufficientDataError,
    InvalidSignalError,
    PositionNotFoundError,
    ExchangeRateError
)

logger = logging.getLogger(__name__)


class TradeManager:
    """Trade lifecycle manager with timezone awareness"""
    
    TARGET_POSITION_VALUE_HUF = 700_000
    EXECUTION_DELAY_MINUTES = 15
    EOD_LIQUIDATION_HOUR = 16
    EOD_LIQUIDATION_MINUTE = 45

    # Pyramiding parameters (set MAX_PARALLEL_POSITIONS = 1 to disable pyramiding)
    MAX_PARALLEL_POSITIONS = 1          # Max open trades per symbol per direction (1 = no pyramiding)
    PYRAMIDING_MIN_HOURS = 6            # Min hours between entry signals
    PYRAMIDING_MIN_SENTIMENT = 40.0     # Min |sentiment_score| for sentiment-driven pyramid
    
    def __init__(self, db: Session):
        """Initialize trade manager"""
        self.db = db
        self.price_service = PriceService()
    
    def open_position(self, signal: Signal) -> Optional[SimulatedTrade]:
        """
        Open new position based on signal.
        
        Args:
            signal: Signal object (created_at is UTC)
        
        Returns:
            SimulatedTrade object or None if cannot open
        
        Raises:
            PositionAlreadyExistsError: If open position exists
            InsufficientDataError: If no price data
            InvalidSignalError: If signal invalid
        """
        symbol = signal.ticker_symbol
        
        # 1. VALIDATE SIGNAL
        if signal.combined_score is None:
            raise InvalidSignalError(signal.id, "Missing combined_score")
        
        if abs(signal.combined_score) < 25:
            raise InvalidSignalError(
                signal.id,
                f"Neutral signal (score={signal.combined_score})"
            )
        
        # 2. CHECK EXISTING POSITION
        new_direction = "LONG" if signal.combined_score >= 25 else "SHORT"
        signal_execution_utc = signal.created_at + timedelta(minutes=self.EXECUTION_DELAY_MINUTES)

        # Count currently OPEN trades on this symbol in the same direction
        open_same_dir = self.db.query(SimulatedTrade).filter(
            SimulatedTrade.symbol == symbol,
            SimulatedTrade.status == "OPEN",
            SimulatedTrade.direction == new_direction
        ).all()

        # Count currently OPEN trades in the OPPOSING direction
        open_opposing = self.db.query(SimulatedTrade).filter(
            SimulatedTrade.symbol == symbol,
            SimulatedTrade.status == "OPEN",
            SimulatedTrade.direction != new_direction
        ).first()

        if open_opposing:
            # Opposing open trade exists → only allow if this is a flip signal
            # (handled below via OPPOSING_SIGNAL exit in backtest_service)
            raise PositionAlreadyExistsError(symbol, open_opposing.id)

        if open_same_dir:
            # Same-direction open trade(s) exist → check pyramiding conditions
            # Max 2 parallel positions per symbol per direction
            if len(open_same_dir) >= self.MAX_PARALLEL_POSITIONS:
                raise PositionAlreadyExistsError(symbol, open_same_dir[0].id)

            # Find the MOST RECENT open trade - pyramiding requires 6h gap from the
            # latest entry, not the oldest. This prevents a 3rd position slipping in
            # just because it's far from the 1st.
            newest_open = max(open_same_dir, key=lambda t: t.entry_signal_generated_at)
            oldest_open = min(open_same_dir, key=lambda t: t.entry_signal_generated_at)

            # Pyramiding condition 1: at least 6 hours since the NEWEST open position
            hours_since_newest = (
                signal.created_at - newest_open.entry_signal_generated_at
            ).total_seconds() / 3600
            if hours_since_newest < self.PYRAMIDING_MIN_HOURS:
                raise PositionAlreadyExistsError(symbol, newest_open.id)

            # Pyramiding condition 2a: new signal score > oldest open entry score
            score_stronger = abs(signal.combined_score) > abs(oldest_open.entry_score)

            # Pyramiding condition 2b: strong sentiment dominance (|sentiment_score| >= 40)
            sentiment_dominant = (
                signal.sentiment_score is not None
                and abs(signal.sentiment_score) >= self.PYRAMIDING_MIN_SENTIMENT
            )

            if not (score_stronger or sentiment_dominant):
                raise PositionAlreadyExistsError(symbol, newest_open.id)

            logger.info(
                f"   📈 Pyramiding allowed: {symbol} {new_direction} "
                f"(elapsed_since_newest={hours_since_newest:.1f}h, "
                f"score_stronger={score_stronger}, sentiment_dominant={sentiment_dominant})"
            )

        # Also check for a CLOSED trade that overlaps this signal's execution time.
        # In backtesting, a previous trade on the same symbol may have already been
        # opened and closed within the same run. If the previous trade's entry is
        # at or after this signal's execution time, a new position cannot be opened
        # (the capital was already deployed at that time).
        #
        # Exception: if the overlapping trade closed via OPPOSING_SIGNAL and this
        # signal is in the opposite direction (i.e. it IS that opposing signal),
        # allow opening — this is a position flip/reversal.
        #
        # Pyramiding exception: if there are already open same-direction trades,
        # we skip the overlap check (the capital is being added intentionally).
        if not open_same_dir:
            existing_overlap = self.db.query(SimulatedTrade).filter(
                SimulatedTrade.symbol == symbol,
                SimulatedTrade.status == "CLOSED",
                SimulatedTrade.entry_signal_generated_at <= signal.created_at,
                SimulatedTrade.exit_trigger_time >= signal_execution_utc
            ).first()

            if existing_overlap:
                is_flip = (
                    existing_overlap.exit_reason == "OPPOSING_SIGNAL"
                    and existing_overlap.direction != new_direction
                )
                if not is_flip:
                    raise PositionAlreadyExistsError(symbol, existing_overlap.id)
        
        # 3. CALCULATE EXECUTION TIME (UTC + 15 min, handles weekends)
        # Signal.created_at is in UTC
        signal_utc = signal.created_at
        
        logger.info(f"📍 Opening {symbol}: Signal @ {signal_utc} UTC")
        
        # 4. GET ENTRY PRICE (with timezone conversion)
        try:
            candle = self.price_service.get_5min_candle_at_time(symbol, signal_utc)
            
            if not candle:
                raise InsufficientDataError(symbol, signal_utc.isoformat(), "5m")
            
            entry_price = candle['close']
            execution_time_market = candle['timestamp']  # Market local time
            
            logger.info(f"   Entry: ${entry_price:.2f} @ {execution_time_market} (market time)")
            
        except InsufficientDataError as e:
            logger.warning(f"   ⚠️  Skip {symbol}: {e}")
            raise
        
        # 5. DETERMINE DIRECTION
        direction = "LONG" if signal.combined_score >= 25 else "SHORT"
        
        # 6. CALCULATE POSITION SIZE
        position_size, position_value, usd_huf_rate = self._calculate_position_size(
            symbol, entry_price
        )
        
        logger.info(f"   Size: {position_size} shares, {position_value:,.0f} HUF")
        
        # 7. VALIDATE SL/TP
        stop_loss_price = signal.stop_loss
        take_profit_price = signal.take_profit
        
        if not stop_loss_price or not take_profit_price:
            raise InvalidSignalError(signal.id, "Missing SL/TP")
        
        if direction == "LONG":
            if not (stop_loss_price < entry_price < take_profit_price):
                raise InvalidSignalError(
                    signal.id,
                    f"Invalid LONG levels: SL={stop_loss_price}, Entry={entry_price}, TP={take_profit_price}"
                )
        else:
            if not (take_profit_price < entry_price < stop_loss_price):
                raise InvalidSignalError(
                    signal.id,
                    f"Invalid SHORT levels: TP={take_profit_price}, Entry={entry_price}, SL={stop_loss_price}"
                )
        
        # 8. CREATE TRADE RECORD
        trade = SimulatedTrade(
            symbol=symbol,
            direction=direction,
            status="OPEN",
            entry_signal_id=signal.id,
            entry_signal_generated_at=signal.created_at,
            entry_execution_time=execution_time_market,  # Market local time
            entry_price=entry_price,
            entry_score=signal.combined_score,
            entry_confidence=signal.overall_confidence or 0.0,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            initial_stop_loss_price=stop_loss_price,    # Snapshot at entry for reference
            initial_take_profit_price=take_profit_price, # Snapshot at entry for reference
            sl_tp_update_count=0,
            position_size_shares=position_size,
            position_value_huf=position_value,
            usd_huf_rate=usd_huf_rate
        )
        
        self.db.add(trade)
        
        logger.info(f"   ✅ Position opened: {symbol} {direction} @ ${entry_price:.2f}")
        
        return trade

    def open_position_simulated(self, signal: Signal) -> Optional['SimulatedTrade']:
        """
        Open a simulated (fine-tuning only) trade without score/parallel checks.

        Used by BacktestService for:
        - Gyenge signalok (15 <= |score| < 25)
        - Parallel signalok, amik valódi kereskedésben ki lettek volna hagyva

        Az is_real_trade flag-et a hívó állítja be False-ra.

        Raises:
            InsufficientDataError: Ha nincs árfolyamadat
            InvalidSignalError: Ha hiányzik SL/TP vagy érvénytelen szintek
        """
        symbol = signal.ticker_symbol
        signal_utc = signal.created_at

        direction = "LONG" if signal.combined_score >= 0 else "SHORT"

        logger.debug(f"📍 Opening simulated {symbol} ({direction}): Signal @ {signal_utc} UTC")

        # GET ENTRY PRICE
        candle = self.price_service.get_5min_candle_at_time(symbol, signal_utc)
        if not candle:
            raise InsufficientDataError(symbol, signal_utc.isoformat(), "5m")

        entry_price = candle['close']
        execution_time_market = candle['timestamp']

        # CALCULATE POSITION SIZE
        position_size, position_value, usd_huf_rate = self._calculate_position_size(
            symbol, entry_price
        )

        # VALIDATE SL/TP
        stop_loss_price = signal.stop_loss
        take_profit_price = signal.take_profit

        if not stop_loss_price or not take_profit_price:
            raise InvalidSignalError(signal.id, "Missing SL/TP")

        if direction == "LONG":
            if not (stop_loss_price < entry_price < take_profit_price):
                raise InvalidSignalError(
                    signal.id,
                    f"Invalid LONG levels: SL={stop_loss_price}, Entry={entry_price}, TP={take_profit_price}"
                )
        else:
            if not (take_profit_price < entry_price < stop_loss_price):
                raise InvalidSignalError(
                    signal.id,
                    f"Invalid SHORT levels: TP={take_profit_price}, Entry={entry_price}, SL={stop_loss_price}"
                )

        trade = SimulatedTrade(
            symbol=symbol,
            direction=direction,
            status="OPEN",
            entry_signal_id=signal.id,
            entry_signal_generated_at=signal.created_at,
            entry_execution_time=execution_time_market,
            entry_price=entry_price,
            entry_score=signal.combined_score,
            entry_confidence=signal.overall_confidence or 0.0,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            initial_stop_loss_price=stop_loss_price,
            initial_take_profit_price=take_profit_price,
            sl_tp_update_count=0,
            position_size_shares=position_size,
            position_value_huf=position_value,
            usd_huf_rate=usd_huf_rate,
            is_real_trade=False,
        )

        self.db.add(trade)
        return trade

    def close_position(
        self,
        trade: SimulatedTrade,
        exit_reason: str,
        exit_signal: Optional[Signal] = None,
        trigger_time_utc: Optional[datetime] = None
    ) -> SimulatedTrade:
        """
        Close an open position.
        
        Args:
            trade: SimulatedTrade (status='OPEN')
            exit_reason: Exit reason code
            exit_signal: Optional exit signal
            trigger_time_utc: Trigger time in UTC
        
        Returns:
            Updated trade object
        """
        if trade.status != "OPEN":
            raise ValueError(f"Trade {trade.id} not open")
        
        valid_reasons = ['SL_HIT', 'TP_HIT', 'OPPOSING_SIGNAL', 'EOD_AUTO_LIQUIDATION']
        if exit_reason not in valid_reasons:
            raise ValueError(f"Invalid exit_reason: {exit_reason}")
        
        trigger_utc = trigger_time_utc or datetime.utcnow()
        
        logger.info(f"🔴 Closing {trade.symbol}: {exit_reason} @ {trigger_utc} UTC")
        
        # Get exit price (with timezone conversion)
        # For EOD liquidation the trigger_utc is the last valid trading slot.
        # get_5min_candle_at_time adds a 15-min execution offset internally, which would
        # push the lookup into after-hours and cause InsufficientDataError.
        # Work around this by passing trigger_utc - 15min so the internal offset lands
        # exactly on trigger_utc (the last available candle of the day).
        candle_lookup_utc = (
            trigger_utc - timedelta(minutes=self.EXECUTION_DELAY_MINUTES)
            if exit_reason == 'EOD_AUTO_LIQUIDATION'
            else trigger_utc
        )
        try:
            candle = self.price_service.get_5min_candle_at_time(trade.symbol, candle_lookup_utc)

            if not candle:
                # Fallback: use theoretical price
                if exit_reason == 'SL_HIT':
                    exit_price = trade.stop_loss_price
                elif exit_reason == 'TP_HIT':
                    exit_price = trade.take_profit_price
                else:
                    current = self.price_service.get_current_price(trade.symbol)
                    exit_price = current if current else trade.entry_price

                execution_time_market = trigger_utc
                logger.warning(f"   No candle, using theoretical: ${exit_price:.2f}")
            else:
                exit_price = candle['close']
                execution_time_market = candle['timestamp']
                logger.info(f"   Exit: ${exit_price:.2f} @ {execution_time_market}")

        except InsufficientDataError:
            # Use theoretical prices
            if exit_reason == 'SL_HIT':
                exit_price = trade.stop_loss_price
            elif exit_reason == 'TP_HIT':
                exit_price = trade.take_profit_price
            else:
                exit_price = trade.entry_price

            execution_time_market = trigger_utc
            logger.warning(f"   No data, theoretical: ${exit_price:.2f}")
        
        # Calculate P&L
        pnl_percent, pnl_amount_huf = self._calculate_pnl(
            trade.direction,
            trade.entry_price,
            exit_price,
            trade.position_size_shares,
            trade.usd_huf_rate
        )
        
        duration_minutes = int(
            (execution_time_market - trade.entry_execution_time).total_seconds() / 60
        )
        
        # Update trade
        trade.status = "CLOSED"
        trade.exit_trigger_time = trigger_utc
        trade.exit_execution_time = execution_time_market
        trade.exit_price = exit_price
        trade.exit_reason = exit_reason
        trade.pnl_percent = pnl_percent
        trade.pnl_amount_huf = pnl_amount_huf
        trade.duration_minutes = duration_minutes
        
        if exit_signal:
            trade.exit_signal_id = exit_signal.id
            trade.exit_score = exit_signal.combined_score
            trade.exit_confidence = exit_signal.overall_confidence or 0.0
        
        logger.info(
            f"   ✅ Closed: P&L {pnl_percent:+.2f}% ({pnl_amount_huf:+,.0f} HUF), "
            f"{duration_minutes}min"
        )
        
        return trade
    
    def check_exit_triggers(
        self,
        trade: SimulatedTrade,
        check_time_utc: datetime,
        new_signal: Optional[Signal] = None
    ) -> Optional[Dict]:
        """Check exit triggers at specific UTC time"""
        if trade.status != "OPEN":
            return None
        
        # Check price triggers
        price_trigger = self.price_service.check_price_triggers(
            trade.symbol,
            trade.stop_loss_price,
            trade.take_profit_price,
            trade.direction,
            check_time_utc
        )
        
        if price_trigger and price_trigger['triggered']:
            return {
                'should_exit': True,
                'exit_reason': price_trigger['trigger_type'],
                'exit_signal': None,
                'trigger_time': check_time_utc
            }
        
        # Check opposing signal
        if new_signal and self._is_opposing_signal(trade, new_signal):
            return {
                'should_exit': True,
                'exit_reason': 'OPPOSING_SIGNAL',
                'exit_signal': new_signal,
                'trigger_time': new_signal.created_at
            }
        
        # Check EOD liquidation (SHORT only)
        if trade.direction == "SHORT":
            market_time = self.price_service._utc_to_market_time(check_time_utc, trade.symbol)
            if self._is_eod_time(market_time):
                return {
                    'should_exit': True,
                    'exit_reason': 'EOD_AUTO_LIQUIDATION',
                    'exit_signal': None,
                    'trigger_time': check_time_utc
                }
        
        return None
    
    def get_open_positions(self, symbol: Optional[str] = None) -> List[SimulatedTrade]:
        """Get open positions"""
        query = self.db.query(SimulatedTrade).filter(SimulatedTrade.status == "OPEN")
        if symbol:
            query = query.filter(SimulatedTrade.symbol == symbol)
        return query.all()
    
    def _calculate_position_size(self, symbol: str, entry_price: float) -> tuple:
        """Calculate position size"""
        is_huf_ticker = symbol.endswith('.BD')
        
        if is_huf_ticker:
            shares = math.floor(self.TARGET_POSITION_VALUE_HUF / entry_price)
            position_value_huf = shares * entry_price
            usd_huf_rate = None
        else:
            usd_huf_rate = self.price_service.get_usd_huf_rate()
            if not usd_huf_rate:
                raise ExchangeRateError()
            
            target_usd = self.TARGET_POSITION_VALUE_HUF / usd_huf_rate
            shares = math.floor(target_usd / entry_price)
            position_value_huf = shares * entry_price * usd_huf_rate
        
        return shares, position_value_huf, usd_huf_rate
    
    def _calculate_pnl(self, direction: str, entry: float, exit: float, shares: int, usd_huf: Optional[float]) -> tuple:
        """Calculate P&L"""
        if direction == "LONG":
            pnl_percent = ((exit - entry) / entry) * 100
            pnl_per_share = exit - entry
        else:
            pnl_percent = ((entry - exit) / entry) * 100
            pnl_per_share = entry - exit
        
        pnl_amount = pnl_per_share * shares
        pnl_amount_huf = pnl_amount * usd_huf if usd_huf else pnl_amount
        
        return pnl_percent, pnl_amount_huf
    
    def _is_opposing_signal(self, trade: SimulatedTrade, new_signal: Signal) -> bool:
        """Check if signal opposes current position"""
        if new_signal.ticker_symbol != trade.symbol:
            return False
        if abs(new_signal.combined_score) < 25:
            return False
        
        if trade.direction == "LONG":
            return new_signal.combined_score <= -25
        else:
            return new_signal.combined_score >= 25
    
    def _is_eod_time(self, market_time: datetime) -> bool:
        """Check if at/past EOD liquidation time (market local time)"""
        return (
            market_time.hour > self.EOD_LIQUIDATION_HOUR or
            (market_time.hour == self.EOD_LIQUIDATION_HOUR and 
             market_time.minute >= self.EOD_LIQUIDATION_MINUTE)
        )
