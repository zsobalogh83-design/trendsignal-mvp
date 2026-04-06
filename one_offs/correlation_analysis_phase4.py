"""
Phase 4: Raw Technical Indicator Correlation Analysis
======================================================
A technikai score ÖSSZETEVŐI (nyers indikátor értékek) korrelációja
a forward return-ökkel – score-aggregáció nélkül.

Célkérdés:
  A technical_score=0 (letiltás) helyes döntés volt a PONTOZÁSI FORMULÁRA,
  de a nyers RSI/MACD/ADX/BB értékek tartalmaznak-e BÁRMILYEN
  prediktív jelet a jövőbeli árelmozdulásoknál?

Sections:
  A) Feature engineering (derived indicators)
  B) Egyedi indikátor korreláció (Pearson r, Spearman ρ, BUY/SELL szétválasztva)
  C) Quartilis analízis (melyik értéktartomány ad jobb eredményt)
  D) Decilis analízis (nemlineáris pattern keresés)
  E) Sentiment × indikátor interakció
  F) Legjobb indikátor kombinációk (2-feature együttes hatás)
  G) Összefoglaló ranking

Futtatás:
  python -X utf8 one_offs/correlation_analysis_phase4.py
  python -X utf8 one_offs/correlation_analysis_phase4.py --horizon 1d
"""

import sys, os, argparse, sqlite3, math
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "trendsignal.db"
RESULTS_FILE = "one_offs/results_phase4_full.txt"

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--horizon", default="4h",
                    choices=["1h", "2h", "4h", "1d"],
                    help="Forward return horizon (default: 4h)")
parser.add_argument("--min-score", type=float, default=15.0,
                    help="Minimum |combined_score| (default: 15)")
args = parser.parse_args()

HORIZON = args.horizon
MIN_SCORE = args.min_score

HORIZON_BARS = {"1h": 4, "2h": 8, "4h": 16, "1d": None}

# ── Output routing ────────────────────────────────────────────────────────────
_out_file = open(RESULTS_FILE, "w", encoding="utf-8")

def out(msg=""):
    print(msg)
    _out_file.write(msg + "\n")
    _out_file.flush()

# ── Statistics (no scipy) ─────────────────────────────────────────────────────
def _mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")

def _std(xs):
    if len(xs) < 2:
        return float("nan")
    m = _mean(xs)
    return math.sqrt(sum((x - m)**2 for x in xs) / (len(xs) - 1))

def _t_to_p(t, df):
    """Two-tailed p-value from t-statistic (approx via beta regularised)."""
    if math.isnan(t) or df <= 0:
        return float("nan")
    x = df / (df + t * t)
    # Regularised incomplete beta via continued fraction (Abramowitz & Stegun)
    def _ibeta(a, b, x):
        if x <= 0: return 0.0
        if x >= 1: return 1.0
        lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
        front = math.exp(math.log(x)*a + math.log(1-x)*b - lbeta) / a
        # Lentz continued fraction
        eps = 1e-10
        qab, qap, qam = a+b, a+1, a-1
        c, d = 1.0, 1.0 - qab*x/qap
        if abs(d) < eps: d = eps
        d = 1/d; h = d
        for m2 in range(1, 101):
            m2x2 = 2 * m2
            aa = m2 * (b-m2) * x / ((qam+m2x2) * (a+m2x2))
            d = 1 + aa*d
            if abs(d) < eps: d = eps
            c = 1 + aa/c
            if abs(c) < eps: c = eps
            d = 1/d; h *= d*c
            aa = -(a+m2) * (qab+m2) * x / ((a+m2x2) * (qap+m2x2))
            d = 1 + aa*d
            if abs(d) < eps: d = eps
            c = 1 + aa/c
            if abs(c) < eps: c = eps
            d = 1/d; delta = d*c; h *= delta
            if abs(delta-1) < 3e-7: break
        return front * h
    p_one = _ibeta(df/2, 0.5, x)
    return min(1.0, p_one)

