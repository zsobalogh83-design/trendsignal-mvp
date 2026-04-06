"""
TrendSignal - Hír–Árfolyam Korreláció Elemzés
==============================================

Megvizsgálja, hogy az LLM által adott előrejelzések (llm_price_impact, llm_score)
mennyire korrelálnak a hír megjelenése utáni 6 órás valós árfolyammozgással.

Adatforrás:
  - archive_news_items: 75K sor, mind LLM-mel elemzett (2024-03 – 2026-03)
  - news_items + news_tickers: 6.5K LLM-es sor (2026-01 – most)
  - price_data (interval='15m'): 15 perces gyertyák

Futtatás:
    python one_offs/analyze_news_price_correlation.py

Kimenet:
    one_offs/news_correlation_output/
        summary.txt
        01_direction_accuracy.csv
        02_magnitude_correlation.csv
        03_decay_validation.csv
        04_finbert_vs_llm.csv
        05_catalyst_performance.csv
        06_recommendations.txt
"""

import os
import sys
import sqlite3
import csv
from datetime import datetime, timedelta
from bisect import bisect_left, bisect_right
from collections import defaultdict
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Konfiguráció
# ---------------------------------------------------------------------------

DB_PATH     = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trendsignal.db")
OUTPUT_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_correlation_output")

# Elemzési időablakok (perc)
WINDOWS_MIN = [60, 120, 240, 360]   # 1h, 2h, 4h, 6h

# US tőzsde kereskedési idő (UTC percben)
# EDT: 13:30–20:00 UTC | EST: 14:30–21:00 UTC → konzervatív: 13:30–21:00
US_OPEN_UTC_MIN  = 13 * 60 + 30   # 13:30 UTC
US_CLOSE_UTC_MIN = 21 * 60        # 21:00 UTC

# BÉT kereskedési idő (UTC)
BET_OPEN_UTC_MIN  =  7 * 60       # 07:00 UTC (08:00 CET)
BET_CLOSE_UTC_MIN = 15 * 60       # 15:00 UTC (16:00 CET)

# Irány-döntés küszöb (% alatt "semleges" mozgás)
DIRECTION_NEUTRAL_PCT = 0.15

# Relevancia küszöb az archive_news_items av_relevance_score-jához
MIN_RELEVANCE_SCORE = 0.3

# ---------------------------------------------------------------------------
# Segédfüggvények
# ---------------------------------------------------------------------------

def _ts(s: str) -> datetime:
    """ISO string → naive datetime."""
    if s is None:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s[:len(fmt) + 6], fmt)
        except ValueError:
            continue
    return None


