"""
TrendSignal - Archive Backtest Service
Visszamenőleges trade szimuláció archive_signals + price_data_alpaca alapján.

Logika:
- Minden BUY/SELL archive_signal kap egy archive_simulated_trade-et
- Entry: signal_timestamp + 1 bar (15 perc) nyitóárán
- Exit prioritás: SL_HIT | TP_HIT | OPPOSING_SIGNAL | MAX_HOLD_LIQUIDATION
- TP/SL ütközés esetén: amelyik közelebb volt a nyitóárhoz, az teljesül előbb
- Teljesítmény: ticker-enkénti in-memory price lookup (1 DB lekérés/ticker)

Version: 1.0
"""

from __future__ import annotations

import logging
import sqlite3
from bisect import bisect_left
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Konstansok ──────────────────────────────────────────────────────────────
ALERT_THRESHOLD = 25          # is_real_trade határ (score >= 25)
MAX_HOLD_BARS   = 10 * 26     # 10 kereskedési nap × 26 bar/nap (15m, 09:30-16:00 ET)
US_OPEN_UTC     = (14, 30)    # 09:30 ET
US_CLOSE_UTC    = (21,  0)    # 16:00 ET


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
                "opposing": 0,
                "max_hold": 0,
                "open": 0,
                "skipped": 0,
            }

            for symbol in all_symbols:
                stats = self._run_ticker(conn, symbol, score_threshold)
                total_stats["tickers"] += 1
                for k in ("signals_processed", "trades_created", "tp_hit",
                          "sl_hit", "opposing", "max_hold", "open", "skipped"):
                    total_stats[k] += stats.get(k, 0)
                logger.info(
                    f"  {symbol}: {stats['trades_created']} trade "
                    f"(TP={stats['tp_hit']} SL={stats['sl_hit']} "
                    f"OPP={stats['opposing']} MAX={stats['max_hold']} "
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
            "tp_hit": 0, "sl_hit": 0, "opposing": 0,
            "max_hold": 0, "open": 0, "skipped": 0,
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

        # 4. Minden signalhoz szimuláció
        trades_to_insert: List[Dict] = []

        for sig in signals:
            stats["signals_processed"] += 1

            entry_price = sig["entry_price"]
            sl          = sig["stop_loss"]
            tp          = sig["take_profit"]

            if not entry_price or not sl or not tp:
                stats["skipped"] += 1
                continue

            direction   = "LONG" if sig["score"] > 0 else "SHORT"
            is_real     = abs(sig["score"]) >= ALERT_THRESHOLD
            signal_ts   = sig["ts"]

            # Entry: a signal timestampje utáni első bar
            entry_bar_idx = self._find_next_bar(bars_ts, signal_ts)
            if entry_bar_idx is None:
                stats["skipped"] += 1
                continue

            entry_bar  = bars[entry_bar_idx]
            entry_time = entry_bar["ts"]

            # Opposing signal lista: LONG trade-et SELL zár, SHORT trade-et BUY zár
            opp_list = opp_short if direction == "LONG" else opp_long

            # Exit szimulálás
            result = self._simulate_exit(
                bars=bars,
                bars_ts=bars_ts,
                start_idx=entry_bar_idx,
                direction=direction,
                entry_price=entry_price,
                sl=sl,
                tp=tp,
                signal_ts=signal_ts,
                opp_list=opp_list,
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
            elif exit_reason == "OPPOSING_SIGNAL":
                stats["opposing"] += 1
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
                "id":         r["id"],
                "ts":         ts,
                "score":      r["combined_score"],
                "confidence": r["overall_confidence"],
                "entry_price": r["entry_price"],
                "stop_loss":   r["stop_loss"],
                "take_profit": r["take_profit"],
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
        signal_ts: datetime,
        opp_list: List[datetime],
        symbol: str,
    ) -> Dict:
        """
        Végigmegy a bar-okon és megkeresi az első exit-et.

        Returns:
            Dict: exit_price, exit_time, exit_reason, duration_bars
        """
        bars_held = 0

        for idx in range(start_idx, len(bars)):
            bar = bars[idx]
            bar_ts = bar["ts"]

            # Kereskedési időn kívüli bar-okat kihagyjuk
            if _is_weekend(bar_ts) or not _is_trading_hours(bar_ts, symbol):
                continue

            bars_held += 1

            # Max hold limit
            if bars_held > MAX_HOLD_BARS:
                return {
                    "exit_price":  bar["close"],
                    "exit_time":   bar_ts,
                    "exit_reason": "MAX_HOLD_LIQUIDATION",
                    "duration_bars": bars_held,
                }

            h = bar["high"]
            l = bar["low"]
            o = bar["open"]

            # SL / TP ütközés detektálása
            if direction == "LONG":
                sl_hit = l <= sl
                tp_hit = h >= tp
            else:
                sl_hit = h >= sl
                tp_hit = l <= tp

            if sl_hit and tp_hit:
                # Mindkettő ütközött ugyanazon a bar-on:
                # amelyik közelebb volt a bar nyitóárához, az teljesült előbb
                if direction == "LONG":
                    dist_sl = abs(o - sl)
                    dist_tp = abs(o - tp)
                else:
                    dist_sl = abs(o - sl)
                    dist_tp = abs(o - tp)

                if dist_sl <= dist_tp:
                    return {
                        "exit_price":    sl,
                        "exit_time":     bar_ts,
                        "exit_reason":   "SL_HIT",
                        "duration_bars": bars_held,
                    }
                else:
                    return {
                        "exit_price":    tp,
                        "exit_time":     bar_ts,
                        "exit_reason":   "TP_HIT",
                        "duration_bars": bars_held,
                    }

            if sl_hit:
                return {
                    "exit_price":    sl,
                    "exit_time":     bar_ts,
                    "exit_reason":   "SL_HIT",
                    "duration_bars": bars_held,
                }

            if tp_hit:
                return {
                    "exit_price":    tp,
                    "exit_time":     bar_ts,
                    "exit_reason":   "TP_HIT",
                    "duration_bars": bars_held,
                }

            # Opposing signal ellenőrzése (csak ALERT szintű, >= 25)
            opp_ts = self._find_opposing_signal(opp_list, signal_ts, bar_ts)
            if opp_ts:
                return {
                    "exit_price":    bar["close"],
                    "exit_time":     bar_ts,
                    "exit_reason":   "OPPOSING_SIGNAL",
                    "duration_bars": bars_held,
                }

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
