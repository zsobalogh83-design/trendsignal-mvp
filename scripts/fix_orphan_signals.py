#!/usr/bin/env python3
"""
scripts/fix_orphan_signals.py
==============================
A signals táblában lévő 'orphan' sorok (amelyekhez nincs signal_calculations
bejegyzés) SL/TP értékeinek javítása az aktuális compute_sl_tp() logikával.

Miért kell?
  - A recalc_sl_tp.py csak a signal_calculations-ból kiindulva dolgozott.
  - 269 BUY/SELL signals sornak (régi generálásból) nincs signal_calculations
    párja → ezek az eredeti, hibás SL/TP értékeket tartalmazzák.
  - SELL soroknál: 5%-os LONG SL cap volt alkalmazva, nem a helyes 1.5%-os SHORT.
  - BUY soroknál: régi, egységes multiplierek → kissé más SL/TP mint az új logika.

Input: signals.reasoning_json -> ATR, atr_pct, nearest_support, nearest_resistance
Output: signals.stop_loss, signals.take_profit, signals.risk_reward_ratio frissítve

Futtatás:
  python scripts/fix_orphan_signals.py           # Dry-run (csak preview)
  python scripts/fix_orphan_signals.py --apply   # DB frissítés
  python scripts/fix_orphan_signals.py --limit 20
  python scripts/fix_orphan_signals.py --ticker IBM
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict
from statistics import mean

# Windows konzolon UTF-8 kimenet
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
from dataclasses import dataclass

from optimizer.trade_simulator import SimConfig, compute_sl_tp, SL_MAX_PCT
from src.config import TRADE_FEE_PCT, get_config


DB_PATH = PROJECT_ROOT / "trendsignal.db"


# ---------------------------------------------------------------------------
# Adat struktúrák
# ---------------------------------------------------------------------------

@dataclass
class OrphanSignalRow:
    sig_id: int
    ticker: str
    decision: str
    entry_price: float
    overall_confidence: float
    # reasoning_json-ból kinyert
    atr: float
    atr_pct: float
    nearest_support: Optional[float]
    nearest_resistance: Optional[float]
    # jelenlegi értékek
    old_sl: float
    old_tp: float
    old_rr: float


@dataclass
class FixResult:
    row: OrphanSignalRow
    new_sl: float
    new_tp: float
    new_rr: float
    sl_method: str
    tp_method: str
    fee_floor_applied: bool
    parse_error: bool = False  # ha a reasoning_json parse sikertelen

    @property
    def sl_delta_pct(self) -> float:
        ep = self.row.entry_price
        return (self.new_sl - self.row.old_sl) / ep * 100.0 if ep > 0 else 0.0

    @property
    def tp_delta_pct(self) -> float:
        ep = self.row.entry_price
        return (self.new_tp - self.row.old_tp) / ep * 100.0 if ep > 0 else 0.0

    @property
    def sl_changed(self) -> bool:
        return abs(self.new_sl - self.row.old_sl) > 1e-6

    @property
    def tp_changed(self) -> bool:
        return abs(self.new_tp - self.row.old_tp) > 1e-6

    @property
    def anything_changed(self) -> bool:
        return self.sl_changed or self.tp_changed


# ---------------------------------------------------------------------------
# DB betöltés
# ---------------------------------------------------------------------------

def load_orphan_rows(
    db_path: Path,
    limit: Optional[int] = None,
    ticker_filter: Optional[str] = None,
) -> List[OrphanSignalRow]:
    """
    Betölti a signals táblából azokat a BUY/SELL sorokat,
    amelyekhez nincs signal_calculations bejegyzés.
    Az ATR és S/R adatokat a reasoning_json-ból nyeri ki.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    query = """
        SELECT s.id, s.ticker_symbol, s.decision,
               s.entry_price, s.overall_confidence,
               s.stop_loss, s.take_profit, s.risk_reward_ratio,
               s.reasoning_json
        FROM signals s
        LEFT JOIN signal_calculations sc ON s.id = sc.signal_id
        WHERE s.decision IN ('BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL')
          AND sc.signal_id IS NULL
          AND s.entry_price > 0
    """
    params: List = []

    if ticker_filter:
        query += " AND s.ticker_symbol = ?"
        params.append(ticker_filter)

    query += " ORDER BY s.id ASC"
    if limit:
        query += f" LIMIT {limit}"

    rows_raw = conn.execute(query, params).fetchall()
    conn.close()

    result: List[OrphanSignalRow] = []
    for r in rows_raw:
        rj = r["reasoning_json"]
        atr, atr_pct, support, resistance = _parse_reasoning_json(rj)

        row = OrphanSignalRow(
            sig_id=r["id"],
            ticker=r["ticker_symbol"],
            decision=r["decision"],
            entry_price=r["entry_price"] or 0.0,
            overall_confidence=r["overall_confidence"] or 0.6,
            atr=atr,
            atr_pct=atr_pct,
            nearest_support=support,
            nearest_resistance=resistance,
            old_sl=r["stop_loss"] or 0.0,
            old_tp=r["take_profit"] or 0.0,
            old_rr=r["risk_reward_ratio"] or 0.0,
        )
        result.append(row)

    return result


