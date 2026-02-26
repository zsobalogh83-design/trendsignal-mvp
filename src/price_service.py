"""
TrendSignal - Price Service (SIMPLE - No Timezone Conversion)
DB-first price lookup with UTC timestamps only

ASSUMPTIONS:
- Signal.created_at = UTC (timezone-naive)
- PriceData.timestamp = UTC (timezone-naive)
- NO timezone conversion needed
- Trading hours check: 9:30-16:00 ET (14:30-21:00 UTC), 9:00-17:00 CET (8:00-16:00 UTC)

Version: 3.0 - Simplified
Date: 2026-02-17
"""

import yfinance as yf
from datetime import datetime, timedelta, time
from typing import Optional, Dict
import logging
import pytz

from src.exceptions import InsufficientDataError
from src.database import SessionLocal
from src.models import PriceData

logger = logging.getLogger(__name__)


class PriceService:
    """Simple price service - UTC only, no timezone games"""
    
    def __init__(self):
        """Initialize price service"""
        pass
    
    def _is_trading_hours(self, utc_time: datetime, symbol: str) -> bool:
        """
        Check if UTC time is during market trading hours.
        
        Args:
            utc_time: UTC timestamp
            symbol: Ticker symbol
        
        Returns:
            True if during trading hours
        """
        # Get hour in UTC
        hour = utc_time.hour
        minute = utc_time.minute
        time_decimal = hour + minute / 60.0
        
        if symbol.endswith('.BD'):
            # BÉT: 9:00-17:00 CET = 8:00-16:00 UTC
            return 8.0 <= time_decimal < 16.0
        else:
            # US: 9:30-16:00 ET = 14:30-21:00 UTC
            return 14.5 <= time_decimal < 21.0
    
    def _is_weekend(self, utc_time: datetime) -> bool:
        """Check if weekend (Saturday=5, Sunday=6)"""
        return utc_time.weekday() >= 5

    def _next_market_open_utc(self, utc_time: datetime, symbol: str) -> datetime:
        """
        Return the next market open time in UTC after utc_time,
        if utc_time is outside trading hours or on a weekend.

        Market open times (UTC):
            BÉT (.BD): 08:00 UTC (09:00 CET, winter) – use 08:00 as conservative open
            US:        14:30 UTC (09:30 ET)

        Args:
            utc_time: UTC datetime that is outside trading hours
            symbol: Ticker symbol

        Returns:
            UTC datetime of the next market open
        """
        if symbol.endswith('.BD'):
            open_hour, open_minute = 8, 0      # 08:00 UTC = 09:00 CET
        else:
            open_hour, open_minute = 14, 30    # 14:30 UTC = 09:30 ET

        candidate = utc_time.replace(hour=open_hour, minute=open_minute, second=0, microsecond=0)

        # If we're already past today's open, move to next day
        if candidate <= utc_time:
            candidate += timedelta(days=1)

        # Skip weekends (Saturday=5, Sunday=6)
        while candidate.weekday() >= 5:
            candidate += timedelta(days=1)

        return candidate

    def _utc_to_market_time(self, utc_time: datetime, symbol: str) -> datetime:
        """
        Convert UTC datetime to market local time.

        Args:
            utc_time: Timezone-naive UTC datetime
            symbol: Ticker symbol (determines market timezone)

        Returns:
            Timezone-naive datetime in market local time
        """
        if symbol.endswith('.BD'):
            # BÉT: CET/CEST (Europe/Budapest)
            market_tz = pytz.timezone('Europe/Budapest')
        else:
            # US markets: ET (America/New_York)
            market_tz = pytz.timezone('America/New_York')

        # Localize as UTC then convert
        utc_aware = pytz.utc.localize(utc_time)
        market_aware = utc_aware.astimezone(market_tz)

        # Return timezone-naive market time
        return market_aware.replace(tzinfo=None)

    def get_5min_candle_at_time(
        self, 
        symbol: str, 
        signal_time_utc: datetime,
        tolerance_minutes: int = 15
    ) -> Optional[Dict]:
        """
        Get 5-minute candle near signal execution time.
        
        SIMPLE LOGIC:
        1. Execution time = Signal time + 15 min
        2. Query DB for candle within ±15 min
        3. If not found, fallback to yfinance (ONLY if trading hours)
        
        Args:
            symbol: Ticker symbol
            signal_time_utc: Signal creation time (UTC)
            tolerance_minutes: Search window (default: 15)
        
        Returns:
            Dict with candle data or None
        
        Raises:
            InsufficientDataError: If no data available
        """
        # Calculate execution time (UTC): signal + 15 min delay
        execution_time_utc = signal_time_utc + timedelta(minutes=15)

        # If execution time falls outside trading hours or on a weekend,
        # move to next market open (signal arrived after-hours or manually)
        if self._is_weekend(execution_time_utc) or not self._is_trading_hours(execution_time_utc, symbol):
            next_open = self._next_market_open_utc(execution_time_utc, symbol)
            logger.info(
                f"   {symbol}: Execution {execution_time_utc} outside trading hours → "
                f"forwarding to next open {next_open} UTC"
            )
            execution_time_utc = next_open

        logger.debug(f"   {symbol}: Signal {signal_time_utc} → execution {execution_time_utc} UTC")
        
        # STEP 1: Try DB first (FAST)
        try:
            db = SessionLocal()
            try:
                # Search window
                time_start = execution_time_utc - timedelta(minutes=tolerance_minutes)
                time_end = execution_time_utc + timedelta(minutes=tolerance_minutes)
                
                # Query DB (timestamps are UTC)
                candles = db.query(PriceData).filter(
                    PriceData.ticker_symbol == symbol,
                    PriceData.interval == '5m',
                    PriceData.timestamp >= time_start,
                    PriceData.timestamp <= time_end
                ).all()
                
                if candles:
                    # Find closest
                    closest = min(
                        candles,
                        key=lambda c: abs((c.timestamp - execution_time_utc).total_seconds())
                    )
                    
                    time_diff_minutes = abs(
                        (closest.timestamp - execution_time_utc).total_seconds() / 60
                    )
                    
                    if time_diff_minutes <= tolerance_minutes:
                        logger.info(
                            f"   ✅ DB: {symbol} @ {closest.timestamp} "
                            f"(offset: {time_diff_minutes:.1f}min), close=${closest.close:.2f}"
                        )
                        
                        return {
                            'timestamp': closest.timestamp,
                            'open': float(closest.open),
                            'high': float(closest.high),
                            'low': float(closest.low),
                            'close': float(closest.close),
                            'volume': int(closest.volume)
                        }
            
            finally:
                db.close()
        
        except Exception as e:
            logger.warning(f"   DB error for {symbol}: {e}")
        
        # STEP 2: Fallback to yfinance (ONLY if trading hours AND already in the past)

        # Skip if the candle is in the future – data doesn't exist yet
        now_utc = datetime.utcnow()
        if execution_time_utc > now_utc:
            logger.debug(f"   {symbol}: Execution time {execution_time_utc} is in the future, skip yfinance")
            raise InsufficientDataError(symbol, execution_time_utc.isoformat(), "5m")

        # Skip if weekend (no point querying yfinance)
        if self._is_weekend(execution_time_utc):
            logger.debug(f"   {symbol}: Weekend UTC time, skip yfinance")
            raise InsufficientDataError(symbol, execution_time_utc.isoformat(), "5m")

        # Skip if outside trading hours (pre-market / after-hours)
        if not self._is_trading_hours(execution_time_utc, symbol):
            logger.debug(f"   {symbol}: Outside trading hours, skip yfinance")
            raise InsufficientDataError(symbol, execution_time_utc.isoformat(), "5m")

        # Skip if the yfinance query window (execution_time - 2h) falls on a weekend –
        # yfinance returns no data for weekend windows and logs misleading "delisted" errors
        yf_window_start = execution_time_utc - timedelta(hours=2)
        if self._is_weekend(yf_window_start):
            logger.debug(f"   {symbol}: yfinance window start {yf_window_start} is on weekend, skip yfinance")
            raise InsufficientDataError(symbol, execution_time_utc.isoformat(), "5m")
        
        # If here: trading hours, query yfinance
        logger.info(f"   ⚠️  DB miss for {symbol}, querying yfinance...")
        
        try:
            # Localize to UTC so yfinance.history() gets correct Unix timestamps.
            # Naive datetimes are interpreted as local time by Python's .timestamp(),
            # which shifts the query by the server's UTC offset (e.g. +5h on EST),
            # landing it after market close and causing "Data doesn't exist" errors.
            start_time = pytz.utc.localize(execution_time_utc - timedelta(hours=2))
            end_time = pytz.utc.localize(execution_time_utc + timedelta(hours=1))

            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_time, end=end_time, interval="5m")
            
            if df.empty:
                raise InsufficientDataError(symbol, execution_time_utc.isoformat(), "5m")

            # Convert timezone-aware index to timezone-naive UTC
            # yfinance returns timestamps in the exchange's local timezone (ET for US, CET for BÉT)
            # tz_convert('UTC') correctly handles DST, then strip tzinfo for naive comparison
            if df.index.tzinfo is not None or hasattr(df.index, 'tz') and df.index.tz is not None:
                df.index = df.index.tz_convert('UTC').tz_localize(None)
            # else: already naive, leave as-is
            
            # Find closest
            time_differences = abs(df.index - execution_time_utc)
            closest_idx = time_differences.argmin()
            closest_candle = df.iloc[closest_idx]
            closest_time = df.index[closest_idx]
            
            time_diff_minutes = abs((closest_time - execution_time_utc).total_seconds() / 60)
            
            if time_diff_minutes > tolerance_minutes:
                raise InsufficientDataError(symbol, execution_time_utc.isoformat(), "5m")
            
            candle_data = {
                'timestamp': closest_time,
                'open': float(closest_candle['Open']),
                'high': float(closest_candle['High']),
                'low': float(closest_candle['Low']),
                'close': float(closest_candle['Close']),
                'volume': int(closest_candle['Volume'])
            }
            
            logger.info(
                f"   ✅ yfinance: {symbol} @ {closest_time} "
                f"(offset: {time_diff_minutes:.1f}min), close=${candle_data['close']:.2f}"
            )
            
            return candle_data
            
        except InsufficientDataError:
            raise
        except Exception as e:
            logger.error(f"   yfinance error: {e}")
            raise InsufficientDataError(symbol, execution_time_utc.isoformat(), "5m")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")
            
            if data.empty:
                return None
            
            return float(data['Close'].iloc[-1])
            
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None
    
    def get_usd_huf_rate(self) -> Optional[float]:
        """Get current USD/HUF exchange rate"""
        try:
            ticker = yf.Ticker("USDHUF=X")
            data = ticker.history(period="1d")
            
            if data.empty:
                return None
            
            rate = float(data['Close'].iloc[-1])
            return rate
            
        except Exception as e:
            logger.error(f"Error fetching USD/HUF rate: {e}")
            return None
    
    def check_price_triggers(
        self,
        symbol: str,
        stop_loss: float,
        take_profit: float,
        direction: str,
        check_time_utc: datetime,
        tolerance_minutes: int = 15
    ) -> Optional[Dict]:
        """
        Check if SL/TP was hit at specific UTC time.
        
        Returns:
            Dict with trigger info or None
        """
        try:
            candle = self.get_5min_candle_at_time(symbol, check_time_utc, tolerance_minutes)
            
            if not candle:
                return None
            
            candle_high = candle['high']
            candle_low = candle['low']
            
            if direction == 'LONG':
                if candle_low <= stop_loss:
                    return {'triggered': True, 'trigger_type': 'SL_HIT', 'candle': candle}
                elif candle_high >= take_profit:
                    return {'triggered': True, 'trigger_type': 'TP_HIT', 'candle': candle}
            
            elif direction == 'SHORT':
                if candle_high >= stop_loss:
                    return {'triggered': True, 'trigger_type': 'SL_HIT', 'candle': candle}
                elif candle_low <= take_profit:
                    return {'triggered': True, 'trigger_type': 'TP_HIT', 'candle': candle}
            
            return {'triggered': False, 'trigger_type': None, 'candle': candle}
            
        except InsufficientDataError:
            return None
        except Exception as e:
            logger.error(f"Error checking price triggers: {e}")
            return None
