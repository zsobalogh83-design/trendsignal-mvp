"""
TrendSignal - TF-IDF alapu deduplikacio + arfolyam korrelacio
=============================================================

Azonositja az "elso megjelenes" hireket TF-IDF cosine similarity alapjan:
- Minden tickerre idorendben feldolgozza a cikkeket
- Ha egy cikk az elozo 24 oraban megjelent barmely cikkel >= threshold
  hasonlosagot mutat, "ismetles"-kent jeloli
- Csak az "elso megjelenes" cikkeken vegez arfolyam-korrelacio elemzest

Futtatas:
    python one_offs/analyze_dedup_correlation.py
    python one_offs/analyze_dedup_correlation.py --threshold 0.35
    python one_offs/analyze_dedup_correlation.py --window-hours 12
"""

import sqlite3
import math
import re
import argparse
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

DB_PATH       = "trendsignal.db"
US_OPEN       = 13
US_CLOSE      = 21
MIN_RELEVANCE = 0.3

# ---------------------------------------------------------------------------
# TF-IDF hasonlosag
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list:
    """Egyszeru szotokenizalas, stopword szures."""
    STOPWORDS = {
        "a","an","the","and","or","but","in","on","at","to","for","of","with",
        "by","from","as","is","was","are","were","be","been","being","have",
        "has","had","do","does","did","will","would","could","should","may",
        "might","shall","can","its","it","this","that","these","those","after",
        "before","during","about","into","through","over","under","up","down",
        "out","off","than","then","when","where","who","which","how","why",
        "not","no","nor","so","yet","both","either","neither","each","every",
        "all","any","few","more","most","other","some","such","own","same",
    }
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


def build_tfidf(docs: list) -> list:
    """
    docs: list of token-listak
    Visszaad: list of dict {term: tfidf_score}
    """
    N = len(docs)
    if N == 0:
        return []

    # DF szamitas
    df = defaultdict(int)
    for tokens in docs:
        for t in set(tokens):
            df[t] += 1

    # TF-IDF vektorok
    vectors = []
    for tokens in docs:
        tf = defaultdict(int)
        for t in tokens:
            tf[t] += 1
        vec = {}
        for t, cnt in tf.items():
            idf = math.log((N + 1) / (df[t] + 1)) + 1
            vec[t] = (cnt / len(tokens)) * idf
        # Normalizalas
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm > 0:
            vec = {t: v / norm for t, v in vec.items()}
        vectors.append(vec)
    return vectors


def cosine(vec_a: dict, vec_b: dict) -> float:
    """Ket normalizalt TF-IDF vektor kozotti cosine similarity."""
    common = set(vec_a.keys()) & set(vec_b.keys())
    return sum(vec_a[t] * vec_b[t] for t in common)


# ---------------------------------------------------------------------------
# Price data
# ---------------------------------------------------------------------------

def load_price_map(conn):
    rows = conn.execute(
        "SELECT ticker_symbol, timestamp, close FROM price_data "
        "WHERE interval='15m' ORDER BY ticker_symbol, timestamp"
    ).fetchall()
    pm = defaultdict(list)
    for ticker, ts, close in rows:
        pm[ticker].append((ts, float(close)))
    return pm