def _utc_min(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def _is_us_trading(dt: datetime) -> bool:
    m = _utc_min(dt)
    return US_OPEN_UTC_MIN <= m < US_CLOSE_UTC_MIN and dt.weekday() < 5


def _is_bet_trading(dt: datetime) -> bool:
    m = _utc_min(dt)
    return BET_OPEN_UTC_MIN <= m < BET_CLOSE_UTC_MIN and dt.weekday() < 5


def _is_trading(dt: datetime, ticker: str) -> bool:
    if ticker.endswith(".BD"):
        return _is_bet_trading(dt)
    return _is_us_trading(dt)


def _pearson(xs, ys):
    """Pearson r, n, p-value (kétoldali t-teszt közelítés)."""
    n = len(xs)
    if n < 5:
        return None, n, None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx  = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy  = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0, n, 1.0
    r = num / (dx * dy)
    r = max(-1.0, min(1.0, r))
    # t = r * sqrt(n-2) / sqrt(1-r^2)
    if abs(r) >= 1.0:
        return r, n, 0.0
    t = r * math.sqrt(n - 2) / math.sqrt(1 - r * r)
    # p-value közelítés (kétoldali): nagyon durva, de elegendő tájékoztató jelleggel
    # |t| > 4 → p < 0.0001, |t| > 3 → p < 0.005, |t| > 2 → p < 0.05
    if abs(t) > 4:
        p = 0.0001
    elif abs(t) > 3:
        p = 0.005
    elif abs(t) > 2:
        p = 0.05
    else:
        p = max(0.05, 1.0 - abs(t) / 4.0)
    return round(r, 4), n, p


def _direction(pct: float) -> str:
    if pct > DIRECTION_NEUTRAL_PCT:
        return "up"
    if pct < -DIRECTION_NEUTRAL_PCT:
        return "down"
    return "neutral"


def _llm_predicted_direction(llm_price_impact: str) -> str:
    if llm_price_impact in ("up", "strong_up"):
        return "up"
    if llm_price_impact in ("down", "strong_down"):
        return "down"
    return "neutral"


def _safe_float(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _mean(lst):
    lst = [x for x in lst if x is not None]
    return sum(lst) / len(lst) if lst else None


def _pct_fmt(v):
    if v is None:
        return "N/A"
    return f"{v:.1f}%"


def _r_fmt(v):
    if v is None:
        return "N/A"
    return f"{v:.4f}"


# ---------------------------------------------------------------------------
# 1. Adatbetöltés
# ---------------------------------------------------------------------------

def load_price_data(conn: sqlite3.Connection):
    """
    Betölti az összes 15m gyertyát memóriába per ticker.
    Visszatér: {ticker: [(timestamp_dt, close), ...]} rendezett timestamps szerint.
    """
    print("[1/6] Price data betöltése 15m gyertyák...")
    rows = conn.execute(
        "SELECT ticker_symbol, timestamp, close FROM price_data WHERE interval='15m' ORDER BY ticker_symbol, timestamp"
    ).fetchall()
    data = defaultdict(list)
    for ticker, ts_str, close in rows:
        dt = _ts(ts_str)
        if dt and close is not None:
            data[ticker].append((dt, float(close)))
    print(f"    Betöltve: {sum(len(v) for v in data.values()):,} gyertya, {len(data)} ticker")
    return dict(data)


def get_price_at(price_map: dict, ticker: str, target_dt: datetime, tolerance_min: int = 20):
    """
    Megkeresi a target_dt-hez legközelebbi close árat ±tolerance_min percen belül.
    Visszatér: float vagy None.
    """
    candles = price_map.get(ticker)
    if not candles:
        return None
    timestamps = [c[0] for c in candles]
    # Bináris kereséssel a legközelebbi
    lo = bisect_left(timestamps, target_dt - timedelta(minutes=tolerance_min))
    hi = bisect_right(timestamps, target_dt + timedelta(minutes=tolerance_min))
    if lo >= hi:
        return None
    best = min(range(lo, hi), key=lambda i: abs((candles[i][0] - target_dt).total_seconds()))
    return candles[best][1]


def load_news(conn: sqlite3.Connection) -> list:
    """
    Betölti az összes releváns hírt mindkét forrásból.
    Visszatér: list of dict (egységes séma).
    """
    print("[2/6] Hírek betöltése...")
    records = []

    # --- archive_news_items (fő forrás) ---
    rows = conn.execute("""
        SELECT
            ticker_symbol,
            published_at,
            av_relevance_score,
            llm_score,
            llm_price_impact,
            llm_impact_level,
            llm_impact_duration,
            llm_catalyst_type,
            llm_priced_in,
            llm_confidence,
            finbert_score,
            active_score,
            active_score_source
        FROM archive_news_items
        WHERE active_score_source IN ('llm', 'llm_v2')
          AND llm_price_impact IS NOT NULL
          AND ticker_symbol NOT LIKE '%.BD'
    """).fetchall()

    for r in rows:
        ticker      = r[0]
        pub_dt      = _ts(r[1])
        if pub_dt is None:
            continue
        relevance   = _safe_float(r[2]) or 0.0
        if relevance < MIN_RELEVANCE_SCORE:
            continue
        if not _is_trading(pub_dt, ticker):
            continue
        records.append({
            "source":        "archive",
            "ticker":        ticker,
            "published_at":  pub_dt,
            "relevance":     relevance,
            "llm_score":     _safe_float(r[3]),
            "llm_impact":    r[4],
            "llm_level":     r[5],
            "llm_duration":  r[6],
            "llm_catalyst":  r[7],
            "llm_priced_in": bool(r[8]) if r[8] is not None else None,
            "llm_confidence":r[9],
            "finbert_score": _safe_float(r[10]),
            "active_score":  _safe_float(r[11]),
            "active_source": r[12],
        })

    # --- news_items + news_tickers (friss, live adatok) ---
    rows2 = conn.execute("""
        SELECT
            t.symbol         AS ticker_symbol,
            n.published_at,
            nt.relevance_score,
            n.llm_score,
            n.llm_price_impact,
            n.llm_impact_level,
            n.llm_impact_duration,
            n.llm_catalyst_type,
            n.llm_priced_in,
            n.llm_confidence,
            n.finbert_score,
            n.active_score,
            n.active_score_source
        FROM news_items n
        JOIN news_tickers nt ON nt.news_id = n.id
        JOIN tickers t ON t.id = nt.ticker_id
        WHERE n.active_score_source IN ('llm', 'llm_v2')
          AND n.llm_price_impact IS NOT NULL
          AND t.symbol NOT LIKE '%.BD'
          AND nt.relevance_score >= ?
    """, (MIN_RELEVANCE_SCORE,)).fetchall()

    for r in rows2:
        ticker  = r[0]
        pub_dt  = _ts(r[1])
        if pub_dt is None:
            continue
        if not _is_trading(pub_dt, ticker):
            continue
        records.append({
            "source":        "live",
            "ticker":        ticker,
            "published_at":  pub_dt,
            "relevance":     _safe_float(r[2]) or 0.0,
            "llm_score":     _safe_float(r[3]),
            "llm_impact":    r[4],
            "llm_level":     r[5],
            "llm_duration":  r[6],
            "llm_catalyst":  r[7],
            "llm_priced_in": bool(r[8]) if r[8] is not None else None,
            "llm_confidence":r[9],
            "finbert_score": _safe_float(r[10]),
            "active_score":  _safe_float(r[11]),
            "active_source": r[12],
        })

    print(f"    Betöltve: {len(records):,} hír (archive: {sum(1 for r in records if r['source']=='archive'):,}, live: {sum(1 for r in records if r['source']=='live'):,})")
    return records


def enrich_with_price_changes(records: list, price_map: dict) -> list:
    """
    Minden hírhez kiszámolja a t+1h, t+2h, t+4h, t+6h árfolyamváltozást.
    Szűri azokat, ahol a t0 ár nem elérhető.
    """
    print("[3/6] Árfolyamváltozások kiszámítása...")
    enriched = []
    missing_t0 = 0

    for rec in records:
        pub_dt = rec["published_at"]
        ticker = rec["ticker"]
        t0 = pub_dt + timedelta(minutes=15)   # belépési pont

        entry_price = get_price_at(price_map, ticker, t0)
        if entry_price is None or entry_price == 0:
            missing_t0 += 1
            continue

        pct_changes = {}
        for w_min in WINDOWS_MIN:
            target = t0 + timedelta(minutes=w_min)
            exit_price = get_price_at(price_map, ticker, target)
            if exit_price is not None and exit_price > 0:
                pct_changes[w_min] = round((exit_price - entry_price) / entry_price * 100, 4)
            else:
                pct_changes[w_min] = None

        rec["entry_price"]  = entry_price
        rec["pct_changes"]  = pct_changes
        enriched.append(rec)

    print(f"    Feldolgozva: {len(enriched):,} hír | Kihagyva (nincs t0 ár): {missing_t0:,}")
    return enriched


# ---------------------------------------------------------------------------
# 2–6. Elemzési szekciók
# ---------------------------------------------------------------------------

def analyze_direction_accuracy(records: list) -> list:
    """
    Szekció 1: Irány-pontosság szegmensenként.
    Dimenzió: llm_confidence × llm_impact_level × llm_priced_in × window
    """
    print("[4/6] Irány-pontosság elemzés...")
    results = []

    def _run(label, subset, window_min):
        vals = [(r["llm_impact"], r["pct_changes"].get(window_min)) for r in subset
                if r["pct_changes"].get(window_min) is not None]
        if len(vals) < 10:
            return
        n = len(vals)
        correct  = sum(1 for imp, pct in vals if _llm_predicted_direction(imp) == _direction(pct))
        neutral_actual = sum(1 for imp, pct in vals if _direction(pct) == "neutral")
        wrong    = n - correct - neutral_actual
        acc      = correct / n * 100

        results.append({
            "segment":          label,
            "window_h":         window_min // 60,
            "n":                n,
            "accuracy_pct":     round(acc, 1),
            "correct":          correct,
            "neutral_actual":   neutral_actual,
            "wrong":            wrong,
        })

    # Globális
    for w in WINDOWS_MIN:
        _run("ALL", records, w)

    # llm_confidence szegmensek
    for conf in ("high", "medium", "low"):
        sub = [r for r in records if r["llm_confidence"] == conf]
        for w in WINDOWS_MIN:
            _run(f"confidence={conf}", sub, w)

    # llm_impact_level szegmensek
    for lvl in (5, 4, 3, 2, 1):
        sub = [r for r in records if r["llm_level"] == lvl]
        for w in WINDOWS_MIN:
            _run(f"impact_level={lvl}", sub, w)

    # priced_in
    for pi in (False, True):
        sub = [r for r in records if r["llm_priced_in"] == pi]
        for w in WINDOWS_MIN:
            _run(f"priced_in={pi}", sub, w)

    # confidence × impact_level kombinációk (top kombinációk)
    for conf in ("high", "medium"):
        for lvl in (5, 4, 3):
            sub = [r for r in records if r["llm_confidence"] == conf and r["llm_level"] == lvl]
            for w in WINDOWS_MIN:
                _run(f"confidence={conf}_level={lvl}", sub, w)

    return results


def analyze_magnitude_correlation(records: list) -> list:
    """
    Szekció 2: llm_score magnitudó vs valós árfolyamváltozás Pearson-korrelációja.
    """
    print("[4/6] Magnitudó-korreláció elemzés...")
    results = []

    def _run(label, subset, window_min):
        pairs = [(r["llm_score"], r["pct_changes"].get(window_min))
                 for r in subset
                 if r["llm_score"] is not None and r["pct_changes"].get(window_min) is not None]
        if len(pairs) < 10:
            return
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        r, n, p = _pearson(xs, ys)
        results.append({
            "segment":      label,
            "window_h":     window_min // 60,
            "n":            n,
            "pearson_r":    r,
            "p_value_approx": p,
            "significant":  p is not None and p <= 0.05,
            "avg_llm_score":  round(_mean(xs), 4),
            "avg_pct_change": round(_mean(ys), 4),
        })

    for w in WINDOWS_MIN:
        _run("ALL", records, w)
    for conf in ("high", "medium", "low"):
        sub = [r for r in records if r["llm_confidence"] == conf]
        for w in WINDOWS_MIN:
            _run(f"confidence={conf}", sub, w)
    for pi in (False, True):
        sub = [r for r in records if r["llm_priced_in"] == pi]
        for w in WINDOWS_MIN:
            _run(f"priced_in={pi}", sub, w)
    # Csak nem-neutral előrejelzések
    sub_nn = [r for r in records if r["llm_impact"] not in ("neutral",)]
    for w in WINDOWS_MIN:
        _run("non_neutral_only", sub_nn, w)

    return results


def analyze_decay_validation(records: list) -> list:
    """
    Szekció 3: Hír kora vs irány-pontosság.
    Ha a hír signal_calculation időpontjában már X óra régi volt,
    mennyire pontos az LLM előrejelzés?
    Mivel nincs signal_calculation kapcsolatunk a hírekhez, a published_at
    napszakát és az "el lett-e használva" kérdést kerülő úton közelítjük:
    a hír kereskedési napon belül melyik sávban érkezett?
    """
    print("[4/6] Decay-modell validáció...")
    results = []

    # Csoportok: hír napján belüli időpozíció
    def _news_age_band(dt: datetime) -> str:
        m = _utc_min(dt)
        # US: nyitás 13:30 UTC
        mins_since_open = m - US_OPEN_UTC_MIN
        if mins_since_open < 0:
            return None
        if mins_since_open < 120:
            return "0-2h"
        elif mins_since_open < 360:
            return "2-6h"
        elif mins_since_open < 480:
            return "6-8h (napvége)"
        return None  # napvégen túl

    for band in ("0-2h", "2-6h", "6-8h (napvége)"):
        sub = [r for r in records if _news_age_band(r["published_at"]) == band]
        for w in WINDOWS_MIN:
            vals = [(r["llm_impact"], r["pct_changes"].get(w)) for r in sub
                    if r["pct_changes"].get(w) is not None]
            if len(vals) < 10:
                continue
            n = len(vals)
            correct = sum(1 for imp, pct in vals if _llm_predicted_direction(imp) == _direction(pct))
            neutral_actual = sum(1 for imp, pct in vals if _direction(pct) == "neutral")
            acc = correct / n * 100
            avg_abs_move = _mean([abs(pct) for _, pct in vals])
            results.append({
                "news_age_band":    band,
                "window_h":         w // 60,
                "n":                n,
                "accuracy_pct":     round(acc, 1),
                "neutral_actual_pct": round(neutral_actual / n * 100, 1),
                "avg_abs_move_pct": round(avg_abs_move, 4) if avg_abs_move else None,
            })

    return results


def analyze_finbert_vs_llm(records: list) -> list:
    """
    Szekció 4: FinBERT score vs LLM score összehasonlítás.
    Hol divergálnak, és melyik a pontosabb?
    """
    print("[4/6] FinBERT vs LLM összehasonlítás...")
    results = []

    # Csak azok ahol mindkét score elérhető
    both = [r for r in records if r["finbert_score"] is not None and r["llm_score"] is not None]

    # Egyező vs eltérő irány
    def _fb_dir(score):
        if score > 0.05:
            return "up"
        if score < -0.05:
            return "down"
        return "neutral"

    agree = [r for r in both if _fb_dir(r["finbert_score"]) == _llm_predicted_direction(r["llm_impact"])]
    disagree = [r for r in both if _fb_dir(r["finbert_score"]) != _llm_predicted_direction(r["llm_impact"])]

    for label, sub in [("agree_fb_llm", agree), ("disagree_fb_llm", disagree), ("all_both", both)]:
        for w in WINDOWS_MIN:
            # LLM accuracy
            llm_vals = [(r["llm_impact"], r["pct_changes"].get(w)) for r in sub
                        if r["pct_changes"].get(w) is not None]
            # FinBERT accuracy
            fb_vals = [(_fb_dir(r["finbert_score"]), r["pct_changes"].get(w)) for r in sub
                       if r["pct_changes"].get(w) is not None]

            n = len(llm_vals)
            if n < 10:
                continue

            llm_correct = sum(1 for imp, pct in llm_vals if _llm_predicted_direction(imp) == _direction(pct))
            fb_correct  = sum(1 for imp, pct in fb_vals  if imp == _direction(pct))

            results.append({
                "segment":              label,
                "window_h":             w // 60,
                "n":                    n,
                "llm_accuracy_pct":     round(llm_correct / n * 100, 1),
                "finbert_accuracy_pct": round(fb_correct  / n * 100, 1),
                "llm_wins":             llm_correct > fb_correct,
            })

    # Divergens esetek: LLM bullish de FinBERT bearish (és fordítva) — mennyire teljesít az LLM?
    llm_up_fb_down = [r for r in both if _llm_predicted_direction(r["llm_impact"]) == "up"
                      and _fb_dir(r["finbert_score"]) == "down"]
    llm_down_fb_up = [r for r in both if _llm_predicted_direction(r["llm_impact"]) == "down"
                      and _fb_dir(r["finbert_score"]) == "up"]

    for label, sub in [("LLM_up_FB_down", llm_up_fb_down), ("LLM_down_FB_up", llm_down_fb_up)]:
        for w in WINDOWS_MIN:
            vals = [(r["llm_impact"], r["pct_changes"].get(w)) for r in sub
                    if r["pct_changes"].get(w) is not None]
            if len(vals) < 5:
                continue
            n = len(vals)
            correct = sum(1 for imp, pct in vals if _llm_predicted_direction(imp) == _direction(pct))
            avg_pct = _mean([pct for _, pct in vals])
            results.append({
                "segment":          label,
                "window_h":         w // 60,
                "n":                n,
                "llm_accuracy_pct": round(correct / n * 100, 1),
                "avg_actual_pct":   round(avg_pct, 4) if avg_pct else None,
                "llm_wins":         None,
                "finbert_accuracy_pct": None,
            })

    return results


def analyze_catalyst_performance(records: list) -> list:
    """
    Szekció 5: Catalyst típusonkénti teljesítmény.
    """
    print("[4/6] Catalyst-típus teljesítmény elemzés...")
    results = []

    catalysts = set(r["llm_catalyst"] for r in records if r["llm_catalyst"])

    for cat in sorted(catalysts):
        sub = [r for r in records if r["llm_catalyst"] == cat]
        for w in WINDOWS_MIN:
            vals = [(r["llm_impact"], r["pct_changes"].get(w)) for r in sub
                    if r["pct_changes"].get(w) is not None]
            if len(vals) < 10:
                continue
            n = len(vals)
            correct = sum(1 for imp, pct in vals if _llm_predicted_direction(imp) == _direction(pct))
            neutral_actual = sum(1 for _, pct in vals if _direction(pct) == "neutral")
            acc = correct / n * 100
            avg_abs = _mean([abs(pct) for _, pct in vals])
            # Irány megoszlás
            n_up   = sum(1 for imp, _ in vals if _llm_predicted_direction(imp) == "up")
            n_down = sum(1 for imp, _ in vals if _llm_predicted_direction(imp) == "down")
            n_neut = sum(1 for imp, _ in vals if _llm_predicted_direction(imp) == "neutral")

            results.append({
                "catalyst_type":       cat,
                "window_h":            w // 60,
                "n":                   n,
                "accuracy_pct":        round(acc, 1),
                "neutral_actual_pct":  round(neutral_actual / n * 100, 1),
                "avg_abs_move_pct":    round(avg_abs, 4) if avg_abs else None,
                "llm_up_pct":          round(n_up / n * 100, 1),
                "llm_down_pct":        round(n_down / n * 100, 1),
                "llm_neutral_pct":     round(n_neut / n * 100, 1),
            })

    return results


# ---------------------------------------------------------------------------
# 7. Javaslatok generálása
# ---------------------------------------------------------------------------

def generate_recommendations(dir_acc: list, mag_corr: list, decay: list,
                               fb_vs_llm: list, catalyst: list) -> list:
    recs = []

    # --- A. llm_confidence='low' megbízhatósága ---
    low_conf = [r for r in dir_acc if r["segment"] == "confidence=low" and r["window_h"] == 2]
    if low_conf:
        acc = low_conf[0]["accuracy_pct"]
        if acc < 55:
            recs.append({
                "priority": "HIGH",
                "area": "llm_confidence_low",
                "finding": f"llm_confidence='low' irány-pontosság {acc}% (2h ablak) — nem szignifikánsan jobb a véletlennél",
                "suggestion": "FinBERT fallback alkalmazása llm_confidence='low' esetén: active_score_source legyen 'finbert'",
                "config_key": "—",
                "code_file": "src/llm_context_checker.py vagy signal_generator.py",
            })

    # --- B. Priced-in penalty kalibráció ---
    pi_true  = [r for r in dir_acc if "priced_in=True"  in r["segment"] and r["window_h"] == 2]
    pi_false = [r for r in dir_acc if "priced_in=False" in r["segment"] and r["window_h"] == 2]
    if pi_true and pi_false:
        acc_t = pi_true[0]["accuracy_pct"]
        acc_f = pi_false[0]["accuracy_pct"]
        if acc_t < acc_f - 10:
            recs.append({
                "priority": "MEDIUM",
                "area": "llm_priced_in_penalty",
                "finding": f"priced_in=True accuracy {acc_t}% vs priced_in=False {acc_f}% — szignifikáns különbség",
                "suggestion": "A jelenlegi 55% penalty megfontolható, esetleg 40-50%-ra csökkenteni vagy priced_in=True esetén 'neutral'-ra kényszeríteni",
                "config_key": "IMPACT_SCORE_MAP priced_in szorzó",
                "code_file": "src/llm_context_checker.py",
            })

    # --- C. Decay modell validáció ---
    early = [r for r in decay if r["news_age_band"] == "0-2h"         and r["window_h"] == 2]
    mid   = [r for r in decay if r["news_age_band"] == "2-6h"         and r["window_h"] == 2]
    late  = [r for r in decay if r["news_age_band"] == "6-8h (napvége)" and r["window_h"] == 2]
    if early and mid:
        drop = early[0]["accuracy_pct"] - mid[0]["accuracy_pct"]
        if drop < 3:
            recs.append({
                "priority": "LOW",
                "area": "decay_weights_2_6h",
                "finding": f"0-2h accuracy {early[0]['accuracy_pct']}% vs 2-6h {mid[0]['accuracy_pct']}% — különbség csak {drop:.1f}pp, a jelenlegi 0.85 decay lehet konzervatív",
                "suggestion": "DECAY_2_6H értéke emelhető 0.90-re (vagy 1.0-ra)",
                "config_key": "DECAY_2_6H",
                "code_file": "config.json",
            })
        elif drop > 10:
            recs.append({
                "priority": "MEDIUM",
                "area": "decay_weights_2_6h",
                "finding": f"0-2h accuracy {early[0]['accuracy_pct']}% vs 2-6h {mid[0]['accuracy_pct']}% — {drop:.1f}pp esés",
                "suggestion": "DECAY_2_6H értéke csökkentendő 0.70-re",
                "config_key": "DECAY_2_6H",
                "code_file": "config.json",
            })
    if early and late:
        drop = early[0]["accuracy_pct"] - late[0]["accuracy_pct"]
        if drop > 15:
            recs.append({
                "priority": "MEDIUM",
                "area": "decay_weights_6_12h",
                "finding": f"0-2h accuracy {early[0]['accuracy_pct']}% vs 6-8h {late[0]['accuracy_pct']}% — {drop:.1f}pp esés",
                "suggestion": "DECAY_6_12H értéke csökkentendő, pl. 0.60 → 0.40",
                "config_key": "DECAY_6_12H",
                "code_file": "config.json",
            })

    # --- D. FinBERT vs LLM divergencia ---
    diverge_up   = [r for r in fb_vs_llm if r["segment"] == "LLM_up_FB_down"  and r["window_h"] == 2]
    diverge_down = [r for r in fb_vs_llm if r["segment"] == "LLM_down_FB_up"  and r["window_h"] == 2]
    for label, div in [("LLM_up_FB_down", diverge_up), ("LLM_down_FB_up", diverge_down)]:
        if div:
            acc = div[0]["llm_accuracy_pct"]
            avg = div[0].get("avg_actual_pct")
            if acc < 50:
                recs.append({
                    "priority": "HIGH",
                    "area": f"divergence_{label}",
                    "finding": f"Divergens hírek ({label}): LLM accuracy csak {acc}%, avg_pct={avg}",
                    "suggestion": "Ellentétes FinBERT/LLM esetén a score átlagolása vagy FinBERT preferálása javasolt",
                    "config_key": "active_score_source logika",
                    "code_file": "src/llm_context_checker.py",
                })

    # --- E. Catalyst type problémák ---
    weak_catalysts = [r for r in catalyst if r["window_h"] == 2 and r["accuracy_pct"] < 52 and r["n"] >= 30]
    for wc in weak_catalysts:
        recs.append({
            "priority": "MEDIUM",
            "area": f"catalyst_{wc['catalyst_type']}",
            "finding": f"catalyst='{wc['catalyst_type']}': {wc['accuracy_pct']}% accuracy (n={wc['n']}, 2h ablak)",
            "suggestion": f"'{wc['catalyst_type']}' típusú híreknél az LLM score súlyát csökkenteni (pl. 0.7× szorzó), vagy SENTIMENT_WEIGHT csökkentése ebben a kategóriában",
            "config_key": "— (egyedi catalyst súly jelenleg nincs, kód módosítás szükséges)",
            "code_file": "src/signal_generator.py",
        })

    # --- F. Magnitudó-korreláció ---
    all_mag = [r for r in mag_corr if r["segment"] == "ALL" and r["window_h"] == 2]
    if all_mag:
        r_val = all_mag[0]["pearson_r"]
        if r_val is not None and abs(r_val) < 0.15:
            recs.append({
                "priority": "HIGH",
                "area": "magnitude_calibration",
                "finding": f"llm_score magnitudó-korrelációja csak r={r_val} (2h ablak) — az LLM score nagyság nem prediktív",
                "suggestion": "Az IMPACT_SCORE_MAP értékeit felülvizsgálni: a score differenciálás (0.35 vs 0.75) lehet nem indokolt — simább skálára hozni",
                "config_key": "IMPACT_SCORE_MAP",
                "code_file": "src/llm_context_checker.py",
            })
        elif r_val is not None and abs(r_val) > 0.30:
            recs.append({
                "priority": "INFO",
                "area": "magnitude_calibration",
                "finding": f"llm_score magnitudó-korrelációja r={r_val} (2h) — az LLM score prediktív, a jelenlegi skála fenntartható",
                "suggestion": "A magnitudó-skála ésszerű, de az IMPACT_SCORE_MAP fine-tune-olható a tényleges átlagos mozgásokhoz igazítva",
                "config_key": "IMPACT_SCORE_MAP",
                "code_file": "src/llm_context_checker.py",
            })

    if not recs:
        recs.append({
            "priority": "INFO",
            "area": "overall",
            "finding": "Nem találtunk egyértelmű gyengeséget a jelenlegi scoring rendszerben",
            "suggestion": "Az elemzés alapján a jelenlegi paraméterek ésszerűek",
            "config_key": "—",
            "code_file": "—",
        })

    return recs


# ---------------------------------------------------------------------------
# CSV + szöveges export
# ---------------------------------------------------------------------------

def write_csv(path: str, rows: list, fieldnames: list):
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def print_section(title: str, rows: list, key_fields: list, filter_fn=None):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    filtered = [r for r in rows if filter_fn(r)] if filter_fn else rows
    if not filtered:
        print("  (nincs elegendő adat)")
        return
    header = "  " + " | ".join(f"{f[:20]:20s}" for f in key_fields)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for r in filtered[:40]:
        row_str = "  " + " | ".join(f"{str(r.get(f, ''))[:20]:20s}" for f in key_fields)
        print(row_str)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("  TrendSignal - Hír–Árfolyam Korreláció Elemzés")
    print("=" * 70)
    print(f"  DB:     {DB_PATH}")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  Időablakok: {[f'{w//60}h' for w in WINDOWS_MIN]}")
    print()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # --- Betöltés ---
    price_map = load_price_data(conn)
    records   = load_news(conn)
    records   = enrich_with_price_changes(records, price_map)
    conn.close()

    if not records:
        print("HIBA: Nincs elemezhető adat!")
        return

    print(f"\n  Elemzési alap: {len(records):,} hír-árfolyam pár")

    # --- Elemzések ---
    dir_acc  = analyze_direction_accuracy(records)
    mag_corr = analyze_magnitude_correlation(records)
    decay    = analyze_decay_validation(records)
    fb_llm   = analyze_finbert_vs_llm(records)
    catalyst = analyze_catalyst_performance(records)
    recos    = generate_recommendations(dir_acc, mag_corr, decay, fb_llm, catalyst)

    # --- CSV export ---
    write_csv(os.path.join(OUTPUT_DIR, "01_direction_accuracy.csv"), dir_acc,
              ["segment", "window_h", "n", "accuracy_pct", "correct", "neutral_actual", "wrong"])
    write_csv(os.path.join(OUTPUT_DIR, "02_magnitude_correlation.csv"), mag_corr,
              ["segment", "window_h", "n", "pearson_r", "p_value_approx", "significant", "avg_llm_score", "avg_pct_change"])
    write_csv(os.path.join(OUTPUT_DIR, "03_decay_validation.csv"), decay,
              ["news_age_band", "window_h", "n", "accuracy_pct", "neutral_actual_pct", "avg_abs_move_pct"])
    write_csv(os.path.join(OUTPUT_DIR, "04_finbert_vs_llm.csv"), fb_llm,
              ["segment", "window_h", "n", "llm_accuracy_pct", "finbert_accuracy_pct", "llm_wins", "avg_actual_pct"])
    write_csv(os.path.join(OUTPUT_DIR, "05_catalyst_performance.csv"), catalyst,
              ["catalyst_type", "window_h", "n", "accuracy_pct", "neutral_actual_pct",
               "avg_abs_move_pct", "llm_up_pct", "llm_down_pct", "llm_neutral_pct"])
    write_csv(os.path.join(OUTPUT_DIR, "06_recommendations.csv"), recos,
              ["priority", "area", "finding", "suggestion", "config_key", "code_file"])

    # --- Konzol összefoglaló ---
    print_section(
        "1. Irány-pontosság (ALL szegmens, 2h ablak)",
        dir_acc,
        ["segment", "window_h", "n", "accuracy_pct"],
        lambda r: r["segment"] == "ALL" or "confidence=" in r["segment"] or "priced_in=" in r["segment"]
    )

    print_section(
        "2. Magnitudó-korreláció (Pearson r, 2h ablak)",
        mag_corr,
        ["segment", "window_h", "n", "pearson_r", "p_value_approx", "significant"],
        lambda r: r["window_h"] == 2
    )

    print_section(
        "3. Decay-modell validáció (2h ablak)",
        decay,
        ["news_age_band", "window_h", "n", "accuracy_pct", "avg_abs_move_pct"],
        lambda r: r["window_h"] == 2
    )

    print_section(
        "4. FinBERT vs LLM (2h ablak)",
        fb_llm,
        ["segment", "window_h", "n", "llm_accuracy_pct", "finbert_accuracy_pct", "llm_wins"],
        lambda r: r["window_h"] == 2
    )

    print_section(
        "5. Catalyst teljesitmeny (2h ablak, n>=30)",
        catalyst,
        ["catalyst_type", "window_h", "n", "accuracy_pct", "avg_abs_move_pct"],
        lambda r: r["window_h"] == 2 and r["n"] >= 30
    )

    print(f"\n{'='*70}")
    print("  JAVASLATOK")
    print(f"{'='*70}")
    for i, rec in enumerate(recos, 1):
        print(f"\n  [{rec['priority']}] #{i} — {rec['area']}")
        print(f"  Megfigyelés: {rec['finding']}")
        print(f"  Javaslat:    {rec['suggestion']}")
        if rec['config_key'] != "—":
            print(f"  Config:      {rec['config_key']}")
        print(f"  Fájl:        {rec['code_file']}")

    # Summary szövegfájl
    summary_path = os.path.join(OUTPUT_DIR, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"TrendSignal Hír–Árfolyam Korreláció Elemzés\n")
        f.write(f"Futtatva: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Elemzési alap: {len(records):,} hír-árfolyam pár\n\n")

        global_2h = [r for r in dir_acc if r["segment"] == "ALL" and r["window_h"] == 2]
        if global_2h:
            f.write(f"Globális irány-pontosság (2h): {global_2h[0]['accuracy_pct']}% (n={global_2h[0]['n']:,})\n")
        global_mag = [r for r in mag_corr if r["segment"] == "ALL" and r["window_h"] == 2]
        if global_mag:
            f.write(f"Magnitudó-korreláció (2h): r={global_mag[0]['pearson_r']}\n")

        f.write(f"\nJavaslatok ({len(recos)} db):\n")
        for i, rec in enumerate(recos, 1):
            f.write(f"  [{rec['priority']}] {rec['area']}: {rec['finding'][:80]}\n")

    print(f"\n{'='*70}")
    print(f"  Kész! Eredmények: {OUTPUT_DIR}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