def _parse_reasoning_json(rj_str) -> tuple:
    """
    Kinyeri a reasoning_json-ból: (atr, atr_pct, nearest_support, nearest_resistance).
    Ha parse hiba → (0.0, 2.5, None, None).
    """
    default = (0.0, 2.5, None, None)
    if not rj_str:
        return default
    try:
        d = json.loads(rj_str)
        # ATR: components.technical.atr / atr_pct
        tech = d.get("components", {}).get("technical", {})
        atr = float(tech.get("atr", 0.0) or 0.0)
        atr_pct = float(tech.get("atr_pct", 2.5) or 2.5)

        # S/R: reasoning.risk.support_resistance
        sr = d.get("reasoning", {}).get("risk", {}).get("support_resistance", {})
        support = sr.get("support")
        resistance = sr.get("resistance")

        support    = float(support)    if support    is not None else None
        resistance = float(resistance) if resistance is not None else None

        return atr, atr_pct, support, resistance
    except Exception:
        return default


# ---------------------------------------------------------------------------
# Újraszámítás
# ---------------------------------------------------------------------------

def fix_one(row: OrphanSignalRow, sim_cfg: SimConfig, trade_fee_pct: float) -> FixResult:
    """
    Újraszámítja egy orphan signals sor SL/TP értékét.
    """
    if row.atr <= 0:
        # Ha nincs ATR adat, nem tudunk számítani → változatlan
        return FixResult(
            row=row,
            new_sl=row.old_sl, new_tp=row.old_tp, new_rr=row.old_rr,
            sl_method="no_atr", tp_method="no_atr",
            fee_floor_applied=False, parse_error=True,
        )

    new_sl, new_tp, sl_method, tp_method = compute_sl_tp(
        decision=row.decision,
        entry_price=row.entry_price,
        atr=row.atr,
        atr_pct=row.atr_pct,
        confidence=row.overall_confidence,
        nearest_support=row.nearest_support,
        nearest_resistance=row.nearest_resistance,
        sim_cfg=sim_cfg,
    )

    # Fee floor (mirrors signal_generator.py Step 3)
    risk = abs(row.entry_price - new_sl)
    reward = abs(new_tp - row.entry_price)
    min_tp_distance = risk + (row.entry_price * trade_fee_pct * 2)
    fee_floor_applied = False
    if reward < min_tp_distance:
        fee_floor_applied = True
        if "BUY" in row.decision:
            new_tp = row.entry_price + min_tp_distance
        else:
            new_tp = row.entry_price - min_tp_distance
        tp_method = "fee_floor"
        reward = abs(new_tp - row.entry_price)

    new_rr = reward / risk if risk > 0 else 0.0

    return FixResult(
        row=row,
        new_sl=new_sl, new_tp=new_tp, new_rr=new_rr,
        sl_method=sl_method, tp_method=tp_method,
        fee_floor_applied=fee_floor_applied,
    )


# ---------------------------------------------------------------------------
# Statisztika
# ---------------------------------------------------------------------------

