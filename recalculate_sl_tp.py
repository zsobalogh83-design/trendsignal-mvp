"""
Visszamenőleges SL/TP újrakalkuláló script
==========================================
Minden meglévő BUY/SELL signal SL/TP értékét újraszámolja az aktuális
(fejlettebb) kalkulációs logikával, majd frissíti:

  1. signals.stop_loss, signals.take_profit, signals.risk_reward_ratio
  2. signals.reasoning_json (levels_meta hozzáadva)
  3. signal_calculations.stop_loss, .take_profit, .risk_reward_ratio
  4. simulated_trades.stop_loss_price, .take_profit_price  (OPEN trades only)
     → initial_stop_loss_price, initial_take_profit_price szintén frissül,
       ha a trade az adott signalhoz tartozik (entry_signal_id match)

HOLD signalokat és NULL entry_price-ú signalokat kihagyja.

Futtatás:
  python recalculate_sl_tp.py [--dry-run] [--ticker AAPL] [--signal-id 123]

Opciók:
  --dry-run      Nem ír semmit az adatbázisba, csak kiírja az előtt/utána értékeket
  --ticker XYZ   Csak az adott ticker signaljait számolja újra
  --signal-id N  Csak egy adott signal-t számol újra
  --from-id N    Signal ID-tól kezdve (pl. csak az új signalokat)
"""

import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Import project modules (same pattern as main.py)
# ─────────────────────────────────────────────
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

try:
    from database import SessionLocal
    from models import Signal, SignalCalculation, SimulatedTrade
    from signal_generator import SignalGenerator
    from config import get_config
except ImportError as e:
    logger.error(f"Import hiba: {e}")
    logger.error("Futtasd a script gyökér könyvtárból: python recalculate_sl_tp.py")
    sys.exit(1)


def build_technical_data_from_signal(signal: Signal, calc: SignalCalculation = None) -> dict:
    """
    Rekonstruálja a technical_data dict-et a signal és signal_calculation rekordokból.
    Ez kell a _calculate_levels() híváshoz.
    """
    reasoning = {}
    if signal.reasoning_json:
        try:
            reasoning = json.loads(signal.reasoning_json)
        except Exception:
            pass

    components = reasoning.get("components", {})
    tech = components.get("technical", {})

    # ATR — prioritás: signal_calculation > reasoning.components.technical > becslés
    atr = None
    atr_pct = None

    if calc:
        atr = calc.atr
        atr_pct = calc.atr_pct

    if atr is None:
        atr = tech.get("atr")
    if atr_pct is None:
        atr_pct = tech.get("atr_pct")

    # Fallback: ATR becslés entry_price 2%-a
    entry_price = signal.entry_price or 0
    if atr is None and entry_price > 0:
        atr = entry_price * 0.02
        atr_pct = 2.0

    technical_data = {
        "current_price": entry_price,
        "atr":           atr,
        "atr_pct":       atr_pct or 2.0,
        "overall_confidence": signal.overall_confidence or 0.6,
        "rsi":   tech.get("rsi"),
        "sma_20": tech.get("sma_20") or (calc.sma_20 if calc else None),
        "sma_50": tech.get("sma_50") or (calc.sma_50 if calc else None),
        "adx":   tech.get("adx")   or (calc.adx   if calc else None),
    }

    return technical_data


def build_risk_data_from_signal(signal: Signal, calc: SignalCalculation = None) -> dict:
    """
    Rekonstruálja a risk_data dict-et a signal és signal_calculation rekordokból.
    """
    reasoning = {}
    if signal.reasoning_json:
        try:
            reasoning = json.loads(signal.reasoning_json)
        except Exception:
            pass

    reasoning_inner = reasoning.get("reasoning", {})
    risk_inner = reasoning_inner.get("risk", {})
    sr = risk_inner.get("support_resistance", {})

    # S/R szintek
    nearest_support    = sr.get("support")
    nearest_resistance = sr.get("resistance")

    # Fallback: signal_calculation tábla
    if calc:
        if nearest_support    is None: nearest_support    = calc.nearest_support
        if nearest_resistance is None: nearest_resistance = calc.nearest_resistance

    risk_data = {
        "nearest_support":    nearest_support,
        "nearest_resistance": nearest_resistance,
        "score":              signal.risk_score or 0,
        "volatility":         risk_inner.get("volatility", 2.5),
        "confidence":         0.7,
    }

    return risk_data