def pearson_r(xs, ys):
    n = len(xs)
    if n < 10:
        return float("nan"), float("nan"), n
    mx, my = _mean(xs), _mean(ys)
    sx = sum((x-mx)**2 for x in xs)
    sy = sum((y-my)**2 for y in ys)
    sxy = sum((xs[i]-mx)*(ys[i]-my) for i in range(n))
    if sx == 0 or sy == 0:
        return float("nan"), float("nan"), n
    r = sxy / math.sqrt(sx * sy)
    r = max(-1, min(1, r))
    t = r * math.sqrt(n - 2) / math.sqrt(1 - r*r + 1e-12)
    p = _t_to_p(t, n - 2)
    return r, p, n

def spearman_r(xs, ys):
    n = len(xs)
    if n < 10:
        return float("nan"), float("nan"), n
    def _rank(vals):
        idx = sorted(range(n), key=lambda i: vals[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and vals[idx[j+1]] == vals[idx[j]]:
                j += 1
            r = (i + j) / 2.0 + 1
            for k in range(i, j+1):
                ranks[idx[k]] = r
            i = j + 1
        return ranks
    rx, ry = _rank(xs), _rank(ys)
    return pearson_r(rx, ry)

def p_stars(p):
    if math.isnan(p): return ""
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    return ""

def dir_acc(xs, ys):
    """Direction accuracy: frac of cases where sign(x)==sign(y), ignoring zeros."""
    pairs = [(x, y) for x, y in zip(xs, ys) if x != 0 and y != 0]
    if not pairs:
        return float("nan"), 0
    correct = sum(1 for x, y in pairs if (x > 0) == (y > 0))
    return correct / len(pairs), len(pairs)

# ── DB helpers ────────────────────────────────────────────────────────────────
def load_signals(conn) -> List[Dict]:
    rows = conn.execute("""
        SELECT
            s.id, s.ticker_symbol, s.signal_timestamp,
            s.combined_score, s.sentiment_score, s.technical_score, s.risk_score,
            s.decision,
            s.close_price,
            s.rsi, s.macd, s.macd_signal, s.macd_hist,
            s.sma_20, s.sma_50, s.sma_200,
            s.atr, s.atr_pct,
            s.bb_upper, s.bb_lower,
            s.stoch_k, s.stoch_d,
            s.nearest_support, s.nearest_resistance
        FROM archive_signals s
        WHERE s.decision != 'HOLD'
          AND ABS(s.combined_score) >= ?
        ORDER BY s.ticker_symbol, s.signal_timestamp
    """, (MIN_SCORE,)).fetchall()

    result = []
    for r in rows:
        ts = r["signal_timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        result.append({k: r[k] for k in r.keys()} | {"signal_timestamp": ts})
    return result

def load_price_bars(conn, symbol: str) -> List[Dict]:
    rows = conn.execute("""
        SELECT timestamp, open, high, low, close
        FROM price_data
        WHERE ticker_symbol = ? AND interval = '15m'
        ORDER BY timestamp
    """, (symbol,)).fetchall()
    result = []
    for r in rows:
        ts = r["timestamp"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        result.append({"ts": ts, "close": r["close"]})
    return result

def get_forward_return(bars: List[Dict], signal_ts: datetime, horizon: str) -> Optional[float]:
    """15m bar-ok alapján forward return számítás."""
    # Entry = signal_ts + 15 perc (első elérhető bar)
    entry_ts = signal_ts + timedelta(minutes=15)
    # Megkeresi az entry bar-t
    entry_price = None
    entry_idx = None
    for i, b in enumerate(bars):
        if b["ts"] >= entry_ts:
            entry_price = b["close"]
            entry_idx = i
            break
    if entry_price is None or entry_idx is None:
        return None

    if horizon == "1d":
        # Következő nap záróára
        entry_date = bars[entry_idx]["ts"].date()
        exit_price = None
        for b in bars[entry_idx+1:]:
            if b["ts"].date() > entry_date:
                exit_price = b["close"]
                break
        if exit_price is None:
            return None
        return (exit_price - entry_price) / entry_price * 100
    else:
        n_bars = HORIZON_BARS[horizon]
        exit_idx = entry_idx + n_bars
        if exit_idx >= len(bars):
            return None
        exit_price = bars[exit_idx]["close"]
        return (exit_price - entry_price) / entry_price * 100

# ── Feature engineering ───────────────────────────────────────────────────────
def compute_features(sig: Dict) -> Dict:
    """Nyers indikátorokból derived feature-öket számít."""
    f = {}
    close = sig.get("close_price")

    # 1. RSI (nyers érték)
    f["rsi"] = sig.get("rsi")

    # 2. MACD histogram (nyers)
    f["macd_hist"] = sig.get("macd_hist")

    # 3. MACD histogram ATR-rel normálva (relatív momentum erősség)
    atr = sig.get("atr")
    macd_h = sig.get("macd_hist")
    f["macd_hist_norm"] = (macd_h / atr) if (atr and atr > 0 and macd_h is not None) else None

    # 4. ATR% (volatilitás)
    f["atr_pct"] = sig.get("atr_pct")

    # 5. Bollinger Band pozíció: 0=alsó szalag, 1=felső szalag
    bbu, bbl = sig.get("bb_upper"), sig.get("bb_lower")
    if close and bbu and bbl and (bbu - bbl) > 0:
        f["bb_position"] = (close - bbl) / (bbu - bbl)
    else:
        f["bb_position"] = None

    # 6. Bollinger szalagszélesség (normált volatilitás)
    if close and bbu and bbl and close > 0:
        f["bb_width"] = (bbu - bbl) / close * 100
    else:
        f["bb_width"] = None

    # 7. Stochastic %K
    f["stoch_k"] = sig.get("stoch_k")

    # 8. Price vs SMA20 (%)
    sma20 = sig.get("sma_20")
    f["price_vs_sma20"] = ((close - sma20) / sma20 * 100) if (close and sma20 and sma20 > 0) else None

    # 9. Price vs SMA50 (%)
    sma50 = sig.get("sma_50")
    f["price_vs_sma50"] = ((close - sma50) / sma50 * 100) if (close and sma50 and sma50 > 0) else None

    # 10. Price vs SMA200 (%) – trend irány
    sma200 = sig.get("sma_200")
    f["price_vs_sma200"] = ((close - sma200) / sma200 * 100) if (close and sma200 and sma200 > 0) else None

    # 11. SMA20 vs SMA50 (%) – rövid-közép trend
    f["sma20_vs_sma50"] = ((sma20 - sma50) / sma50 * 100) if (sma20 and sma50 and sma50 > 0) else None

    # 12. Távolság a legközelebbi ellenállástól (%)
    resist = sig.get("nearest_resistance")
    f["dist_to_resistance"] = ((resist - close) / close * 100) if (resist and close and close > 0) else None

    # 13. Távolság a legközelebbi támasztól (%)
    support = sig.get("nearest_support")
    f["dist_to_support"] = ((close - support) / close * 100) if (support and close and close > 0) else None

    # 14. R:R arány a signal szintjéről
    sl, tp = sig.get("stop_loss"), sig.get("take_profit")
    if close and sl and tp and abs(close - sl) > 0:
        f["rr_ratio"] = abs(tp - close) / abs(close - sl)
    else:
        f["rr_ratio"] = None

    # 15. SMA alignment score: SMA20>SMA50>SMA200 = +2, részleges = +1/0/-1/-2
    alignment = 0
    if sma20 and sma50:
        alignment += 1 if sma20 > sma50 else -1
    if sma50 and sma200:
        alignment += 1 if sma50 > sma200 else -1
    f["sma_alignment"] = alignment if (sma20 and sma50 and sma200) else None

    return f

FEATURE_LABELS = {
    "rsi":               "RSI (nyers érték)",
    "macd_hist":         "MACD histogram (nyers)",
    "macd_hist_norm":    "MACD hist / ATR (normált)",
    "atr_pct":           "ATR% (volatilitás)",
    "bb_position":       "Bollinger pozíció (0=also, 1=felso)",
    "bb_width":          "Bollinger szalagszélessége (%)",
    "stoch_k":           "Stochastic %K",
    "price_vs_sma20":    "Ár vs SMA20 (%)",
    "price_vs_sma50":    "Ár vs SMA50 (%)",
    "price_vs_sma200":   "Ár vs SMA200 (%)",
    "sma20_vs_sma50":    "SMA20 vs SMA50 (%)",
    "dist_to_resistance":"Távolság ellenállástól (%)",
    "dist_to_support":   "Távolság támasztól (%)",
    "rr_ratio":          "R:R arány",
    "sma_alignment":     "SMA alignment score (-2..+2)",
}

# ── Forward return sign for BUY/SELL ─────────────────────────────────────────
def effective_return(raw_ret: float, decision: str) -> float:
    """BUY=long (ret as-is), SELL=short (ret negated)."""
    if decision == "BUY":
        return raw_ret
    else:
        return -raw_ret

# ── Quartile helpers ──────────────────────────────────────────────────────────
def quartile_analysis(feat_vals, ret_vals, n_buckets=4) -> List[Dict]:
    """Feature értékek szerinti bucket analízis."""
    pairs = [(f, r) for f, r in zip(feat_vals, ret_vals)
             if f is not None and not math.isnan(f) and not math.isnan(r)]
    if len(pairs) < n_buckets * 5:
        return []
    pairs.sort(key=lambda x: x[0])
    size = len(pairs) // n_buckets
    buckets = []
    for i in range(n_buckets):
        start = i * size
        end = (i + 1) * size if i < n_buckets - 1 else len(pairs)
        chunk = pairs[start:end]
        fvals = [p[0] for p in chunk]
        rvals = [p[1] for p in chunk]
        win = sum(1 for r in rvals if r > 0) / len(rvals) if rvals else 0
        buckets.append({
            "label":    f"Q{i+1}",
            "f_min":    min(fvals),
            "f_max":    max(fvals),
            "f_mean":   _mean(fvals),
            "n":        len(chunk),
            "mean_ret": _mean(rvals),
            "win_rate": win,
        })
    return buckets

def decile_analysis(feat_vals, ret_vals) -> List[Dict]:
    """10 decilis – nemlineáris pattern keresés."""
    return quartile_analysis(feat_vals, ret_vals, n_buckets=10)

# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
def main():
    out("=" * 72)
    out("PHASE 4: RAW TECHNICAL INDICATOR CORRELATION ANALYSIS")
    out(f"Horizon: {HORIZON} | Min |score|: {MIN_SCORE}")
    out("=" * 72)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # ── Load signals ──────────────────────────────────────────────────────────
    out("\nLoading signals...")
    signals = load_signals(conn)
    out(f"  Total signals: {len(signals):,}")

    # ── Load price bars per ticker ────────────────────────────────────────────
    tickers = list({s["ticker_symbol"] for s in signals})
    bars_by_ticker = {}
    for tk in tickers:
        bars = load_price_bars(conn, tk)
        bars_by_ticker[tk] = bars
    out(f"  Tickers: {', '.join(sorted(tickers))}")

    # ── Compute forward returns + features ───────────────────────────────────
    out("\nComputing forward returns and features...")
    records = []
    missing = 0
    for sig in signals:
        tk = sig["ticker_symbol"]
        bars = bars_by_ticker.get(tk, [])
        raw_ret = get_forward_return(bars, sig["signal_timestamp"], HORIZON)
        if raw_ret is None:
            missing += 1
            continue
        feats = compute_features(sig)
        records.append({
            "ticker":    tk,
            "decision":  sig["decision"],
            "score":     sig["combined_score"],
            "sentiment": sig["sentiment_score"],
            "raw_ret":   raw_ret,
            "eff_ret":   effective_return(raw_ret, sig["decision"]),
            **feats,
        })
    out(f"  Valid records: {len(records):,}  (missing price: {missing:,})")

    buy_recs  = [r for r in records if r["decision"] == "BUY"]
    sell_recs = [r for r in records if r["decision"] == "SELL"]
    out(f"  BUY: {len(buy_recs):,}  |  SELL: {len(sell_recs):,}")

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION B: Egyedi indikátor korreláció
    # ═════════════════════════════════════════════════════════════════════════
    out("\n" + "=" * 72)
    out("SECTION B: INDIVIDUAL INDICATOR CORRELATIONS")
    out("=" * 72)
    out("Pearson r és Spearman rho a forward return-nel")
    out("eff_ret = BUY esetén raw_ret, SELL esetén -raw_ret (long/short nézet)\n")

    feature_names = list(FEATURE_LABELS.keys())

    results_summary = []  # (feature, r_all, p_all, r_buy, r_sell, label)

    for feat in feature_names:
        label = FEATURE_LABELS[feat]
        out(f"--- {feat}: {label} ---")

        for subset_label, subset in [("ALL", records), ("BUY", buy_recs), ("SELL", sell_recs)]:
            xs = [r[feat] for r in subset if r[feat] is not None]
            ys = [r["eff_ret"] for r in subset if r[feat] is not None]
            if len(xs) < 20:
                out(f"  [{subset_label}] n={len(xs)} (insufficient)")
                continue
            r_p, p_p, n = pearson_r(xs, ys)
            r_s, p_s, _ = spearman_r(xs, ys)
            da, n_da = dir_acc(xs, ys)
            out(f"  [{subset_label:4s}] n={n:5,}  "
                f"Pearson r={r_p:+.4f}{p_stars(p_p)} (p={p_p:.4f})  "
                f"Spearman rho={r_s:+.4f}{p_stars(p_s)}  "
                f"dir_acc={da:.1%}")
        out()

        # Summary-be csak ALL kerül
        xs_all = [r[feat] for r in records if r[feat] is not None]
        ys_all = [r["eff_ret"] for r in records if r[feat] is not None]
        xs_buy = [r[feat] for r in buy_recs if r[feat] is not None]
        ys_buy = [r["eff_ret"] for r in buy_recs if r[feat] is not None]
        xs_sell = [r[feat] for r in sell_recs if r[feat] is not None]
        ys_sell = [r["eff_ret"] for r in sell_recs if r[feat] is not None]
        r_all = pearson_r(xs_all, ys_all)[0] if xs_all else float("nan")
        r_buy = pearson_r(xs_buy, ys_buy)[0] if xs_buy else float("nan")
        r_sell = pearson_r(xs_sell, ys_sell)[0] if xs_sell else float("nan")
        p_all = pearson_r(xs_all, ys_all)[1] if xs_all else float("nan")
        results_summary.append((feat, r_all, p_all, r_buy, r_sell, label))

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION C: Quartilis analízis
    # ═════════════════════════════════════════════════════════════════════════
    out("\n" + "=" * 72)
    out("SECTION C: QUARTILE ANALYSIS")
    out("=" * 72)
    out("Feature értéktartományonként átlagos effective return\n")

    for feat in feature_names:
        label = FEATURE_LABELS[feat]
        xs = [r[feat] for r in records if r[feat] is not None]
        ys = [r["eff_ret"] for r in records if r[feat] is not None]
        buckets = quartile_analysis(xs, ys, n_buckets=4)
        if not buckets:
            continue
        out(f"--- {feat} ---")
        out(f"  {'Bucket':<6}  {'Range':<22}  {'N':>5}  {'Mean ret':>9}  {'Win%':>6}")
        for b in buckets:
            out(f"  {b['label']:<6}  [{b['f_min']:>8.2f} .. {b['f_max']:>8.2f}]  "
                f"{b['n']:>5}  {b['mean_ret']:>+8.4f}%  {b['win_rate']:>5.1%}")
        out()

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION D: Decilis – nemlineáris pattern
    # ═════════════════════════════════════════════════════════════════════════
    out("\n" + "=" * 72)
    out("SECTION D: DECILE ANALYSIS (nonlinear patterns)")
    out("=" * 72)
    out("10 egyenlő méretű bucket – görbület keresés\n")

    # Csak a legfontosabb feature-ökre
    key_features = ["rsi", "macd_hist", "bb_position", "stoch_k",
                    "price_vs_sma200", "atr_pct", "dist_to_resistance"]

    for feat in key_features:
        label = FEATURE_LABELS[feat]
        # BUY és SELL külön – mert az eff_ret nézőpont különbözik
        for subset_label, subset in [("BUY", buy_recs), ("SELL", sell_recs)]:
            xs = [r[feat] for r in subset if r[feat] is not None]
            ys = [r["eff_ret"] for r in subset if r[feat] is not None]
            buckets = decile_analysis(xs, ys)
            if not buckets:
                continue
            out(f"--- {feat} [{subset_label}] ---")
            bar_scale = 40
            max_abs = max(abs(b["mean_ret"]) for b in buckets) or 1
            for b in buckets:
                bar_len = int(abs(b["mean_ret"]) / max_abs * bar_scale)
                bar = ("+" if b["mean_ret"] >= 0 else "-") * bar_len
                out(f"  D{b['label'][1:]:<2} [{b['f_mean']:>8.2f}]  "
                    f"n={b['n']:>4}  ret={b['mean_ret']:>+7.4f}%  {bar}")
            out()

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION E: Sentiment × Indikátor interakció
    # ═════════════════════════════════════════════════════════════════════════
    out("\n" + "=" * 72)
    out("SECTION E: SENTIMENT x INDICATOR INTERACTION")
    out("=" * 72)
    out("Magas vs alacsony sentiment esetén az indikátor hatása\n")

    SENT_HIGH = 40.0
    SENT_LOW  = 20.0

    for feat in ["rsi", "macd_hist", "bb_position", "price_vs_sma200", "atr_pct"]:
        label = FEATURE_LABELS[feat]
        out(f"--- {feat}: {label} ---")

        for subset_label, subset in [("BUY", buy_recs), ("SELL", sell_recs)]:
            high_sent = [r for r in subset
                         if r["sentiment"] is not None and abs(r["sentiment"]) >= SENT_HIGH]
            low_sent  = [r for r in subset
                         if r["sentiment"] is not None and abs(r["sentiment"]) < SENT_LOW]

            for grp_label, grp in [("sent>=40", high_sent), ("sent<20", low_sent)]:
                xs = [r[feat] for r in grp if r[feat] is not None]
                ys = [r["eff_ret"] for r in grp if r[feat] is not None]
                if len(xs) < 20:
                    continue
                r_p, p_p, n = pearson_r(xs, ys)
                out(f"  [{subset_label}/{grp_label}] n={n:4,}  "
                    f"r={r_p:+.4f}{p_stars(p_p)} (p={p_p:.4f})")
        out()

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION F: Két indikátor kombinált hatása
    # ═════════════════════════════════════════════════════════════════════════
    out("\n" + "=" * 72)
    out("SECTION F: TWO-INDICATOR GRID (quartile cross)")
    out("=" * 72)
    out("2x2 grid: melyik értéktartomány-kombináció ad legjobb eredményt\n")

    combos = [
        ("rsi",        "macd_hist"),
        ("rsi",        "price_vs_sma200"),
        ("macd_hist",  "price_vs_sma200"),
        ("bb_position","atr_pct"),
        ("rsi",        "atr_pct"),
        ("macd_hist",  "bb_position"),
        ("stoch_k",    "macd_hist"),
        ("price_vs_sma200", "atr_pct"),
    ]

    def split_median(vals):
        """None-ok eltávolítása, median szerinti split."""
        clean = sorted(v for v in vals if v is not None)
        if not clean:
            return None
        return clean[len(clean) // 2]

    for feat_a, feat_b in combos:
        label_a = feat_a
        label_b = feat_b
        xs_a = [r[feat_a] for r in records]
        xs_b = [r[feat_b] for r in records]
        med_a = split_median(xs_a)
        med_b = split_median(xs_b)
        if med_a is None or med_b is None:
            continue

        # 2x2 grid
        grid = defaultdict(list)
        for r in records:
            a, b = r[feat_a], r[feat_b]
            if a is None or b is None:
                continue
            ka = "HI" if a >= med_a else "LO"
            kb = "HI" if b >= med_b else "LO"
            grid[(ka, kb)].append(r["eff_ret"])

        out(f"--- {feat_a} x {feat_b} (median split: {med_a:.2f} / {med_b:.2f}) ---")
        out(f"  {'':10}  {feat_b+'_LO':>14}  {feat_b+'_HI':>14}")
        for ka in ["HI", "LO"]:
            row = f"  {feat_a+'_'+ka:10}"
            for kb in ["LO", "HI"]:
                vals = grid[(ka, kb)]
                if vals:
                    row += f"  n={len(vals):4} ret={_mean(vals):+.4f}%"
                else:
                    row += f"  {'–':>14}"
            out(row)
        out()

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION G: BUY/SELL specifikus indikátor viselkedés
    # ═════════════════════════════════════════════════════════════════════════
    out("\n" + "=" * 72)
    out("SECTION G: SIGNAL-DIRECTION SPECIFIC ANALYSIS")
    out("=" * 72)
    out("Melyik indikátor értéknél volt a legjobb BUY / SELL teljesítmény?\n")

    for feat in key_features:
        label = FEATURE_LABELS[feat]
        out(f"--- {feat}: {label} ---")
        for subset_label, subset in [("BUY", buy_recs), ("SELL", sell_recs)]:
            xs = [r[feat] for r in subset if r[feat] is not None]
            ys = [r["eff_ret"] for r in subset if r[feat] is not None]
            buckets = quartile_analysis(xs, ys, n_buckets=4)
            if not buckets:
                continue
            best = max(buckets, key=lambda b: b["mean_ret"])
            worst = min(buckets, key=lambda b: b["mean_ret"])
            out(f"  [{subset_label}] "
                f"best: {best['label']} [{best['f_min']:.1f}..{best['f_max']:.1f}] "
                f"ret={best['mean_ret']:+.4f}%  |  "
                f"worst: {worst['label']} [{worst['f_min']:.1f}..{worst['f_max']:.1f}] "
                f"ret={worst['mean_ret']:+.4f}%")
        out()

    # ═════════════════════════════════════════════════════════════════════════
    # SECTION H: Összefoglaló ranking
    # ═════════════════════════════════════════════════════════════════════════
    out("\n" + "=" * 72)
    out("SECTION H: SUMMARY RANKING")
    out("=" * 72)
    out("Indikátorok rendezve |Pearson r| szerint (ALL szignalokra, eff_ret)\n")

    ranked = sorted(results_summary, key=lambda x: abs(x[1]) if not math.isnan(x[1]) else 0, reverse=True)

    out(f"  {'Feature':<22}  {'r_all':>8}  {'p':>7}  {'sig':>4}  "
        f"{'r_buy':>8}  {'r_sell':>8}  Label")
    out("  " + "-" * 90)
    for feat, r_all, p_all, r_buy, r_sell, label in ranked:
        stars = p_stars(p_all)
        r_a = f"{r_all:+.4f}" if not math.isnan(r_all) else "   nan"
        r_b = f"{r_buy:+.4f}" if not math.isnan(r_buy) else "   nan"
        r_s = f"{r_sell:+.4f}" if not math.isnan(r_sell) else "   nan"
        p_s = f"{p_all:.4f}" if not math.isnan(p_all) else "   nan"
        out(f"  {feat:<22}  {r_a}  {p_s}  {stars:>4}  {r_b}  {r_s}  {label[:40]}")

    out()
    out("Interpretation guide:")
    out("  |r| < 0.01 = elhanyagolható")
    out("  |r| 0.01-0.03 = gyenge de statisztikailag szignifikáns (n nagy)")
    out("  |r| 0.03-0.07 = mérsékelt – entry gate-ként hasznos lehet")
    out("  |r| > 0.07 = erős – érdemi prediktív érték")
    out()
    out("*** = p<0.001  ** = p<0.01  * = p<0.05")

    out("\n" + "=" * 72)
    out(f"Results saved to: {RESULTS_FILE}")
    out("=" * 72)

    conn.close()
    _out_file.close()

if __name__ == "__main__":
    main()
