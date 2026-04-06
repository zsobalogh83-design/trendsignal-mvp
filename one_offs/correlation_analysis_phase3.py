"""
TrendSignal - Phase 3: Konfiguráció-optimalizálás és Backtest
=============================================================

A Phase 1-2 leletei alapján konkrét konfigurációs változtatásokat tesztel
visszamenőleges szimulációval:

  A) Baseline mérés (jelenlegi rendszer)
  B) Egyedi javítások tesztelése (A/B módszer)
     B1. OPPOSING_SIGNAL exit letiltása
     B2. Score küszöb emelése
     B3. news_avg_score_1h szűrő
     B4. RSI alignment szűrő
     B5. dist_to_resistance szűrő
     B6. MACD irány alignment szűrő
  C) Sentiment/Technical/Risk súly grid-search
  D) Legjobb kombinált stratégiák
  E) Végső config javaslat

A szimulált hozam számítása:
  - BUY signal: long pozíció -> forward return vesszük
  - SELL signal: short pozíció -> forward return negáltja
  - Win: ha a szimulált hozam > 0
  - Metric: dir_acc, mean_return, win_rate, profit_factor, trade_count

Futtatás:
    python one_offs/correlation_analysis_phase3.py
    python one_offs/correlation_analysis_phase3.py --horizon 4h
    python one_offs/correlation_analysis_phase3.py --horizon 4h > results_phase3.txt
"""

import sqlite3
import math
import argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from itertools import product

import numpy as np
import pandas as pd

DB_PATH = "trendsignal.db"


# ─────────────────────────────────────────────────────────────────────────────
# Stat segédek
# ─────────────────────────────────────────────────────────────────────────────

def _t_to_p(t: float, df: int) -> float:
    z = abs(t) * (1 - 1 / (4 * max(df, 1)))
    return min(1.0, float(math.erfc(z / math.sqrt(2))))


def pearson_r(x, y):
    n = len(x)
    if n < 10:
        return 0.0, 1.0
    mx, my = x.mean(), y.mean()
    dx, dy = x - mx, y - my
    denom = math.sqrt((dx**2).sum() * (dy**2).sum())
    if denom == 0:
        return 0.0, 1.0
    r = float((dx * dy).sum() / denom)
    r = max(-1.0, min(1.0, r))
    if abs(r) == 1.0:
        return r, 0.0
    t = r * math.sqrt(n - 2) / math.sqrt(1 - r**2)
    return round(r, 4), round(_t_to_p(t, n - 2), 4)


