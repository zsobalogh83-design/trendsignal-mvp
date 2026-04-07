"""
TrendSignal - Archive Backtest Service
Visszamenőleges trade szimuláció archive_signals + price_data alapján.

Logika:
- Minden BUY/SELL archive_signal kap egy archive_simulated_trade-et
- Entry: signal_timestamp utáni első kereskedési bar NYITÓÁRÁN (+15 perces végrehajtási késés)
- SL/TP: a signal által javasolt szintek; az új entry price alapján érvényesség-ellenőrzés fut
- Exit logika: → src/trade_simulator_core.py (kanonikus implementáció, optimizer is ezt hívja)
- Teljesítmény: ticker-enkénti in-memory price lookup (1 DB lekérés/ticker)

Version: 5.0 – Exit szimuláció kiszervezve trade_simulator_core-ba (szinkron az optimizerrel)
"""

from __future__ import annotations

import logging
import sqlite3
import pytz
from bisect import bisect_left
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.trade_simulator_core import (
    simulate_exit as _core_simulate_exit,
    Bar as _Bar,
    _is_trading_hours,   # kanonikus DST-aware implementáció
    _is_weekend,
)
from config import get_config as _get_config
from src.entry_gates import check_entry_gates

_ET_TZ = pytz.timezone('America/New_York')


def _us_eod_utc(dt_utc: datetime) -> datetime:
    """4:00 PM ET (DST-aware) → naive UTC datetime.
    EDT: 20:00 UTC | EST: 21:00 UTC — automatikusan kezeli a nyári/téli időszámítást."""
    utc_aware = pytz.utc.localize(dt_utc)
    et_time   = utc_aware.astimezone(_ET_TZ)
    et_close  = _ET_TZ.localize(
        et_time.replace(hour=16, minute=0, second=0, microsecond=0, tzinfo=None)
    )
    return et_close.astimezone(pytz.utc).replace(tzinfo=None)

logger = logging.getLogger(__name__)

# ── Konstansok ──────────────────────────────────────────────────────────────
# Szimulációs konstansok (ALERT_THRESHOLD, MAX_HOLD_BARS stb.) a trade_simulator_core-ban vannak.
from src.trade_simulator_core import ALERT_THRESHOLD  # noqa: E402

TRADE_FEE_PCT      = 0.002                            # Round-trip díj: 0.2%
DIRECTION_2H_TOLERANCE = timedelta(minutes=20)        # ±tűrés 5m bar keresésnél


# ── Segédfüggvények ──────────────────────────────────────────────────────────

# ── ArchiveBacktestService ────────────────────────────────────────────────────

