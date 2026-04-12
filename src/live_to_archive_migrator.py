"""
TrendSignal - Live → Archive Migrator

Két migrációs útvonal:

A) Lezárt trade-del rendelkező signalok (migrate_closed_trade_to_archive):
   simulated_trades (CLOSED) → archive_signals + archive_simulated_trades

B) Trade nélküli lejárt/archivált signalok (migrate_signal_without_trade):
   signals (expired/archived, nincs CLOSED trade) → archive_signals
   Az archive_simulated_trades bejegyzést az ArchiveBacktestService hozza létre
   a következő recalculate-and-resimulate futtatáskor.

Az eredeti rekordok a live táblákban maradnak (nem törlődnek).
Minden migráció idempotent (INSERT OR IGNORE / már-migrált ellenőrzés).

Version: 1.1
Date: 2026-03-31
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "trendsignal.db"


def migrate_closed_trade_to_archive(
    trade_id: int,
    db_path: Path = DATABASE_PATH,
) -> bool:
    """
    Egy lezárt live trade-et átmásol az archive táblákba.

    Parameters
    ----------
    trade_id : int
        simulated_trades.id — a lezárt trade azonosítója.
    db_path : Path
        SQLite DB elérési útja.

    Returns
    -------
    bool
        True  = sikeres migráció (vagy már korábban migrált → idempotent)
        False = kihagyva (nem CLOSED, hiányzó adat) vagy hiba
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        # ------------------------------------------------------------------ #
        # 1. Lezárt trade betöltése
        # ------------------------------------------------------------------ #
        trade = conn.execute(
            "SELECT * FROM simulated_trades WHERE id = ? AND status = 'CLOSED'",
            (trade_id,),
        ).fetchone()

        if not trade:
            logger.debug(f"[Migrator] Trade {trade_id}: nem CLOSED vagy nem létezik — kihagyva")
            return False

        # OPPOSING_SIGNAL exit-ek nem migrálódnak — ez az exit típus le van tiltva
        if trade["exit_reason"] == "OPPOSING_SIGNAL":
            logger.debug(f"[Migrator] Trade {trade_id}: OPPOSING_SIGNAL exit — kihagyva (letiltott exit típus)")
            return False

        # ------------------------------------------------------------------ #
        # 2. signal_calculations sor betöltése (legfrissebb a signal_id-hoz)
        # ------------------------------------------------------------------ #
        sc = conn.execute(
            """
            SELECT * FROM signal_calculations
            WHERE signal_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (trade["entry_signal_id"],),
        ).fetchone()

        # ------------------------------------------------------------------ #
        # 3. signals sor betöltése (ticker_id, strength, reasoning_json, fallback adatok)
        # ------------------------------------------------------------------ #
        sig = conn.execute(
            """
            SELECT id, ticker_id, ticker_symbol, decision, strength, status,
                   combined_score, sentiment_score, technical_score, risk_score,
                   overall_confidence, sentiment_confidence, technical_confidence,
                   entry_price, stop_loss, take_profit, risk_reward_ratio,
                   reasoning_json, technical_indicator_id, created_at
            FROM signals WHERE id = ?
            """,
            (trade["entry_signal_id"],),
        ).fetchone()

        # 3b. Ha nincs signal_calculations → fallback: technical_indicators
        ti = None
        if not sc:
            if sig and sig["technical_indicator_id"]:
                ti = conn.execute(
                    "SELECT * FROM technical_indicators WHERE id = ?",
                    (sig["technical_indicator_id"],),
                ).fetchone()
            if not sc and not ti and (not sig or not sig["entry_price"]):
                logger.warning(
                    f"[Migrator] Trade {trade_id}: nincs signal_calculations, "
                    "technical_indicators és entry_price sem — kihagyva"
                )
                return False

        # Egységes adatforrás (sc elsőbbséget élvez, ti majd sig fallback)
        ticker_symbol = sc["ticker_symbol"] if sc else (sig["ticker_symbol"] if sig else trade["symbol"])
        signal_ts     = sc["calculated_at"]  if sc else (sig["created_at"] if sig else None)
        close_price   = sc["current_price"]  if sc else (ti["close_price"] if ti else (sig["entry_price"] if sig else None))
        atr_val       = sc["atr"]            if sc else (ti["atr"] if ti else None)
        atr_pct_val   = sc["atr_pct"]        if sc else (
                            round(atr_val / close_price * 100, 4)
                            if (atr_val and close_price) else None)

        if not signal_ts:
            logger.warning(f"[Migrator] Trade {trade_id}: nem sikerült signal_timestamp meghatározni — kihagyva")
            return False

        # ------------------------------------------------------------------ #
        # 4. archive_signals INSERT OR IGNORE
        #    UNIQUE constraint: (ticker_symbol, signal_timestamp)
        # ------------------------------------------------------------------ #
        overall_confidence = _avg3(
            sc["sentiment_confidence"]    if sc else (sig["sentiment_confidence"] if sig else None),
            sc["technical_confidence"]    if sc else (sig["technical_confidence"] if sig else None),
            sc["risk_confidence"]         if sc else None,
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO archive_signals (
                ticker_id, ticker_symbol, signal_timestamp,
                decision, strength,
                combined_score, sentiment_score, technical_score, risk_score,
                overall_confidence,
                sentiment_confidence, technical_confidence, risk_confidence,
                entry_price, stop_loss, take_profit, risk_reward_ratio,
                close_price,
                rsi, macd, macd_signal, macd_hist,
                sma_20, sma_50, sma_200,
                atr, atr_pct,
                bb_upper, bb_lower,
                stoch_k, stoch_d,
                nearest_support, nearest_resistance,
                news_count, reasoning_json,
                generated_at
            ) VALUES (
                ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                CURRENT_TIMESTAMP
            )
            """,
            (
                sig["ticker_id"] if sig else None,
                ticker_symbol,
                signal_ts,
                sc["decision"]          if sc else (sig["decision"] if sig else None),
                sig["strength"]         if sig else None,
                sc["combined_score"]    if sc else (sig["combined_score"] if sig else None),
                sc["sentiment_score"]   if sc else (sig["sentiment_score"] if sig else None),
                sc["technical_score"]   if sc else (sig["technical_score"] if sig else None),
                sc["risk_score"]        if sc else (sig["risk_score"] if sig else None),
                overall_confidence,
                sc["sentiment_confidence"] if sc else (sig["sentiment_confidence"] if sig else None),
                sc["technical_confidence"] if sc else (sig["technical_confidence"] if sig else None),
                sc["risk_confidence"]   if sc else None,
                sc["entry_price"]       if sc else (sig["entry_price"] if sig else None),
                sc["stop_loss"]         if sc else (sig["stop_loss"] if sig else None),
                sc["take_profit"]       if sc else (sig["take_profit"] if sig else None),
                sc["risk_reward_ratio"] if sc else (sig["risk_reward_ratio"] if sig else None),
                close_price,
                sc["rsi"]               if sc else (ti["rsi"]            if ti else None),
                sc["macd"]              if sc else (ti["macd"]           if ti else None),
                sc["macd_signal"]       if sc else (ti["macd_signal"]    if ti else None),
                sc["macd_histogram"]    if sc else (ti["macd_histogram"] if ti else None),
                sc["sma_20"]            if sc else (ti["sma_20"]         if ti else None),
                sc["sma_50"]            if sc else (ti["sma_50"]         if ti else None),
                sc["sma_200"]           if sc else (ti["sma_200"]        if ti else None),
                atr_val,
                atr_pct_val,
                sc["bb_upper"]          if sc else (ti["bb_upper"]       if ti else None),
                sc["bb_lower"]          if sc else (ti["bb_lower"]       if ti else None),
                sc["stoch_k"]           if sc else (ti["stoch_k"]        if ti else None),
                sc["stoch_d"]           if sc else (ti["stoch_d"]        if ti else None),
                sc["nearest_support"]   if sc else None,
                sc["nearest_resistance"] if sc else None,
                sc["news_count"]        if sc else None,
                sig["reasoning_json"]   if sig else None,
            ),
        )

        # archive_signals.id lekérése (akár most szúrtuk be, akár már volt)
        arch_sig = conn.execute(
            "SELECT id FROM archive_signals WHERE ticker_symbol = ? AND signal_timestamp = ?",
            (ticker_symbol, signal_ts),
        ).fetchone()

        if not arch_sig:
            logger.error(
                f"[Migrator] Trade {trade_id}: nem sikerült archive_signals id-t lekérni — kihagyva"
            )
            conn.rollback()
            return False

        archive_signal_id = arch_sig["id"]

        # ------------------------------------------------------------------ #
        # 5. archive_simulated_trades INSERT OR IGNORE
        #    Ha már migrálva van (ugyanaz az archive_signal_id), kihagyjuk
        # ------------------------------------------------------------------ #
        already = conn.execute(
            "SELECT id FROM archive_simulated_trades WHERE archive_signal_id = ?",
            (archive_signal_id,),
        ).fetchone()

        if already:
            # Már migrálva — de a signal státuszát még frissíthetjük ha szükséges
            if trade["entry_signal_id"]:
                conn.execute(
                    "UPDATE signals SET status = 'migrated' WHERE id = ? AND status != 'migrated'",
                    (trade["entry_signal_id"],),
                )
            conn.commit()
            logger.debug(
                f"[Migrator] Trade {trade_id}: már migrálva "
                f"(archive_signal_id={archive_signal_id})"
            )
            return True  # idempotent siker

        duration_bars = (
            round(trade["duration_minutes"] / 15)
            if trade["duration_minutes"] is not None
            else None
        )

        def _bool_int(v) -> Optional[int]:
            """Boolean → 0/1/None SQLite-kompatibilis formátumba."""
            return None if v is None else int(bool(v))

        conn.execute(
            """
            INSERT INTO archive_simulated_trades (
                archive_signal_id, ticker_symbol, direction, status,
                entry_price, entry_time,
                stop_loss_price, take_profit_price,
                exit_price, exit_time, exit_reason,
                pnl_percent, pnl_net_percent,
                duration_bars,
                combined_score, overall_confidence,
                is_real_trade,
                direction_2h_eligible, direction_2h_correct, direction_2h_pct
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?,
                ?,
                ?, ?,
                ?,
                ?, ?, ?
            )
            """,
            (
                archive_signal_id,
                trade["symbol"],
                trade["direction"],
                "CLOSED",
                trade["entry_price"],
                trade["entry_execution_time"],
                trade["stop_loss_price"],
                trade["take_profit_price"],
                trade["exit_price"],
                trade["exit_execution_time"],
                trade["exit_reason"],
                trade["pnl_percent"],
                trade["pnl_percent"],                    # pnl_net_percent = pnl_percent
                duration_bars,
                trade["entry_score"],                    # combined_score
                trade["entry_confidence"],               # overall_confidence
                _bool_int(trade["is_real_trade"]),
                _bool_int(trade["direction_2h_eligible"]),
                _bool_int(trade["direction_2h_correct"]),
                trade["direction_2h_pct"],
            ),
        )

        # Signal státuszát 'migrated'-re állítjuk, hogy eltűnjön a live nézetből.
        # A live history endpoint ['active','expired','archived']-et mutat alapból —
        # 'migrated' nem szerepel köztük, így a signal csak az archive nézetben látszik.
        if trade["entry_signal_id"]:
            conn.execute(
                "UPDATE signals SET status = 'migrated' WHERE id = ?",
                (trade["entry_signal_id"],),
            )

        # Híreket is átmásoljuk archive_news_items-be
        _migrate_news(conn, ticker_symbol, signal_ts)

        conn.commit()
        logger.info(
            f"[Migrator] ✅ Trade {trade_id} "
            f"({trade['symbol']} {trade['direction']} {trade['exit_reason']}) "
            f"→ archive_simulated_trades (archive_signal_id={archive_signal_id})"
        )
        return True

    except Exception as exc:
        logger.error(f"[Migrator] ❌ Trade {trade_id} migrálása sikertelen: {exc}", exc_info=True)
        try:
            conn.rollback()
        except Exception:
            pass
        return False

    finally:
        conn.close()


