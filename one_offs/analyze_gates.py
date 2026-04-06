"""
Gate hatás elemzés: kvartilis bontás indikátoronként

Megmutatja milyen threshold értékek lennének ténylegesen hasznosak
a BUY és SELL trade-ek kimenetelének javításához.
"""
import sqlite3
import statistics
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "trendsignal.db"

def quartile_analysis(values_outcomes, label, direction, n_buckets=4):
    """Adott indikátor értékek vs outcome kvartilis bontásban."""
    if not values_outcomes:
        return
    values_outcomes.sort(key=lambda x: x[0])
    bucket_size = max(1, len(values_outcomes) // n_buckets)
    print(f"\n  {label} ({direction}) — {len(values_outcomes)} trade:")
    for i in range(n_buckets):
        start = i * bucket_size
        end = start + bucket_size if i < n_buckets - 1 else len(values_outcomes)
        bucket = values_outcomes[start:end]
        vals = [x[0] for x in bucket]
        pnls = [x[1] for x in bucket]
        wins = sum(1 for p in pnls if p > 0)
        wr   = wins / len(pnls) * 100
        avg  = sum(pnls) / len(pnls)
        print(f"    Q{i+1} [{min(vals):+7.2f} … {max(vals):+7.2f}]"
              f"  n={len(bucket):4d}  WR={wr:5.1f}%  avg={avg:+.3f}%")

def threshold_scan(values_outcomes, label, direction, is_sell_gate=False, steps=10):
    """
    Végigpásztáz threshold értékeket és megmutatja melyik javítja a WR-t.
    is_sell_gate=False: gate blokkol ha érték >= threshold (BUY gate)
    is_sell_gate=True:  gate blokkol ha érték <= threshold (SELL gate)
    """
    if not values_outcomes:
        return
    vals = sorted([x[0] for x in values_outcomes])
    lo, hi = vals[int(len(vals)*0.1)], vals[int(len(vals)*0.9)]
    step = (hi - lo) / steps if hi > lo else 1

    baseline_wr = sum(1 for _, p in values_outcomes if p > 0) / len(values_outcomes) * 100
    best_delta = 0
    best_thresh = None

    print(f"\n  Threshold scan: {label} ({direction})  baseline WR={baseline_wr:.1f}%")
    print(f"  {'Threshold':>12}  {'Passed n':>8}  {'Passed WR':>9}  {'Blocked n':>9}  {'Blocked WR':>10}  Delta")

    threshold = lo
    while threshold <= hi:
        if not is_sell_gate:
            passed  = [(v,p) for v,p in values_outcomes if v < threshold]
            blocked = [(v,p) for v,p in values_outcomes if v >= threshold]
        else:
            passed  = [(v,p) for v,p in values_outcomes if v > threshold]
            blocked = [(v,p) for v,p in values_outcomes if v <= threshold]

        if len(passed) < 5 or len(blocked) < 5:
            threshold += step
            continue

        wr_p = sum(1 for _,p in passed  if p > 0) / len(passed)  * 100
        wr_b = sum(1 for _,p in blocked if p > 0) / len(blocked) * 100
        delta = wr_p - baseline_wr
        marker = " ◄ best" if delta > best_delta else ""
        if delta > best_delta:
            best_delta = delta
            best_thresh = threshold
        print(f"  {threshold:>12.2f}  {len(passed):>8d}  {wr_p:>8.1f}%  {len(blocked):>9d}  {wr_b:>9.1f}%  {delta:+.1f}%{marker}")
        threshold += step

    if best_thresh:
        print(f"  → Legjobb threshold: {best_thresh:.2f}  (+{best_delta:.1f}% WR)")


def analyze(conn):
    rows = conn.execute("""
        SELECT
            ast.direction,
            ast.pnl_net_percent,
            asi.rsi,
            asi.macd_hist,
            asi.sma_200,
            asi.close_price,
            asi.nearest_resistance
        FROM archive_simulated_trades ast
        JOIN archive_signals asi ON ast.archive_signal_id = asi.id
        WHERE ast.exit_reason != 'OPEN'
          AND ast.pnl_net_percent IS NOT NULL
    """).fetchall()

    print(f"Elemzett zárt trades: {len(rows)}")

    buy  = [r for r in rows if r[0] == "LONG"]
    sell = [r for r in rows if r[0] == "SHORT"]

    def wr(subset):
        if not subset: return 0
        return sum(1 for r in subset if r[1] > 0) / len(subset) * 100

    print(f"\nBASELINE: összes={len(rows)} WR={wr(rows):.1f}%")
    print(f"  BUY  n={len(buy):5d}  WR={wr(buy):.1f}%")
    print(f"  SELL n={len(sell):5d}  WR={wr(sell):.1f}%")

    # ── RSI ──────────────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("RSI ELEMZÉS")
    buy_rsi  = [(r[2], r[1]) for r in buy  if r[2] is not None]
    sell_rsi = [(r[2], r[1]) for r in sell if r[2] is not None]
    quartile_analysis(buy_rsi,  "RSI", "BUY")
    quartile_analysis(sell_rsi, "RSI", "SELL")
    threshold_scan(buy_rsi,  "RSI", "BUY",  is_sell_gate=False)
    threshold_scan(sell_rsi, "RSI", "SELL", is_sell_gate=True)

    # ── MACD Histogram ───────────────────────────────────────────────────
    print("\n" + "="*65)
    print("MACD HISTOGRAM ELEMZÉS")
    buy_macd  = [(r[3], r[1]) for r in buy  if r[3] is not None]
    sell_macd = [(r[3], r[1]) for r in sell if r[3] is not None]
    quartile_analysis(buy_macd,  "MACD Hist", "BUY")
    quartile_analysis(sell_macd, "MACD Hist", "SELL")
    threshold_scan(buy_macd,  "MACD Hist", "BUY",  is_sell_gate=False)
    threshold_scan(sell_macd, "MACD Hist", "SELL", is_sell_gate=True)

    # ── SMA200 távolság ───────────────────────────────────────────────────
    print("\n" + "="*65)
    print("SMA200 TÁVOLSÁG ELEMZÉS")
    def sma200_pct(r):
        if r[4] and r[5] and r[4] > 0:
            return (r[5] - r[4]) / r[4] * 100
        return None
    buy_sma  = [(sma200_pct(r), r[1]) for r in buy  if sma200_pct(r) is not None]
    sell_sma = [(sma200_pct(r), r[1]) for r in sell if sma200_pct(r) is not None]
    quartile_analysis(buy_sma,  "SMA200 pct", "BUY")
    quartile_analysis(sell_sma, "SMA200 pct", "SELL")
    threshold_scan(buy_sma,  "SMA200 pct", "BUY",  is_sell_gate=False)
    threshold_scan(sell_sma, "SMA200 pct", "SELL", is_sell_gate=True)

    # ── Resistance távolság ───────────────────────────────────────────────
    print("\n" + "="*65)
    print("RESISTANCE TÁVOLSÁG ELEMZÉS (BUY)")
    def dist_r(r):
        if r[6] and r[5] and r[5] > 0:
            return (r[6] - r[5]) / r[5] * 100
        return None
    buy_dist = [(dist_r(r), r[1]) for r in buy if dist_r(r) is not None]
    if buy_dist:
        quartile_analysis(buy_dist, "Dist Resist", "BUY")
        threshold_scan(buy_dist, "Dist Resist", "BUY", is_sell_gate=False)
    else:
        print("  Nincs resistance adat BUY trade-ekhez")


if __name__ == "__main__":
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = None
    analyze(conn)
    conn.close()
