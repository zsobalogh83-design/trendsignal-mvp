"""
TrendSignal - Backtest Service (v4 - Fine-tuning simulation)
Processes ALL actionable signals, creates trade for each

SIGNAL THRESHOLDS:
- SIGNAL_THRESHOLD = 15: HOLD zone határa (signal generálás küszöbe, változatlan)
- ALERT_THRESHOLD  = 25: Valódi alert küszöb (Telegram, éles kereskedés)

IS_REAL_TRADE FLAG:
- True:  |score| >= 25 ÉS nem volt párhuzamos pozíció → valódi trade lett volna
- False: |score| < 25 VAGY párhuzamos lett volna → csak modell finomhangoláshoz

LOGIC:
- Minden |score| >= 15 signal szimulálva (HOLD zone-on kívül)
- Alert/exit logika (SL/TP, opposing signal, EOD) minden szimulált trade-re fut
- SL/TP updated in-flight by same-direction signals (signal-based trailing)

SL/TP UPDATE RULES:
- LONG: new SL > current SL → update (move stop up, lock in gains)
         new TP > current TP → update (raise target if market is stronger)
- SHORT: new SL < current SL → update (move stop down, lock in gains)
         new TP < current TP → update (lower target if market is weaker)
- Only non-neutral same-direction signals trigger updates (|score| >= 25)
- The entry signal itself is excluded from updates

Version: 4.0 - Fine-tuning simulation
Date: 2026-02-21
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
import time

from src.models import Signal, SimulatedTrade, PriceData
from src.database import SessionLocal
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
    ) -> Dict:
        """
        Run incremental backtest ensuring every signal has a trade.

        - CLOSED trades: skipped (never modified)
        - OPEN trades: exit triggers checked, SL/TP updated
        - Missing trades: created fresh

        Args:
            date_from: Start date (UTC)
            date_to: End date (UTC)
            symbols: Filter symbols

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
                result = self._process_signal(signal)
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
    
    def _process_signal(self, signal: Signal) -> str:
        """
        Process single signal - ensure it has a trade.

        - CLOSED trade → skip (final)
        - OPEN trade → check exit triggers / update SL-TP
        - No trade → create new

        Returns:
            Status string for stats
        """
        # Check existing trade
        trade = self.db.query(SimulatedTrade).filter(
            SimulatedTrade.entry_signal_id == signal.id
        ).first()

        # Case 1: Already closed - never touch it
        if trade and trade.status == 'CLOSED':
            return 'already_closed'
        
        # Case 2: Open trade - check exit triggers
        if trade and trade.status == 'OPEN':
            was_closed = self._check_and_close_trade(trade)
            return 'newly_closed' if was_closed else 'still_open'
        
        # Case 3: No trade - create new
        # Meghatározzuk, hogy valódi alert-szintű signal-e
        is_real = abs(signal.combined_score) >= self.ALERT_THRESHOLD

        try:
            logger.debug(f"   Creating trade for {signal.ticker_symbol} signal {signal.id} (real={is_real})")

            if is_real:
                # Valódi alert-szintű signal: normál open_position() futtatása
                # (score + parallel ellenőrzéssel)
                trade = self.trade_manager.open_position(signal)
                if trade:
                    trade.is_real_trade = True
            else:
                # Gyenge signal (15 <= |score| < 25): ellenőrzések nélkül szimulálva
                trade = self.trade_manager.open_position_simulated(signal)

            if not trade:
                return 'skipped_invalid'

            self.db.flush()

            was_closed = self._check_and_close_trade(trade)
            return 'newly_opened' if not was_closed else 'newly_closed'

        except InsufficientDataError as e:
            logger.debug(f"   Skip {signal.ticker_symbol}: No price data")
            return 'skipped_no_data'

        except InvalidSignalError as e:
            logger.debug(f"   Skip {signal.ticker_symbol}: {e}")
            return 'skipped_invalid'

        except PositionAlreadyExistsError as e:
            # Párhuzamos trade lett volna - szimulálva is_real_trade=False-szal
            logger.debug(f"   Parallel signal {signal.ticker_symbol}: simulating as non-real trade")
            try:
                trade = self.trade_manager.open_position_simulated(signal)
                if not trade:
                    return 'skipped_invalid'
                self.db.flush()
                was_closed = self._check_and_close_trade(trade)
                return 'newly_opened' if not was_closed else 'newly_closed'
            except (InsufficientDataError, InvalidSignalError) as inner_e:
                logger.debug(f"   Skip parallel {signal.ticker_symbol}: {inner_e}")
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

        # LONG max hold tracking (kereskedési napokban, belépés napja = nap 1)
        from src.config import get_config as _get_config
        _cfg = _get_config()
        trading_days_held = 1
        last_counted_date = trade.entry_execution_time.date()

        # Check every 15 minutes
        while check_time_utc <= now_utc:
            # Skip weekends entirely - jump directly to next market open
            if price_service._is_weekend(check_time_utc):
                check_time_utc = price_service._next_market_open_utc(check_time_utc, trade.symbol)
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
                # Last slot of the trading day: SHORT trades get EOD-liquidated here,
                # LONG trades apply trailing SL then skip to next day.
                if trade.direction == 'SHORT':
                    trigger = self._check_exit_triggers_at_time(trade, check_time_utc)
                    if trigger:
                        logger.debug(
                            f"      Exit: {trade.symbol} {trigger['exit_reason']} "
                            f"@ {check_time_utc} UTC (EOD)"
                        )
                        self.trade_manager.close_position(
                            trade,
                            exit_reason=trigger['exit_reason'],
                            exit_signal=trigger.get('exit_signal'),
                            trigger_time_utc=check_time_utc
                        )
                        return True
                else:
                    # LONG EOD: napszámláló növelése
                    eod_date = check_time_utc.date()
                    if eod_date != last_counted_date:
                        trading_days_held += 1
                        last_counted_date = eod_date

                    # Max hold kényszerzárás
                    if trading_days_held > _cfg.long_max_hold_days:
                        logger.debug(
                            f"      Exit: {trade.symbol} MAX_HOLD_LIQUIDATION "
                            f"@ {check_time_utc} UTC (nap {trading_days_held})"
                        )
                        self.trade_manager.close_position(
                            trade,
                            exit_reason='MAX_HOLD_LIQUIDATION',
                            exit_signal=None,
                            trigger_time_utc=check_time_utc
                        )
                        return True

                    # LONG: nap végén price-based trailing SL igazítás
                    # (tighten_factor alkalmazása késői napokon)
                    self._apply_eod_trailing_sl(trade, check_time_utc, trading_days_held)
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
    
    def _apply_eod_trailing_sl(
        self,
        trade: SimulatedTrade,
        eod_time_utc: datetime,
        trading_days_held: int = 1,
    ) -> None:
        """
        Nap végi price-based trailing SL igazítás LONG trade-eknél.

        Logika:
        - Az entry-kori SL-TP távolságot (%-ban) rögzítjük – ez az eredeti kockázati
          paraméter, amit meg akarunk őrizni.
        - Az aznapi utolsó 5 perces gyertya záróárát (day_close) vesszük referenciának:
          trailing_sl = day_close * (1 - sl_pct)
        - Miért close és nem high?
          A záróár a nap végén kialakult, stabilabb árszint. Az intraday high egy pillanatnyi
          csúcs lehet, amely után rögtön visszaesés következhet – arra alapozva a SL-t
          feleslegesen magasra húznánk, és az egy kisebb korrekció esetén is kiverne.
          A záróár reálisabb: azt az árat tükrözi, amelyen a piac valóban bezárt.
        - Ha a záróár az entry fölé ment → kiszámítjuk az új trailing SL-t
        - Ha ez magasabb az aktuális SL-nél → felhúzzuk (csak felfelé mozog!)
        - trading_days_held >= long_trailing_tighten_day esetén az sl_distance_pct
          szűkül (tighten_factor szorzóval) → agresszívabb profit lock-in a tartás vége felé

        Ez biztosítja, hogy az árfolyam emelkedésével a veszteség csökken, és egy hosszabb
        uptrend esetén végül nyereséggel zárhatunk.
        """
        if trade.direction != 'LONG':
            return

        # Az aznapi utolsó 5m gyertya záróárának lekérése
        try:
            day_start = eod_time_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = eod_time_utc

            db = SessionLocal()
            try:
                result = db.query(PriceData.close).filter(
                    PriceData.ticker_symbol == trade.symbol,
                    PriceData.interval == '5m',
                    PriceData.timestamp >= day_start,
                    PriceData.timestamp <= day_end
                ).order_by(PriceData.timestamp.desc()).first()

                day_close = float(result[0]) if result else None
            finally:
                db.close()

        except Exception as e:
            logger.warning(f"   EOD trailing SL: nem sikerult a napi close lekérese ({trade.symbol}): {e}")
            return

        if not day_close:
            return

        # Csak akkor érdekes, ha a záróár az entry fölé ment
        if day_close <= trade.entry_price:
            return

        # Eredeti SL távolság %-ban az entry ártól
        # LONG: SL < entry_price → sl_pct = (entry - orig_SL) / entry
        orig_sl = trade.initial_stop_loss_price
        if not orig_sl or orig_sl >= trade.entry_price:
            return

        sl_distance_pct = (trade.entry_price - orig_sl) / trade.entry_price

        # Késői napokban szűkebb trailing SL — profit lock-in agresszívabb
        from src.config import get_config as _get_config_tsl
        _cfg_tsl = _get_config_tsl()
        if trading_days_held >= _cfg_tsl.long_trailing_tighten_day:
            sl_distance_pct *= _cfg_tsl.long_trailing_tighten_factor

        # Trailing SL: day_close alapján számítva
        trailing_sl = day_close * (1.0 - sl_distance_pct)

        # Csak felfelé mozgatjuk
        if trailing_sl <= trade.stop_loss_price:
            return

        # Nem mehet a TP fölé (az nem SL lenne, hanem TP)
        trailing_sl = min(trailing_sl, trade.take_profit_price * 0.999)

        old_sl = trade.stop_loss_price
        trade.stop_loss_price = round(trailing_sl, 4)
        trade.sl_tp_update_count = (trade.sl_tp_update_count or 0) + 1
        trade.sl_tp_last_updated_at = eod_time_utc

        logger.debug(
            f"   📈 EOD trailing SL: {trade.symbol} LONG "
            f"day_close={day_close:.4f}, {old_sl:.4f} → {trade.stop_loss_price:.4f} "
            f"(sl_dist={sl_distance_pct*100:.2f}%, @ {eod_time_utc})"
        )

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
        # Triggered at the last valid trading slot of the day: when check_time is
        # within trading hours but check_time + 15min is already outside (market close).
        if trade.direction == 'SHORT':
            price_service = self.trade_manager.price_service
            if not price_service._is_weekend(check_time_utc):
                check_plus_15 = check_time_utc + timedelta(minutes=15)
                if not price_service._is_trading_hours(check_plus_15, trade.symbol):
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
        Update trade SL from a same-direction signal if the new level is more
        favourable (locks in more profit / reduces risk).

        Csak az SL-t frissítjük signal alapján – a TP-t NEM.
        Indok: a TP emelése megakadályozza a nyereség realizálását. Ha az esti signal
        TP-t 273-ról 291-re emeli, de az ár másnap csak 279-ig megy, a trade sosem
        zár TP-n. Az entry-kori TP marad érvényes célárként; a trailing SL (EOD
        price-based) gondoskodik a nyereség védelméről, ha az ár emelkedik.

        LONG: jobb SL = magasabb SL (közelebb az árhoz alulról → profit lock-in)
        SHORT: jobb SL = alacsonyabb SL (közelebb az árhoz felülről → profit lock-in)

        Returns:
            True if SL was updated, False otherwise
        """
        if signal.stop_loss is None:
            return False

        updated = False

        if trade.direction == 'LONG':
            if signal.stop_loss > trade.stop_loss_price:
                logger.debug(
                    f"      SL updated {trade.symbol} LONG: "
                    f"{trade.stop_loss_price:.4f} -> {signal.stop_loss:.4f} "
                    f"(signal {signal.id} @ {check_time_utc})"
                )
                trade.stop_loss_price = signal.stop_loss
                updated = True

        else:  # SHORT
            if signal.stop_loss < trade.stop_loss_price:
                logger.debug(
                    f"      SL updated {trade.symbol} SHORT: "
                    f"{trade.stop_loss_price:.4f} -> {signal.stop_loss:.4f} "
                    f"(signal {signal.id} @ {check_time_utc})"
                )
                trade.stop_loss_price = signal.stop_loss
                updated = True

        if updated:
            trade.sl_tp_update_count = (trade.sl_tp_update_count or 0) + 1
            trade.sl_tp_last_updated_at = check_time_utc

        return updated
    
    def _trading_session_start(self, check_time_utc: datetime, symbol: str) -> datetime:
        """
        Az előző kereskedési nap nyitányától keresünk signalokat.

        PROBLÉMA: A US piaci signalok este 18-22 UTC-kor érkeznek (piaczárás után).
        Ha check_time = Feb 4 14:30 UTC és day_start = Feb 4 00:00 UTC, akkor a
        Feb 3 19:15 UTC-kor érkezett esti signalok LÁTHATATLANOK maradnak –
        mert az előző UTC nap estéjén keletkeztek.

        MEGOLDÁS: A keresési ablak az ELŐZŐ kereskedési nap nyitányától indul.
        - US (nem .BD): nyitány 14:30 UTC → session_start = tegnap 14:30 UTC
        - BÉT (.BD):    nyitány 08:00 UTC → session_start = tegnap 08:00 UTC

        Ez biztosítja, hogy az előző est összes signalját (18-22 UTC) a következő
        nap kereskedési ideje alatt (14:30-21:00 UTC) is látjuk.

        Hétvégi napokat visszafelé átugrik (pénteki nyitányig megy vissza).
        """
        if symbol.endswith('.BD'):
            open_hour, open_minute = 8, 0
        else:
            open_hour, open_minute = 14, 30

        # Az előző kereskedési nap nyitánya: 1 nappal visszalépünk, hétvégét átugorjuk
        prev_day = check_time_utc - timedelta(days=1)
        # Hétvégén visszamegyünk péntekig
        while prev_day.weekday() >= 5:  # 5=Sat, 6=Sun
            prev_day -= timedelta(days=1)

        return prev_day.replace(
            hour=open_hour, minute=open_minute, second=0, microsecond=0
        )

    def _find_opposing_signal(self, trade: SimulatedTrade, check_time_utc: datetime) -> Optional[Signal]:
        """Find opposing signal since the current trading session start up to check_time.

        Uses trading-session boundaries instead of UTC-midnight so that signals
        arriving in the evening (e.g. 19-22 UTC for US markets) are visible during
        the NEXT trading day's checks (14:30+ UTC), which are in a different UTC day.

        We return the strongest (highest abs score) opposing signal so the most
        decisive reversal wins.
        """
        session_start = self._trading_session_start(check_time_utc, trade.symbol)

        signals = self.db.query(Signal).filter(
            and_(
                Signal.ticker_symbol == trade.symbol,
                Signal.created_at >= session_start,
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
        """Find the strongest same-direction signal since the current trading session
        start up to check_time.

        Uses trading-session boundaries (not UTC midnight) so that evening signals
        (19-22 UTC for US) are visible during the next trading day's 14:30+ UTC checks.

        Used for signal-based adaptive SL/TP update:
        - LONG trade → signals with combined_score >= 25
        - SHORT trade → signals with combined_score <= -25

        The entry signal is excluded. Only signals with at least one of SL/TP are useful.
        """
        session_start = self._trading_session_start(check_time_utc, trade.symbol)

        signals = self.db.query(Signal).filter(
            and_(
                Signal.ticker_symbol == trade.symbol,
                Signal.created_at >= session_start,
                Signal.created_at <= check_time_utc,
                Signal.id != trade.entry_signal_id
            )
        ).all()

        best = None
        for signal in signals:
            if signal.stop_loss is None and signal.take_profit is None:
                continue

            if trade.direction == 'LONG' and signal.combined_score >= 25:
                if best is None or abs(signal.combined_score) > abs(best.combined_score):
                    best = signal
            elif trade.direction == 'SHORT' and signal.combined_score <= -25:
                if best is None or abs(signal.combined_score) > abs(best.combined_score):
                    best = signal

        return best

    ALERT_THRESHOLD = 25  # Valódi alert küszöb (Telegram, real trade)
    SIGNAL_THRESHOLD = 15  # Signal generálási küszöb (HOLD zone határa)

    def _get_signals(
        self,
        date_from: Optional[datetime],
        date_to: Optional[datetime],
        symbols: Optional[List[str]]
    ) -> List[Signal]:
        """Get all actionable signals to process.

        Két kategória kerül szimulációba:
        - |score| >= 25: valódi alert-szintű signalok (is_real_trade lehet True vagy False)
        - 15 <= |score| < 25: gyengébb signalok (is_real_trade=False, csak finomhangoláshoz)
        """
        query = self.db.query(Signal)

        if date_from:
            query = query.filter(Signal.created_at >= date_from)

        if date_to:
            query = query.filter(Signal.created_at <= date_to)

        if symbols:
            query = query.filter(Signal.ticker_symbol.in_(symbols))

        # Minden nem-neutral signal (HOLD zone határán túl)
        query = query.filter(
            or_(
                Signal.combined_score >= self.SIGNAL_THRESHOLD,
                Signal.combined_score <= -self.SIGNAL_THRESHOLD
            )
        )

        query = query.order_by(Signal.created_at.asc())

        return query.all()
