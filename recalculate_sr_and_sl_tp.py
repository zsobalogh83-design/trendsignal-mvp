"""
Visszamenőleges S/R + SL/TP újrakalkuláló script
==================================================
1. lépés: Minden signal S/R szintjét újraszámolja a javított detect_support_resistance()
          algoritmussal, a DB-ben tárolt historikus 1d árfolyamadatokból.

2. lépés: Minden signal SL/TP értékét újraszámolja a javított _calculate_levels()
          algoritmussal az új S/R értékek felhasználásával.

Frissíti:
  - signals.stop_loss, .take_profit, .risk_reward_ratio
  - signals.reasoning_json (support_resistance + levels_meta)
  - signal_calculations.nearest_support, .nearest_resistance
  - signal_calculations.stop_loss, .take_profit, .risk_reward_ratio
  - signal_calculations.entry_exit_details (sl_method, tp_method)
  - simulated_trades.stop_loss_price, .take_profit_price (OPEN, sl_tp_update_count==0)
  - simulated_trades.initial_stop_loss_price, .initial_take_profit_price

Futtatás:
  python recalculate_sr_and_sl_tp.py [--dry-run] [--ticker AAPL] [--signal-id 123] [--verbose]
"""

import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ── Import project modules ────────────────────────────────────────────────────
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

try:
    from database import SessionLocal
    from models import Signal, SignalCalculation, SimulatedTrade, PriceData
    from signal_generator import SignalGenerator
    from technical_analyzer import detect_support_resistance
    from config import get_config
except ImportError as e:
    logger.error(f"Import hiba: {e}")
    logger.error("Futtasd a script gyökér könyvtárból: python recalculate_sr_and_sl_tp.py")
    sys.exit(1)

import pandas as pd
import numpy as np
from sqlalchemy import and_


# ─────────────────────────────────────────────────────────────────────────────
# 1. HISTORIKUS ÁRFOLYAMADATOK LEKÉRÉSE A DB-BŐL
# ─────────────────────────────────────────────────────────────────────────────

def fetch_daily_data_from_db(db, ticker: str, as_of_date: datetime, lookback_days: int = 180) -> pd.DataFrame:
    """
    Lekéri a ticker összes elérhető 1d OHLCV adatát a DB-ből, az as_of_date-ig.
    Az összes rendelkezésre álló historikus adatot használja (nem limitál lookback_days-re),
    hogy minél több S/R szintet lehessen detektálni.
    """
    rows = (
        db.query(PriceData)
        .filter(
            PriceData.ticker_symbol == ticker,
            PriceData.interval == '1d',
            PriceData.timestamp <= as_of_date,
        )
        .order_by(PriceData.timestamp.asc())
        .all()
    )

    if not rows:
        return pd.DataFrame()

    data = {
        'Open':   [r.open   for r in rows],
        'High':   [r.high   for r in rows],
        'Low':    [r.low    for r in rows],
        'Close':  [r.close  for r in rows],
        'Volume': [r.volume for r in rows],
    }
    idx = pd.DatetimeIndex([r.timestamp for r in rows])
    df = pd.DataFrame(data, index=idx)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. S/R ÚJRAKALKULÁLÁS EGY SIGNALHOZ
# ─────────────────────────────────────────────────────────────────────────────