class ArchiveBacktestService:
    """
    Ticker-enkénti bulk feldolgozás:
    1. Betölti az összes 15m bar-t memóriába (price_data, interval='15m')
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
        progress_callback=None,
    ) -> Dict:
        """
        Futtatja az archív backtestet az összes (vagy megadott) tickerre.

        Adatbiztonsági garancia: minden ticker DELETE + INSERT + COMMIT egységesen fut.
        Megszakítás esetén a már befejezett tickerek adatai megmaradnak; csak az
        aktuálisan feldolgozott ticker kerül elveszett állapotba (újrafuttatáskor
        helyreáll).

        Args:
            symbols:           Ha None, minden ticker fut.
            score_threshold:   Minimum |combined_score| a szimulációhoz.
            progress_callback: Opcionális callable(ticker, index, total) a progress UI-hoz.

        Returns:
            Stats dict.
        """
        _BAK = "archive_simulated_trades_bak"

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # ── Backup kezelés ───────────────────────────────────────────────
            # Ha létezik backup tábla, az előző futás megszakadt → auto-restore
            bak_exists = conn.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{_BAK}'"
            ).fetchone()
            if bak_exists:
                print(
                    f"[ArchiveBacktest] [!] Megszakadt előző futás backupja megtalálva — visszaállítás...",
                    flush=True,
                )
                logger.warning("archive_simulated_trades_bak found — restoring from backup")
                if symbols:
                    placeholders = ",".join("?" * len(symbols))
                    conn.execute(
                        f"DELETE FROM archive_simulated_trades WHERE ticker_symbol IN ({placeholders})",
                        symbols,
                    )
                    conn.execute(
                        f"INSERT INTO archive_simulated_trades "
                        f"SELECT * FROM {_BAK} WHERE ticker_symbol IN ({placeholders})",
                        symbols,
                    )
                else:
                    conn.execute("DELETE FROM archive_simulated_trades")
                    conn.execute(f"INSERT INTO archive_simulated_trades SELECT * FROM {_BAK}")
                conn.execute(f"DROP TABLE {_BAK}")
                conn.commit()
                print("[ArchiveBacktest] [OK] Visszaállítás kész — most friss futtatás indul.", flush=True)

            # ── Backup létrehozása a futtatás előtt ──────────────────────────
            if symbols:
                placeholders = ",".join("?" * len(symbols))
                conn.execute(
                    f"CREATE TABLE {_BAK} AS "
                    f"SELECT * FROM archive_simulated_trades WHERE ticker_symbol IN ({placeholders})",
                    symbols,
                )
            else:
                conn.execute(
                    f"CREATE TABLE {_BAK} AS SELECT * FROM archive_simulated_trades"
                )
            conn.commit()
            print(
                f"[ArchiveBacktest] Backup létrehozva ({_BAK}). "
                f"Megszakítás esetén az eredeti adatok visszaállíthatók.",
                flush=True,
            )

            # ── Feldolgozás ──────────────────────────────────────────────────
            all_symbols = self._get_symbols(conn, symbols)
            total = len(all_symbols)
            logger.info(f"Archive backtest: {total} ticker")
            print(f"[ArchiveBacktest] {total} ticker feldolgozása indul...", flush=True)

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

            for i, symbol in enumerate(all_symbols, 1):
                if progress_callback:
                    try:
                        progress_callback(symbol, i, total)
                    except Exception:
                        pass
                print(f"[ArchiveBacktest] [{i}/{total}] {symbol} ...", flush=True)
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
                print(
                    f"[ArchiveBacktest] [{i}/{total}] {symbol}: "
                    f"{stats['trades_created']} trade kész",
                    flush=True,
                )

            # ── Siker: backup törlése ────────────────────────────────────────
            conn.execute(f"DROP TABLE IF EXISTS {_BAK}")
            conn.commit()
            print(
                f"[ArchiveBacktest] [OK] Kész. Összesen: {total_stats['trades_created']} trade. Backup törölve.",
                flush=True,
            )
            return total_stats

        except Exception:
            # Hiba esetén a backup tábla megmarad — következő futáskor auto-restore
            logger.error(
                "ArchiveBacktestService megszakadt — backup tábla megmarad visszaállításhoz",
                exc_info=True,
            )
            raise
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
        bars = self._load_price_bars(conn, symbol, interval='15m')
        if not bars:
            logger.warning(f"  {symbol}: nincs 15m ár adat, kihagyva")
            return stats

        bars_ts = [b["ts"] for b in bars]

        # 1b. Betöltjük az 5m bar-okat a 2H direction számításhoz
        bars_5m = self._load_price_bars(conn, symbol, interval='5m')
        bars_5m_ts = [b["ts"] for b in bars_5m]

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

            # ── Entry gates (közös logika: src/entry_gates.py) ──────────────────
            _cfg = _get_config()
            blocked, _filter, _reason = check_entry_gates(
                direction=direction,
                rsi=sig.get("rsi"),
                macd_hist=sig.get("macd_hist"),
                sma_200=sig.get("sma_200"),
                sma_50=sig.get("sma_50"),
                close_price=sig.get("close_price"),
                nearest_resistance=sig.get("nearest_resistance"),
                cfg=_cfg,
            )
            if blocked:
                stats["skipped"] += 1; continue

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
            else:
                sl_pct = (signal_sl - signal_entry) / signal_entry
                tp_pct = (signal_entry - signal_tp) / signal_entry

            # Hard cap: régi signalok (stock split, pre-cap kód) abnormális SL/TP
            # értékeit a jelenlegi config limitjeire korlátozzuk
            if direction == "LONG":
                sl_pct = min(sl_pct, _cfg.sl_max_pct)
                tp_pct = min(tp_pct, _cfg.tp_max_pct)
            else:
                sl_pct = min(sl_pct, _cfg.short_sl_max_pct)
                tp_pct = min(tp_pct, _cfg.short_tp_max_pct)

            if direction == "LONG":
                sl = round(entry_price * (1.0 - sl_pct), 4)
                tp = round(entry_price * (1.0 + tp_pct), 4)
            else:
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
                pnl_net_pct = round(pnl_pct - TRADE_FEE_PCT * 100, 4)
            else:
                pnl_pct     = None
                pnl_net_pct = None

            # 2H direction számítás
            d2h = self._compute_2h_direction(
                bars_5m=bars_5m,
                bars_5m_ts=bars_5m_ts,
                entry_time=entry_time,
                direction=direction,
                symbol=symbol,
            )

            trades_to_insert.append({
                "archive_signal_id":   sig["id"],
                "ticker_symbol":       symbol,
                "direction":           direction,
                "status":              status,
                "entry_price":         entry_price,
                "entry_time":          entry_time.isoformat(),
                "stop_loss_price":     sl,
                "take_profit_price":   tp,
                "exit_price":          exit_price,
                "exit_time":           exit_time.isoformat() if exit_time else None,
                "exit_reason":         exit_reason,
                "pnl_percent":         round(pnl_pct, 4) if pnl_pct is not None else None,
                "pnl_net_percent":     pnl_net_pct,
                "duration_bars":       duration,
                "combined_score":      sig["score"],
                "overall_confidence":  sig["confidence"],
                "is_real_trade":       1 if is_real else 0,
                "direction_2h_eligible": 1 if d2h["eligible"] else 0,
                "direction_2h_correct":  1 if d2h["correct"] else 0 if d2h["eligible"] else None,
                "direction_2h_pct":      d2h["pct"],
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

        # 5. Per-ticker DELETE (régi adatok) + Bulk INSERT + COMMIT
        # Adatbiztonsági garancia: ha a processz megszakad egy ticker közben,
        # csak az adott ticker adatai vesznek el; az összes korábbi ticker safe.
        conn.execute(
            "DELETE FROM archive_simulated_trades WHERE ticker_symbol = ?", (symbol,)
        )
        if trades_to_insert:
            conn.executemany(
                """INSERT INTO archive_simulated_trades
                   (archive_signal_id, ticker_symbol, direction, status,
                    entry_price, entry_time, stop_loss_price, take_profit_price,
                    exit_price, exit_time, exit_reason,
                    pnl_percent, pnl_net_percent, duration_bars, combined_score,
                    overall_confidence, is_real_trade,
                    direction_2h_eligible, direction_2h_correct, direction_2h_pct)
                   VALUES
                   (:archive_signal_id, :ticker_symbol, :direction, :status,
                    :entry_price, :entry_time, :stop_loss_price, :take_profit_price,
                    :exit_price, :exit_time, :exit_reason,
                    :pnl_percent, :pnl_net_percent, :duration_bars, :combined_score,
                    :overall_confidence, :is_real_trade,
                    :direction_2h_eligible, :direction_2h_correct, :direction_2h_pct)
                """,
                trades_to_insert,
            )
        conn.commit()  # ← per-ticker commit: megszakítás esetén a korábbi tickerek megmaradnak

        return stats

    # ── Ár / bar segédek ─────────────────────────────────────────────────────

    def _load_price_bars(self, conn: sqlite3.Connection, symbol: str, interval: str = '15m') -> List[Dict]:
        """Betölti az összes bar-t memóriába rendezett listába (alapértelmezetten 15m)."""
        rows = conn.execute(
            """SELECT timestamp, open, high, low, close
               FROM price_data
               WHERE ticker_symbol = ? AND interval = ?
               ORDER BY timestamp""",
            (symbol, interval),
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
                      entry_price, stop_loss, take_profit,
                      rsi, macd_hist, sma_200, sma_50, close_price, nearest_resistance
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
                "id":                 r["id"],
                "ts":                 ts,
                "score":              r["combined_score"],
                "confidence":         r["overall_confidence"],
                "signal_entry_price": r["entry_price"],
                "stop_loss":          r["stop_loss"],
                "take_profit":        r["take_profit"],
                "rsi":                r["rsi"],
                "macd_hist":          r["macd_hist"],
                "sma_200":            r["sma_200"],
                "sma_50":             r["sma_50"],
                "close_price":        r["close_price"],
                "nearest_resistance": r["nearest_resistance"],
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

    def _compute_2h_direction(
        self,
        bars_5m: List[Dict],
        bars_5m_ts: List[datetime],
        entry_time: datetime,
        direction: str,
        symbol: str,
    ) -> Dict:
        """
        Kiszámolja, hogy a belépéstől számított 2 óra alatt helyes irányt mozgott-e a piac.
        Logika megegyezik a backtest_service._fill_2h_direction()-nel.

        Returns:
            {"eligible": bool, "correct": bool|None, "pct": float|None}
        """
        # Csak kereskedési időben
        if _is_weekend(entry_time) or not _is_trading_hours(entry_time, symbol):
            return {"eligible": False, "correct": None, "pct": None}

        # EOD időpont (DST-aware)
        if symbol.endswith('.BD'):
            eod = entry_time.replace(hour=16, minute=0, second=0, microsecond=0)
        else:
            eod = _us_eod_utc(entry_time)   # 20:00 UTC (EDT) vagy 21:00 UTC (EST)

        raw_exit  = entry_time + timedelta(hours=2)
        exit_time = min(raw_exit, eod - timedelta(minutes=5))

        if (exit_time - entry_time).total_seconds() < 300:
            return {"eligible": False, "correct": None, "pct": None}

        if not bars_5m:
            return {"eligible": False, "correct": None, "pct": None}

        # Keressük a legközelebbi 5m bar-t ±20 percen belül entry_time-nál
        entry_candle = self._find_closest_5m_bar(bars_5m, bars_5m_ts, entry_time)
        exit_candle  = self._find_closest_5m_bar(bars_5m, bars_5m_ts, exit_time)

        if entry_candle is None or exit_candle is None:
            return {"eligible": False, "correct": None, "pct": None}

        ep  = float(entry_candle["close"])
        xp  = float(exit_candle["close"])
        pct = (xp - ep) / ep * 100

        correct = (xp > ep) if direction == "LONG" else (xp < ep)
        return {"eligible": True, "correct": correct, "pct": round(pct, 3)}

    def _find_closest_5m_bar(
        self,
        bars_5m: List[Dict],
        bars_5m_ts: List[datetime],
        target_time: datetime,
    ) -> Optional[Dict]:
        """Megkeresi a target_time-hoz legközelebbi 5m bar-t ±20 percen belül."""
        idx = bisect_left(bars_5m_ts, target_time)
        candidates = []
        for i in range(max(0, idx - 3), min(len(bars_5m), idx + 4)):
            diff = abs((bars_5m_ts[i] - target_time).total_seconds())
            if diff <= DIRECTION_2H_TOLERANCE.total_seconds():
                candidates.append((diff, bars_5m[i]))
        if not candidates:
            return None
        return min(candidates, key=lambda x: x[0])[1]

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
        Exit szimuláció — delegál a src.trade_simulator_core.simulate_exit()-hez.
        A kanonikus szimulációs logika ott van; az optimizer is ugyanazt hívja.
        """
        # Dict-eket Bar-okká konvertálunk (a core duck-typed, de Bar attribútumokra számít)
        core_bars = [
            _Bar(timestamp=b["ts"], open=b["open"], high=b["high"],
                 low=b["low"], close=b["close"])
            for b in bars[start_idx:]
        ]
        return _core_simulate_exit(
            bars=core_bars,
            direction=direction,
            entry_price=entry_price,
            sl=sl,
            tp=tp,
            orig_sl_pct=orig_sl_pct,
            signal_ts=signal_ts,
            opp_list=opp_list,
            same_dir_signals=same_dir_signals,
            symbol=symbol,
        )