def recalculate_signal(
    signal: Signal,
    calc: SignalCalculation,
    generator: SignalGenerator,
    dry_run: bool
) -> dict:
    """
    Újraszámítja az SL/TP értékeket egy signalhoz.
    Visszaad egy dict-et az előtte/utána értékekkel.
    """
    if signal.decision == "HOLD" or not signal.entry_price:
        return None

    technical_data = build_technical_data_from_signal(signal, calc)
    risk_data      = build_risk_data_from_signal(signal, calc)

    try:
        levels = generator._calculate_levels(
            decision      = signal.decision,
            current_price = signal.entry_price,
            technical_data = technical_data,
            risk_data      = risk_data,
        )
    except Exception as e:
        logger.warning(f"  ⚠️  Signal #{signal.id} kalkuláció hiba: {e}")
        return None

    if levels[0] is None:
        return None

    new_entry, new_sl, new_tp, new_rr, sl_method, tp_method = levels

    result = {
        "signal_id":  signal.id,
        "ticker":     signal.ticker_symbol,
        "decision":   signal.decision,
        "entry":      signal.entry_price,
        # Régi értékek
        "old_sl":     signal.stop_loss,
        "old_tp":     signal.take_profit,
        "old_rr":     signal.risk_reward_ratio,
        # Új értékek
        "new_sl":     new_sl,
        "new_tp":     new_tp,
        "new_rr":     new_rr,
        "sl_method":  sl_method,
        "tp_method":  tp_method,
    }

    if dry_run:
        return result

    # ── 1. signals tábla frissítése ─────────────────────────────────────
    signal.stop_loss         = new_sl
    signal.take_profit       = new_tp
    signal.risk_reward_ratio = new_rr

    # reasoning_json frissítése: levels_meta hozzáadva
    try:
        reasoning = json.loads(signal.reasoning_json) if signal.reasoning_json else {}
        reasoning["levels_meta"] = {
            "sl_method": sl_method,
            "tp_method": tp_method,
        }
        signal.reasoning_json = json.dumps(reasoning, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"  ⚠️  reasoning_json update hiba #{signal.id}: {e}")

    # ── 2. signal_calculations tábla frissítése ─────────────────────────
    if calc:
        calc.stop_loss         = new_sl
        calc.take_profit       = new_tp
        calc.risk_reward_ratio = new_rr

        # entry_exit_details frissítése, ha létezik
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

    return result


def update_simulated_trades(db, signal: Signal, new_sl: float, new_tp: float, dry_run: bool) -> int:
    """
    Frissíti a signal-hoz kötött SimulatedTrade rekordokat.

    - Ha a trade OPEN és az entry_signal_id == signal.id:
        → stop_loss_price, take_profit_price, initial_stop_loss_price, initial_take_profit_price
    - Ha a trade CLOSED és az entry_signal_id == signal.id:
        → csak initial_stop_loss_price, initial_take_profit_price (historikus referencia)

    Visszaad: frissített rekordok száma
    """
    trades = db.query(SimulatedTrade).filter(
        SimulatedTrade.entry_signal_id == signal.id
    ).all()

    count = 0
    for trade in trades:
        if dry_run:
            count += 1
            continue

        # Initial értékek mindig frissülnek (historikus konzisztencia)
        trade.initial_stop_loss_price  = new_sl
        trade.initial_take_profit_price = new_tp

        # OPEN trade-nél az aktuális SL/TP is frissül
        # (de csak ha a sl_tp_update_count == 0, vagyis még nem módosult)
        if trade.status == 'OPEN' and (trade.sl_tp_update_count or 0) == 0:
            trade.stop_loss_price  = new_sl
            trade.take_profit_price = new_tp
            trade.sl_tp_last_updated_at = datetime.utcnow()

        count += 1

    return count