def migrate_signal_without_trade(
    signal_id: int,
    db_path: Path = DATABASE_PATH,
) -> bool:
    """
    Trade nélküli lejárt/archivált live signal migrálása archive_signals-ba.

    Csak a signal adatait másolja át (signal_calculations → archive_signals).
    Az archive_simulated_trades bejegyzést az ArchiveBacktestService hozza létre
    a következő recalculate-and-resimulate futtatáskor — így a recalc is
    tudja majd újraszámolni a score-okat, és a backtest is tud rá trade-et szimulálni.

    Feltételek:
      - signal.status IN ('expired', 'archived')
      - nincs hozzá CLOSED simulated_trade (azt migrate_closed_trade_to_archive kezeli)
      - van signal_calculations bejegyzés

    Returns
    -------
    bool
        True  = sikeres migráció (vagy már korábban migrált → idempotent)
        False = kihagyva vagy hiba
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        # 1. Signal betöltése — migrálható feltételek:
        #    a) Bármely nem-aktív státusz (soha nem nyit trade-et)
        #    b) HOLD döntés active státusszal — soha nem nyit trade-et,
        #       feleslegesen tömíti a live nézetet
        _MIGRATABLE = (
            'expired', 'archived', 'nogo',
            'skip_hours', 'parallel_skip', 'no_sl_tp',
            'no_data', 'invalid_levels',
            'macd_filtered', 'rsi_filtered',
        )
        sig = conn.execute(
            f"""
            SELECT id, ticker_id, ticker_symbol, decision, strength, status,
                   combined_score, sentiment_score, technical_score, risk_score,
                   overall_confidence, sentiment_confidence, technical_confidence,
                   entry_price, stop_loss, take_profit, risk_reward_ratio,
                   reasoning_json, technical_indicator_id, created_at
            FROM signals
            WHERE id = ?
              AND (
                status IN ({','.join('?'*len(_MIGRATABLE))})
                OR (status = 'active' AND decision = 'HOLD')
              )
            """,
            (signal_id, *_MIGRATABLE),
        ).fetchone()

        if not sig:
            logger.debug(
                f"[Migrator] Signal {signal_id}: nem migrálható "
                "(nem HOLD/active, és nem lejárt státusz) — kihagyva"
            )
            return False

        # 2a. Ha van CLOSED trade, azt migrate_closed_trade_to_archive kezeli
        closed_trade = conn.execute(
            """
            SELECT id FROM simulated_trades
            WHERE entry_signal_id = ? AND status = 'CLOSED'
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()

        if closed_trade:
            logger.debug(
                f"[Migrator] Signal {signal_id}: lezárt trade létezik "
                f"(trade_id={closed_trade['id']}) — migrate_closed_trade_to_archive kezeli"
            )
            return False

        # 2b. Ha van OPEN trade, a signal még él — nem migrálható
        open_trade = conn.execute(
            """
            SELECT id FROM simulated_trades
            WHERE entry_signal_id = ? AND status = 'OPEN'
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()

        if open_trade:
            logger.debug(
                f"[Migrator] Signal {signal_id}: nyitott trade létezik "
                f"(trade_id={open_trade['id']}) — signal még live, kihagyva"
            )
            return False

        # 3a. signal_calculations betöltése (elsődleges forrás)
        sc = conn.execute(
            """
            SELECT * FROM signal_calculations
            WHERE signal_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (signal_id,),
        ).fetchone()

        # 3b. Ha nincs signal_calculations → fallback: technical_indicators
        ti = None
        if not sc and sig["technical_indicator_id"]:
            ti = conn.execute(
                "SELECT * FROM technical_indicators WHERE id = ?",
                (sig["technical_indicator_id"],),
            ).fetchone()

        if not sc and not ti and not sig["entry_price"]:
            logger.warning(
                f"[Migrator] Signal {signal_id}: nincs signal_calculations, "
                "technical_indicators és entry_price sem — kihagyva"
            )
            return False

        # Egységes adatforrás összeállítása (sc elsőbbséget élvez)
        ticker_symbol  = (sc["ticker_symbol"]  if sc else sig["ticker_symbol"])
        signal_ts      = (sc["calculated_at"]  if sc else sig["created_at"])
        close_price    = (sc["current_price"]  if sc else
                          (ti["close_price"] if ti else sig["entry_price"]))
        atr_val        = (sc["atr"]            if sc else (ti["atr"]   if ti else None))
        atr_pct_val    = (sc["atr_pct"]        if sc else
                          (round(atr_val / close_price * 100, 4)
                           if (atr_val and close_price) else None))

        # 4. Idempotencia: már szerepel-e archive_signals-ban?
        existing = conn.execute(
            "SELECT id FROM archive_signals WHERE ticker_symbol = ? AND signal_timestamp = ?",
            (ticker_symbol, signal_ts),
        ).fetchone()

        if existing:
            # Már migrálva — de a signal státuszát még frissítjük ha szükséges
            if sig["status"] != "migrated":
                conn.execute(
                    "UPDATE signals SET status = 'migrated' WHERE id = ?",
                    (signal_id,),
                )
                conn.commit()
                logger.debug(
                    f"[Migrator] Signal {signal_id}: már archive-ban, "
                    "de signals.status → migrated frissítve"
                )
            return True  # idempotent siker

        # 5. archive_signals INSERT — sc adatok, vagy ti/signals fallback
        overall_confidence = _avg3(
            sc["sentiment_confidence"] if sc else sig["sentiment_confidence"],
            sc["technical_confidence"] if sc else sig["technical_confidence"],
            sc["risk_confidence"]      if sc else None,
        )

        conn.execute(
            """
            INSERT OR IGNORE INTO archive_signals (
                ticker_id, ticker_symbol, signal_timestamp,
                decision, strength,
                combined_score, sentiment_score, technical_score, risk_score,
                overall_confidence,
                sentiment_confidence, technical_confidence, risk_confidence,
                entry_price, stop_loss, take_profit, risk_reward_ratio,
                close_price,
                rsi, macd, macd_signal, macd_hist,
                sma_20, sma_50, sma_200,
                atr, atr_pct,
                bb_upper, bb_lower,
                stoch_k, stoch_d,
                nearest_support, nearest_resistance,
                news_count, reasoning_json,
                generated_at
            ) VALUES (
                ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                CURRENT_TIMESTAMP
            )
            """,
            (
                sig["ticker_id"],
                ticker_symbol,
                signal_ts,
                sc["decision"]          if sc else sig["decision"],
                sig["strength"],
                sc["combined_score"]    if sc else sig["combined_score"],
                sc["sentiment_score"]   if sc else sig["sentiment_score"],
                sc["technical_score"]   if sc else sig["technical_score"],
                sc["risk_score"]        if sc else sig["risk_score"],
                overall_confidence,
                sc["sentiment_confidence"] if sc else sig["sentiment_confidence"],
                sc["technical_confidence"] if sc else sig["technical_confidence"],
                sc["risk_confidence"]   if sc else None,
                sc["entry_price"]       if sc else sig["entry_price"],
                sc["stop_loss"]         if sc else sig["stop_loss"],
                sc["take_profit"]       if sc else sig["take_profit"],
                sc["risk_reward_ratio"] if sc else sig["risk_reward_ratio"],
                close_price,
                sc["rsi"]               if sc else (ti["rsi"]              if ti else None),
                sc["macd"]              if sc else (ti["macd"]             if ti else None),
                sc["macd_signal"]       if sc else (ti["macd_signal"]      if ti else None),
                sc["macd_histogram"]    if sc else (ti["macd_histogram"]   if ti else None),
                sc["sma_20"]            if sc else (ti["sma_20"]           if ti else None),
                sc["sma_50"]            if sc else (ti["sma_50"]           if ti else None),
                sc["sma_200"]           if sc else (ti["sma_200"]          if ti else None),
                atr_val,
                atr_pct_val,
                sc["bb_upper"]          if sc else (ti["bb_upper"]         if ti else None),
                sc["bb_lower"]          if sc else (ti["bb_lower"]         if ti else None),
                sc["stoch_k"]           if sc else (ti["stoch_k"]          if ti else None),
                sc["stoch_d"]           if sc else (ti["stoch_d"]          if ti else None),
                sc["nearest_support"]   if sc else None,   # ti-ben nincs
                sc["nearest_resistance"] if sc else None,  # ti-ben nincs
                sc["news_count"]        if sc else None,
                sig["reasoning_json"],
            ),
        )

        # Minden migrált signalt 'migrated' státuszra állítunk,
        # így eltűnnek a live nézetből és csak az archive nézetben látszanak.
        conn.execute(
            "UPDATE signals SET status = 'migrated' WHERE id = ?",
            (signal_id,),
        )

        # Híreket is átmásoljuk archive_news_items-be
        _migrate_news(conn, ticker_symbol, signal_ts)

        conn.commit()
        logger.info(
            f"[Migrator] ✅ Signal {signal_id} "
            f"({ticker_symbol} {sig['decision']} status={sig['status']} → migrated) "
            f"→ archive_signals (trade nélkül)"
        )
        return True

    except Exception as exc:
        logger.error(
            f"[Migrator] ❌ Signal {signal_id} (trade nélküli) migrálása sikertelen: {exc}",
            exc_info=True,
        )
        try:
            conn.rollback()
        except Exception:
            pass
        return False

    finally:
        conn.close()


