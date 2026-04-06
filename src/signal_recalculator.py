"""
TrendSignal - Signal Recalculator Service

Recalculates all archive_signals component scores using the CURRENT config,
then ArchiveBacktestService can re-simulate trades on the updated signals.

Why this is needed:
  The optimizer can approve changes to parameters that affect technical_score,
  risk_score, and sentiment_score — not just the signal/trade thresholds.
  After an optimizer proposal is approved (config.json updated), the stored
  scores in archive_signals become stale.  Re-simulating trades on stale scores
  gives incorrect backtest results.

What this service updates per archive_signal:
  - technical_score   : from stored RSI/MACD/SMA/BB/Stoch + new config weights
  - risk_score        : from stored atr_pct/nearest_support/resistance + new risk weights
                        (ADX is not stored → trend_strength component = 0.0 / neutral)
  - sentiment_score   : from archive_news_items join (24h window) + new decay weights
                        Falls back to stored sentiment_score if no news found.
  - combined_score    : new component scores × new component weights + alignment_bonus
  - base_combined_score, alignment_bonus, rr_correction
  - decision, strength : re-determined from new combined_score + confidence
  - stop_loss, take_profit, risk_reward_ratio : recalculated from stored close_price/atr

Version: 1.0
Date: 2026-03-30
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "trendsignal.db"


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------

class SignalRecalculator:
    """
    Recalculates archive_signals with current config and writes results back to DB.

    Usage:
        recalculator = SignalRecalculator(db_path)
        stats = recalculator.run(symbols=None)  # None = all tickers
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or DATABASE_PATH)

    # Backup tábla neve (csak az UPDATE-elt oszlopok)
    _BAK = "archive_signals_bak"
    _BAK_COLS = (
        "id, decision, strength, combined_score, base_combined_score, "
        "alignment_bonus, rr_correction, sentiment_score, technical_score, "
        "risk_score, overall_confidence, stop_loss, take_profit, risk_reward_ratio"
    )

    def run(self, symbols: Optional[List[str]] = None, progress_callback=None) -> Dict:
        """
        Recalculate all (or specified) archive_signals with current config.

        Adatbiztonsági garancia:
        - A futás elején backup készül az érintett rekordokról (archive_signals_bak).
        - Per-ticker commit: haladás megmarad, megszakítás esetén max 1 ticker work lost.
        - Siker esetén a backup törlődik.
        - Következő futás elején, ha backup létezik: auto-restore → clean start.

        Returns stats dict with signals_updated count per ticker.
        """
        from src.config import get_config
        cfg = get_config()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            # ── Backup kezelés ───────────────────────────────────────────────
            bak_exists = conn.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{self._BAK}'"
            ).fetchone()
            if bak_exists:
                print(
                    "[SignalRecalculator] [!] Megszakadt előző futás backupja megtalálva — visszaállítás...",
                    flush=True,
                )
                logger.warning("archive_signals_bak found — restoring from backup")
                # SQLite-kompatibilis correlated UPDATE (nem támogat FROM/JOIN-t régebbi verziókban)
                for col in ("decision", "strength", "combined_score", "base_combined_score",
                            "alignment_bonus", "rr_correction", "sentiment_score",
                            "technical_score", "risk_score", "overall_confidence",
                            "stop_loss", "take_profit", "risk_reward_ratio"):
                    conn.execute(
                        f"UPDATE archive_signals SET {col} = "
                        f"(SELECT {col} FROM {self._BAK} b WHERE b.id = archive_signals.id) "
                        f"WHERE id IN (SELECT id FROM {self._BAK})"
                    )
                conn.execute(f"DROP TABLE {self._BAK}")
                conn.commit()
                print("[SignalRecalculator] [OK] Visszaállítás kész — most friss futtatás indul.", flush=True)

            # ── Érintett tickerek meghatározása ──────────────────────────────
            if symbols:
                placeholders = ",".join("?" * len(symbols))
                rows = conn.execute(
                    f"SELECT DISTINCT ticker_symbol FROM archive_signals "
                    f"WHERE ticker_symbol IN ({placeholders})",
                    symbols,
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT DISTINCT ticker_symbol FROM archive_signals"
                ).fetchall()

            all_symbols = [r["ticker_symbol"] for r in rows]

            # ── Backup létrehozása az összes érintett rekordról ──────────────
            if symbols:
                placeholders = ",".join("?" * len(symbols))
                conn.execute(
                    f"CREATE TABLE {self._BAK} AS "
                    f"SELECT {self._BAK_COLS} FROM archive_signals "
                    f"WHERE ticker_symbol IN ({placeholders})",
                    symbols,
                )
            else:
                conn.execute(
                    f"CREATE TABLE {self._BAK} AS "
                    f"SELECT {self._BAK_COLS} FROM archive_signals"
                )
            conn.commit()
            print(
                f"[SignalRecalculator] Backup létrehozva ({self._BAK}, "
                f"{len(all_symbols)} ticker). Megszakítás esetén auto-restore.",
                flush=True,
            )

            # ── Feldolgozás (per-ticker commit) ──────────────────────────────
            print(f"[SignalRecalculator] {len(all_symbols)} ticker feldolgozása indul...", flush=True)
            logger.info(f"SignalRecalculator: {len(all_symbols)} tickers to process")

            total_updated = 0
            ticker_stats: Dict[str, int] = {}
            total = len(all_symbols)
            for i, symbol in enumerate(all_symbols, 1):
                if progress_callback:
                    try:
                        progress_callback(symbol, i, total)
                    except Exception:
                        pass
                updated = self._process_ticker(conn, symbol, cfg)
                total_updated += updated
                ticker_stats[symbol] = updated
                print(f"[SignalRecalculator] [{i}/{total}] {symbol}: {updated} signal frissítve", flush=True)
                logger.info(f"  {symbol}: {updated} signals updated")

            # ── Siker: backup törlése ────────────────────────────────────────
            conn.execute(f"DROP TABLE {self._BAK}")
            conn.commit()
            print(f"[SignalRecalculator] [OK] Kész. Összesen: {total_updated} signal frissítve. Backup törölve.", flush=True)
            return {
                "symbols_processed": len(all_symbols),
                "signals_updated": total_updated,
                "per_ticker": ticker_stats,
            }

        except Exception:
            # Hiba esetén a backup tábla megmarad — következő futáskor auto-restore
            logger.error(
                "SignalRecalculator megszakadt — backup tábla megmarad visszaállításhoz",
                exc_info=True,
            )
            raise
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Per-ticker processing
    # -----------------------------------------------------------------------

    def _process_ticker(self, conn: sqlite3.Connection, symbol: str, cfg) -> int:
        # Load all archive_signals for this ticker
        signal_rows = conn.execute("""
            SELECT
                id,
                signal_timestamp,
                decision,
                close_price,
                rsi, macd, macd_signal, macd_hist,
                sma_20, sma_50,
                bb_upper, bb_lower,
                stoch_k, stoch_d,
                atr, atr_pct,
                nearest_support, nearest_resistance,
                overall_confidence,
                sentiment_confidence, technical_confidence, risk_confidence,
                sentiment_score, technical_score, risk_score
            FROM archive_signals
            WHERE ticker_symbol = ?
            ORDER BY signal_timestamp ASC
        """, (symbol,)).fetchall()

        if not signal_rows:
            return 0

        # Load all relevant news for this ticker once (is_relevant=1, not duplicate)
        news_rows = conn.execute("""
            SELECT
                published_at,
                active_score,
                sentiment_confidence,
                llm_impact_duration
            FROM archive_news_items
            WHERE ticker_symbol = ?
              AND is_relevant = 1
              AND is_duplicate = 0
              AND active_score IS NOT NULL
            ORDER BY published_at ASC
        """, (symbol,)).fetchall()

        # Build list of news dicts for in-memory filtering
        all_news = []
        for n in news_rows:
            ts = _parse_ts(n["published_at"])
            if ts is None:
                continue
            all_news.append({
                "ts": ts,
                "active_score": _f(n["active_score"]) or 0.0,
                "sentiment_confidence": _f(n["sentiment_confidence"]) or 0.5,
                "llm_impact_duration": n["llm_impact_duration"],
            })

        updates = []
        for sig in signal_rows:
            update = self._recalculate_signal(sig, all_news, cfg)
            if update is not None:
                updates.append(update)

        if updates:
            conn.executemany("""
                UPDATE archive_signals SET
                    decision            = :decision,
                    strength            = :strength,
                    combined_score      = :combined_score,
                    base_combined_score = :base_combined_score,
                    alignment_bonus     = :alignment_bonus,
                    rr_correction       = :rr_correction,
                    sentiment_score     = :sentiment_score,
                    technical_score     = :technical_score,
                    risk_score          = :risk_score,
                    overall_confidence  = :overall_confidence,
                    entry_price         = :entry_price,
                    stop_loss           = :stop_loss,
                    take_profit         = :take_profit,
                    risk_reward_ratio   = :risk_reward_ratio
                WHERE id = :id
            """, updates)
            conn.commit()  # per-ticker commit: megszakítás esetén a korábbi tickerek megmaradnak

        return len(updates)

    # -----------------------------------------------------------------------
    # Per-signal recalculation
    # -----------------------------------------------------------------------

    def _recalculate_signal(self, sig, all_news: List[Dict], cfg) -> Optional[Dict]:
        sig_ts = _parse_ts(sig["signal_timestamp"])
        if sig_ts is None:
            return None

        close_price = _f(sig["close_price"])
        if not close_price or close_price <= 0:
            return None

        # ── 1. Technical score ──────────────────────────────────────────────
        tech_score = self._calc_technical_score(sig, cfg)

        # ── 2. Risk score ───────────────────────────────────────────────────
        risk_score = self._calc_risk_score(sig, cfg)

        # ── 3. Sentiment score ──────────────────────────────────────────────
        news_for_signal = self._get_news_for_signal(all_news, sig_ts)
        if news_for_signal:
            sent_score, sent_conf = self._calc_sentiment_score(news_for_signal, sig_ts, cfg)
        else:
            # Fall back to stored value (no archive news found)
            raw = _f(sig["sentiment_score"]) or 0.0
            # Stored sentiment_score is already in -100..+100 range for archive signals
            sent_score = raw
            sent_conf = _f(sig["sentiment_confidence"]) or 0.5

        # ── 4. Confidences ──────────────────────────────────────────────────
        # Technical confidence: keep stored (ADX-dependent, can't fully recalculate)
        tech_conf = _f(sig["technical_confidence"]) or 0.65
        # Risk confidence: recalculate alongside risk_score
        risk_conf = self._calc_risk_confidence(sig, cfg)

        # ── 5. Component weights ────────────────────────────────────────────
        sw = cfg.sentiment_weight
        tw = cfg.technical_weight
        rw = cfg.risk_weight

        # ── 6. Combined score ───────────────────────────────────────────────
        # Mirror signal_generator.py generate_signal() formula exactly:
        #   base = sent * sw + tech * tw + (risk - 50) * rw
        sent_contribution = sent_score * sw
        tech_contribution = tech_score * tw
        risk_contribution = (risk_score - 50) * rw
        base_combined = sent_contribution + tech_contribution + risk_contribution

        # ── 7. Alignment bonus ──────────────────────────────────────────────
        alignment_bonus = self._calc_alignment_bonus(sent_score, tech_score, risk_score, cfg)
        combined = base_combined + alignment_bonus

        # ── 8. Overall confidence ───────────────────────────────────────────
        overall_conf = round(sent_conf * sw + tech_conf * tw + risk_conf * rw, 4)

        # ── 9. Preliminary decision (for SL/TP) ─────────────────────────────
        # BUG FIX: use _determine_decision here (not just hold_zone_threshold),
        # because moderate_buy_score < hold_zone_threshold is possible after
        # optimizer tuning (e.g. moderate_buy=15.9, hold_zone=25.9).
        # If we only checked hold_zone, we'd skip SL/TP for MODERATE BUY signals.
        prelim_decision, _ = self._determine_decision(combined, overall_conf, cfg)

        # ── 10. SL/TP calculation ────────────────────────────────────────────
        stop_loss = None
        take_profit = None
        rr_ratio = None
        rr_correction = 0

        atr = _f(sig["atr"])
        atr_pct = _f(sig["atr_pct"]) or 2.0
        nearest_support = _f(sig["nearest_support"])
        nearest_resistance = _f(sig["nearest_resistance"])

        if prelim_decision != "HOLD" and atr and atr > 0:
            # Guard: skip signals where ATR is unreasonably large vs price
            # (e.g. NVDA post-split where stored ATR is pre-split scale)
            if atr >= close_price * 0.5:
                logger.warning(
                    f"Signal {sig['id']}: ATR ({atr:.2f}) >= 50% of price ({close_price:.2f}) "
                    f"— skipping SL/TP (likely stale pre-split ATR)"
                )
            else:
                try:
                    from optimizer.trade_simulator import SimConfig, compute_sl_tp
                    sim_cfg = SimConfig(
                        signal_threshold=float(cfg.hold_zone_threshold),
                        atr_stop_high_conf=cfg.stop_loss_atr_high_conf,
                        atr_stop_default=cfg.stop_loss_atr_mult,
                        atr_stop_low_conf=cfg.stop_loss_atr_low_conf,
                        atr_tp_low_vol=cfg.take_profit_atr_low_vol,
                        atr_tp_high_vol=cfg.take_profit_atr_high_vol,
                        vol_low_threshold=cfg.take_profit_vol_low_threshold,
                        vol_high_threshold=cfg.take_profit_vol_high_threshold,
                        sr_support_soft_pct=cfg.sr_support_soft_distance_pct,
                        sr_support_hard_pct=cfg.sr_support_max_distance_pct,
                        sr_resistance_soft_pct=cfg.sr_resistance_soft_distance_pct,
                        sr_resistance_hard_pct=cfg.sr_resistance_max_distance_pct,
                        sr_buffer_atr_mult=cfg.stop_loss_sr_buffer,
                        short_atr_stop_high_conf=cfg.short_atr_stop_high_conf,
                        short_atr_stop_default=cfg.short_atr_stop_default,
                        short_atr_stop_low_conf=cfg.short_atr_stop_low_conf,
                        short_atr_tp_low_vol=cfg.short_atr_tp_low_vol,
                        short_atr_tp_high_vol=cfg.short_atr_tp_high_vol,
                        short_sl_max_pct=cfg.short_sl_max_pct,
                        long_max_hold_days=cfg.long_max_hold_days,
                        long_trailing_tighten_day=cfg.long_trailing_tighten_day,
                        long_trailing_tighten_factor=cfg.long_trailing_tighten_factor,
                    )
                    sl, tp, sl_method, tp_method = compute_sl_tp(
                        decision=prelim_decision,
                        entry_price=close_price,
                        atr=atr,
                        atr_pct=atr_pct,
                        confidence=overall_conf,
                        nearest_support=nearest_support,
                        nearest_resistance=nearest_resistance,
                        sim_cfg=sim_cfg,
                    )

                    # Sanity check: SL/TP must be on the correct side of entry price
                    # and TP must be positive (guards against extreme ATR artifacts)
                    sl_ok = (sl < close_price) if prelim_decision == "BUY" else (sl > close_price)
                    tp_ok = (tp > close_price) if prelim_decision == "BUY" else (0 < tp < close_price)
                    if not sl_ok or not tp_ok:
                        logger.warning(
                            f"Signal {sig['id']} ({prelim_decision}): invalid SL={sl:.4f}/TP={tp:.4f} "
                            f"for price={close_price:.4f} — discarding"
                        )
                    else:
                        stop_loss = round(sl, 4)
                        take_profit = round(tp, 4)

                        risk_dist = abs(close_price - stop_loss)
                        reward_dist = abs(take_profit - close_price)
                        rr_ratio = round(reward_dist / risk_dist, 2) if risk_dist > 0 else 0.0

                        # R:R correction (mirrors signal_generator.py)
                        direction = 1 if prelim_decision == "BUY" else -1
                        if tp_method == "rr_target":
                            rr_correction = -3 * direction
                        elif rr_ratio >= 3.0:
                            rr_correction = 3 * direction
                        elif rr_ratio >= 2.5:
                            rr_correction = 2 * direction
                        elif rr_ratio >= 2.0:
                            rr_correction = 1 * direction

                        combined += rr_correction
                except Exception as e:
                    logger.debug(f"SL/TP calc failed for signal {sig['id']}: {e}")

        # ── 11. Final decision ───────────────────────────────────────────────
        decision, strength = self._determine_decision(combined, overall_conf, cfg)

        # entry_price = a signal keletkezésekor érvényes close_price
        # (non-HOLD signaloknál mindig kitöltendő — ha eddig None volt, most pótoljuk)
        entry_price = close_price if decision != "HOLD" else None

        return {
            "id": sig["id"],
            "decision": decision,
            "strength": strength,
            "combined_score": round(combined, 2),
            "base_combined_score": round(base_combined, 2),
            "alignment_bonus": alignment_bonus,
            "rr_correction": rr_correction,
            "sentiment_score": round(sent_score, 2),
            "technical_score": round(tech_score, 2),
            "risk_score": round(risk_score, 2),
            "overall_confidence": overall_conf,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": rr_ratio,
        }

    # -----------------------------------------------------------------------
    # Technical score (from stored indicators + new config weights)
    # Mirrors optimizer/backtester.py _replay_technical()
    # -----------------------------------------------------------------------

    def _calc_technical_score(self, sig, cfg) -> float:
        price   = _f(sig["close_price"])
        rsi     = _f(sig["rsi"])
        sma_20  = _f(sig["sma_20"])
        sma_50  = _f(sig["sma_50"])
        macd_h  = _f(sig["macd_hist"])
        macd_v  = _f(sig["macd"])
        bb_up   = _f(sig["bb_upper"])
        bb_lo   = _f(sig["bb_lower"])
        stoch_k = _f(sig["stoch_k"])
        stoch_d = _f(sig["stoch_d"])

        if price is None:
            return 0.0

        is_bullish_trend = self._infer_trend(price, sma_20, sma_50)

        sma_score   = self._score_sma(price, sma_20, sma_50, cfg)
        rsi_score   = self._score_rsi(rsi, is_bullish_trend, cfg)
        macd_score  = self._score_macd(macd_v, macd_h)
        bb_score    = self._score_bollinger(price, bb_up, bb_lo, is_bullish_trend)
        stoch_score = self._score_stochastic(stoch_k, is_bullish_trend, cfg)

        tech = (
            sma_score   * cfg.tech_sma_weight +
            rsi_score   * cfg.tech_rsi_weight +
            macd_score  * cfg.tech_macd_weight +
            bb_score    * cfg.tech_bollinger_weight +
            stoch_score * cfg.tech_stochastic_weight
            # volume_score: not stored → 0.0 * cfg.tech_volume_weight
        )
        return float(_clamp(tech, -100.0, 100.0))

    @staticmethod
    def _infer_trend(price, sma_20, sma_50) -> Optional[bool]:
        if price and sma_20 and sma_50:
            if price > sma_20 and sma_20 > sma_50:
                return True
            if price < sma_20 and sma_20 < sma_50:
                return False
        return None

    @staticmethod
    def _score_sma(price, sma_20, sma_50, cfg) -> float:
        if price is None:
            return 0.0
        score = 0.0
        if sma_20:
            if price > sma_20:
                score += cfg.tech_sma20_bullish
            else:
                score -= cfg.tech_sma20_bearish
        if sma_50:
            if price > sma_50:
                score += cfg.tech_sma50_bullish
            else:
                score -= cfg.tech_sma50_bearish
        if sma_20 and sma_50:
            if sma_20 > sma_50:
                score += cfg.tech_golden_cross
            else:
                score -= cfg.tech_death_cross
        # Normalize: max +60, min -40 → -100 to +100 (mirrors signal_generator.py)
        normalized = (score / 60.0) * 100
        return float(_clamp(normalized, -100.0, 100.0))

    @staticmethod
    def _score_rsi(rsi, is_bullish_trend, cfg) -> float:
        if rsi is None:
            return 0.0
        ob  = cfg.rsi_overbought
        os_ = cfg.rsi_oversold
        nl  = cfg.rsi_neutral_low
        nh  = cfg.rsi_neutral_high
        if nl < rsi < nh:
            raw = cfg.tech_rsi_neutral
        elif nh <= rsi < ob:
            raw = cfg.tech_rsi_bullish
        elif os_ < rsi <= nl:
            raw = -cfg.tech_rsi_weak_bullish
        elif rsi >= ob:
            raw = -cfg.tech_rsi_overbought
        elif rsi <= os_:
            raw = cfg.tech_rsi_oversold if (is_bullish_trend is not False) else 0
        else:
            raw = 0
        # Normalize: max +30, min -20 → -100 to +100 (mirrors signal_generator.py)
        normalized = (raw / 30.0) * 100
        return float(_clamp(normalized, -100.0, 100.0))

    @staticmethod
    def _score_macd(macd_val, macd_hist) -> float:
        if macd_hist is None and macd_val is None:
            return 0.0
        hist = macd_hist if macd_hist is not None else 0.0
        return float(_clamp(hist * 20.0, -100.0, 100.0))

    @staticmethod
    def _score_bollinger(price, bb_up, bb_lo, is_bullish_trend) -> float:
        if price is None or bb_up is None or bb_lo is None:
            return 0.0
        bb_width = bb_up - bb_lo
        if bb_width <= 0:
            return 0.0
        bb_position = (price - bb_lo) / bb_width
        # Mirrors signal_generator.py calculate_bollinger_component_score()
        if bb_position > 0.8:
            score = -70
        elif bb_position < 0.2:
            score = 70 if is_bullish_trend is not False else 0
        elif 0.4 <= bb_position <= 0.6:
            score = 30
        else:
            score = 0
        return float(_clamp(score, -100.0, 100.0))

    @staticmethod
    def _score_stochastic(stoch_k, is_bullish_trend, cfg) -> float:
        if stoch_k is None:
            return 0.0
        if stoch_k < cfg.stoch_oversold:
            score = 100 if is_bullish_trend is not False else 0
        elif stoch_k > cfg.stoch_overbought:
            score = -100
        else:
            score = 0
        return float(_clamp(score, -100.0, 100.0))

    # -----------------------------------------------------------------------
    # Risk score (from stored atr_pct/S&R + new risk weights; ADX = neutral)
    # Mirrors signal_generator.py calculate_risk_score()
    # -----------------------------------------------------------------------

    def _calc_risk_score(self, sig, cfg) -> float:
        atr_pct = _f(sig["atr_pct"])
        close_price = _f(sig["close_price"])
        nearest_support = _f(sig["nearest_support"])
        nearest_resistance = _f(sig["nearest_resistance"])

        if not atr_pct:
            atr_pct = 2.0
        if not close_price or close_price <= 0:
            return 50.0  # neutral

        # Fallback S/R if missing
        if nearest_support is None:
            nearest_support = close_price * 0.97
        if nearest_resistance is None:
            nearest_resistance = close_price * 1.03

        # 1. Volatility risk (mirrors signal_generator.py)
        vl = cfg.atr_vol_very_low
        lo = cfg.atr_vol_low
        mo = cfg.atr_vol_moderate
        hi = cfg.atr_vol_high
        if atr_pct < vl:
            volatility_risk = +0.8
        elif atr_pct < lo:
            volatility_risk = 0.8 - ((atr_pct - vl) / (lo - vl)) * 0.4
        elif atr_pct < mo:
            volatility_risk = 0.4 - ((atr_pct - lo) / (mo - lo)) * 0.4
        elif atr_pct < hi:
            volatility_risk = 0.0 - ((atr_pct - mo) / (hi - mo)) * 0.4
        else:
            volatility_risk = max(-0.8, -0.4 - ((atr_pct - hi) / 2.0) * 0.4)

        # 2. S/R proximity risk
        support_dist_pct = ((close_price - nearest_support) / close_price) * 100
        resistance_dist_pct = ((nearest_resistance - close_price) / close_price) * 100
        min_distance = min(abs(support_dist_pct), abs(resistance_dist_pct))

        if min_distance < 1.0:
            proximity_risk = -0.8
        elif min_distance < 2.0:
            proximity_risk = -0.8 + ((min_distance - 1.0) / 1.0) * 0.4
        elif min_distance < 4.0:
            proximity_risk = -0.4 + ((min_distance - 2.0) / 2.0) * 0.4
        elif min_distance < 6.0:
            proximity_risk = 0.0 + ((min_distance - 4.0) / 2.0) * 0.4
        else:
            proximity_risk = min(0.8, 0.4 + ((min_distance - 6.0) / 4.0) * 0.4)

        # 3. Trend strength (ADX not stored → neutral = 0.0)
        trend_risk = 0.0

        risk_raw = (
            volatility_risk * cfg.risk_volatility_weight +
            proximity_risk  * cfg.risk_proximity_weight +
            trend_risk      * cfg.risk_trend_strength_weight
        ) * 200  # Scale to -100..+100 range

        return float(_clamp(risk_raw, -100.0, 100.0))

    def _calc_risk_confidence(self, sig, cfg) -> float:
        """Recalculate risk confidence using same weights (ADX component = 0.60 neutral)."""
        atr_pct = _f(sig["atr_pct"]) or 2.0
        close_price = _f(sig["close_price"])
        nearest_support = _f(sig["nearest_support"])
        nearest_resistance = _f(sig["nearest_resistance"])

        if not close_price or close_price <= 0:
            return 0.60

        if nearest_support is None:
            nearest_support = close_price * 0.97
        if nearest_resistance is None:
            nearest_resistance = close_price * 1.03

        # Vol confidence (mirrors calculate_risk_score)
        vl = cfg.atr_vol_very_low
        lo = cfg.atr_vol_low
        mo = cfg.atr_vol_moderate
        hi = cfg.atr_vol_high
        if atr_pct < vl:
            vol_conf = 0.95
        elif atr_pct < lo:
            vol_conf = 0.90
        elif atr_pct < mo:
            vol_conf = 0.75
        elif atr_pct < hi:
            vol_conf = 0.65
        else:
            vol_conf = 0.50

        # Proximity confidence
        support_dist = ((close_price - nearest_support) / close_price) * 100
        resistance_dist = ((nearest_resistance - close_price) / close_price) * 100
        min_dist = min(abs(support_dist), abs(resistance_dist))
        if min_dist < 1.0:
            prox_conf = 0.35
        elif min_dist < 2.0:
            prox_conf = 0.45
        elif min_dist < 4.0:
            prox_conf = 0.65
        elif min_dist < 6.0:
            prox_conf = 0.80
        else:
            prox_conf = 0.85

        trend_conf = 0.60  # No ADX → neutral

        return float(
            vol_conf  * cfg.risk_volatility_weight +
            prox_conf * cfg.risk_proximity_weight +
            trend_conf * cfg.risk_trend_strength_weight
        )

    # -----------------------------------------------------------------------
    # Sentiment score (from archive_news_items + new decay weights)
    # Mirrors signal_generator.py aggregate_sentiment_from_news()
    # -----------------------------------------------------------------------

    @staticmethod
    def _get_news_for_signal(all_news: List[Dict], sig_ts: datetime) -> List[Dict]:
        """Return news items published within 24h before signal_timestamp."""
        window_start = sig_ts - timedelta(hours=24)
        return [n for n in all_news if window_start <= n["ts"] <= sig_ts]

    def _calc_sentiment_score(
        self, news_items: List[Dict], sig_ts: datetime, cfg
    ) -> Tuple[float, float]:
        """
        Calculate sentiment score and confidence from archive_news_items.
        Returns (sentiment_score_-100_to_100, sentiment_confidence_0_to_1).
        """
        decay_weights = cfg.decay_weights
        duration_weight = cfg.duration_weight

        weighted_scores = []
        weights_sum = 0.0
        confidences = []
        raw_scores_for_conf = []

        for item in news_items:
            news_ts = item["ts"]
            age_hours = (sig_ts - news_ts).total_seconds() / 3600.0

            if age_hours < 2:
                decay = decay_weights.get("0-2h", 1.0)
            elif age_hours < 6:
                decay = decay_weights.get("2-6h", 0.85)
            elif age_hours < 12:
                decay = decay_weights.get("6-12h", 0.60)
            elif age_hours < 24:
                decay = decay_weights.get("12-24h", 0.35)
            else:
                decay = 0.0

            if decay <= 0:
                continue

            duration = duration_weight.get(item.get("llm_impact_duration") or "days", 1.0)
            # Archive news items don't have source credibility stored → default 1.0
            credibility = 1.0
            score = item["active_score"]  # already in -1..+1 range (finbert/llm)

            effective_weight = decay * credibility * duration
            weighted_scores.append(score * effective_weight)
            weights_sum += effective_weight
            confidences.append(item["sentiment_confidence"])
            raw_scores_for_conf.append(score)

        if weights_sum <= 0.0 or not weighted_scores:
            return 0.0, 0.5

        # Weighted average sentiment (-1..+1) × 100 = -100..+100
        weighted_avg = sum(weighted_scores) / weights_sum
        sentiment_score = float(_clamp(weighted_avg * 100.0, -100.0, 100.0))

        # Confidence calculation (mirrors signal_generator.py aggregate_sentiment_from_news)
        news_count = len(news_items)

        # Component 1: FinBERT confidence (capped)
        finbert_conf = sum(confidences) / len(confidences) if confidences else 0.5
        finbert_conf_normalized = min(finbert_conf * 0.85, 0.90)

        # Component 2: News volume factor
        if news_count >= cfg.sentiment_conf_full_news_count:
            volume_factor = 1.0
        elif news_count >= cfg.sentiment_conf_high_news_count:
            volume_factor = 0.85
        elif news_count >= cfg.sentiment_conf_med_news_count:
            volume_factor = 0.70
        elif news_count >= cfg.sentiment_conf_low_news_count:
            volume_factor = 0.55
        else:
            volume_factor = 0.40

        # Component 3: Sentiment consistency
        pos_threshold = cfg.sentiment_positive_threshold
        neg_threshold = cfg.sentiment_negative_threshold
        positive_count = sum(1 for s in raw_scores_for_conf if s > pos_threshold)
        negative_count = sum(1 for s in raw_scores_for_conf if s < neg_threshold)
        if news_count > 0:
            consistency = max(positive_count, negative_count) / news_count
        else:
            consistency = 0.5

        sentiment_conf = (
            finbert_conf_normalized * 0.40 +
            volume_factor           * 0.35 +
            consistency             * 0.25
        )

        return sentiment_score, float(sentiment_conf)

    # -----------------------------------------------------------------------
    # Alignment bonus (mirrors signal_generator.py _calculate_alignment_bonus)
    # -----------------------------------------------------------------------

    def _calc_alignment_bonus(
        self, sentiment: float, technical: float, risk: float, cfg
    ) -> int:
        """
        Alignment bonus — mirrors signal_generator.py exactly.
        Uses (risk - 50) centering for direction check and |risk - 50| for strength.
        """
        abs_sent = abs(sentiment)
        abs_tech = abs(technical)
        abs_risk = abs(risk - 50)  # center at 50 (neutral risk = 50)

        tech_thr = cfg.alignment_tech_threshold
        sent_thr = cfg.alignment_sent_threshold
        risk_thr = cfg.alignment_risk_threshold

        tr_strong = abs_tech > tech_thr and abs_risk > risk_thr
        st_strong = abs_sent > sent_thr and abs_tech > sent_thr
        sr_strong = abs_sent > sent_thr and abs_risk > risk_thr

        strong_pairs = sum([tr_strong, st_strong, sr_strong])

        if strong_pairs == 3:
            bonus_magnitude = cfg.alignment_bonus_all
        elif strong_pairs == 1:
            if tr_strong:
                bonus_magnitude = cfg.alignment_bonus_tr
            elif st_strong:
                bonus_magnitude = cfg.alignment_bonus_st
            else:
                bonus_magnitude = cfg.alignment_bonus_sr
        else:
            return 0

        # Direction: bonus is positive for BUY-aligned, negative for SELL-aligned
        if sentiment > 0 and technical > 0 and risk > 50:
            return bonus_magnitude
        elif sentiment < 0 and technical < 0 and risk < 50:
            return -bonus_magnitude
        else:
            return 0

    # -----------------------------------------------------------------------
    # Decision determination (mirrors signal_generator.py _determine_decision)
    # -----------------------------------------------------------------------

    @staticmethod
    def _determine_decision(combined_score: float, confidence: float, cfg) -> Tuple[str, str]:
        """Determine BUY/SELL/HOLD decision and strength from score + confidence."""
        strong_buy_score    = cfg.strong_buy_score
        strong_buy_conf     = cfg.strong_buy_confidence
        moderate_buy_score  = cfg.moderate_buy_score
        moderate_buy_conf   = cfg.moderate_buy_confidence
        strong_sell_score   = cfg.strong_sell_score
        strong_sell_conf    = cfg.strong_sell_confidence
        moderate_sell_score = cfg.moderate_sell_score
        moderate_sell_conf  = cfg.moderate_sell_confidence
        hold_zone           = cfg.hold_zone_threshold

        if combined_score >= strong_buy_score and confidence >= strong_buy_conf:
            return "BUY", "STRONG"
        elif combined_score >= moderate_buy_score and confidence >= moderate_buy_conf:
            return "BUY", "MODERATE"
        elif combined_score <= strong_sell_score and confidence >= strong_sell_conf:
            return "SELL", "STRONG"
        elif combined_score <= moderate_sell_score and confidence >= moderate_sell_conf:
            return "SELL", "MODERATE"
        elif combined_score >= hold_zone:
            return "BUY", "WEAK"
        elif combined_score <= -hold_zone:
            return "SELL", "WEAK"
        else:
            return "HOLD", "NEUTRAL"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _f(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _parse_ts(s) -> Optional[datetime]:
    """Parse ISO timestamp string to naive UTC datetime."""
    if s is None:
        return None
    if isinstance(s, datetime):
        return s.replace(tzinfo=None)
    s = str(s).strip()
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
    ):
        try:
            return datetime.strptime(s[:len(fmt)], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", ""))
    except ValueError:
        return None