def run_recalculation(args):
    """Fő újrakalkuláló logika."""
    dry_run = args.dry_run
    mode = "🔍 DRY-RUN (nem ír az adatbázisba)" if dry_run else "✏️  LIVE (ír az adatbázisba)"

    logger.info("=" * 60)
    logger.info(f"TrendSignal SL/TP Visszamenőleges Újrakalkulátor")
    logger.info(f"Mód: {mode}")
    logger.info("=" * 60)

    db = SessionLocal()
    generator = SignalGenerator()

    try:
        # ── Signalok lekérdezése ─────────────────────────────────────────
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
        total = len(signals)
        logger.info(f"Feldolgozandó signalok: {total} db")
        logger.info("-" * 60)

        if total == 0:
            logger.info("Nincs feldolgozandó signal.")
            return

        # ── Signal_calculations előre lekérése (1 query) ─────────────────
        signal_ids = [s.id for s in signals]
        calcs = db.query(SignalCalculation).filter(
            SignalCalculation.signal_id.in_(signal_ids)
        ).all()
        calc_by_signal = {c.signal_id: c for c in calcs}

        # ── Statisztikák ─────────────────────────────────────────────────
        stats = {
            "processed":   0,
            "skipped":     0,
            "sl_changed":  0,
            "tp_changed":  0,
            "rr_improved": 0,
            "trades_updated": 0,
            "errors":      0,
        }

        # ── Feldolgozás ──────────────────────────────────────────────────
        for i, signal in enumerate(signals, 1):
            calc = calc_by_signal.get(signal.id)

            try:
                result = recalculate_signal(signal, calc, generator, dry_run)
            except Exception as e:
                logger.error(f"  ❌ Signal #{signal.id} ({signal.ticker_symbol}): {e}")
                stats["errors"] += 1
                continue

            if result is None:
                stats["skipped"] += 1
                continue

            stats["processed"] += 1

            sl_diff = abs((result["new_sl"] or 0) - (result["old_sl"] or 0))
            tp_diff = abs((result["new_tp"] or 0) - (result["old_tp"] or 0))

            sl_changed = sl_diff > 0.001
            tp_changed = tp_diff > 0.001
            rr_old = result["old_rr"] or 0
            rr_new = result["new_rr"] or 0

            if sl_changed: stats["sl_changed"] += 1
            if tp_changed: stats["tp_changed"] += 1
            if rr_new > rr_old: stats["rr_improved"] += 1

            # Log — csak ha változott valami
            if sl_changed or tp_changed:
                entry = result["entry"]
                logger.info(
                    f"  #{result['signal_id']:4d} {result['ticker']:8s} {result['decision']:4s} | "
                    f"Entry: {entry:.2f} | "
                    f"SL: {result['old_sl']:.2f} → {result['new_sl']:.2f} [{result['sl_method']}] | "
                    f"TP: {result['old_tp']:.2f} → {result['new_tp']:.2f} [{result['tp_method']}] | "
                    f"R:R: {rr_old:.2f} → {rr_new:.2f}"
                )
            else:
                logger.debug(
                    f"  #{result['signal_id']:4d} {result['ticker']:8s} — nincs változás (SL/TP azonos)"
                )

            # SimulatedTrade frissítés
            if not dry_run:
                n = update_simulated_trades(db, signal, result["new_sl"], result["new_tp"], dry_run=False)
                stats["trades_updated"] += n
            else:
                n = update_simulated_trades(db, signal, result["new_sl"], result["new_tp"], dry_run=True)
                stats["trades_updated"] += n

            # Commit minden 50. rekordnál (teljesítmény)
            if not dry_run and i % 50 == 0:
                db.commit()
                logger.info(f"  💾 Közbenső commit: {i}/{total}")

        # ── Végső commit ─────────────────────────────────────────────────
        if not dry_run:
            db.commit()
            logger.info("  💾 Végső commit kész.")

        # ── Összefoglaló ─────────────────────────────────────────────────
        logger.info("")
        logger.info("=" * 60)
        logger.info("ÖSSZEFOGLALÓ")
        logger.info("=" * 60)
        logger.info(f"  Összes signal:          {total}")
        logger.info(f"  Feldolgozva:            {stats['processed']}")
        logger.info(f"  Kihagyva (HOLD/NULL):   {stats['skipped']}")
        logger.info(f"  Hiba:                   {stats['errors']}")
        logger.info(f"  SL megváltozott:        {stats['sl_changed']}")
        logger.info(f"  TP megváltozott:        {stats['tp_changed']}")
        logger.info(f"  R:R javult:             {stats['rr_improved']}")
        logger.info(f"  Trade rekordok érintve: {stats['trades_updated']}")
        if dry_run:
            logger.info("")
            logger.info("  ⚠️  DRY-RUN: adatbázis NEM módosult.")
            logger.info("  Futtasd --dry-run nélkül az éles íráshoz.")
        logger.info("=" * 60)

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


def main():
    parser = argparse.ArgumentParser(
        description="TrendSignal SL/TP visszamenőleges újrakalkulátor"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Nem ír az adatbázisba, csak megmutatja a változásokat"
    )
    parser.add_argument(
        "--ticker", type=str, default=None,
        help="Csak az adott ticker signaljait számolja újra (pl. AAPL)"
    )
    parser.add_argument(
        "--signal-id", type=int, default=None,
        help="Csak egy adott signal újrakalkulálása (ID alapján)"
    )
    parser.add_argument(
        "--from-id", type=int, default=None,
        help="Csak az adott ID-tól kezdve (pl. 1200 → csak az újabb signalok)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Részletes log (debug szint)"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    run_recalculation(args)


if __name__ == "__main__":
    main()
