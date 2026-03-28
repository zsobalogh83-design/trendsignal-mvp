"""
TrendSignal - Archive Backtest Service
Visszamenőleges trade szimuláció archive_signals + price_data_alpaca alapján.

Logika:
- Minden BUY/SELL archive_signal kap egy archive_simulated_trade-et
- Entry: signal_timestamp utáni első kereskedési bar NYITÓÁRÁN (+15 perces végrehajtási késés)
- SL/TP: a signal által javasolt szintek; az új entry price alapján érvényesség-ellenőrzés fut
- Exit prioritás (bar-onként, live-val egyező sorrendben):
    1. STAGNATION_EXIT       – 6 egymást követő 15m bar az entry ±30% × initial_risk sávon belül
    2. SL_HIT / TP_HIT       – stop/target elérése (TP/SL ütközésnél nyitóárhoz közelebb lévő nyer)
    2b. Intraday breakeven   – ár eléri az entry + 0.5×initial_risk szintet → SL = entry;
                               TP tightening – ár 50%+ úton van a TP felé → TP szűkítése
    3. OPPOSING_SIGNAL       – ellentétes alert-szintű signal, +15 perces végrehajtással;
                               kereskedési időn kívüli végrehajtásnál következő nap nyitóján
    4. EOD_AUTO_LIQUIDATION  – SHORT trade-ek nap végén kötelezően zárnak
    5. MAX_HOLD_LIQUIDATION  – 10 kereskedési nap után kényszerzárás
- SL dinamikus frissítés (live-val egyező):
    - Azonos irányú signal (|score| >= 25) → SL frissítés ha kedvezőbb (profit lock-in)
      LONG: új SL > jelenlegi SL → frissít; SHORT: új SL < jelenlegi SL → frissít
    - TP-t NEM frissítjük signal alapján (entry-kori TP marad a cél)
    - EOD trailing SL (csak LONG): nap végén day_close × (1 - sl_pct), csak felfelé
      3. naptól szűkebb szorzó (LONG_TRAILING_TIGHTEN_FACTOR) → profit lock-in
- TP/SL ütközés esetén: amelyik közelebb volt a bar nyitóárhoz, az teljesül előbb
- Teljesítmény: ticker-enkénti in-memory price lookup (1 DB lekérés/ticker)

Version: 4.0 – Intraday breakeven + TP tightening + OPP/EOD prioritás igazítás (live-val egyező)
"""

from __future__ import annotations

import logging
import sqlite3
from bisect import bisect_left
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Konstansok ──────────────────────────────────────────────────────────────
ALERT_THRESHOLD              = 25          # is_real_trade határ (score >= 25)
MAX_HOLD_BARS                = 10 * 26     # 10 kereskedési nap × 26 bar/nap (15m, 09:30-16:00 ET)
US_OPEN_UTC                  = (14, 30)    # 09:30 ET
US_CLOSE_UTC                 = (21,  0)    # 16:00 ET
STAGNATION_CONSECUTIVE_SLOTS = 10          # 10 × 15min = 150 perc oldalazás → exit
STAGNATION_BAND_FACTOR       = 0.20        # sáv = 0.20 × initial_risk
LONG_TRAILING_TIGHTEN_DAY    = 3           # ettől a naptól szűkebb trailing SL (live-val egyező)
LONG_TRAILING_TIGHTEN_FACTOR = 0.6         # sl_pct szorzója a tighten naptól


# ── Segédfüggvények ──────────────────────────────────────────────────────────

def _is_trading_hours(dt: datetime, symbol: str) -> bool:
    h, m = dt.hour, dt.minute
    td = h + m / 60.0
    if symbol.endswith(".BD"):
        return 8.0 <= td < 16.0
    return 14.5 <= td < 21.0


def _is_weekend(dt: datetime) -> bool:
    return dt.weekday() >= 5


def _next_market_open(dt: datetime, symbol: str) -> datetime:
    open_h, open_m = (8, 0) if symbol.endswith(".BD") else US_OPEN_UTC
    candidate = dt.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
    if candidate <= dt:
        candidate += timedelta(days=1)
    while _is_weekend(candidate):
        candidate += timedelta(days=1)
    return candidate