def print_statistics(results: List[FixResult]) -> None:
    total = len(results)
    parse_errors = [r for r in results if r.parse_error]
    valid = [r for r in results if not r.parse_error]
    changed = [r for r in valid if r.anything_changed]
    sl_changed = [r for r in valid if r.sl_changed]
    tp_changed = [r for r in valid if r.tp_changed]
    fee_floor = [r for r in valid if r.fee_floor_applied]

    buy_changed  = [r for r in changed if "BUY"  in r.row.decision]
    sell_changed = [r for r in changed if "SELL" in r.row.decision]

    print("\n" + "=" * 70)
    print("  FIX ORPHAN SIGNALS — Eredmény összefoglaló")
    print("=" * 70)
    print(f"  Összes orphan signals sor  : {total:>6,}")
    print(f"  Parse hiba (nincs ATR)     : {len(parse_errors):>6,}")
    print(f"  Feldolgozható              : {len(valid):>6,}")
    print(f"  Változott (bármi)          : {len(changed):>6,}  ({len(changed)/max(1,len(valid))*100:.1f}%)")
    print(f"    -> SL változott          : {len(sl_changed):>6,}")
    print(f"    -> TP változott          : {len(tp_changed):>6,}")
    print(f"    -> Fee floor alkalmazva  : {len(fee_floor):>6,}")
    print(f"    -> BUY változott         : {len(buy_changed):>6,}")
    print(f"    -> SELL változott        : {len(sell_changed):>6,}")

    if changed:
        sl_deltas = [r.sl_delta_pct for r in changed if r.sl_changed]
        tp_deltas = [r.tp_delta_pct for r in changed if r.tp_changed]
        rr_deltas = [r.new_rr - r.row.old_rr for r in changed]

        print()
        print("  Delta statisztikák (változott soroknál):")
        if sl_deltas:
            print(f"    SL delta (% entry-hez): avg={mean(sl_deltas):+.4f}%"
                  f"  min={min(sl_deltas):+.4f}%  max={max(sl_deltas):+.4f}%")
        if tp_deltas:
            print(f"    TP delta (% entry-hez): avg={mean(tp_deltas):+.4f}%"
                  f"  min={min(tp_deltas):+.4f}%  max={max(tp_deltas):+.4f}%")
        if rr_deltas:
            print(f"    R:R delta             : avg={mean(rr_deltas):+.4f}"
                  f"  min={min(rr_deltas):+.4f}  max={max(rr_deltas):+.4f}")

    # Ticker szerinti bontás
    ticker_stats: Dict[str, Dict] = {}
    for r in results:
        t = r.row.ticker
        if t not in ticker_stats:
            ticker_stats[t] = {"total": 0, "changed": 0, "errors": 0}
        ticker_stats[t]["total"] += 1
        if r.anything_changed:
            ticker_stats[t]["changed"] += 1
        if r.parse_error:
            ticker_stats[t]["errors"] += 1

    if ticker_stats:
        print()
        print("  Ticker szerinti összesítés:")
        print(f"    {'Ticker':<12}  {'Összes':>7}  {'Változott':>9}  {'Hiba':>6}")
        print("    " + "-"*38)
        for ticker, stats in sorted(ticker_stats.items()):
            pct = stats["changed"] / stats["total"] * 100
            print(f"    {ticker:<12}  {stats['total']:>7,}  "
                  f"{stats['changed']:>7,} ({pct:4.0f}%)  {stats['errors']:>6,}")

    # Top SELL sorok SL javítással
    sell_fixed = sorted(
        [r for r in changed if "SELL" in r.row.decision],
        key=lambda r: abs(r.sl_delta_pct), reverse=True
    )[:10]

    if sell_fixed:
        print()
        print("  SELL sorok SL javítása (legnagyobb változás):")
        print(f"    {'sig_id':>7}  {'ticker':<12}  {'entry':>9}  "
              f"{'old_sl':>9}  {'new_sl':>9}  {'old_sl%':>8}  {'new_sl%':>8}  "
              f"{'old_rr':>6}  {'new_rr':>6}  {'sl_m':<10}")
        print("    " + "-"*108)
        for r in sell_fixed:
            old_sl_pct = abs(r.row.old_sl - r.row.entry_price) / r.row.entry_price * 100
            new_sl_pct = abs(r.new_sl - r.row.entry_price) / r.row.entry_price * 100
            print(
                f"    {r.row.sig_id:>7}  {r.row.ticker:<12}  {r.row.entry_price:>9.4f}  "
                f"{r.row.old_sl:>9.4f}  {r.new_sl:>9.4f}  "
                f"{old_sl_pct:>7.3f}%  {new_sl_pct:>7.3f}%  "
                f"{r.row.old_rr:>6.2f}  {r.new_rr:>6.2f}  {r.sl_method:<10}"
            )

    # Parse hibák (ha van)
    if parse_errors:
        print()
        print(f"  Parse hibás sorok ({len(parse_errors)}) — nem módosíthatók:")
        for r in parse_errors[:5]:
            print(f"    sig_id={r.row.sig_id}  {r.row.ticker}  {r.row.decision}")
    print()