def _sig(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "** "
    if p < 0.05:  return "*  "
    return "   "


def section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def subsection(title):
    print(f"\n--- {title} ---")


# ─────────────────────────────────────────────────────────────────────────────
# Adatbetöltés
# ─────────────────────────────────────────────────────────────────────────────

def load_signals(conn, tickers):
    ph = ",".join("?" * len(tickers))
    df = pd.read_sql_query(f"""
        SELECT id, ticker_symbol, signal_timestamp, decision, strength,
               combined_score, base_combined_score, sentiment_score,
               technical_score, risk_score,
               overall_confidence, sentiment_confidence, technical_confidence,
               entry_price, stop_loss, take_profit, risk_reward_ratio,
               close_price, rsi, macd, macd_signal, macd_hist,
               sma_20, sma_50, sma_200, atr, atr_pct,
               bb_upper, bb_lower, stoch_k, stoch_d,
               nearest_support, nearest_resistance, news_count
        FROM archive_signals
        WHERE ticker_symbol IN ({ph})
        ORDER BY ticker_symbol, signal_timestamp
    """, conn, params=tickers)
    df["signal_timestamp"] = pd.to_datetime(df["signal_timestamp"], utc=True, errors="coerce")
    return df


def load_news_scores(conn, tickers):
    """Minden signalhoz az elmúlt 1h átlag hír score-ja."""
    ph = ",".join("?" * len(tickers))
    df = pd.read_sql_query(f"""
        SELECT ticker_symbol, published_at, active_score
        FROM archive_news_items
        WHERE ticker_symbol IN ({ph})
          AND published_at IS NOT NULL
          AND active_score IS NOT NULL
        ORDER BY ticker_symbol, published_at
    """, conn, params=tickers)
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    return df.dropna(subset=["published_at"])


def load_15m_prices(conn, tickers):
    ph = ",".join("?" * len(tickers))
    rows = conn.execute(f"""
        SELECT ticker_symbol, timestamp, close FROM price_data
        WHERE interval='15m' AND ticker_symbol IN ({ph})
        ORDER BY ticker_symbol, timestamp
    """, tickers).fetchall()
    pm = defaultdict(list)
    for ticker, ts, close in rows:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            pm[ticker].append((dt, float(close)))
        except Exception:
            pass
    return dict(pm)


def load_daily_prices(conn, tickers):
    ph = ",".join("?" * len(tickers))
    rows = conn.execute(f"""
        SELECT ticker_symbol, timestamp, close FROM price_data
        WHERE interval='1d' AND ticker_symbol IN ({ph})
        ORDER BY ticker_symbol, timestamp
    """, tickers).fetchall()
    pm = defaultdict(list)
    for ticker, ts, close in rows:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            pm[ticker].append((dt, float(close)))
        except Exception:
            pass
    return dict(pm)


def load_trades(conn, tickers):
    ph = ",".join("?" * len(tickers))
    df = pd.read_sql_query(f"""
        SELECT * FROM archive_simulated_trades
        WHERE ticker_symbol IN ({ph}) AND status='CLOSED'
        ORDER BY ticker_symbol, entry_time
    """, conn, params=tickers)
    for col in ["entry_time", "exit_time"]:
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Forward return számítás
# ─────────────────────────────────────────────────────────────────────────────

def _find_after(bars, dt):
    lo, hi = 0, len(bars) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if bars[mid][0] < dt: lo = mid + 1
        else: hi = mid - 1
    return bars[lo][1] if lo < len(bars) else None


def _find_before_or_at(bars, dt):
    lo, hi, res = 0, len(bars) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if bars[mid][0] <= dt:
            res = bars[mid][1]; lo = mid + 1
        else: hi = mid - 1
    return res


def compute_fwd_returns(df, pm_15m, pm_1d, n_bars):
    """n_bars: int (15m bar-ok száma), vagy None (next day close)"""
    rets = []
    for row in df.itertuples():
        bars = pm_15m.get(row.ticker_symbol, [])
        p0 = _find_after(bars, row.signal_timestamp)
        if not p0 or p0 == 0:
            rets.append(float("nan")); continue
        if n_bars is None:
            daily = pm_1d.get(row.ticker_symbol, [])
            nd = (row.signal_timestamp + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0)
            p1 = _find_after(daily, nd)
        else:
            target = row.signal_timestamp + timedelta(minutes=15 * n_bars)
            p1 = _find_before_or_at(bars, target)
        rets.append((p1 - p0) / p0 * 100 if p1 and p0 > 0 else float("nan"))
    df = df.copy()
    df["fwd_ret"] = rets
    return df


def add_news_avg(df, news_df):
    """Hozzáadja a news_avg_1h oszlopot (az elmúlt 1h átlag active_score-a)."""
    by_ticker = {}
    for ticker, grp in news_df.groupby("ticker_symbol"):
        by_ticker[ticker] = grp.sort_values("published_at")[["published_at", "active_score"]].values

    scores = []
    for row in df.itertuples():
        ticker = row.ticker_symbol
        sig_dt = row.signal_timestamp
        if pd.isna(sig_dt) or ticker not in by_ticker:
            scores.append(float("nan")); continue
        data = by_ticker[ticker]
        # Keressük az elmúlt 1h híreit
        win_start = sig_dt - timedelta(hours=1)
        # Bináris kereséssel a határok megtalálása
        n = len(data)
        lo, hi, left = 0, n - 1, n
        while lo <= hi:
            mid = (lo + hi) // 2
            if pd.Timestamp(data[mid][0]) >= win_start: left = mid; hi = mid - 1
            else: lo = mid + 1
        lo, hi, right = 0, n - 1, -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if pd.Timestamp(data[mid][0]) <= sig_dt: right = mid; lo = mid + 1
            else: hi = mid - 1
        if left <= right and right >= 0:
            vals = [float(data[i][1]) for i in range(left, right + 1) if data[i][1] is not None]
            scores.append(float(np.mean(vals)) if vals else float("nan"))
        else:
            scores.append(float("nan"))
    df = df.copy()
    df["news_avg_1h"] = scores
    return df


def is_us_hours(dt):
    if pd.isna(dt): return False
    return dt.weekday() < 5 and (13 * 60 + 30) <= (dt.hour * 60 + dt.minute) < 20 * 60


# ─────────────────────────────────────────────────────────────────────────────
# Stratégia szimulátor
# ─────────────────────────────────────────────────────────────────────────────

def simulate(df, score_col="combined_score", threshold=15.0,
             buy_filters=None, sell_filters=None, extra_filters=None):
    """
    Szimulálja egy stratégia teljesítményét a signal-szintű forward return-ök alapján.

    Paraméterek:
        score_col:     a döntéshez használt score oszlop neve
        threshold:     |score| >= threshold -> BUY vagy SELL (különben skip)
        buy_filters:   listája bool Series-eknek, amelyeknek BUY esetén igaznak kell lenni
        sell_filters:  listája bool Series-eknek, amelyeknek SELL esetén igaznak kell lenni
        extra_filters: mindkét irányra alkalmazott szűrők

    Visszatér: dict metrikákkal
    """
    d = df[df["fwd_ret"].notna()].copy()
    if score_col not in d.columns:
        return None

    score = d[score_col]

    # Alap döntés: score alapján
    long_mask  = score >= threshold
    short_mask = score <= -threshold

    # Extra szűrők (mindkét irányra)
    if extra_filters:
        for f in extra_filters:
            if f is not None and len(f) == len(d):
                long_mask  = long_mask  & f.reindex(d.index, fill_value=False)
                short_mask = short_mask & f.reindex(d.index, fill_value=False)

    # BUY-specifikus szűrők
    if buy_filters:
        for f in buy_filters:
            if f is not None and len(f) == len(d):
                long_mask = long_mask & f.reindex(d.index, fill_value=False)

    # SELL-specifikus szűrők
    if sell_filters:
        for f in sell_filters:
            if f is not None and len(f) == len(d):
                short_mask = short_mask & f.reindex(d.index, fill_value=False)

    longs  = d[long_mask]
    shorts = d[short_mask]

    if len(longs) + len(shorts) < 10:
        return None

    # Szimulált hozamok: long = +ret, short = -ret
    long_rets  = longs["fwd_ret"].values
    short_rets = -shorts["fwd_ret"].values
    all_rets   = np.concatenate([long_rets, short_rets])

    wins = (all_rets > 0).sum()
    losses = (all_rets <= 0).sum()

    profit_factor = (
        all_rets[all_rets > 0].sum() / abs(all_rets[all_rets < 0].sum())
        if (all_rets < 0).any() and (all_rets > 0).any() else float("nan")
    )

    # Direction accuracy: jó irányú trade aránya (|ret|>0.05 szűréssel)
    sig_mask = np.abs(all_rets) > 0.05
    da = (all_rets[sig_mask] > 0).mean() * 100 if sig_mask.sum() > 5 else float("nan")

    return {
        "n_total": len(longs) + len(shorts),
        "n_long":  len(longs),
        "n_short": len(shorts),
        "mean_ret": float(all_rets.mean()),
        "win_rate": float(wins / len(all_rets) * 100),
        "dir_acc":  float(da),
        "profit_factor": float(profit_factor),
        "total_ret": float(all_rets.sum()),
        "std_ret":   float(all_rets.std()),
        "sharpe":    float(all_rets.mean() / all_rets.std() * math.sqrt(252 * 2))
                     if all_rets.std() > 0 else float("nan"),
    }


def fmt_result(r, baseline=None):
    """Egy sor formázása, opcionális baseline-hoz képesti delta jelzéssel."""
    if r is None:
        return "N/A"
    da   = f"{r['dir_acc']:.1f}%" if not math.isnan(r['dir_acc']) else " N/A"
    pf   = f"{r['profit_factor']:.3f}" if not math.isnan(r['profit_factor']) else "  N/A"
    sh   = f"{r['sharpe']:.3f}" if not math.isnan(r['sharpe']) else "  N/A"

    base_str = ""
    if baseline:
        delta_wr  = r["win_rate"]  - baseline["win_rate"]
        delta_ret = r["mean_ret"]  - baseline["mean_ret"]
        delta_da  = (r["dir_acc"]  - baseline["dir_acc"]
                     if not math.isnan(r["dir_acc"]) and not math.isnan(baseline["dir_acc"])
                     else float("nan"))
        dwr = f"{delta_wr:>+6.2f}pp" if not math.isnan(delta_wr) else "      "
        dda = f"{delta_da:>+6.2f}pp" if not math.isnan(delta_da) else "      "
        drt = f"{delta_ret:>+8.4f}%" if not math.isnan(delta_ret) else "         "
        base_str = f"  [{dda} dir | {dwr} win | {drt} ret]"

    return (f"n={r['n_total']:>6,}  "
            f"dir={da}  "
            f"win={r['win_rate']:>5.1f}%  "
            f"ret={r['mean_ret']:>+8.4f}%  "
            f"PF={pf}  "
            f"sharpe={sh}"
            f"{base_str}")


# ─────────────────────────────────────────────────────────────────────────────
# A) Baseline
# ─────────────────────────────────────────────────────────────────────────────

def analyze_baseline(df, trades_df):
    section("A) BASELINE — JELENLEGI RENDSZER TELJESÍTMÉNYE")

    print(f"\n  Signal-szintű szimuláció (threshold=15, eredeti combined_score):")
    base = simulate(df, threshold=15)
    print(f"  {fmt_result(base)}\n")

    print("  Szimulált kereskedések (archive_simulated_trades):")
    t = trades_df
    closed = t[t["status"] == "CLOSED"] if "status" in t.columns else t
    print(f"  n={len(closed):,}  "
          f"win_rate={( closed['pnl_percent'] > 0).mean()*100:.1f}%  "
          f"mean_pnl={closed['pnl_percent'].mean():>+.4f}%  "
          f"total_pnl={closed['pnl_percent'].sum():>+.2f}%")

    subsection("Exit reason breakdown")
    print(f"  {'Exit reason':<25} {'n':>7}  {'mean_pnl%':>10}  {'win_rate':>9}  {'kum_hatás':>10}")
    total_n = len(closed)
    for reason, grp in closed.groupby("exit_reason"):
        wr = (grp["pnl_percent"] > 0).mean() * 100
        mr = grp["pnl_percent"].mean()
        kum = grp["pnl_percent"].sum()
        print(f"  {reason:<25} {len(grp):>7,}  {mr:>+10.4f}  {wr:>8.1f}%  {kum:>+10.2f}%")

    return base


# ─────────────────────────────────────────────────────────────────────────────
# B) Egyedi javítások
# ─────────────────────────────────────────────────────────────────────────────

def analyze_individual_fixes(df, trades_df, baseline):
    section("B) EGYEDI JAVÍTÁSOK — A/B TESZT")

    print(f"\n  {'Változtatás':<52} {'Eredmény + delta a baseline-hoz'}")
    print("  " + "-" * 120)

    # Előre kiszámítjuk a szűrőfeltételeket
    rsi       = df["rsi"]
    macd_hist = df["macd_hist"]
    atr_pct   = df["atr_pct"]
    close     = df["close_price"]
    sma200    = df["sma_200"].fillna(method="ffill")
    dist_res  = (df["nearest_resistance"] - close) / close * 100
    news_avg  = df["news_avg_1h"] if "news_avg_1h" in df.columns else None
    score     = df["combined_score"]

    fixes = []

    # B0: Különböző küszöbök (csak referencia)
    for thr in [25, 40, 50, 65]:
        r = simulate(df, threshold=thr)
        fixes.append((f"  Score küszöb |score| >= {thr}", r))

    print(f"\n  {'B0: Score küszöb hatása':<52}")
    for label, r in fixes:
        print(f"  {label:<52} {fmt_result(r, baseline)}")

    fixes = []

    # B1: RSI alignment — BUY csak RSI<55, SELL csak RSI>45
    r = simulate(df, threshold=15,
                 buy_filters=[rsi < 55],
                 sell_filters=[rsi > 45])
    fixes.append(("B1a. RSI alignment (BUY<55 / SELL>45)", r))

    r = simulate(df, threshold=15,
                 buy_filters=[rsi < 50],
                 sell_filters=[rsi > 50])
    fixes.append(("B1b. RSI alignment (BUY<50 / SELL>50)", r))

    r = simulate(df, threshold=15,
                 buy_filters=[rsi < 45],
                 sell_filters=[rsi > 55])
    fixes.append(("B1c. RSI alignment (BUY<45 / SELL>55)", r))

    r = simulate(df, threshold=15,
                 buy_filters=[rsi < 40],
                 sell_filters=[rsi > 60])
    fixes.append(("B1d. RSI alignment strict (BUY<40 / SELL>60)", r))

    print(f"\n  {'B1: RSI alignment szűrők':<52}")
    for label, r in fixes:
        print(f"  {label:<52} {fmt_result(r, baseline)}")

    fixes = []

    # B2: MACD alignment — BUY csak MACD_hist>0, SELL csak MACD_hist<0
    r = simulate(df, threshold=15,
                 buy_filters=[macd_hist > 0],
                 sell_filters=[macd_hist < 0])
    fixes.append(("B2a. MACD alignment (BUY>0 / SELL<0)", r))

    r = simulate(df, threshold=15,
                 buy_filters=[macd_hist > 0],
                 sell_filters=[macd_hist < 0],
                 extra_filters=[df["combined_score"].abs() >= 25])
    fixes.append(("B2b. MACD align + |score|>=25", r))

    print(f"\n  {'B2: MACD alignment szűrők':<52}")
    for label, r in fixes:
        print(f"  {label:<52} {fmt_result(r, baseline)}")

    fixes = []

    # B3: News avg score szűrő
    if news_avg is not None and news_avg.notna().sum() > 1000:
        r = simulate(df, threshold=15, extra_filters=[news_avg > 0])
        fixes.append(("B3a. news_avg_1h > 0", r))

        r = simulate(df, threshold=15, extra_filters=[news_avg > 0.1])
        fixes.append(("B3b. news_avg_1h > 0.1", r))

        r = simulate(df, threshold=15, extra_filters=[news_avg.notna()])
        fixes.append(("B3c. Csak ahol van hír az elmúlt 1h-ban", r))

        # BUY: news pozitív kell, SELL: news negatív kell
        r = simulate(df, threshold=15,
                     buy_filters=[news_avg >= 0],
                     sell_filters=[news_avg <= 0])
        fixes.append(("B3d. news_avg aligned (BUY:pos / SELL:neg)", r))

        print(f"\n  {'B3: News átlag score szűrők':<52}")
        for label, r in fixes:
            print(f"  {label:<52} {fmt_result(r, baseline)}")
    else:
        print(f"\n  B3: news_avg_1h nem elérhető, kihagyva.")

    fixes = []

    # B4: Trend alignment (SMA200)
    above = close > sma200
    r = simulate(df, threshold=15,
                 buy_filters=[above],
                 sell_filters=[~above])
    fixes.append(("B4a. Trend alignment (BUY>SMA200 / SELL<SMA200)", r))

    r = simulate(df, threshold=15,
                 buy_filters=[~above],
                 sell_filters=[above])
    fixes.append(("B4b. Counter-trend (BUY<SMA200 / SELL>SMA200) [mean-rev]", r))

    print(f"\n  {'B4: Trend alignment (SMA200)':<52}")
    for label, r in fixes:
        print(f"  {label:<52} {fmt_result(r, baseline)}")

    fixes = []

    # B5: dist_to_resistance szűrő (csak ha van elég adat)
    dr = (df["nearest_resistance"] - close) / close * 100
    dr_valid = dr.notna() & (dr > 0)

    for pct in [1.0, 2.0, 3.0, 5.0]:
        r = simulate(df, threshold=15, buy_filters=[dr_valid & (dr > pct)])
        fixes.append((f"B5. BUY csak ha resistance > {pct}% felett", r))

    print(f"\n  {'B5: dist_to_resistance szűrők (BUY-ra)':<52}")
    for label, r in fixes:
        print(f"  {label:<52} {fmt_result(r, baseline)}")

    fixes = []

    # B6: Momentum alignment
    mom = (np.sign(macd_hist.fillna(0)) +
           np.sign(50 - rsi.fillna(50)) +
           np.sign(50 - df["stoch_k"].fillna(50)))

    r = simulate(df, threshold=15,
                 buy_filters=[mom >= 1],
                 sell_filters=[mom <= -1])
    fixes.append(("B6a. Momentum aligned (mom>=1 BUY / mom<=-1 SELL)", r))

    r = simulate(df, threshold=15,
                 buy_filters=[mom >= 2],
                 sell_filters=[mom <= -2])
    fixes.append(("B6b. Momentum aligned strict (mom>=2 / mom<=-2)", r))

    r = simulate(df, threshold=15,
                 buy_filters=[mom == 3],
                 sell_filters=[mom == -3])
    fixes.append(("B6c. Teljes momentum egyezés (mom=3 / mom=-3)", r))

    print(f"\n  {'B6: Momentum alignment':<52}")
    for label, r in fixes:
        print(f"  {label:<52} {fmt_result(r, baseline)}")

    # B7: OPPOSING_SIGNAL exit hatása (trades szintjén)
    subsection("B7: OPPOSING_SIGNAL exit letiltásának szimulált hatása")

    opp = trades_df[trades_df["exit_reason"] == "OPPOSING_SIGNAL"]
    rest = trades_df[trades_df["exit_reason"] != "OPPOSING_SIGNAL"]

    print(f"\n  Jelenlegi rendszer (összes exit):")
    print(f"    n={len(trades_df):,}  "
          f"win={( trades_df['pnl_percent']>0).mean()*100:.1f}%  "
          f"mean={trades_df['pnl_percent'].mean():>+.4f}%  "
          f"sum={trades_df['pnl_percent'].sum():>+.2f}%")

    print(f"\n  Ha az OPPOSING_SIGNAL exiteket kizárjuk (többi exit marad):")
    print(f"    n={len(rest):,}  "
          f"win={( rest['pnl_percent']>0).mean()*100:.1f}%  "
          f"mean={rest['pnl_percent'].mean():>+.4f}%  "
          f"sum={rest['pnl_percent'].sum():>+.2f}%")

    # Mi lett volna az átlagos OPPOSING exit-nél, ha nem zárjuk be?
    # Közelítés: az OPPOSING exit belépési ártól az EOD-ig tartó mozgás
    print(f"\n  OPPOSING exits statisztika:")
    print(f"    n={len(opp):,}  "
          f"win={( opp['pnl_percent']>0).mean()*100:.1f}%  "
          f"mean={opp['pnl_percent'].mean():>+.4f}%  "
          f"sum={opp['pnl_percent'].sum():>+.2f}%")
    print(f"    -> Ezek a kereskedések összesen "
          f"{opp['pnl_percent'].sum():>+.2f}% P&L-t termeltek,")
    print(f"       ami azt jelenti, hogy {abs(opp['pnl_percent'].sum()):.2f}% "
          f"veszteség keletkezett az OPPOSING exit logikából.")


# ─────────────────────────────────────────────────────────────────────────────
# C) Súly grid-search
# ─────────────────────────────────────────────────────────────────────────────

def analyze_weight_grid(df, baseline):
    section("C) SENTIMENT / TECHNICAL / RISK SÚLY GRID-SEARCH")

    print(f"\n  Jelenleg: sentiment=0.70  technical=0.20  risk=0.10")
    print(f"  Keresés: minden (ws, wt, wr) ahol ws+wt+wr=1.0")
    print(f"  Metrika: dir_acc (fő), majd mean_ret (döntetlen esetén)\n")

    # Csak BUY+SELL signalok
    d = df[df["fwd_ret"].notna() & df["decision"].isin(["BUY", "SELL"])].copy()

    # Lehetséges súlyok (0.1 lépésközzel)
    weight_options = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    results = []

    for ws, wt, wr in product(weight_options, repeat=3):
        if abs(ws + wt + wr - 1.0) > 0.001:
            continue
        # Újraszámított score
        new_score = (ws * d["sentiment_score"].fillna(0) +
                     wt * d["technical_score"].fillna(0) +
                     wr * d["risk_score"].fillna(0))
        d2 = d.copy()
        d2["new_score"] = new_score
        r = simulate(d2, score_col="new_score", threshold=15)
        if r and r["n_total"] >= 100:
            results.append((ws, wt, wr, r))

    if not results:
        print("  Nincs elegendo adat a grid-search-hoz.")
        return None

    # Rendezés: dir_acc desc, majd mean_ret desc
    results.sort(key=lambda x: (
        x[3]["dir_acc"] if not math.isnan(x[3]["dir_acc"]) else 0,
        x[3]["mean_ret"]
    ), reverse=True)

    print(f"  {'Súlyok (sent/tech/risk)':<28} {'n':>7}  {'dir_acc':>9}  "
          f"{'win_rate':>9}  {'mean_ret':>10}  {'PF':>7}  {'sharpe':>8}")
    print("  " + "-" * 85)

    # Top 15
    for ws, wt, wr, r in results[:15]:
        da  = f"{r['dir_acc']:.1f}%" if not math.isnan(r['dir_acc']) else " N/A"
        pf  = f"{r['profit_factor']:.3f}" if not math.isnan(r['profit_factor']) else "  N/A"
        sh  = f"{r['sharpe']:.3f}" if not math.isnan(r['sharpe']) else "  N/A"
        mark = " <<<" if ws == 0.7 and wt == 0.2 and wr == 0.1 else ""
        print(f"  sent={ws:.1f} tech={wt:.1f} risk={wr:.1f}  {' ':<6} "
              f"{r['n_total']:>7,}  {da:>9}  {r['win_rate']:>8.1f}%  "
              f"{r['mean_ret']:>+10.4f}  {pf:>7}  {sh:>8}{mark}")

    best = results[0]
    print(f"\n  Jelenlegi (0.7/0.2/0.1): "
          f"dir_acc={baseline['dir_acc']:.1f}%  mean_ret={baseline['mean_ret']:>+.4f}%")
    print(f"  Legjobb  ({best[0]:.1f}/{best[1]:.1f}/{best[2]:.1f}): "
          f"dir_acc={best[3]['dir_acc']:.1f}%  mean_ret={best[3]['mean_ret']:>+.4f}%")

    # Fixált küszöb mellett is
    subsection("Grid-search |score|>=25 kuszobnel")
    results25 = []
    for ws, wt, wr, r_15 in results:
        d2 = d.copy()
        d2["new_score"] = (ws * d["sentiment_score"].fillna(0) +
                           wt * d["technical_score"].fillna(0) +
                           wr * d["risk_score"].fillna(0))
        r = simulate(d2, score_col="new_score", threshold=25)
        if r and r["n_total"] >= 50:
            results25.append((ws, wt, wr, r))

    results25.sort(key=lambda x: (
        x[3]["dir_acc"] if not math.isnan(x[3]["dir_acc"]) else 0,
        x[3]["mean_ret"]
    ), reverse=True)

    print(f"\n  {'Súlyok (sent/tech/risk)':<28} {'n':>7}  {'dir_acc':>9}  "
          f"{'mean_ret':>10}  {'PF':>7}")
    print("  " + "-" * 65)
    for ws, wt, wr, r in results25[:10]:
        da = f"{r['dir_acc']:.1f}%" if not math.isnan(r['dir_acc']) else " N/A"
        pf = f"{r['profit_factor']:.3f}" if not math.isnan(r['profit_factor']) else "  N/A"
        mark = " <<<" if ws == 0.7 and wt == 0.2 and wr == 0.1 else ""
        print(f"  sent={ws:.1f} tech={wt:.1f} risk={wr:.1f}  {' ':<6} "
              f"{r['n_total']:>7,}  {da:>9}  {r['mean_ret']:>+10.4f}  {pf:>7}{mark}")

    return best


# ─────────────────────────────────────────────────────────────────────────────
# D) Kombinált stratégiák
# ─────────────────────────────────────────────────────────────────────────────

def analyze_combined_strategies(df, best_weights, baseline):
    section("D) KOMBINÁLT STRATÉGIÁK")

    print(f"\n  Tesztelés: több javítás egyszerre alkalmazva.\n")

    rsi       = df["rsi"]
    macd_hist = df["macd_hist"]
    close     = df["close_price"]
    sma200    = df["sma_200"].fillna(method="ffill")
    above     = close > sma200
    dr        = (df["nearest_resistance"] - close) / close * 100
    news_avg  = df.get("news_avg_1h", pd.Series(float("nan"), index=df.index))
    mom       = (np.sign(macd_hist.fillna(0)) +
                 np.sign(50 - rsi.fillna(50)) +
                 np.sign(50 - df["stoch_k"].fillna(50)))

    # Legjobb súlyokkal számított score
    if best_weights:
        ws, wt, wr = best_weights[0], best_weights[1], best_weights[2]
        df = df.copy()
        df["best_score"] = (ws * df["sentiment_score"].fillna(0) +
                            wt * df["technical_score"].fillna(0) +
                            wr * df["risk_score"].fillna(0))
        score_col = "best_score"
        weight_label = f"súlyok: S={ws:.1f}/T={wt:.1f}/R={wr:.1f}"
    else:
        score_col = "combined_score"
        weight_label = "eredeti súlyok"

    combos = [
        # (label, threshold, buy_filters, sell_filters, extra_filters)
        ("Baseline (eredeti)",
         15, None, None, None),

        ("RSI align + küszöb 25",
         25, [rsi < 55], [rsi > 45], None),

        ("MACD align + küszöb 25",
         25, [macd_hist > 0], [macd_hist < 0], None),

        ("RSI + MACD align + küszöb 25",
         25, [rsi < 55, macd_hist > 0], [rsi > 45, macd_hist < 0], None),

        ("RSI + MACD align + küszöb 40",
         40, [rsi < 55, macd_hist > 0], [rsi > 45, macd_hist < 0], None),

        ("Momentum align (mom>=1) + küszöb 25",
         25, [mom >= 1], [mom <= -1], None),

        ("Counter-trend (BUY<SMA200 / SELL>SMA200) + RSI",
         25, [~above, rsi < 55], [above, rsi > 45], None),

        ("Counter-trend + MACD align",
         25, [~above, macd_hist > 0], [above, macd_hist < 0], None),

        ("Legjobb súlyok + RSI align + küszöb 25",
         25, [rsi < 55], [rsi > 45], None),

        ("Legjobb súlyok + RSI + MACD + küszöb 25",
         25, [rsi < 55, macd_hist > 0], [rsi > 45, macd_hist < 0], None),

        ("Legjobb súlyok + RSI + MACD + küszöb 40",
         40, [rsi < 55, macd_hist > 0], [rsi > 45, macd_hist < 0], None),
    ]

    # news_avg szűrős kombinációk ha elérhető
    if news_avg.notna().sum() > 1000:
        combos += [
            ("RSI + MACD + news_avg>0 + küszöb 25",
             25, [rsi < 55, macd_hist > 0, news_avg >= 0],
             [rsi > 45, macd_hist < 0, news_avg <= 0], None),
        ]

    print(f"  {'Kombináció':<52} {fmt_result(simulate(df, threshold=15), baseline)}")
    print("  " + "-" * 120)

    combo_results = []
    for label, thr, bf, sf, ef in combos:
        sc = score_col if "súlyok" in label or label == "Baseline (eredeti)" else "combined_score"
        r = simulate(df, score_col=sc, threshold=thr,
                     buy_filters=bf, sell_filters=sf, extra_filters=ef)
        combo_results.append((label, r))
        marker = " <<<" if r and not math.isnan(r.get("dir_acc", float("nan"))) and r["dir_acc"] > 52 else ""
        print(f"  {label:<52} {fmt_result(r, baseline)}{marker}")

    # Legjobb kombináció
    valid = [(l, r) for l, r in combo_results
             if r and not math.isnan(r.get("dir_acc", float("nan")))]
    if valid:
        best_combo = max(valid, key=lambda x: (x[1]["dir_acc"], x[1]["mean_ret"]))
        print(f"\n  Legjobb kombináció: '{best_combo[0]}'")
        print(f"  {fmt_result(best_combo[1])}")

    return combo_results


# ─────────────────────────────────────────────────────────────────────────────
# E) Végső config javaslat
# ─────────────────────────────────────────────────────────────────────────────

def print_config_recommendation(df, best_weights, baseline, horizon):
    section("E) VÉGSŐ CONFIG JAVASLAT")

    ws_rec = best_weights[0] if best_weights else 0.3
    wt_rec = best_weights[1] if best_weights else 0.5
    wr_rec = best_weights[2] if best_weights else 0.2

    rsi = df["rsi"]
    macd_hist = df["macd_hist"]
    close = df["close_price"]
    sma200 = df["sma_200"].fillna(method="ffill")
    above = close > sma200

    # "Legjobb" konfig szimulálása
    df2 = df.copy()
    df2["rec_score"] = (ws_rec * df["sentiment_score"].fillna(0) +
                        wt_rec * df["technical_score"].fillna(0) +
                        wr_rec * df["risk_score"].fillna(0))

    r_rec = simulate(df2, score_col="rec_score", threshold=25,
                     buy_filters=[rsi < 55, macd_hist > 0],
                     sell_filters=[rsi > 45, macd_hist < 0])

    print(f"""
  ╔══════════════════════════════════════════════════════════════════════════╗
  ║  AJÁNLOTT CONFIG VÁLTOZTATÁSOK                                          ║
  ╠══════════════════════════════════════════════════════════════════════════╣
  ║                                                                          ║
  ║  [1] SÚLYOK MÓDOSÍTÁSA (config.json)                                    ║
  ║      Jelenlegi: weight_sentiment=0.70  weight_technical=0.20            ║
  ║                 weight_risk=0.10                                         ║
  ║      Javasolt:  weight_sentiment={ws_rec:.2f}  weight_technical={wt_rec:.2f}            ║
  ║                 weight_risk={wr_rec:.2f}                                         ║
  ║                                                                          ║
  ║  [2] DÖNTÉSI KÜSZÖB EMELÉSE                                             ║
  ║      Jelenlegi: threshold_buy=15  threshold_sell=-15                    ║
  ║      Javasolt:  threshold_buy=25  threshold_sell=-25                    ║
  ║                                                                          ║
  ║  [3] RSI ALIGNMENT SZŰRŐ (ÚJ)                                          ║
  ║      BUY signal csak ha: RSI < 55                                       ║
  ║      SELL signal csak ha: RSI > 45                                      ║
  ║                                                                          ║
  ║  [4] MACD ALIGNMENT SZŰRŐ (ÚJ)                                         ║
  ║      BUY signal csak ha: MACD_histogram > 0                             ║
  ║      SELL signal csak ha: MACD_histogram < 0                            ║
  ║                                                                          ║
  ║  [5] OPPOSING_SIGNAL EXIT LETILTÁSA                                     ║
  ║      Az OPPOSING_SIGNAL exit átlagos P&L = -0.19%                      ║
  ║      Az exit jelek csak 46.4%-ban mutatnak helyes irányt                ║
  ║      -> Tiltsd le ezt az exit módot, vagy emeld a küszöbét              ║
  ║                                                                          ║
  ║  [6] news_avg_score_1h SZŰRŐ (ÚJ - opcionális)                         ║
  ║      Ha az elmúlt 1h hírek átlagos score-ja elérhető:                   ║
  ║      BUY signal csak ha: news_avg_1h >= 0                               ║
  ║      SELL signal csak ha: news_avg_1h <= 0                              ║
  ║      (Ez a 2. legerősebb predictor: r=+0.035***)                        ║
  ║                                                                          ║
  ╠══════════════════════════════════════════════════════════════════════════╣
  ║  SZIMULÁLT EREDMÉNY AZ AJÁNLOTT CONFIGGAL ({horizon} horizon):           ║
  ╠══════════════════════════════════════════════════════════════════════════╣""")

    if r_rec:
        da = f"{r_rec['dir_acc']:.1f}%" if not math.isnan(r_rec['dir_acc']) else "N/A"
        pf = f"{r_rec['profit_factor']:.3f}" if not math.isnan(r_rec['profit_factor']) else "N/A"
        sh = f"{r_rec['sharpe']:.3f}" if not math.isnan(r_rec['sharpe']) else "N/A"
        delta_da  = (r_rec["dir_acc"] - baseline["dir_acc"]
                     if not math.isnan(r_rec["dir_acc"]) and not math.isnan(baseline["dir_acc"])
                     else float("nan"))
        delta_wr  = r_rec["win_rate"] - baseline["win_rate"]
        delta_ret = r_rec["mean_ret"] - baseline["mean_ret"]
        print(f"  ║  Baseline:   n={baseline['n_total']:>6,}  dir={baseline['dir_acc']:.1f}%  "
              f"win={baseline['win_rate']:.1f}%  ret={baseline['mean_ret']:>+.4f}%      ║")
        print(f"  ║  Javasolt:   n={r_rec['n_total']:>6,}  dir={da}  "
              f"win={r_rec['win_rate']:.1f}%  ret={r_rec['mean_ret']:>+.4f}%      ║")
        dd = f"{delta_da:>+.1f}pp" if not math.isnan(delta_da) else "  N/A"
        print(f"  ║  Delta:                  dir={dd}  "
              f"win={delta_wr:>+.1f}pp  ret={delta_ret:>+.4f}%      ║")
    else:
        print("  ║  Nem sikerult szimulalni (nincs eleg adat a szurok utan).         ║")

    print(f"  ╚══════════════════════════════════════════════════════════════════════════╝")

    # config.json snippet
    print(f"""
  CONFIG.JSON SNIPPET (javasolt értékek):
  ----------------------------------------
  {{
    "weight_sentiment": {ws_rec:.2f},
    "weight_technical": {wt_rec:.2f},
    "weight_risk":      {wr_rec:.2f},
    "threshold_buy":    25,
    "threshold_sell":  -25,
    "signal_filters": {{
      "rsi_buy_max":        55,
      "rsi_sell_min":       45,
      "require_macd_align": true,
      "opposing_signal_exit_enabled": false
    }}
  }}
""")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker",  nargs="+", default=None)
    parser.add_argument("--horizon", default="2h", choices=["1h", "2h", "4h", "1d"])
    parser.add_argument("--skip-news", action="store_true", default=False)
    args = parser.parse_args()

    print("=" * 80)
    print("  TrendSignal — Phase 3: Konfiguráció-optimalizálás és Backtest")
    print(f"  Dátum: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Horizon: {args.horizon}")
    print("=" * 80)

    all_us = ["AAPL", "AMZN", "GOOGL", "IBM", "META", "MSFT", "NVDA", "TSLA"]
    tickers = args.ticker if args.ticker else all_us

    conn = sqlite3.connect(DB_PATH)

    print(f"\n  Betöltés: {', '.join(tickers)}")
    print("  [1/5] Archive signals...")
    df = load_signals(conn, tickers)

    print("  [2/5] 15m árak...")
    pm_15m = load_15m_prices(conn, tickers)

    print("  [3/5] 1d árak...")
    pm_1d  = load_daily_prices(conn, tickers)

    print("  [4/5] Kereskedések...")
    trades = load_trades(conn, tickers)

    if not args.skip_news:
        print("  [5/5] Hír score-ok betöltése...")
        news_df = load_news_scores(conn, tickers)
        print(f"         {len(news_df):,} hír betöltve")
    conn.close()

    # Forward returns
    n_bars_map = {"1h": 4, "2h": 8, "4h": 16, "1d": None}
    print(f"\n  Forward return számítás ({args.horizon})...")
    df = compute_fwd_returns(df, pm_15m, pm_1d, n_bars_map[args.horizon])

    if not args.skip_news:
        print("  News átlag score hozzáadása...")
        df = add_news_avg(df, news_df)

    # US piaci szűrő
    us_mask = df["signal_timestamp"].apply(is_us_hours)
    df = df[us_mask].copy()
    print(f"  US piaci szűrő után: {len(df):,} signal  "
          f"(fwd_ret érvényes: {df['fwd_ret'].notna().sum():,})\n")

    # Elemzések
    baseline = analyze_baseline(df, trades)
    analyze_individual_fixes(df, trades, baseline)
    best = analyze_weight_grid(df, baseline)
    best_weights = (best[0], best[1], best[2]) if best else None
    analyze_combined_strategies(df, best_weights, baseline)
    print_config_recommendation(df, best_weights, baseline, args.horizon)

    print("\n" + "=" * 80)
    print("  KÉSZ")
    print("  Egyéb futtatási lehetőségek:")
    print("    python one_offs/correlation_analysis_phase3.py --horizon 4h")
    print("    python one_offs/correlation_analysis_phase3.py --horizon 1d")
    print("    python one_offs/correlation_analysis_phase3.py --ticker NVDA TSLA")
    print("=" * 80)


if __name__ == "__main__":
    main()