def recalculate_sr_for_signal(db, signal: Signal, config, verbose: bool = False) -> dict:
    """
    Újraszámítja az S/R szinteket a signal keletkezési idejéhez tartozó historikus adatokból.
    Visszaad egy dict-et:
      {
        'nearest_support': float|None,
        'nearest_resistance': float|None,
        'support_levels': [...],     # teljes lista
        'resistance_levels': [...],  # teljes lista
        'data_bars': int,            # hány 1d bar volt elérhető
      }
    """
    ticker    = signal.ticker_symbol
    as_of     = signal.created_at or datetime.utcnow()
    lookback  = getattr(config, 'sr_dbscan_lookback', 180)

    df = fetch_daily_data_from_db(db, ticker, as_of, lookback_days=lookback + 10)

    if df.empty or len(df) < 10:
        if verbose:
            logger.debug(f"    Nincs elég 1d adat: {ticker} @ {as_of.date()} ({len(df)} bar)")
        return {
            'nearest_support': None,
            'nearest_resistance': None,
            'support_levels': [],
            'resistance_levels': [],
            'data_bars': len(df),
        }

    # Config paraméterek — visszamenőleges kalkulációhoz lazított paraméterek:
    # order=5 (order=7 túl kevés pivotot talál napi adaton),
    # min_samples=2 (min_samples=3 túl szigorú, üres eredményt ad)
    proximity_pct = getattr(config, 'sr_dbscan_eps', 4.0) / 100.0   # 4.0 → 0.04
    order         = 5   # Napi adatra optimalizált (order=7 túl kevés pivotot ad)
    min_samples   = 2   # Két egyező pivot elegendő egy szignifikáns szinthez

    try:
        sr = detect_support_resistance(
            df,
            lookback_days=len(df),   # Az összes elérhető adatot felhasználja
            proximity_pct=proximity_pct,
            order=order,
            min_samples=min_samples,
        )
    except Exception as e:
        logger.warning(f"    S/R kalkuláció hiba ({ticker}): {e}")
        return {
            'nearest_support': None,
            'nearest_resistance': None,
            'support_levels': [],
            'resistance_levels': [],
            'data_bars': len(df),
        }

    nearest_support    = sr['support'][0]['price']    if sr['support']    else None
    nearest_resistance = sr['resistance'][0]['price'] if sr['resistance'] else None

    if verbose:
        logger.debug(
            f"    S/R ({len(df)} bars): "
            f"support={nearest_support}, resistance={nearest_resistance} "
            f"({len(sr['support'])} sup / {len(sr['resistance'])} res levels)"
        )

    return {
        'nearest_support':    nearest_support,
        'nearest_resistance': nearest_resistance,
        'support_levels':     sr['support'],
        'resistance_levels':  sr['resistance'],
        'data_bars':          len(df),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. SL/TP ÚJRAKALKULÁLÁS (meglévő logika, új S/R-rel)
# ─────────────────────────────────────────────────────────────────────────────

def recalculate_sl_tp_for_signal(signal: Signal, calc: SignalCalculation,
                                  sr_result: dict, generator: SignalGenerator) -> dict | None:
    """
    Újraszámítja az SL/TP értékeket az új S/R adatokkal.
    Visszaad egy dict-et az előtte/utána értékekkel, vagy None-t ha kihagyandó.
    """
    if signal.decision == "HOLD" or not signal.entry_price:
        return None

    # technical_data rekonstruálása (ugyanaz mint recalculate_sl_tp.py-ban)
    reasoning = {}
    if signal.reasoning_json:
        try:
            reasoning = json.loads(signal.reasoning_json)
        except Exception:
            pass

    components = reasoning.get("components", {})
    tech = components.get("technical", {})

    atr = None
    atr_pct = None
    if calc:
        atr = calc.atr
        atr_pct = calc.atr_pct
    if atr is None:
        atr = tech.get("atr")
    if atr_pct is None:
        atr_pct = tech.get("atr_pct")

    entry_price = signal.entry_price
    if atr is None and entry_price > 0:
        atr = entry_price * 0.02
        atr_pct = 2.0

    technical_data = {
        "current_price":      entry_price,
        "atr":                atr,
        "atr_pct":            atr_pct or 2.0,
        "overall_confidence": signal.overall_confidence or 0.6,
        "rsi":                tech.get("rsi"),
        "sma_20":             tech.get("sma_20") or (calc.sma_20 if calc else None),
        "sma_50":             tech.get("sma_50") or (calc.sma_50 if calc else None),
        "adx":                tech.get("adx")    or (calc.adx    if calc else None),
    }

    # risk_data az ÚJ S/R értékekkel (new format: list of dicts)
    risk_data = {
        "support":    sr_result['support_levels'],
        "resistance": sr_result['resistance_levels'],
        # fallback single values is also kept for old parse_support_resistance compat
        "nearest_support":    sr_result['nearest_support'],
        "nearest_resistance": sr_result['nearest_resistance'],
        "score":      signal.risk_score or 0,
        "volatility": 2.5,
        "confidence": 0.7,
    }

    try:
        levels = generator._calculate_levels(
            decision       = signal.decision,
            current_price  = entry_price,
            technical_data = technical_data,
            risk_data      = risk_data,
        )
    except Exception as e:
        logger.warning(f"  _calculate_levels hiba #{signal.id}: {e}")
        return None

    if levels[0] is None:
        return None

    new_entry, new_sl, new_tp, new_rr, sl_method, tp_method = levels

    return {
        "signal_id":  signal.id,
        "ticker":     signal.ticker_symbol,
        "decision":   signal.decision,
        "entry":      entry_price,
        # Régi S/R
        "old_support":    sr_result.get('_old_support'),
        "old_resistance": sr_result.get('_old_resistance'),
        # Új S/R
        "new_support":    sr_result['nearest_support'],
        "new_resistance": sr_result['nearest_resistance'],
        # Régi SL/TP
        "old_sl": signal.stop_loss,
        "old_tp": signal.take_profit,
        "old_rr": signal.risk_reward_ratio,
        # Új SL/TP
        "new_sl":    new_sl,
        "new_tp":    new_tp,
        "new_rr":    new_rr,
        "sl_method": sl_method,
        "tp_method": tp_method,
        "data_bars": sr_result['data_bars'],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. DB ÍRÁS
# ─────────────────────────────────────────────────────────────────────────────

def write_to_db(db, signal: Signal, calc: SignalCalculation, result: dict, sr_result: dict):
    """Frissíti a signals, signal_calculations és reasoning_json mezőket."""

    new_sl     = result['new_sl']
    new_tp     = result['new_tp']
    new_rr     = result['new_rr']
    sl_method  = result['sl_method']
    tp_method  = result['tp_method']
    new_sup    = sr_result['nearest_support']
    new_res    = sr_result['nearest_resistance']
    sup_levels = sr_result['support_levels']
    res_levels = sr_result['resistance_levels']

    # ── signals tábla ────────────────────────────────────────────────────────
    signal.stop_loss         = new_sl
    signal.take_profit       = new_tp
    signal.risk_reward_ratio = new_rr

    # reasoning_json frissítése
    try:
        r = json.loads(signal.reasoning_json) if signal.reasoning_json else {}

        # S/R frissítése a reasoning.risk.support_resistance-ben
        r.setdefault("reasoning", {}).setdefault("risk", {})["support_resistance"] = {
            "support":    new_sup,
            "resistance": new_res,
        }

        # Részletes szintek mentése
        r["reasoning"]["risk"]["support_levels"]    = sup_levels
        r["reasoning"]["risk"]["resistance_levels"] = res_levels

        # levels_meta frissítése
        r["levels_meta"] = {
            "sl_method": sl_method,
            "tp_method": tp_method,
        }

        signal.reasoning_json = json.dumps(r, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"  reasoning_json update hiba #{signal.id}: {e}")

    # ── signal_calculations tábla ────────────────────────────────────────────
    if calc:
        calc.nearest_support    = new_sup
        calc.nearest_resistance = new_res
        calc.stop_loss          = new_sl
        calc.take_profit        = new_tp
        calc.risk_reward_ratio  = new_rr

        try:
            if calc.entry_exit_details:
                eed = json.loads(calc.entry_exit_details)
                eed["stop_loss"]         = new_sl
                eed["take_profit"]       = new_tp
                eed["risk_reward_ratio"] = new_rr
                eed["sl_method"]         = sl_method
                eed["tp_method"]         = tp_method
                calc.entry_exit_details  = json.dumps(eed, ensure_ascii=False)
        except Exception:
            pass

        try:
            if calc.risk_details:
                rd = json.loads(calc.risk_details)
                rd["nearest_support"]    = new_sup
                rd["nearest_resistance"] = new_res
                rd["support_levels"]     = sup_levels
                rd["resistance_levels"]  = res_levels
                calc.risk_details        = json.dumps(rd, ensure_ascii=False)
        except Exception:
            pass


def update_simulated_trades(db, signal: Signal, new_sl: float, new_tp: float, dry_run: bool) -> int:
    """Frissíti a signal-hoz kötött SimulatedTrade rekordokat."""
    trades = db.query(SimulatedTrade).filter(
        SimulatedTrade.entry_signal_id == signal.id
    ).all()

    count = 0
    for trade in trades:
        if not dry_run:
            trade.initial_stop_loss_price   = new_sl
            trade.initial_take_profit_price = new_tp

            if trade.status == 'OPEN' and (trade.sl_tp_update_count or 0) == 0:
                trade.stop_loss_price   = new_sl
                trade.take_profit_price = new_tp
                trade.sl_tp_last_updated_at = datetime.utcnow()
        count += 1

    return count


# ─────────────────────────────────────────────────────────────────────────────
# 5. FŐ LOGIKA
# ─────────────────────────────────────────────────────────────────────────────

def run(args):
    dry_run = args.dry_run
    verbose = args.verbose
    mode    = "DRY-RUN (nem ír az adatbázisba)" if dry_run else "LIVE (ír az adatbázisba)"

    logger.info("=" * 65)
    logger.info("TrendSignal S/R + SL/TP Visszamenőleges Újrakalkulátor")
    logger.info(f"Mód: {mode}")
    logger.info("=" * 65)

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    db        = SessionLocal()
    config    = get_config()
    if hasattr(config, 'reload'):
        config.reload()

    generator = SignalGenerator()

    try:
        # ── Signalok lekérése ─────────────────────────────────────────────
        query = db.query(Signal).filter(
            Signal.decision.in_(["BUY", "SELL"]),
            Signal.entry_price.isnot(None),
            Signal.entry_price > 0,
        )

        if args.ticker:
            query = query.filter(Signal.ticker_symbol == args.ticker.upper())
            logger.info(f"Szűrés: ticker = {args.ticker.upper()}")

        if args.signal_id:
            query = query.filter(Signal.id == args.signal_id)
            logger.info(f"Szűrés: signal_id = {args.signal_id}")

        if args.from_id:
            query = query.filter(Signal.id >= args.from_id)
            logger.info(f"Szűrés: id >= {args.from_id}")

        signals = query.order_by(Signal.id.asc()).all()
        total   = len(signals)
        logger.info(f"Feldolgozandó signalok: {total} db")
        logger.info("-" * 65)

        if total == 0:
            logger.info("Nincs feldolgozandó signal.")
            return

        # ── SignalCalculation előre lekérése ──────────────────────────────
        signal_ids    = [s.id for s in signals]
        calcs         = db.query(SignalCalculation).filter(
            SignalCalculation.signal_id.in_(signal_ids)
        ).all()
        calc_by_signal = {c.signal_id: c for c in calcs}

        # ── Statisztikák ─────────────────────────────────────────────────
        stats = {
            "processed":      0,
            "skipped":        0,
            "no_data":        0,
            "sr_changed":     0,
            "sl_changed":     0,
            "tp_changed":     0,
            "rr_improved":    0,
            "trades_updated": 0,
            "errors":         0,
        }

        # ── Feldolgozás ───────────────────────────────────────────────────
        for i, signal in enumerate(signals, 1):
            calc = calc_by_signal.get(signal.id)

            # Régi S/R értékek kimentése (összehasonlításhoz)
            old_sup = calc.nearest_support    if calc else None
            old_res = calc.nearest_resistance if calc else None

            # Ha calc nincs, próbáljuk reasoning_json-ból
            if old_sup is None or old_res is None:
                try:
                    r  = json.loads(signal.reasoning_json) if signal.reasoning_json else {}
                    sr = r.get("reasoning", {}).get("risk", {}).get("support_resistance", {})
                    if old_sup is None: old_sup = sr.get("support")
                    if old_res is None: old_res = sr.get("resistance")
                except Exception:
                    pass

            try:
                # ── LÉPÉS 1: S/R újrakalkulálás ──────────────────────────
                sr_result = recalculate_sr_for_signal(db, signal, config, verbose=verbose)
                sr_result['_old_support']    = old_sup
                sr_result['_old_resistance'] = old_res

                if sr_result['data_bars'] < 10:
                    logger.warning(
                        f"  #{signal.id:4d} {signal.ticker_symbol:8s} — "
                        f"nincs elegendő 1d adat ({sr_result['data_bars']} bar), kihagyva"
                    )
                    stats["no_data"] += 1
                    stats["skipped"] += 1
                    continue

                # ── LÉPÉS 2: SL/TP újrakalkulálás ────────────────────────
                result = recalculate_sl_tp_for_signal(signal, calc, sr_result, generator)

                if result is None:
                    stats["skipped"] += 1
                    continue

            except Exception as e:
                logger.error(f"  ❌ Signal #{signal.id} ({signal.ticker_symbol}): {e}")
                stats["errors"] += 1
                continue

            stats["processed"] += 1

            # Változás detektálás
            sr_sup_changed = abs((sr_result['nearest_support']    or 0) - (old_sup or 0)) > 0.01
            sr_res_changed = abs((sr_result['nearest_resistance'] or 0) - (old_res or 0)) > 0.01
            sl_changed     = abs((result['new_sl'] or 0) - (result['old_sl'] or 0)) > 0.001
            tp_changed     = abs((result['new_tp'] or 0) - (result['old_tp'] or 0)) > 0.001
            rr_old         = result['old_rr'] or 0
            rr_new         = result['new_rr'] or 0

            if sr_sup_changed or sr_res_changed: stats["sr_changed"] += 1
            if sl_changed: stats["sl_changed"] += 1
            if tp_changed: stats["tp_changed"] += 1
            if rr_new > rr_old: stats["rr_improved"] += 1

            # Log
            entry = result['entry']
            sup_str = f"{sr_result['nearest_support']:.2f}"  if sr_result['nearest_support']    else "None"
            res_str = f"{sr_result['nearest_resistance']:.2f}" if sr_result['nearest_resistance'] else "None"
            old_sup_str = f"{old_sup:.2f}" if old_sup else "None"
            old_res_str = f"{old_res:.2f}" if old_res else "None"

            logger.info(
                f"  #{result['signal_id']:4d} {result['ticker']:8s} {result['decision']:4s} | "
                f"Entry: {entry:.2f} | "
                f"SUP: {old_sup_str} → {sup_str} | "
                f"RES: {old_res_str} → {res_str} | "
                f"SL: {result['old_sl']:.2f} → {result['new_sl']:.2f} [{result['sl_method']}] | "
                f"TP: {result['old_tp']:.2f} → {result['new_tp']:.2f} [{result['tp_method']}] | "
                f"R:R: {rr_old:.2f} → {rr_new:.2f}"
            )

            # DB írás
            if not dry_run:
                write_to_db(db, signal, calc, result, sr_result)
                n = update_simulated_trades(db, signal, result['new_sl'], result['new_tp'], dry_run=False)
                stats["trades_updated"] += n
            else:
                n = update_simulated_trades(db, signal, result['new_sl'], result['new_tp'], dry_run=True)
                stats["trades_updated"] += n

            # Közbenső commit minden 50. rekordnál
            if not dry_run and i % 50 == 0:
                db.commit()
                logger.info(f"  Közbenső commit: {i}/{total}")

        # ── Végső commit ──────────────────────────────────────────────────
        if not dry_run:
            db.commit()
            logger.info("  Végső commit kész.")

        # ── Összefoglaló ──────────────────────────────────────────────────
        logger.info("")
        logger.info("=" * 65)
        logger.info("ÖSSZEFOGLALÓ")
        logger.info("=" * 65)
        logger.info(f"  Összes signal:          {total}")
        logger.info(f"  Feldolgozva:            {stats['processed']}")
        logger.info(f"  Kihagyva (HOLD/NULL):   {stats['skipped']}")
        logger.info(f"  Kihagyva (nincs adat):  {stats['no_data']}")
        logger.info(f"  Hiba:                   {stats['errors']}")
        logger.info(f"  S/R megváltozott:       {stats['sr_changed']}")
        logger.info(f"  SL megváltozott:        {stats['sl_changed']}")
        logger.info(f"  TP megváltozott:        {stats['tp_changed']}")
        logger.info(f"  R:R javult:             {stats['rr_improved']}")
        logger.info(f"  Trade rekordok érintve: {stats['trades_updated']}")
        if dry_run:
            logger.info("")
            logger.info("  DRY-RUN: adatbázis NEM módosult.")
            logger.info("  Futtasd --dry-run nélkül az éles íráshoz.")
        logger.info("=" * 65)

    except KeyboardInterrupt:
        logger.warning("Megszakítva (Ctrl+C). Rollback...")
        if not dry_run:
            db.rollback()
    except Exception as e:
        logger.error(f"Kritikus hiba: {e}", exc_info=True)
        if not dry_run:
            db.rollback()
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="TrendSignal S/R + SL/TP visszamenőleges újrakalkulátor"
    )
    parser.add_argument("--dry-run",   action="store_true",
                        help="Nem ír az adatbázisba, csak megmutatja a változásokat")
    parser.add_argument("--ticker",    type=str, default=None,
                        help="Csak az adott ticker signaljait számolja újra (pl. AAPL)")
    parser.add_argument("--signal-id", type=int, default=None,
                        help="Csak egy adott signal újrakalkulálása (ID alapján)")
    parser.add_argument("--from-id",   type=int, default=None,
                        help="Csak az adott ID-tól kezdve")
    parser.add_argument("--verbose",   action="store_true",
                        help="Részletes debug log")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
