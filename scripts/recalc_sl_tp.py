#!/usr/bin/env python3
"""
scripts/recalc_sl_tp.py
=======================
Visszamenőleges SL/TP újraszámítás az összes meglévő szignálra.

Miért kell?  Az alábbi kalkulációs logikák változtak az implementáció során:
  1. SHORT daytrade → szűkebb SL/TP multiplierek (0.5–1.0× vs régi 1.5–2.5× ATR)
  2. LONG swing     → fee-floor logika + vol-adaptive TP
  3. SL max cap     → SHORT: 1.5%, LONG: 5%  (korábban egységes volt)
  4. MIN_RISK_REWARD kényszerzárás → TP minimum floor
  5. Fee floor      → TP >= SL_distance + 2×fee%

Futtatás:
  python scripts/recalc_sl_tp.py          # Dry-run (csak preview)
  python scripts/recalc_sl_tp.py --apply  # Ténylegesen frissíti a DB-t
  python scripts/recalc_sl_tp.py --limit 100   # Csak az első 100 sor (tesztelés)
  python scripts/recalc_sl_tp.py --ticker AAPL  # Csak egy ticker
"""

import argparse
import sys
import os
from pathlib import Path

# Windows konzolon UTF-8 kimenet
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Projekt root hozzáadása a Python path-hoz
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import sqlite3
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from statistics import mean, stdev

# ---------------------------------------------------------------------------
# Import a számítási logikából
# ---------------------------------------------------------------------------
from optimizer.trade_simulator import (
    SimConfig,
    compute_sl_tp,
    SL_MAX_PCT,
    MIN_RISK_REWARD,
)
from src.config import TRADE_FEE_PCT, get_config

# ---------------------------------------------------------------------------
# Konstansok
# ---------------------------------------------------------------------------

DB_PATH = PROJECT_ROOT / "trendsignal.db"


# ---------------------------------------------------------------------------
# Adatstruktúrák
# ---------------------------------------------------------------------------

@dataclass
class SignalRow:
    """Egy signal_calculations sor, amelyet újraszámítunk."""
    calc_id: int
    signal_id: int
    ticker: str
    decision: str

    entry_price: float
    atr: float
    atr_pct: float
    nearest_support: Optional[float]
    nearest_resistance: Optional[float]

    # Confidence (weighted average of sub-confidences)
    sentiment_confidence: float
    technical_confidence: float
    risk_confidence: float
    weight_sentiment: float
    weight_technical: float
    weight_risk: float

    # Jelenlegi értékek (összehasonlításhoz)
    old_sl: float
    old_tp: float
    old_rr: float


@dataclass
class RecalcResult:
    """Egy sor újraszámítási eredménye."""
    row: SignalRow

    new_sl: float
    new_tp: float
    new_rr: float
    sl_method: str
    tp_method: str
    fee_floor_applied: bool

    @property
    def sl_delta_pct(self) -> float:
        """SL változás százalékban az entry_price-hoz képest."""
        ep = self.row.entry_price
        if ep <= 0:
            return 0.0
        return (self.new_sl - self.row.old_sl) / ep * 100.0

    @property
    def tp_delta_pct(self) -> float:
        """TP változás százalékban az entry_price-hoz képest."""
        ep = self.row.entry_price
        if ep <= 0:
            return 0.0
        return (self.new_tp - self.row.old_tp) / ep * 100.0

    @property
    def rr_delta(self) -> float:
        return self.new_rr - self.row.old_rr

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