# ── ArchiveBacktestService ────────────────────────────────────────────────────

class ArchiveBacktestService:
    """
    Ticker-enkénti bulk feldolgozás:
    1. Betölti az összes 15m bar-t memóriába (price_data_alpaca, interval='15m')
    2. Betölti az összes archive_signal-t az adott tickerre
    3. Minden BUY/SELL signalhoz szimulál egy trade-et
    4. Bulk INSERT az archive_simulated_trades táblába
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    # ── Publikus API ─────────────────────────────────────────────────────────

    def run(
        self,
        symbols: Optional[List[str]] = None,
        score_threshold: float = 15.0,
    ) -> Dict:
        """
        Futtatja az archív backtestet az összes (vagy megadott) tickerre.

        Args:
            symbols:         Ha None, minden ticker fut.
            score_threshold: Minimum |combined_score| a szimulációhoz.

        Returns:
            Stats dict.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # Törli az előző futtatás eredményeit (teljes újrafuttatás)
            if symbols:
                placeholders = ",".join("?" * len(symbols))
                conn.execute(
                    f"DELETE FROM archive_simulated_trades WHERE ticker_symbol IN ({placeholders})",
                    symbols,
                )
            else:
                conn.execute("DELETE FROM archive_simulated_trades")
            conn.commit()

            all_symbols = self._get_symbols(conn, symbols)
            logger.info(f"Archive backtest: {len(all_symbols)} ticker")

            total_stats = {
                "tickers": 0,
                "signals_processed": 0,
                "trades_created": 0,
                "tp_hit": 0,
                "sl_hit": 0,
                "stagnation": 0,
                "opposing": 0,
                "eod": 0,
                "max_hold": 0,
                "open": 0,
                "skipped": 0,
            }

            for symbol in all_symbols:
                stats = self._run_ticker(conn, symbol, score_threshold)
                total_stats["tickers"] += 1
                for k in ("signals_processed", "trades_created", "tp_hit",
                          "sl_hit", "stagnation", "opposing", "eod", "max_hold", "open", "skipped"):
                    total_stats[k] += stats.get(k, 0)
                logger.info(
                    f"  {symbol}: {stats['trades_created']} trade "
                    f"(TP={stats['tp_hit']} SL={stats['sl_hit']} "
                    f"STAG={stats['stagnation']} OPP={stats['opposing']} "
                    f"EOD={stats['eod']} MAX={stats['max_hold']} "
                    f"OPEN={stats['open']} SKIP={stats['skipped']})"
                )

            conn.commit()
            return total_stats

        finally:
            conn.close()

    # ── Belső metódusok ──────────────────────────────────────────────────────

    def _get_symbols(self, conn: sqlite3.Connection, symbols: Optional[List[str]]) -> List[str]:
        if symbols:
            return symbols
        rows = conn.execute(
            "SELECT DISTINCT ticker_symbol FROM archive_signals WHERE decision != 'HOLD'"
        ).fetchall()
        return [r["ticker_symbol"] for r in rows]

    def _run_ticker(
        self, conn: sqlite3.Connection, symbol: str, score_threshold: float
    ) -> Dict:
        stats = {
            "signals_processed": 0, "trades_created": 0,
            "tp_hit": 0, "sl_hit": 0, "stagnation": 0,
            "opposing": 0, "eod": 0, "max_hold": 0, "open": 0, "skipped": 0,
        }

        # 1. Betöltjük az összes 15m bar-t memóriába
        #    bars: lista, rendezett timestamp szerint
        #    bars_ts: csak a timestamp értékek (bisect kereséshez)
        bars = self._load_price_bars(conn, symbol)
        if not bars:
            logger.warning(f"  {symbol}: nincs 15m ár adat, kihagyva")
            return stats

        bars_ts = [b["ts"] for b in bars]

        # 2. Betöltjük az összes archive_signal-t az adott tickerre
        signals = self._load_signals(conn, symbol, score_threshold)
        logger.debug(f"  {symbol}: {len(signals)} signal, {len(bars)} bar")

        # 3. Betöltjük az összes opposing signal timestampjét irány szerint
        #    opp_long[i]  = BUY signal timestamp (ezek SHORT trade-et zárnak)
        #    opp_short[i] = SELL signal timestamp (ezek LONG trade-et zárnak)
        opp_long  = sorted([s["ts"] for s in signals if s["score"] >= ALERT_THRESHOLD])
        opp_short = sorted([s["ts"] for s in signals if s["score"] <= -ALERT_THRESHOLD])

        # Azonos irányú signal lista SL frissítéshez (live-val egyező logika):
        # (ts, sl) tuple-ok, alert-szintű signalok, SL-lel rendelkezők
        same_dir_long  = sorted(
            [(s["ts"], s["stop_loss"]) for s in signals
             if s["score"] >= ALERT_THRESHOLD and s["stop_loss"]],
            key=lambda x: x[0],
        )
        same_dir_short = sorted(
            [(s["ts"], s["stop_loss"]) for s in signals
             if s["score"] <= -ALERT_THRESHOLD and s["stop_loss"]],
            key=lambda x: x[0],
        )

        # 4. Minden signalhoz szimuláció
        trades_to_insert: List[Dict] = []

        for sig in signals:
            stats["signals_processed"] += 1

            signal_sl    = sig["stop_loss"]
            signal_tp    = sig["take_profit"]
            signal_entry = sig["signal_entry_price"]

            if not signal_sl or not signal_tp or not signal_entry or signal_entry <= 0:
                stats["skipped"] += 1
                continue

            direction = "LONG" if sig["score"] > 0 else "SHORT"
            is_real   = abs(sig["score"]) >= ALERT_THRESHOLD
            signal_ts = sig["ts"]

            # Entry: a signal timestampje utáni első kereskedési bar nyitóárán
            # (15 perces végrehajtási késés, mint a valóságban)
            entry_bar_idx = self._find_next_bar(bars_ts, signal_ts)
            if entry_bar_idx is None:
                stats["skipped"] += 1
                continue

            entry_bar   = bars[entry_bar_idx]
            entry_time  = entry_bar["ts"]
            entry_price = entry_bar["open"]   # ← következő bar nyitóárán lépünk be

            # Pre-market/after-hours entry guard:
            # Ha az entry bar kereskedési időn kívülre esne (pl. utolsó bar + 15 perc = másnap),
            # vagy más kereskedési napra csúszik, a trade-et nem kötjük meg.
            if (_is_weekend(entry_time) or
                    not _is_trading_hours(entry_time, symbol) or
                    entry_time.date() != signal_ts.date()):
                stats["skipped"] += 1
                continue

            if not entry_price:
                stats["skipped"] += 1
                continue

            # SL/TP igazítása az actual entry price-hoz (relatív távolságok megőrzése)
            # LONG: sl = entry*(1 - sl_pct), tp = entry*(1 + tp_pct)
            # SHORT: sl = entry*(1 + sl_pct), tp = entry*(1 - tp_pct)
            if direction == "LONG":
                sl_pct = (signal_entry - signal_sl) / signal_entry
                tp_pct = (signal_tp - signal_entry) / signal_entry
                sl = round(entry_price * (1.0 - sl_pct), 4)
                tp = round(entry_price * (1.0 + tp_pct), 4)
            else:
                sl_pct = (signal_sl - signal_entry) / signal_entry
                tp_pct = (signal_entry - signal_tp) / signal_entry
                sl = round(entry_price * (1.0 + sl_pct), 4)
                tp = round(entry_price * (1.0 - tp_pct), 4)

            # Opposing signal lista: LONG trade-et SELL zár, SHORT trade-et BUY zár
            opp_list = opp_short if direction == "LONG" else opp_long

            # Azonos irányú signal lista SL frissítéshez
            same_dir = same_dir_long if direction == "LONG" else same_dir_short

            # Exit szimulálás
            result = self._simulate_exit(
                bars=bars,
                bars_ts=bars_ts,
                start_idx=entry_bar_idx,
                direction=direction,
                entry_price=entry_price,
                sl=sl,
                tp=tp,
                orig_sl_pct=sl_pct,
                signal_ts=signal_ts,
                opp_list=opp_list,
                same_dir_signals=same_dir,
                symbol=symbol,
            )

            exit_price  = result["exit_price"]
            exit_time   = result["exit_time"]
            exit_reason = result["exit_reason"]
            status      = "CLOSED" if exit_reason != "OPEN" else "OPEN"
            duration    = result["duration_bars"]

            if exit_price and entry_price:
                if direction == "LONG":
                    pnl_pct = (exit_price - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - exit_price) / entry_price * 100
            else:
                pnl_pct = None

            trades_to_insert.append({
                "archive_signal_id": sig["id"],
                "ticker_symbol":     symbol,
                "direction":         direction,
                "status":            status,
                "entry_price":       entry_price,
                "entry_time":        entry_time.isoformat(),
                "stop_loss_price":   sl,
                "take_profit_price": tp,
                "exit_price":        exit_price,
                "exit_time":         exit_time.isoformat() if exit_time else None,
                "exit_reason":       exit_reason,
                "pnl_percent":       round(pnl_pct, 4) if pnl_pct is not None else None,
                "duration_bars":     duration,
                "combined_score":    sig["score"],
                "overall_confidence": sig["confidence"],
                "is_real_trade":     1 if is_real else 0,
            })

            # Stat
            stats["trades_created"] += 1
            if exit_reason == "TP_HIT":
                stats["tp_hit"] += 1
            elif exit_reason == "SL_HIT":
                stats["sl_hit"] += 1
            elif exit_reason == "STAGNATION_EXIT":
                stats["stagnation"] += 1
            elif exit_reason == "OPPOSING_SIGNAL":
                stats["opposing"] += 1
            elif exit_reason == "EOD_AUTO_LIQUIDATION":
                stats["eod"] += 1
            elif exit_reason == "MAX_HOLD_LIQUIDATION":
                stats["max_hold"] += 1
            else:
                stats["open"] += 1

        # 5. Bulk INSERT
        if trades_to_insert:
            conn.executemany(
                """INSERT INTO archive_simulated_trades
                   (archive_signal_id, ticker_symbol, direction, status,
                    entry_price, entry_time, stop_loss_price, take_profit_price,
                    exit_price, exit_time, exit_reason,
                    pnl_percent, duration_bars, combined_score,
                    overall_confidence, is_real_trade)
                   VALUES
                   (:archive_signal_id, :ticker_symbol, :direction, :status,
                    :entry_price, :entry_time, :stop_loss_price, :take_profit_price,
                    :exit_price, :exit_time, :exit_reason,
                    :pnl_percent, :duration_bars, :combined_score,
                    :overall_confidence, :is_real_trade)
                """,
                trades_to_insert,
            )

        return stats

    # ── Ár / bar segédek ─────────────────────────────────────────────────────

    def _load_price_bars(self, conn: sqlite3.Connection, symbol: str) -> List[Dict]:
        """Betölti az összes 15m bar-t memóriába rendezett listába."""
        rows = conn.execute(
            """SELECT timestamp, open, high, low, close
               FROM price_data_alpaca
               WHERE ticker_symbol = ? AND interval = '15m'
               ORDER BY timestamp""",
            (symbol,),
        ).fetchall()
        result = []
        for r in rows:
            ts = datetime.fromisoformat(r["timestamp"]) if isinstance(r["timestamp"], str) else r["timestamp"]
            result.append({
                "ts":    ts,
                "open":  r["open"],
                "high":  r["high"],
                "low":   r["low"],
                "close": r["close"],
            })
        return result

    def _load_signals(
        self, conn: sqlite3.Connection, symbol: str, score_threshold: float
    ) -> List[Dict]:
        """Betölti az összes BUY/SELL archive_signal-t."""
        rows = conn.execute(
            """SELECT id, signal_timestamp, combined_score, overall_confidence,
                      entry_price, stop_loss, take_profit
               FROM archive_signals
               WHERE ticker_symbol = ?
                 AND decision != 'HOLD'
                 AND ABS(combined_score) >= ?
               ORDER BY signal_timestamp""",
            (symbol, score_threshold),
        ).fetchall()
        result = []
        for r in rows:
            ts = r["signal_timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            result.append({
                "id":                r["id"],
                "ts":                ts,
                "score":             r["combined_score"],
                "confidence":        r["overall_confidence"],
                "signal_entry_price": r["entry_price"],   # signal bar close – SL/TP referencia
                "stop_loss":         r["stop_loss"],
                "take_profit":       r["take_profit"],
            })
        return result

    def _find_next_bar(self, bars_ts: List[datetime], signal_ts: datetime) -> Optional[int]:
        """Megkeresi a signal_ts utáni első bar indexét (bisect)."""
        idx = bisect_left(bars_ts, signal_ts)
        # A signal_ts pillanatában lévő bar is az entry lehet, de
        # inkább a következőt vesszük (execution = következő bar nyitó)
        if idx < len(bars_ts) and bars_ts[idx] <= signal_ts:
            idx += 1
        return idx if idx < len(bars_ts) else None

    # ── Exit szimuláció ───────────────────────────────────────────────────────

    def _simulate_exit(
        self,
        bars: List[Dict],
        bars_ts: List[datetime],
        start_idx: int,
        direction: str,
        entry_price: float,
        sl: float,
        tp: float,
        orig_sl_pct: float,
        signal_ts: datetime,
        opp_list: List[datetime],
        same_dir_signals: List[Tuple[datetime, float]],
        symbol: str,
    ) -> Dict:
        """
        Végigmegy a bar-okon és megkeresi az első exit-et.

        SL dinamikusan frissülhet (live-val egyező):
          - Azonos irányú signal (alert-szintű) → SL frissítés ha kedvezőbb
          - Intraday breakeven: ár eléri entry + 0.5×initial_risk → SL = entry (csak egyszer)
          - TP tightening: ár 50%+ úton TP felé → TP szűkítése (current_price + 15% × tp_range)
          - EOD trailing SL (csak LONG): nap végén day_close × (1 - sl_pct), csak felfelé;
            3. naptól szűkebb szorzó

        Prioritás (bar-onként, live-val egyező sorrendben):
        1. STAGNATION_EXIT      – 6 egymást követő bar az entry ±sávon belül
        2. SL_HIT / TP_HIT      – stop/target elérése (TP/SL ütközésnél nyitóárhoz közelebb lévő nyer)
        2b. Intraday breakeven + TP tightening → re-check SL/TP
        3. OPPOSING_SIGNAL      – ellentétes alert-szintű signal, +15 perces végrehajtási késéssel
        4. EOD_AUTO_LIQUIDATION – SHORT trade-ek nap végén kötelezően zárnak
        5. MAX_HOLD_LIQUIDATION – max tartási határ elérése

        Returns:
            Dict: exit_price, exit_time, exit_reason, duration_bars
        """
        # Stagnation sáv: az EREDETI SL-re alapozva (nem frissül, ha SL mozog)
        initial_risk     = abs(entry_price - sl)
        stagnation_band  = STAGNATION_BAND_FACTOR * initial_risk if initial_risk > 0 else 0.0
        stagnation_slots = 0

        # Dinamikus SL/TP (SL frissülhet, TP tighten-elhet)
        current_sl  = sl
        current_tp  = tp
        initial_tp  = tp   # eredeti TP a tightening számításhoz
        be_applied  = False  # intraday breakeven egyszer tüzel

        # Nap végi trailing SL számla (live-val egyező)
        trading_days_held = 0

        # Pending opposing-signal exit
        pending_opp_exit: Optional[datetime] = None

        bars_held = 0

        # Pointer az azonos irányú signalokban (signal_ts utáni első elem)
        sd_idx = bisect_left([s[0] for s in same_dir_signals], signal_ts)

        for idx in range(start_idx, len(bars)):
            bar    = bars[idx]
            bar_ts = bar["ts"]

            # Kereskedési időn kívüli bar-okat kihagyjuk
            if _is_weekend(bar_ts) or not _is_trading_hours(bar_ts, symbol):
                continue

            bars_held += 1

            # ── Azonos irányú signal SL frissítés ─────────────────────────
            # Signalok, amelyek a trade nyitása után, de legkésőbb ezen a baron érkeztek.
            # Csak az SL-t frissítjük, a TP-t nem (live-val egyező).
            while sd_idx < len(same_dir_signals):
                sig_ts, sig_sl = same_dir_signals[sd_idx]
                if sig_ts <= signal_ts:
                    sd_idx += 1
                    continue
                if sig_ts > bar_ts:
                    break
                if direction == "LONG" and sig_sl > current_sl:
                    current_sl = round(sig_sl, 4)
                elif direction == "SHORT" and sig_sl < current_sl:
                    current_sl = round(sig_sl, 4)
                sd_idx += 1

            # ── 1. STAGNATION ──────────────────────────────────────────────
            if stagnation_band > 0:
                in_band = abs(bar["close"] - entry_price) <= stagnation_band
                stagnation_slots = stagnation_slots + 1 if in_band else 0
                if stagnation_slots >= STAGNATION_CONSECUTIVE_SLOTS:
                    return {
                        "exit_price":    bar["close"],
                        "exit_time":     bar_ts,
                        "exit_reason":   "STAGNATION_EXIT",
                        "duration_bars": bars_held,
                    }

            # ── 2. SL / TP ─────────────────────────────────────────────────
            h = bar["high"]
            l = bar["low"]
            o = bar["open"]

            if direction == "LONG":
                sl_hit = l <= current_sl
                tp_hit = h >= current_tp
            else:
                sl_hit = h >= current_sl
                tp_hit = l <= current_tp

            if sl_hit or tp_hit:
                if sl_hit and tp_hit:
                    if abs(o - current_sl) <= abs(o - current_tp):
                        return {"exit_price": current_sl, "exit_time": bar_ts,
                                "exit_reason": "SL_HIT", "duration_bars": bars_held}
                    else:
                        return {"exit_price": current_tp, "exit_time": bar_ts,
                                "exit_reason": "TP_HIT", "duration_bars": bars_held}
                if sl_hit:
                    return {"exit_price": current_sl, "exit_time": bar_ts,
                            "exit_reason": "SL_HIT", "duration_bars": bars_held}
                return {"exit_price": current_tp, "exit_time": bar_ts,
                        "exit_reason": "TP_HIT", "duration_bars": bars_held}

            # ── 2b. Intraday breakeven (live-val egyező) ───────────────────
            # Ha az ár eléri entry + 0.5×initial_risk szintet → SL = entry.
            # Csak egyszer tüzel. Re-check SL ha az új SL-t azonnal leütik.
            if not be_applied and initial_risk > 0:
                be_triggered = False
                if direction == "LONG" and current_sl < entry_price:
                    if h >= entry_price + 0.5 * initial_risk:
                        current_sl  = round(entry_price, 4)
                        be_triggered = True
                        be_applied  = True
                elif direction == "SHORT" and current_sl > entry_price:
                    if l <= entry_price - 0.5 * initial_risk:
                        current_sl  = round(entry_price, 4)
                        be_triggered = True
                        be_applied  = True
                if be_triggered:
                    # Re-check: az új breakeven SL-t ezen a baron azonnal leüthetik
                    if direction == "LONG" and l <= current_sl:
                        return {"exit_price": current_sl, "exit_time": bar_ts,
                                "exit_reason": "SL_HIT", "duration_bars": bars_held}
                    elif direction == "SHORT" and h >= current_sl:
                        return {"exit_price": current_sl, "exit_time": bar_ts,
                                "exit_reason": "SL_HIT", "duration_bars": bars_held}

            # ── 2b. TP tightening (live-val egyező) ───────────────────────
            # Ha az ár >= 50% úton a TP felé: TP = close + 15% × original_tp_range.
            # Csak szűkíthet (current_tp irányába mozog), soha nem tágíthat.
            if direction == "LONG":
                tp_range_val = initial_tp - entry_price
                if tp_range_val > 0:
                    tp_progress = (bar["close"] - entry_price) / tp_range_val
                    if tp_progress >= 0.50:
                        new_tp = bar["close"] + 0.15 * tp_range_val
                        if new_tp < current_tp:
                            current_tp = round(new_tp, 4)
                            if h >= current_tp:  # Re-check TP az új szűkebb célárral
                                return {"exit_price": current_tp, "exit_time": bar_ts,
                                        "exit_reason": "TP_HIT", "duration_bars": bars_held}
            elif direction == "SHORT":
                tp_range_val = entry_price - initial_tp
                if tp_range_val > 0:
                    tp_progress = (entry_price - bar["close"]) / tp_range_val
                    if tp_progress >= 0.50:
                        new_tp = bar["close"] - 0.15 * tp_range_val
                        if new_tp > current_tp:
                            current_tp = round(new_tp, 4)
                            if l <= current_tp:  # Re-check TP az új szűkebb célárral
                                return {"exit_price": current_tp, "exit_time": bar_ts,
                                        "exit_reason": "TP_HIT", "duration_bars": bars_held}

            # ── 3. OPPOSING_SIGNAL végrehajtása (+15 perces késés) ─────────
            # Prioritásban megelőzi az EOD-ot (live-val egyező)
            if pending_opp_exit is not None and bar_ts >= pending_opp_exit:
                return {
                    "exit_price":    bar["open"],
                    "exit_time":     bar_ts,
                    "exit_reason":   "OPPOSING_SIGNAL",
                    "duration_bars": bars_held,
                }

            # ── 4. EOD kezelés (nap utolsó barján) ────────────────────────
            bar_end = bar_ts + timedelta(minutes=15)
            is_last_bar_of_day = not _is_trading_hours(bar_end, symbol) and not _is_weekend(bar_end)

            if is_last_bar_of_day:
                if direction == "SHORT":
                    # SHORT trade-ek intraday kötelezők – nap végén zárjuk
                    return {
                        "exit_price":    bar["close"],
                        "exit_time":     bar_ts,
                        "exit_reason":   "EOD_AUTO_LIQUIDATION",
                        "duration_bars": bars_held,
                    }
                else:
                    # LONG: EOD trailing SL (live-val egyező)
                    trading_days_held += 1
                    if bar["close"] > entry_price:
                        eff_sl_pct = (orig_sl_pct * LONG_TRAILING_TIGHTEN_FACTOR
                                      if trading_days_held >= LONG_TRAILING_TIGHTEN_DAY
                                      else orig_sl_pct)
                        trailing_sl = round(bar["close"] * (1.0 - eff_sl_pct), 4)
                        if trailing_sl > current_sl:
                            current_sl = trailing_sl

            # ── 5. MAX HOLD ─────────────────────────────────────────────────
            if bars_held > MAX_HOLD_BARS:
                return {
                    "exit_price":    bar["close"],
                    "exit_time":     bar_ts,
                    "exit_reason":   "MAX_HOLD_LIQUIDATION",
                    "duration_bars": bars_held,
                }

            # ── Opposing signal keresése (csak ha még nincs pending) ────────
            if pending_opp_exit is None:
                opp_ts = self._find_opposing_signal(opp_list, signal_ts, bar_ts)
                if opp_ts is not None:
                    pending_opp_exit = bar_ts + timedelta(minutes=15)

        # Nincs exit — OPEN marad
        return {
            "exit_price":    None,
            "exit_time":     None,
            "exit_reason":   "OPEN",
            "duration_bars": bars_held,
        }

    def _find_opposing_signal(
        self,
        opp_list: List[datetime],
        signal_ts: datetime,
        bar_ts: datetime,
    ) -> Optional[datetime]:
        """
        Visszaadja az első opposing signal timestampját, ha az a
        signal_ts és bar_ts közé esik.
        """
        idx = bisect_left(opp_list, signal_ts)
        for i in range(idx, len(opp_list)):
            ts = opp_list[i]
            if ts <= signal_ts:
                continue
            if ts <= bar_ts:
                return ts
            break
        return None