# ---------------------------------------------------------------------------
# DB frissítés
# ---------------------------------------------------------------------------

def apply_updates(results: List[FixResult], db_path: Path) -> None:
    changed = [r for r in results if r.anything_changed and not r.parse_error]
    if not changed:
        print("  Nincs változás — DB frissítés nem szükséges.")
        return

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    print(f"\n  DB frissítés indul... ({len(changed):,} signals sor)")

    sig_updates = [
        (r.new_sl, r.new_tp, r.new_rr, r.row.sig_id)
        for r in changed
    ]
    conn.executemany(
        "UPDATE signals SET stop_loss=?, take_profit=?, risk_reward_ratio=? WHERE id=?",
        sig_updates,
    )
    conn.commit()
    conn.close()

    print(f"  ✅ signals frissítve: {len(sig_updates):,} sor")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orphan signals SL/TP javítása (amelyekhez nincs signal_calculations)."
    )
    parser.add_argument("--apply", action="store_true", default=False,
                        help="Ténylegesen frissíti a DB-t. Alapértelmezés: dry-run.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Csak az első N sort dolgozza fel.")
    parser.add_argument("--ticker", type=str, default=None,
                        help="Csak egy ticker szignáljait dolgozza fel.")
    parser.add_argument("--yes", action="store_true", default=False,
                        help="Auto-confirm a DB frissítéshez.")
    args = parser.parse_args()

    dry_run = not args.apply

    print()
    print("=" * 70)
    print("  FIX ORPHAN SIGNALS — Orphan signals SL/TP javítás")
    print("=" * 70)
    print(f"  Mód       : {'DRY-RUN (nincs DB frissítés)' if dry_run else '⚠️  APPLY (DB-t frissítjük!)'}")
    print(f"  DB path   : {DB_PATH}")
    print(f"  Limit     : {args.limit or 'nincs (összes orphan sor)'}")
    print(f"  Ticker    : {args.ticker or 'összes'}")

    if not DB_PATH.exists():
        print(f"\n  HIBA: A DB nem található: {DB_PATH}")
        sys.exit(1)

    try:
        cfg = get_config()
        trade_fee_pct = getattr(cfg, "trade_fee_pct", TRADE_FEE_PCT)
    except Exception:
        trade_fee_pct = TRADE_FEE_PCT

    sim_cfg = SimConfig()
    print(f"  Fee (PCT) : {trade_fee_pct*100:.3f}%")
    print()

    print("  Orphan signals betöltése...")
    rows = load_orphan_rows(DB_PATH, limit=args.limit, ticker_filter=args.ticker)
    print(f"  Betöltve: {len(rows):,} orphan sor")

    if not rows:
        print("  Nincs orphan signals sor.")
        return

    print("  Újraszámítás folyamatban...")
    results: List[FixResult] = []
    for i, row in enumerate(rows):
        if i > 0 and i % 500 == 0:
            print(f"    ... {i:,}/{len(rows):,}")
        results.append(fix_one(row, sim_cfg, trade_fee_pct))

    print(f"  Kész. {len(results):,} sor feldolgozva.")

    print_statistics(results)

    if dry_run:
        changed_count = sum(1 for r in results if r.anything_changed)
        print("  ℹ️  DRY-RUN mód — DB nem módosult.")
        print(f"     {changed_count:,} sor lenne frissítve a signals táblában.")
        print()
        print("  A DB frissítéshez futtasd:")
        print(f"    python scripts/fix_orphan_signals.py --apply"
              + (f" --ticker {args.ticker}" if args.ticker else "")
              + (f" --limit {args.limit}" if args.limit else ""))
        print()
    else:
        print()
        print("  ⚠️  APPLY mód — signals tábla frissítés következik!")
        if not args.yes:
            answer = input("  Biztosan frissíted a DB-t? [yes/no]: ").strip().lower()
            if answer not in ("yes", "y", "igen", "i"):
                print("  Megszakítva — DB nem módosult.")
                sys.exit(0)
        else:
            print("  Auto-confirm (--yes flag) — folytatás...")
        apply_updates(results, DB_PATH)
        print()
        print("  ✅ Kész — signals tábla frissítve.")
        print()


if __name__ == "__main__":
    main()