def load_signal_rows(
    db_path: Path,
    limit: Optional[int] = None,
    ticker_filter: Optional[str] = None,
) -> List[SignalRow]:
    """
    Betölti a signal_calculations táblából az összes szükséges adatot.
    A signals táblából nincs szükségünk semmire (a calc táblában minden megvan).
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    query = """
        SELECT
            sc.id                  AS calc_id,
            sc.signal_id,
            sc.ticker_symbol       AS ticker,
            sc.decision,
            sc.entry_price,
            sc.atr,
            sc.atr_pct,
            sc.nearest_support,
            sc.nearest_resistance,
            sc.sentiment_confidence,
            sc.technical_confidence,
            sc.risk_confidence,
            COALESCE(sc.weight_sentiment, 0.33)  AS weight_sentiment,
            COALESCE(sc.weight_technical, 0.33)  AS weight_technical,
            COALESCE(sc.weight_risk,      0.33)  AS weight_risk,
            sc.stop_loss           AS old_sl,
            sc.take_profit         AS old_tp,
            sc.risk_reward_ratio   AS old_rr
        FROM signal_calculations sc
        WHERE sc.decision IN ('BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL')
          AND sc.entry_price > 0
          AND sc.atr > 0
    """
    params: List = []

    if ticker_filter:
        query += " AND sc.ticker_symbol = ?"
        params.append(ticker_filter)

    query += " ORDER BY sc.id ASC"

    if limit:
        query += f" LIMIT {limit}"

    rows_raw = conn.execute(query, params).fetchall()
    conn.close()

    result: List[SignalRow] = []
    for r in rows_raw:
        row = SignalRow(
            calc_id=r["calc_id"],
            signal_id=r["signal_id"],
            ticker=r["ticker"],
            decision=r["decision"],
            entry_price=r["entry_price"] or 0.0,
            atr=r["atr"] or 0.0,
            atr_pct=r["atr_pct"] or 0.0,
            nearest_support=r["nearest_support"],
            nearest_resistance=r["nearest_resistance"],
            sentiment_confidence=r["sentiment_confidence"] or 0.0,
            technical_confidence=r["technical_confidence"] or 0.0,
            risk_confidence=r["risk_confidence"] or 0.0,
            weight_sentiment=r["weight_sentiment"] or 0.33,
            weight_technical=r["weight_technical"] or 0.33,
            weight_risk=r["weight_risk"] or 0.33,
            old_sl=r["old_sl"] or 0.0,
            old_tp=r["old_tp"] or 0.0,
            old_rr=r["old_rr"] or 0.0,
        )
        result.append(row)

    return result


# ---------------------------------------------------------------------------
# Confidence számítás
# ---------------------------------------------------------------------------

def compute_confidence(row: SignalRow) -> float:
    """
    Weighted average of sub-confidences.
    Mirrors signal_generator.py overall_confidence calculation.
    """
    total_weight = row.weight_sentiment + row.weight_technical + row.weight_risk
    if total_weight <= 0:
        return (row.sentiment_confidence + row.technical_confidence + row.risk_confidence) / 3.0

    return (
        row.sentiment_confidence * row.weight_sentiment
        + row.technical_confidence * row.weight_technical
        + row.risk_confidence * row.weight_risk
    ) / total_weight


# ---------------------------------------------------------------------------
# SL/TP újraszámítás
# ---------------------------------------------------------------------------

def recalc_one(row: SignalRow, sim_cfg: SimConfig, trade_fee_pct: float) -> RecalcResult:
    """
    Újraszámítja egy sor SL/TP értékét a jelenlegi compute_sl_tp() logikával.
    Fee floor logikát is alkalmazza (mirrors signal_generator.py lines 857-869).
    """
    confidence = compute_confidence(row)

    # Döntés normalizálása: BUY/SELL (a compute_sl_tp "BUY" in decision -t néz)
    decision = row.decision  # "BUY", "STRONG_BUY", "SELL", "STRONG_SELL"

    new_sl, new_tp, sl_method, tp_method = compute_sl_tp(
        decision=decision,
        entry_price=row.entry_price,
        atr=row.atr,
        atr_pct=row.atr_pct,
        confidence=confidence,
        nearest_support=row.nearest_support,
        nearest_resistance=row.nearest_resistance,
        sim_cfg=sim_cfg,
    )

    # --- Fee floor (mirrors signal_generator.py Step 3) ---
    # TP distance must be >= SL distance + 2 * fee (entry + exit fee)
    risk = abs(row.entry_price - new_sl)
    reward = abs(new_tp - row.entry_price)
    min_tp_distance = risk + (row.entry_price * trade_fee_pct * 2)

    fee_floor_applied = False
    if reward < min_tp_distance:
        fee_floor_applied = True
        if "BUY" in decision:
            new_tp = row.entry_price + min_tp_distance
        else:
            new_tp = row.entry_price - min_tp_distance
        tp_method = "fee_floor"
        reward = abs(new_tp - row.entry_price)

    new_rr = reward / risk if risk > 0 else 0.0

    return RecalcResult(
        row=row,
        new_sl=new_sl,
        new_tp=new_tp,
        new_rr=new_rr,
        sl_method=sl_method,
        tp_method=tp_method,
        fee_floor_applied=fee_floor_applied,
    )


# ---------------------------------------------------------------------------
# Statisztika és preview
# ---------------------------------------------------------------------------

def print_statistics(results: List[RecalcResult]) -> None:
    """Részletes statisztika nyomtatása a konzolra."""
    total = len(results)
    changed = [r for r in results if r.anything_changed]
    sl_changed = [r for r in results if r.sl_changed]
    tp_changed = [r for r in results if r.tp_changed]
    fee_floor_applied = [r for r in results if r.fee_floor_applied]

    buy_results  = [r for r in results if "BUY"  in r.row.decision]
    sell_results = [r for r in results if "SELL" in r.row.decision]

    buy_changed  = [r for r in buy_results  if r.anything_changed]
    sell_changed = [r for r in sell_results if r.anything_changed]

    print("\n" + "="*70)
    print("  RECALC SL/TP — Eredmény összefoglaló")
    print("="*70)
    print(f"  Összes szignál feldolgozva : {total:>6,}")
    print(f"  Változott (bármi)          : {len(changed):>6,}  ({len(changed)/total*100:.1f}%)")
    print(f"    → SL változott           : {len(sl_changed):>6,}  ({len(sl_changed)/total*100:.1f}%)")
    print(f"    → TP változott           : {len(tp_changed):>6,}  ({len(tp_changed)/total*100:.1f}%)")
    print(f"    → Fee floor alkalmazva   : {len(fee_floor_applied):>6,}  ({len(fee_floor_applied)/total*100:.1f}%)")

    print()
    print("  Irány szerinti bontás:")
    print(f"    BUY  összesen  : {len(buy_results):>5,}   változott: {len(buy_changed):>5,}  ({len(buy_changed)/max(1,len(buy_results))*100:.1f}%)")
    print(f"    SELL összesen  : {len(sell_results):>5,}   változott: {len(sell_changed):>5,}  ({len(sell_changed)/max(1,len(sell_results))*100:.1f}%)")

    if changed:
        sl_deltas = [r.sl_delta_pct for r in changed if r.sl_changed]
        tp_deltas = [r.tp_delta_pct for r in changed if r.tp_changed]
        rr_deltas = [r.rr_delta     for r in changed]

        print()
        print("  Delta statisztikák (változott soroknál):")
        if sl_deltas:
            print(f"    SL delta (%-ban entry-hez): avg={mean(sl_deltas):+.4f}%"
                  f"  min={min(sl_deltas):+.4f}%  max={max(sl_deltas):+.4f}%")
        if tp_deltas:
            print(f"    TP delta (%-ban entry-hez): avg={mean(tp_deltas):+.4f}%"
                  f"  min={min(tp_deltas):+.4f}%  max={max(tp_deltas):+.4f}%")
        if rr_deltas:
            print(f"    R:R delta                 : avg={mean(rr_deltas):+.4f}"
                  f"  min={min(rr_deltas):+.4f}  max={max(rr_deltas):+.4f}")

    # --- Ticker szerinti bontás ---
    ticker_stats: Dict[str, Dict] = {}
    for r in results:
        t = r.row.ticker
        if t not in ticker_stats:
            ticker_stats[t] = {"total": 0, "changed": 0, "direction": set()}
        ticker_stats[t]["total"] += 1
        if r.anything_changed:
            ticker_stats[t]["changed"] += 1
        ticker_stats[t]["direction"].add("BUY" if "BUY" in r.row.decision else "SELL")

    if ticker_stats:
        print()
        print("  Ticker szerinti összesítés:")
        print(f"    {'Ticker':<12}  {'Összes':>7}  {'Változott':>9}  {'Irány':<12}")
        print("    " + "-"*44)
        for ticker, stats in sorted(ticker_stats.items()):
            dirs = "+".join(sorted(stats["direction"]))
            pct  = stats["changed"] / stats["total"] * 100
            print(f"    {ticker:<12}  {stats['total']:>7,}  {stats['changed']:>7,} ({pct:4.0f}%)  {dirs:<12}")

    # --- Minta sorok (top 10 legnagyobb TP változás) ---
    if tp_changed:
        top10 = sorted([r for r in results if r.tp_changed],
                       key=lambda r: abs(r.tp_delta_pct), reverse=True)[:10]
        print()
        print("  Top 10 sor legnagyobb TP változással:")
        print(f"    {'calc_id':>7}  {'sig_id':>7}  {'ticker':<12}  {'dir':<5}  "
              f"{'old_sl':>9}  {'new_sl':>9}  {'old_tp':>9}  {'new_tp':>9}  "
              f"{'old_rr':>6}  {'new_rr':>6}  {'tp_delta':>9}  {'sl_m':<10}  {'tp_m':<12}")
        print("    " + "-"*130)
        for r in top10:
            direction = "BUY" if "BUY" in r.row.decision else "SELL"
            print(
                f"    {r.row.calc_id:>7}  {r.row.signal_id:>7}  {r.row.ticker:<12}  "
                f"{direction:<5}  "
                f"{r.row.old_sl:>9.4f}  {r.new_sl:>9.4f}  "
                f"{r.row.old_tp:>9.4f}  {r.new_tp:>9.4f}  "
                f"{r.row.old_rr:>6.2f}  {r.new_rr:>6.2f}  "
                f"{r.tp_delta_pct:>+8.4f}%  {r.sl_method:<10}  {r.tp_method:<12}"
            )

    # --- Minta: változatlan sorok ---
    unchanged = [r for r in results if not r.anything_changed]
    if unchanged:
        print()
        print(f"  Változatlan sorok (első 5 minta):")
        print(f"    {'calc_id':>7}  {'sig_id':>7}  {'ticker':<12}  {'dir':<5}  "
              f"{'sl':>9}  {'tp':>9}  {'rr':>6}")
        print("    " + "-"*65)
        for r in unchanged[:5]:
            direction = "BUY" if "BUY" in r.row.decision else "SELL"
            print(f"    {r.row.calc_id:>7}  {r.row.signal_id:>7}  {r.row.ticker:<12}  "
                  f"{direction:<5}  {r.new_sl:>9.4f}  {r.new_tp:>9.4f}  {r.new_rr:>6.2f}")

    print()


# ---------------------------------------------------------------------------
# DB frissítés
# ---------------------------------------------------------------------------

def apply_updates(results: List[RecalcResult], db_path: Path) -> None:
    """
    Frissíti a signal_calculations és signals táblákat az újraszámított értékekkel.
    Csak a ténylegesen változott sorokat írja.
    """
    changed = [r for r in results if r.anything_changed]
    if not changed:
        print("  Nincs változás — DB frissítés nem szükséges.")
        return

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    print(f"\n  DB frissítés indul... ({len(changed):,} sor)")

    # Batch update signal_calculations
    calc_updates = [
        (r.new_sl, r.new_tp, r.new_rr, r.row.calc_id)
        for r in changed
    ]
    conn.executemany(
        "UPDATE signal_calculations SET stop_loss=?, take_profit=?, risk_reward_ratio=? WHERE id=?",
        calc_updates,
    )

    # Batch update signals — csak azokat, ahol van signal_id
    sig_updates = [
        (r.new_sl, r.new_tp, r.new_rr, r.row.signal_id)
        for r in changed
        if r.row.signal_id is not None
    ]
    if sig_updates:
        conn.executemany(
            "UPDATE signals SET stop_loss=?, take_profit=?, risk_reward_ratio=? WHERE id=?",
            sig_updates,
        )

    conn.commit()
    conn.close()

    print(f"  ✅ signal_calculations frissítve: {len(calc_updates):,} sor")
    print(f"  ✅ signals frissítve             : {len(sig_updates):,} sor")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visszamenőleges SL/TP újraszámítás az új kalkulációs logikákkal."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Ha megadod, ténylegesen frissíti a DB-t. Alapértelmezés: dry-run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Csak az első N sort dolgozza fel (teszteléshez).",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default=None,
        help="Csak egy ticker szignáljait dolgozza fel.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        default=False,
        help="Auto-confirm a DB frissítéshez (nem kér interaktív megerősítést).",
    )
    args = parser.parse_args()

    dry_run = not args.apply

    print()
    print("=" * 70)
    print("  RECALC SL/TP — Visszamenőleges újraszámítás")
    print("=" * 70)
    print(f"  Mód       : {'DRY-RUN (nincs DB frissítés)' if dry_run else '⚠️  APPLY (DB-t frissítjük!)'}")
    print(f"  DB path   : {DB_PATH}")
    print(f"  Limit     : {args.limit or 'nincs (összes sor)'}")
    print(f"  Ticker    : {args.ticker or 'összes'}")

    if not DB_PATH.exists():
        print(f"\n  ❌ HIBA: A DB nem található: {DB_PATH}")
        sys.exit(1)

    # Jelenlegi produkciós config betöltése
    try:
        cfg = get_config()
        trade_fee_pct = getattr(cfg, "trade_fee_pct", TRADE_FEE_PCT)
    except Exception:
        trade_fee_pct = TRADE_FEE_PCT

    # Mindig default SimConfig (produkciós értékek)
    sim_cfg = SimConfig()
    print(f"  Fee (PCT) : {trade_fee_pct*100:.3f}%")
    print()

    # 1. Betöltés
    print("  Adatok betöltése a DB-ből...")
    rows = load_signal_rows(DB_PATH, limit=args.limit, ticker_filter=args.ticker)
    print(f"  Betöltve: {len(rows):,} sor")

    if not rows:
        print("  Nincs feldolgozandó sor.")
        return

    # 2. Újraszámítás
    print("  Újraszámítás folyamatban...")
    results: List[RecalcResult] = []
    for i, row in enumerate(rows):
        if i > 0 and i % 1000 == 0:
            print(f"    ... {i:,}/{len(rows):,}")
        results.append(recalc_one(row, sim_cfg, trade_fee_pct))

    print(f"  Kész. {len(results):,} sor feldolgozva.")

    # 3. Statisztika
    print_statistics(results)

    # 4. DB frissítés (vagy dry-run info)
    if dry_run:
        changed_count = sum(1 for r in results if r.anything_changed)
        print("  ℹ️  DRY-RUN mód — DB nem módosult.")
        print(f"     {changed_count:,} sor lenne frissítve.")
        print()
        print("  A DB frissítéshez futtasd:")
        print(f"    python scripts/recalc_sl_tp.py --apply"
              + (f" --ticker {args.ticker}" if args.ticker else "")
              + (f" --limit {args.limit}" if args.limit else ""))
        print()
    else:
        print()
        print("  ⚠️  APPLY mód — DB frissítés következik!")
        if not args.yes:
            answer = input("  Biztosan frissíted a DB-t? [yes/no]: ").strip().lower()
            if answer not in ("yes", "y", "igen", "i"):
                print("  Megszakítva — DB nem módosult.")
                sys.exit(0)
        else:
            print("  Auto-confirm (--yes flag) — folytatás...")
        apply_updates(results, DB_PATH)
        print()
        print("  ✅ Kész — DB frissítve.")
        print()


if __name__ == "__main__":
    main()