def find_prices(price_map, ticker, pub_ts_str, window_h):
    bars = price_map.get(ticker, [])
    if not bars:
        return None, None
    try:
        tgt = datetime.fromisoformat(pub_ts_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    except Exception:
        return None, None
    t0 = None
    for ts_str, close in bars:
        try:
            bdt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if bdt >= tgt:
            t0 = close
            break
    if t0 is None:
        return None, None
    end = tgt + timedelta(hours=window_h)
    t1 = None
    for ts_str, close in reversed(bars):
        try:
            bdt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if bdt <= end:
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
# Deduplikacio
# ---------------------------------------------------------------------------

def deduplicate(articles: list, window_hours: int, threshold: float) -> list:
    """
    articles: list of dict {id, ticker, published_at (datetime), tokens, ...}
    Visszaad: csak az 'elso megjelenes' cikkek listaja.
    """
    # Tickerenkent csoportositva, idorendben
    by_ticker = defaultdict(list)
    for a in articles:
        by_ticker[a["ticker"]].append(a)
    for t in by_ticker:
        by_ticker[t].sort(key=lambda x: x["pub_dt"])

    first_only = []
    window = timedelta(hours=window_hours)

    for ticker, arts in by_ticker.items():
        # Csusztatott ablak: csak az aktualis cikk elotti window_hours-ban levok
        recent_tokens  = []   # token-listak
        recent_vecs    = []   # TF-IDF vektorok (inkrementalisan frissitve)
        recent_times   = []   # datetime-ok

        for art in arts:
            dt = art["pub_dt"]
            tokens = art["tokens"]

            # Regiek eltavolitasa az ablakbol
            cutoff = dt - window
            idx = 0
            while idx < len(recent_times) and recent_times[idx] < cutoff:
                idx += 1
            recent_tokens = recent_tokens[idx:]
            recent_vecs   = recent_vecs[idx:]
            recent_times  = recent_times[idx:]

            # Hasonlosag ellenorzese
            is_dup = False
            if recent_tokens and tokens:
                # Az uj cikk vektora az aktualis ablak dokumentumaival egyutt
                all_docs = recent_tokens + [tokens]
                all_vecs = build_tfidf(all_docs)
                new_vec  = all_vecs[-1]
                for prev_vec_idx in range(len(all_vecs) - 1):
                    sim = cosine(all_vecs[prev_vec_idx], new_vec)
                    if sim >= threshold:
                        is_dup = True
                        break

            if not is_dup:
                first_only.append(art)
                art["is_first"] = True
            else:
                art["is_first"] = False

            # Ablakba felvesszuk (duplikatum is, hogy kesobb se jelenjen meg hasonlo)
            recent_tokens.append(tokens)
            recent_times.append(dt)

    return first_only


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
    dx  = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy  = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0, 1.0
    r = num / (dx * dy)
    t = r * math.sqrt(n - 2) / math.sqrt(max(1e-9, 1 - r * r))
    p = 2 / (1 + math.exp(0.717 * abs(t) + 0.416 * t * t))
    return round(r, 4), round(p, 4)


def dir_acc(subset, window, fb_thresh=0.05):
    up   = [r for r in subset if r["fb"] >  fb_thresh and window in r["prices"]]
    down = [r for r in subset if r["fb"] < -fb_thresh and window in r["prices"]]
    n    = len(up) + len(down)
    if n == 0:
        return None, 0
    correct = (sum(1 for r in up   if r["prices"][window] > 0) +
               sum(1 for r in down if r["prices"][window] < 0))
    return round(correct / n * 100, 1), n


def avg_abs(subset, window):
    vals = [abs(r["prices"][window]) for r in subset if window in r["prices"]]
    return round(statistics.mean(vals), 4) if vals else 0.0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold",    type=float, default=0.40,
                        help="TF-IDF cosine similarity kuszob (0.3-0.6 ajanlott)")
    parser.add_argument("--window-hours", type=int,   default=24,
                        help="Idoablak orakban a duplikat-kereseshez")
    parser.add_argument("--fb-thresh",    type=float, default=0.10,
                        help="FinBERT kuszob az irany-predikciohozhoz")
    args = parser.parse_args()

    print("=" * 70)
    print("  TrendSignal - Deduplikalt hirek arfolyam-korrelacio elemzese")
    print("=" * 70)
    print(f"  TF-IDF kuszob:  {args.threshold}")
    print(f"  Idoablak:       {args.window_hours}h")
    print(f"  FinBERT kuszob: {args.fb_thresh}")

    conn = sqlite3.connect(DB_PATH)

    # --- Price data ---
    print("\n[1] Price data betoltese...")
    price_map = load_price_map(conn)
    print(f"    {sum(len(v) for v in price_map.values()):,} gyertya, {len(price_map)} ticker")

    # --- Hirek betoltese ---
    print("\n[2] Hirek betoltese...")
    arch = conn.execute("""
        SELECT id, ticker_symbol, published_at, title, summary,
               finbert_score, av_relevance_score, llm_score_worthy,
               llm_catalyst_type, llm_surprise_dir, llm_is_first_report
        FROM archive_news_items
        WHERE finbert_score IS NOT NULL
          AND ticker_symbol NOT LIKE '%.BD'
          AND av_relevance_score >= ?
          AND active_score_source IN ('llm','llm_v2')
        ORDER BY ticker_symbol, published_at
    """, (MIN_RELEVANCE,)).fetchall()

    live = conn.execute("""
        SELECT n.id, t.symbol, n.published_at, n.title, n.description,
               n.finbert_score, nt.relevance_score, n.llm_score_worthy,
               n.llm_catalyst_type, n.llm_surprise_dir, n.llm_is_first_report
        FROM news_items n
        JOIN news_tickers nt ON nt.news_id = n.id
        JOIN tickers t ON t.id = nt.ticker_id
        WHERE n.finbert_score IS NOT NULL
          AND t.symbol NOT LIKE '%.BD'
          AND nt.relevance_score >= ?
          AND n.active_score_source IN ('llm','llm_v2')
        ORDER BY t.symbol, n.published_at
    """, (MIN_RELEVANCE,)).fetchall()

    conn.close()
    print(f"    Betoltve: {len(arch)+len(live):,} (archive: {len(arch):,}, live: {len(live):,})")

    # --- Cikkek elokeszitese ---
    print("\n[3] Tokenizalas...")
    articles = []
    skip = 0
    for r in list(arch) + list(live):
        row_id, ticker, pub_at, title, summary = r[0], r[1], r[2], r[3], r[4]
        fb, relevance, worthy, catalyst, surp_dir, first_rep = r[5], r[6], r[7], r[8], r[9], r[10]

        if not pub_at:
            skip += 1
            continue
        try:
            pub_dt = datetime.fromisoformat(pub_at.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        except Exception:
            skip += 1
            continue

        text = " ".join(filter(None, [title, summary]))
        tokens = tokenize(text)
        if not tokens:
            skip += 1
            continue

        articles.append({
            "id":        row_id,
            "ticker":    ticker,
            "pub_at":    pub_at,
            "pub_dt":    pub_dt,
            "tokens":    tokens,
            "fb":        float(fb),
            "worthy":    bool(worthy) if worthy is not None else False,
            "catalyst":  catalyst or "other",
            "surp_dir":  surp_dir or "na",
            "llm_first": bool(first_rep) if first_rep is not None else False,
            "prices":    {},
        })

    print(f"    Tokenizalva: {len(articles):,} | Kihagyva: {skip:,}")

    # --- Deduplikacio ---
    print(f"\n[4] TF-IDF deduplikacio (threshold={args.threshold}, window={args.window_hours}h)...")
    first_articles = deduplicate(articles, args.window_hours, args.threshold)
    dup_count = len(articles) - len(first_articles)
    print(f"    Eredeti:      {len(articles):,}")
    print(f"    Duplikat:     {dup_count:,} ({dup_count/len(articles)*100:.1f}%)")
    print(f"    Elso megj.:   {len(first_articles):,} ({len(first_articles)/len(articles)*100:.1f}%)")

    # --- Arfolyamvaltozasok ---
    print("\n[5] Arfolyamvaltozasok kiszamitasa...")
    valid = []
    for art in first_articles:
        if not is_trading(art["pub_at"], art["ticker"]):
            continue
        for w in [1, 2, 4, 6]:
            t0, t1 = find_prices(price_map, art["ticker"], art["pub_at"], w)
            if t0 and t1 and t0 > 0:
                art["prices"][w] = round((t1 - t0) / t0 * 100, 6)
        if art["prices"]:
            valid.append(art)

    print(f"    Feldolgozva (trading ora + van ar): {len(valid):,}")

    W = 2

    # --- 1. Szurt vs szuratlan (deduplikalt) ---
    print("\n" + "=" * 70)
    print("1. FINBERT IRANY-PONTOSSAG - DEDUPLIKALT HIREK (2h ablak)")
    print("=" * 70)
    print(f"  {'Szcenario':<40} {'n':>6}  {'dir_acc':>8}  {'r':>7}  {'p':>7}  {'avg_abs%':>8}")
    print("  " + "-" * 72)

    scenarios = [
        ("Deduplikalt - minden cikk",             valid),
        ("Deduplikalt - LLM szurt",                [r for r in valid if r["worthy"]]),
        ("Deduplikalt - LLM szurt |fb|>0.15",      [r for r in valid if r["worthy"] and abs(r["fb"]) > 0.15]),
        ("Deduplikalt - LLM szurt |fb|>0.30",      [r for r in valid if r["worthy"] and abs(r["fb"]) > 0.30]),
        ("Deduplikalt - LLM szurt |fb|>0.50",      [r for r in valid if r["worthy"] and abs(r["fb"]) > 0.50]),
        ("Deduplikalt - llm_is_first_report=1",    [r for r in valid if r["llm_first"]]),
    ]

    for label, sub in scenarios:
        acc, n = dir_acc(sub, W, args.fb_thresh)
        sub_w = [r for r in sub if W in r["prices"]]
        rv, pv = pearson([r["fb"] for r in sub_w], [r["prices"][W] for r in sub_w])
        sig = "*" if pv < 0.05 else " "
        ab = avg_abs(sub, W)
        print(f"  {label:<40} {len(sub):>6,}  {str(acc)+'%':>8}  {str(rv)+sig:>7}  {pv:>7.4f}  {ab:>8.4f}")

    # --- 2. Idoablakok ---
    print("\n" + "=" * 70)
    print("2. FINBERT IDOABLAKONKENT (deduplikalt + LLM szurt + |fb|>0.15)")
    print("=" * 70)
    sub_filt = [r for r in valid if r["worthy"] and abs(r["fb"]) > 0.15]
    print(f"  {'Ablak':>5}  {'n':>6}  {'dir_acc':>8}  {'r':>7}  {'p':>7}  {'avg_abs%':>8}")
    print("  " + "-" * 50)
    for w in [1, 2, 4, 6]:
        acc, n = dir_acc(sub_filt, w, args.fb_thresh)
        sub_w = [r for r in sub_filt if w in r["prices"]]
        rv, pv = pearson([r["fb"] for r in sub_w], [r["prices"][w] for r in sub_w])
        sig = "*" if pv < 0.05 else " "
        ab = avg_abs(sub_filt, w)
        print(f"  {str(w)+'h':>5}  {n:>6,}  {str(acc)+'%':>8}  {str(rv)+sig:>7}  {pv:>7.4f}  {ab:>8.4f}")

    # --- 3. Score bucket ---
    print("\n" + "=" * 70)
    print("3. FINBERT SCORE BUCKETS (deduplikalt + LLM szurt, 2h)")
    print("=" * 70)
    print(f"  {'Bucket':<33} {'n':>5}  {'fel%':>5}  {'le%':>5}  {'avg_abs%':>8}")
    print("  " + "-" * 58)
    buckets = [
        ("eros pozitiv   fb >  0.50",  [r for r in valid if r["worthy"] and r["fb"] >  0.50]),
        ("kozepes poz    0.20-0.50",   [r for r in valid if r["worthy"] and 0.20 < r["fb"] <= 0.50]),
        ("gyenge poz     0.05-0.20",   [r for r in valid if r["worthy"] and 0.05 < r["fb"] <= 0.20]),
        ("semleges      -0.05..0.05",  [r for r in valid if r["worthy"] and abs(r["fb"]) <= 0.05]),
        ("gyenge neg    -0.20..-0.05", [r for r in valid if r["worthy"] and -0.20 <= r["fb"] < -0.05]),
        ("kozepes neg   -0.50..-0.20", [r for r in valid if r["worthy"] and -0.50 <= r["fb"] < -0.20]),
        ("eros negativ   fb < -0.50",  [r for r in valid if r["worthy"] and r["fb"] < -0.50]),
    ]
    for label, sub in buckets:
        sub_w = [r for r in sub if W in r["prices"]]
        if not sub_w:
            continue
        n    = len(sub_w)
        up   = sum(1 for r in sub_w if r["prices"][W] > 0)
        down = sum(1 for r in sub_w if r["prices"][W] < 0)
        ab   = avg_abs(sub_w, W)
        print(f"  {label:<33} {n:>5,}  {up/n*100:>5.1f}  {down/n*100:>5.1f}  {ab:>8.4f}")

    # --- 4. Ticker bontás ---
    print("\n" + "=" * 70)
    print("4. TICKER SZINTI PONTOSSAG (deduplikalt + LLM szurt + |fb|>0.15, 2h)")
    print("=" * 70)
    print(f"  {'Ticker':<10} {'n':>5}  {'dir_acc':>8}  {'r':>7}  {'avg_abs%':>8}")
    print("  " + "-" * 45)
    for ticker in sorted(set(r["ticker"] for r in valid)):
        sub = [r for r in valid if r["ticker"] == ticker and r["worthy"] and abs(r["fb"]) > 0.15]
        if len(sub) < 15:
            continue
        acc, n = dir_acc(sub, W, args.fb_thresh)
        sub_w = [r for r in sub if W in r["prices"]]
        rv, _ = pearson([r["fb"] for r in sub_w], [r["prices"][W] for r in sub_w])
        ab = avg_abs(sub_w, W)
        print(f"  {ticker:<10} {n:>5,}  {str(acc)+'%':>8}  {rv:>7.4f}  {ab:>8.4f}")

    # --- 5. LLM miss + FB negativ (legjobb kombinacio) ---
    print("\n" + "=" * 70)
    print("5. KOMBINALT SZIGNAL (deduplikalt, 2h)")
    print("=" * 70)
    combos = [
        ("LLM miss + FB negativ",    [r for r in valid if r["worthy"] and r["surp_dir"] == "miss" and r["fb"] < -0.10]),
        ("LLM miss + FB pozitiv",    [r for r in valid if r["worthy"] and r["surp_dir"] == "miss" and r["fb"] >  0.10]),
        ("LLM beat + FB pozitiv",    [r for r in valid if r["worthy"] and r["surp_dir"] == "beat" and r["fb"] >  0.10]),
        ("LLM beat + FB negativ",    [r for r in valid if r["worthy"] and r["surp_dir"] == "beat" and r["fb"] < -0.10]),
        ("miss+neg DEDUPLIKALT",     [r for r in valid if r["worthy"] and r["surp_dir"] == "miss" and r["fb"] < -0.10]),
        ("Csak erős FB neg (>0.5)",  [r for r in valid if r["worthy"] and r["fb"] < -0.50]),
        ("Csak erős FB poz (>0.5)",  [r for r in valid if r["worthy"] and r["fb"] >  0.50]),
    ]
    print(f"  {'Kombinacio':<35} {'n':>5}  {'dir_acc':>8}  {'avg_abs%':>8}")
    print("  " + "-" * 60)
    for label, sub in combos:
        if len(sub) < 5:
            print(f"  {label:<35} n<5")
            continue
        acc, n = dir_acc(sub, W, fb_thresh=0.0)
        ab = avg_abs(sub, W)
        print(f"  {label:<35} {n:>5,}  {str(acc)+'%':>8}  {ab:>8.4f}")

    # --- 6. Threshold szenzitivitas ---
    print("\n" + "=" * 70)
    print("6. THRESHOLD SZENZITIVITAS (miss+FB neg kombó, különböző küszöbök)")
    print("=" * 70)
    print(f"  {'TF-IDF kuszob':<18} {'Elso megj.':>12}  {'miss+neg n':>10}  {'dir_acc':>8}")
    print("  " + "-" * 52)
    for thr in [0.25, 0.30, 0.35, 0.40, 0.50, 0.60]:
        first_t = deduplicate(articles, args.window_hours, thr)
        valid_t = [a for a in first_t
                   if is_trading(a["pub_at"], a["ticker"]) and a["prices"]]
        # Arakat mar betoltottuk, felhasznalhatjuk ha megegyeznek a valid listavaL
        # De itt egyszerusitsuk: szamoljuk a metrikat az uj 'valid' szubszeten
        # Csak azokat vesszuk, amik a valid listaban is szerepelnek (van aruk)
        valid_ids = {r["id"] for r in valid}
        first_ids = {a["id"] for a in first_t}
        overlap   = [r for r in valid if r["id"] in first_ids]
        sub_mn = [r for r in overlap if r["worthy"] and r["surp_dir"] == "miss" and r["fb"] < -0.10]
        acc, n = dir_acc(sub_mn, W, fb_thresh=0.0)
        print(f"  {thr:<18.2f} {len(overlap):>12,}  {len(sub_mn):>10,}  {str(acc)+'%':>8}")

    print("\n" + "=" * 70)
    print("KESZ")
    print("=" * 70)


if __name__ == "__main__":
    main()