def _migrate_news(conn: sqlite3.Connection, ticker_symbol: str, signal_ts: str) -> int:
    """
    A signal_timestamp előtti 24 órában publikált, ticker-hez tartozó news_items
    rekordjait átmásolja archive_news_items-be (INSERT OR IGNORE — idempotent).

    Returns: beszúrt sorok száma
    """
    conn.execute(
        """
        INSERT OR IGNORE INTO archive_news_items (
            url_hash, ticker_symbol, queried_ticker,
            title, url, published_at, fetched_at,
            source, full_text, language,
            is_relevant, sentiment_confidence,
            is_duplicate, duplicate_of, cluster_id,
            av_relevance_score,
            finbert_score, llm_score, llm_price_impact,
            llm_impact_level, llm_impact_duration,
            llm_catalyst_type, llm_priced_in, llm_confidence,
            llm_reason, llm_latency_ms,
            active_score, active_score_source,
            llm_score_worthy, llm_is_first_report, llm_surprise_dir
        )
        SELECT
            ni.url_hash,
            t.symbol,
            t.symbol,
            ni.title, ni.url, ni.published_at, ni.fetched_at,
            ns.name,
            ni.full_text, ni.language,
            ni.is_relevant, ni.sentiment_confidence,
            ni.is_duplicate, ni.duplicate_of, ni.cluster_id,
            nt.relevance_score,
            ni.finbert_score, ni.llm_score, ni.llm_price_impact,
            ni.llm_impact_level, ni.llm_impact_duration,
            ni.llm_catalyst_type, ni.llm_priced_in, ni.llm_confidence,
            ni.llm_reason, ni.llm_latency_ms,
            ni.active_score, ni.active_score_source,
            ni.llm_score_worthy, ni.llm_is_first_report, ni.llm_surprise_dir
        FROM news_items ni
        JOIN news_tickers nt ON nt.news_id = ni.id
        JOIN tickers t ON t.id = nt.ticker_id
        LEFT JOIN news_sources ns ON ns.id = ni.source_id
        WHERE t.symbol = ?
          AND ni.published_at >= datetime(?, '-24 hours')
          AND ni.published_at <= ?
        """,
        (ticker_symbol, signal_ts, signal_ts),
    )
    return conn.total_changes


def _avg3(a, b, c) -> Optional[float]:
    """Három érték átlaga, None értékeket kihagyva."""
    vals = [v for v in (a, b, c) if v is not None]
    return sum(vals) / len(vals) if vals else None
