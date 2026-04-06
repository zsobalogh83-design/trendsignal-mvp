"""
TrendSignal - FinBERT mint elsodleges signal - korrelacio elemzes
=================================================================

Elemzi a FinBERT score es az azt koveto arfolyamvaltozasok osszefuggeseit,
kulonbozo szuresi szcenariokban (LLM v2 score_worthy szuro alkalmazasaval).
"""

import sqlite3
import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

DB_PATH = "trendsignal.db"
US_OPEN  = 13   # UTC ora (09:00 ET)
US_CLOSE = 21   # UTC ora (17:00 ET)
MIN_RELEVANCE = 0.3


# ---------------------------------------------------------------------------
# Price data
# ---------------------------------------------------------------------------

def load_price_map():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT ticker_symbol, timestamp, close FROM price_data WHERE interval='15m' ORDER BY ticker_symbol, timestamp"
    ).fetchall()
    conn.close()
    pm = defaultdict(list)
    for ticker, ts, close in rows:
        pm[ticker].append((ts, float(close)))
    print(f"  {sum(len(v) for v in pm.values()):,} gyertya, {len(pm)} ticker")
    return pm


def find_prices(price_map, ticker, pub_ts_str, window_hours):
    bars = price_map.get(ticker, [])
    if not bars:
        return None, None
    try:
        target_dt = datetime.fromisoformat(pub_ts_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    except Exception:
        return None, None

    t0 = None
    for ts_str, close in bars:
        try:
            bar_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if bar_dt >= target_dt:
            t0 = close
            break
    if t0 is None:
        return None, None

    end_dt = target_dt + timedelta(hours=window_hours)
    t1 = None
    for ts_str, close in reversed(bars):
        try:
            bar_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if bar_dt <= end_dt:
            t1 = close
            break
    return t0, t1


def is_trading(pub_ts_str, ticker):
    if ticker.endswith(".BD"):
        return False
    try:
        dt = datetime.fromisoformat(pub_ts_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        return dt.weekday() < 5 and US_OPEN <= dt.hour < US_CLOSE
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Statisztikak
# ---------------------------------------------------------------------------

def pearson(xs, ys):
    n = len(xs)
    if n < 10:
        return 0.0, 1.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0, 1.0
    r = num / (dx * dy)
    t = r * math.sqrt(n - 2) / math.sqrt(max(1e-9, 1 - r ** 2))
    p = 2 / (1 + math.exp(0.717 * abs(t) + 0.416 * t * t))
    return round(r, 4), round(p, 4)


def dir_accuracy(subset, window, fb_thresh=0.05):
    pred_up   = [r for r in subset if r["fb"] >  fb_thresh and window in r["prices"]]
    pred_down = [r for r in subset if r["fb"] < -fb_thresh and window in r["prices"]]
    n = len(pred_up) + len(pred_down)
    if n == 0:
        return None, 0
    correct = (sum(1 for r in pred_up   if r["prices"][window] > 0) +
               sum(1 for r in pred_down if r["prices"][window] < 0))
    return round(correct / n * 100, 1), n


def avg_abs_move(subset, window):
    vals = [abs(r["prices"][window]) for r in subset if window in r["prices"]]
    return round(statistics.mean(vals), 4) if vals else 0.0


# ---------------------------------------------------------------------------
# Adatok betoltese
# ---------------------------------------------------------------------------

def load_records(price_map):
    conn = sqlite3.connect(DB_PATH)

    arch = conn.execute("""
        SELECT ticker_symbol, published_at, finbert_score, av_relevance_score,
               llm_score_worthy, llm_catalyst_type, llm_confidence,
               llm_surprise_dir, llm_score
        FROM archive_news_items
        WHERE finbert_score IS NOT NULL
          AND ticker_symbol NOT LIKE '%.BD'
          AND av_relevance_score >= ?
          AND active_score_source IN ('llm','llm_v2')
    """, (MIN_RELEVANCE,)).fetchall()

    live = conn.execute("""
        SELECT t.symbol, n.published_at, n.finbert_score, nt.relevance_score,
               n.llm_score_worthy, n.llm_catalyst_type, n.llm_confidence,
               n.llm_surprise_dir, n.llm_score
        FROM news_items n
        JOIN news_tickers nt ON nt.news_id = n.id
        JOIN tickers t ON t.id = nt.ticker_id
        WHERE n.finbert_score IS NOT NULL
          AND t.symbol NOT LIKE '%.BD'
          AND nt.relevance_score >= ?
          AND n.active_score_source IN ('llm','llm_v2')
    """, (MIN_RELEVANCE,)).fetchall()

    conn.close()
    print(f"  Betoltve: {len(arch)+len(live):,} (archive: {len(arch):,}, live: {len(live):,})")

    records = []
    skip = 0
    for r in list(arch) + list(live):
        ticker, pub_at, fb, relevance, worthy, catalyst, conf, surp_dir, llm_sc = r
        if not pub_at or not is_trading(pub_at, ticker):
            skip += 1
            continue
        prices = {}
        for w in [1, 2, 4, 6]:
            t0, t1 = find_prices(price_map, ticker, pub_at, w)
            if t0 and t1 and t0 > 0:
                prices[w] = round((t1 - t0) / t0 * 100, 6)
        if not prices:
            skip += 1
            continue
        records.append({
            "ticker":   ticker,
            "fb":       float(fb),
            "worthy":   bool(worthy) if worthy is not None else False,
            "catalyst": catalyst or "other",
            "conf":     conf or "medium",
            "surp_dir": surp_dir or "na",
            "llm_score":float(llm_sc) if llm_sc else 0.0,
            "prices":   prices,
        })

    print(f"  Feldolgozva: {len(records):,} | Kihagyva (nincs ar/trading): {skip:,}")
    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 72)
    print("  TrendSignal - FinBERT mint elsodleges signal")
    print("=" * 72)

    print("\n[1] Price data betoltese...")
    price_map = load_price_map()

    print("\n[2] Hirek betoltese...")
    records = load_records(price_map)

    W = 2  # fo ablak: 2 ora

    # ------------------------------------------------------------------
    # 1. Szurt vs szuratlan szcenariok
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("1. FINBERT IRANY-PONTOSSAG: SZURT vs SZURATLAN (2h ablak)")
    print("=" * 72)
    print(f"  {'Szcenario':<38} {'n':>7}  {'dir_acc':>8}  {'pearson_r':>10}  {'p_value':>8}  {'avg_abs%':>8}")
    print("  " + "-" * 68)

    scenarios = [
        ("Minden cikk (szuratlan)",          records),
        ("LLM szurt (score_worthy=1)",        [r for r in records if r["worthy"]]),
        ("LLM szurt + |fb|>0.10",             [r for r in records if r["worthy"] and abs(r["fb"]) > 0.10]),
        ("LLM szurt + |fb|>0.20",             [r for r in records if r["worthy"] and abs(r["fb"]) > 0.20]),
        ("LLM szurt + |fb|>0.30",             [r for r in records if r["worthy"] and abs(r["fb"]) > 0.30]),
        ("LLM szurt + |fb|>0.50",             [r for r in records if r["worthy"] and abs(r["fb"]) > 0.50]),
    ]
    for label, sub in scenarios:
        acc, n_pred = dir_accuracy(sub, W)
        sub_w = [r for r in sub if W in r["prices"]]
        rv, pv = pearson([r["fb"] for r in sub_w], [r["prices"][W] for r in sub_w])
        sig = "*" if pv < 0.05 else " "
        ab = avg_abs_move(sub, W)
        print(f"  {label:<38} {len(sub):>7,}  {str(acc)+'%':>8}  {str(rv)+sig:>10}  {pv:>8.4f}  {ab:>8.4f}")

    # ------------------------------------------------------------------
    # 2. Idoablakok
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("2. FINBERT PONTOSSAG IDOABLAKONKENT (LLM szurt + |fb|>0.15)")
    print("=" * 72)
    sub_filt = [r for r in records if r["worthy"] and abs(r["fb"]) > 0.15]
    print(f"  {'Ablak':>6}  {'n_pred':>7}  {'dir_acc':>8}  {'pearson_r':>10}  {'p_val':>7}  {'avg_abs%':>8}")
    print("  " + "-" * 55)
    for w in [1, 2, 4, 6]:
        acc, n_pred = dir_accuracy(sub_filt, w)
        sub_w = [r for r in sub_filt if w in r["prices"]]
        rv, pv = pearson([r["fb"] for r in sub_w], [r["prices"][w] for r in sub_w])
        sig = "*" if pv < 0.05 else " "
        ab = avg_abs_move(sub_filt, w)
        print(f"  {str(w)+'h':>6}  {n_pred:>7,}  {str(acc)+'%':>8}  {str(rv)+sig:>10}  {pv:>7.4f}  {ab:>8.4f}")

    # ------------------------------------------------------------------
    # 3. FinBERT score buckets
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("3. FINBERT SCORE BUCKETS (LLM szurt, 2h ablak)")
    print("=" * 72)
    buckets = [
        ("eros pozitiv   fb > 0.50",    [r for r in records if r["worthy"] and r["fb"] >  0.50]),
        ("kozepes pozitiv 0.20-0.50",   [r for r in records if r["worthy"] and 0.20 < r["fb"] <= 0.50]),
        ("gyenge pozitiv 0.05-0.20",    [r for r in records if r["worthy"] and 0.05 < r["fb"] <= 0.20]),
        ("semleges -0.05..0.05",        [r for r in records if r["worthy"] and abs(r["fb"]) <= 0.05]),
        ("gyenge negativ -0.20..-0.05", [r for r in records if r["worthy"] and -0.20 <= r["fb"] < -0.05]),
        ("kozepes negativ -0.50..-0.20",[r for r in records if r["worthy"] and -0.50 <= r["fb"] < -0.20]),
        ("eros negativ   fb < -0.50",   [r for r in records if r["worthy"] and r["fb"] < -0.50]),
    ]
    print(f"  {'Bucket':<32} {'n':>5}  {'up%':>5}  {'down%':>6}  {'avg_abs%':>8}")
    print("  " + "-" * 60)
    for label, sub in buckets:
        sub_w = [r for r in sub if W in r["prices"]]
        if not sub_w:
            continue
        n = len(sub_w)
        up   = sum(1 for r in sub_w if r["prices"][W] > 0)
        down = sum(1 for r in sub_w if r["prices"][W] < 0)
        ab   = avg_abs_move(sub_w, W)
        print(f"  {label:<32} {n:>5,}  {up/n*100:>5.1f}  {down/n*100:>6.1f}  {ab:>8.4f}")

    # ------------------------------------------------------------------
    # 4. Ticker szinti bontas
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("4. FINBERT PONTOSSAG TICKERENKENT (LLM szurt + |fb|>0.15, 2h)")
    print("=" * 72)
    print(f"  {'Ticker':<10} {'n':>5}  {'dir_acc':>8}  {'pearson_r':>10}  {'avg_abs%':>8}")
    print("  " + "-" * 48)
    for ticker in sorted(set(r["ticker"] for r in records)):
        sub = [r for r in records if r["ticker"] == ticker and r["worthy"] and abs(r["fb"]) > 0.15]
        if len(sub) < 20:
            continue
        acc, n_pred = dir_accuracy(sub, W)
        sub_w = [r for r in sub if W in r["prices"]]
        rv, _ = pearson([r["fb"] for r in sub_w], [r["prices"][W] for r in sub_w])
        ab = avg_abs_move(sub_w, W)
        print(f"  {ticker:<10} {n_pred:>5,}  {str(acc)+'%':>8}  {rv:>10.4f}  {ab:>8.4f}")

    # ------------------------------------------------------------------
    # 5. Catalyst tipusonkent
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("5. FINBERT PONTOSSAG CATALYST TIPUSONKENT (LLM szurt + |fb|>0.10, 2h)")
    print("=" * 72)
    print(f"  {'Catalyst':<22} {'n':>5}  {'dir_acc':>8}  {'pearson_r':>10}  {'avg_abs%':>8}")
    print("  " + "-" * 58)
    for cat in sorted(set(r["catalyst"] for r in records if r["worthy"])):
        sub = [r for r in records if r["worthy"] and r["catalyst"] == cat and abs(r["fb"]) > 0.10]
        if len(sub) < 20:
            continue
        acc, n_pred = dir_accuracy(sub, W)
        sub_w = [r for r in sub if W in r["prices"]]
        rv, pv = pearson([r["fb"] for r in sub_w], [r["prices"][W] for r in sub_w])
        sig = "*" if pv < 0.05 else " "
        ab = avg_abs_move(sub_w, W)
        print(f"  {cat:<22} {n_pred:>5,}  {str(acc)+'%':>8}  {str(rv)+sig:>10}  {ab:>8.4f}")

    # ------------------------------------------------------------------
    # 6. LLM surprise_dir + FinBERT egyezes
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("6. LLM SURPRISE_DIR + FINBERT ATLAGA (LLM szurt, 2h)")
    print("=" * 72)
    print(f"  {'surp_dir':<15} {'n':>5}  {'avg_fb':>8}  {'dir_acc':>8}  {'avg_abs%':>8}")
    print("  " + "-" * 52)
    for sd in ["beat", "miss", "in_line", "no_baseline", "na"]:
        sub = [r for r in records if r["worthy"] and r["surp_dir"] == sd]
        if len(sub) < 10:
            continue
        avg_fb = statistics.mean(r["fb"] for r in sub)
        acc, n_pred = dir_accuracy(sub, W, fb_thresh=0.05)
        ab = avg_abs_move(sub, W)
        print(f"  {sd:<15} {len(sub):>5,}  {avg_fb:>+8.3f}  {str(acc)+'%':>8}  {ab:>8.4f}")

    # ------------------------------------------------------------------
    # 7. Kombinalt: LLM beat/miss + FinBERT egyezes vs ellentet
    # ------------------------------------------------------------------
    print("\n" + "=" * 72)
    print("7. LLM + FINBERT KOMBINALT SZIGNAL (2h)")
    print("=" * 72)
    combos = [
        ("LLM beat + FB pozitiv",   [r for r in records if r["worthy"] and r["surp_dir"]=="beat" and r["fb"] > 0.1]),
        ("LLM beat + FB negativ",   [r for r in records if r["worthy"] and r["surp_dir"]=="beat" and r["fb"] < -0.1]),
        ("LLM miss + FB negativ",   [r for r in records if r["worthy"] and r["surp_dir"]=="miss" and r["fb"] < -0.1]),
        ("LLM miss + FB pozitiv",   [r for r in records if r["worthy"] and r["surp_dir"]=="miss" and r["fb"] > 0.1]),
        ("Csak FB pozitiv (szurt)",  [r for r in records if r["worthy"] and r["fb"] > 0.15 and r["surp_dir"]=="na"]),
        ("Csak FB negativ (szurt)",  [r for r in records if r["worthy"] and r["fb"] < -0.15 and r["surp_dir"]=="na"]),
    ]
    print(f"  {'Kombinacio':<32} {'n':>5}  {'dir_acc':>8}  {'avg_abs%':>8}")
    print("  " + "-" * 58)
    for label, sub in combos:
        if len(sub) < 5:
            print(f"  {label:<32} n<5 (nem szignifikans)")
            continue
        acc, n_pred = dir_accuracy(sub, W, fb_thresh=0.0)
        ab = avg_abs_move(sub, W)
        print(f"  {label:<32} {n_pred:>5,}  {str(acc)+'%':>8}  {ab:>8.4f}")

    print("\n" + "=" * 72)
    print("KESZ")
    print("=" * 72)


if __name__ == "__main__":
    main()
