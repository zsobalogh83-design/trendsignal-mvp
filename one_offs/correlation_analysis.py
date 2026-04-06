"""
TrendSignal - Korreláció-keresési elemzés
==========================================

Célja: megtalálni, hogy az archívban tárolt bemeneti adatok (technikai
indikátorok, sentiment score-ok, hír-metaadatok) és az azokat követő
árfolyammozgások között van-e statisztikailag szignifikáns összefüggés.

Fázisok:
  1. Adatminőség felmérés
  2. Forward return számítás (1h, 2h, 4h, 1d horizonton)
  3. Univariát korreláció-elemzés feature-enként
  4. Interakciós analízis (feature párok)
  5. Kontextuális minták (napszak, score extremitás, news timing)
  6. Összefoglaló rang-táblázat

Futtatás:
    python one_offs/correlation_analysis.py
    python one_offs/correlation_analysis.py --ticker AAPL --horizon 4h
    python one_offs/correlation_analysis.py --min-n 30 --out results.txt
"""

import sqlite3
import math
import argparse
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import numpy as np
import pandas as pd

DB_PATH = "trendsignal.db"

# US piaci óra (UTC): 13:30–20:00
US_OPEN_H, US_OPEN_M = 13, 30
US_CLOSE_H = 20

HORIZONS = {
    "1h":  4,   # 15m bar-ok száma
    "2h":  8,
    "4h":  16,
    "1d":  None,  # másnap záróár  -> külön logika
}


# ─────────────────────────────────────────────────────────────────────────────
# Statisztikai segédek  (scipy nélkül)
# ─────────────────────────────────────────────────────────────────────────────

def _t_to_p(t_stat: float, df: int) -> float:
    """Kétoldali p-érték közelítő számítása t-statisztikából (scipy nélkül)."""
    # Abate & Whitt közelítés, kellő pontosságú pénzügyi elemzéshez
    x = df / (df + t_stat ** 2)
    # Regularized incomplete beta function közelítése halving-gel
    # Egyszerűbb: normál közelítés nagy df esetén
    if df > 30:
        z = abs(t_stat)
        p_one = 0.5 * math.erfc(z / math.sqrt(2))
    else:
        # Kis df-re: Cornish-Fisher közelítés
        z = abs(t_stat) * (1 - 1 / (4 * df))
        p_one = 0.5 * math.erfc(z / math.sqrt(2))
    return min(1.0, 2.0 * p_one)


def pearson_r(x: np.ndarray, y: np.ndarray):
    """Pearson r + kétoldali p-érték."""
    n = len(x)
    if n < 10:
        return 0.0, 1.0
    mx, my = x.mean(), y.mean()
    dx, dy = x - mx, y - my
    denom = math.sqrt((dx ** 2).sum() * (dy ** 2).sum())
    if denom == 0:
        return 0.0, 1.0
    r = float((dx * dy).sum() / denom)
    r = max(-1.0, min(1.0, r))
    if abs(r) == 1.0:
        return r, 0.0
    t = r * math.sqrt(n - 2) / math.sqrt(1 - r ** 2)
    p = _t_to_p(t, n - 2)
    return round(r, 4), round(p, 4)


def spearman_r(x: np.ndarray, y: np.ndarray):
    """Spearman ρ + kétoldali p-érték (rangsoroláson alapuló Pearson)."""
    rx = pd.Series(x).rank().values
    ry = pd.Series(y).rank().values
    return pearson_r(rx, ry)


def cohen_d(group_a: np.ndarray, group_b: np.ndarray) -> float:
    """Cohen d: két csoport átlagainak standardizált különbsége."""
    na, nb = len(group_a), len(group_b)
    if na < 2 or nb < 2:
        return 0.0
    pooled_std = math.sqrt(
        ((na - 1) * group_a.std() ** 2 + (nb - 1) * group_b.std() ** 2) / (na + nb - 2)
    )
    if pooled_std == 0:
        return 0.0
    return (group_a.mean() - group_b.mean()) / pooled_std


def win_rate(y: np.ndarray, threshold: float = 0.0) -> float:
    """Pozitív hozam aránya."""
    if len(y) == 0:
        return float("nan")
    return float((y > threshold).mean())


def direction_accuracy(signals: np.ndarray, returns: np.ndarray, threshold: float = 0.0) -> float:
    """
    Irány-pontosság: a signal előjele és a return előjele megegyezik-e?
    Semleges returnöket (|ret| <= threshold) kizárjuk.
    """
    mask = np.abs(returns) > threshold
    if mask.sum() < 5:
        return float("nan")
    s = np.sign(signals[mask])
    r = np.sign(returns[mask])
    return float((s == r).mean())


def _sig_star(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "** "
    if p < 0.05:
        return "*  "
    return "   "


# ─────────────────────────────────────────────────────────────────────────────
# Adatbetöltés
# ─────────────────────────────────────────────────────────────────────────────

def load_signals(conn: sqlite3.Connection, tickers: list) -> pd.DataFrame:
    ph = ",".join("?" * len(tickers))
    df = pd.read_sql_query(f"""
        SELECT
            id, ticker_symbol, signal_timestamp, decision, strength,
            combined_score, base_combined_score, sentiment_score,
            technical_score, risk_score,
            overall_confidence, sentiment_confidence, technical_confidence, risk_confidence,
            entry_price, stop_loss, take_profit, risk_reward_ratio,
            close_price,
            rsi, macd, macd_signal, macd_hist,
            sma_20, sma_50, sma_200,
            atr, atr_pct,
            bb_upper, bb_lower,
            stoch_k, stoch_d,
            nearest_support, nearest_resistance,
            news_count
        FROM archive_signals
        WHERE ticker_symbol IN ({ph})
        ORDER BY ticker_symbol, signal_timestamp
    """, conn, params=tickers)
    df["signal_timestamp"] = pd.to_datetime(df["signal_timestamp"], utc=True, errors="coerce")
    return df


def load_price_map(conn: sqlite3.Connection, tickers: list) -> dict:
    """
    {ticker: sorted list of (timestamp_utc, close)}  — 15m intervallum
    """
    ph = ",".join("?" * len(tickers))
    rows = conn.execute(f"""
        SELECT ticker_symbol, timestamp, close
        FROM price_data
        WHERE interval='15m' AND ticker_symbol IN ({ph})
        ORDER BY ticker_symbol, timestamp
    """, tickers).fetchall()
    pm = defaultdict(list)
    for ticker, ts, close in rows:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        pm[ticker].append((dt, float(close)))
    return dict(pm)


def load_daily_price_map(conn: sqlite3.Connection, tickers: list) -> dict:
    """
    {ticker: sorted list of (date, close)}  — 1d intervallum, next-day close-hoz
    """
    ph = ",".join("?" * len(tickers))
    rows = conn.execute(f"""
        SELECT ticker_symbol, timestamp, close
        FROM price_data
        WHERE interval='1d' AND ticker_symbol IN ({ph})
        ORDER BY ticker_symbol, timestamp
    """, tickers).fetchall()
    pm = defaultdict(list)
    for ticker, ts, close in rows:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        pm[ticker].append((dt, float(close)))
    return dict(pm)


def load_news_timing(conn: sqlite3.Connection, tickers: list) -> pd.DataFrame:
    """Minden signalhoz: melyik volt a legutóbbi archív hír timestampje."""
    ph = ",".join("?" * len(tickers))
    df = pd.read_sql_query(f"""
        SELECT ticker_symbol, published_at, active_score,
               llm_catalyst_type, llm_confidence, llm_priced_in,
               llm_is_first_report, llm_surprise_dir, finbert_score,
               av_relevance_score
        FROM archive_news_items
        WHERE ticker_symbol IN ({ph})
          AND published_at IS NOT NULL
          AND active_score IS NOT NULL
        ORDER BY ticker_symbol, published_at
    """, conn, params=tickers)
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True, errors="coerce")
    return df.dropna(subset=["published_at"])


# ─────────────────────────────────────────────────────────────────────────────
# Forward return számítás
# ─────────────────────────────────────────────────────────────────────────────

def find_price_at(bars: list, target_dt: datetime) -> float | None:
    """Legközelebbi ár target_dt-kor vagy utána (15m barból)."""
    lo, hi = 0, len(bars) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if bars[mid][0] < target_dt:
            lo = mid + 1
        else:
            hi = mid - 1
    if lo < len(bars):
        return bars[lo][1]
    return None


def find_price_before_or_at(bars: list, target_dt: datetime) -> float | None:
    """Legközelebbi ár target_dt-kor vagy előtte."""
    lo, hi = 0, len(bars) - 1
    result = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if bars[mid][0] <= target_dt:
            result = bars[mid][1]
            lo = mid + 1
        else:
            hi = mid - 1
    return result


def compute_forward_returns(df_signals: pd.DataFrame, price_map: dict,
                            daily_map: dict) -> pd.DataFrame:
    """
    Hozzáadja a df_signals-hoz a forward return oszlopokat:
    fwd_ret_1h, fwd_ret_2h, fwd_ret_4h, fwd_ret_1d (%)
    """
    results = {h: [] for h in ["fwd_ret_1h", "fwd_ret_2h", "fwd_ret_4h", "fwd_ret_1d"]}

    for row in df_signals.itertuples():
        ticker = row.ticker_symbol
        sig_dt = row.signal_timestamp
        if pd.isna(sig_dt):
            for h in results:
                results[h].append(float("nan"))
            continue

        bars_15m = price_map.get(ticker, [])
        bars_1d = daily_map.get(ticker, [])

        # Belépési ár: legközelebbi bar sig_dt után
        p0 = find_price_at(bars_15m, sig_dt)
        if p0 is None or p0 == 0:
            for h in results:
                results[h].append(float("nan"))
            continue

        # 1h, 2h, 4h
        for label, n_bars in [("fwd_ret_1h", 4), ("fwd_ret_2h", 8), ("fwd_ret_4h", 16)]:
            target_dt = sig_dt + timedelta(minutes=15 * n_bars)
            p1 = find_price_before_or_at(bars_15m, target_dt)
            if p1 is not None and p0 > 0:
                results[label].append((p1 - p0) / p0 * 100)
            else:
                results[label].append(float("nan"))

        # 1d: következő kereskedési nap záróárja
        next_day = (sig_dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        p1d = find_price_at(bars_1d, next_day)
        if p1d is not None and p0 > 0:
            results["fwd_ret_1d"].append((p1d - p0) / p0 * 100)
        else:
            results["fwd_ret_1d"].append(float("nan"))

    for col, vals in results.items():
        df_signals = df_signals.copy()
        df_signals[col] = vals
    return df_signals


# ─────────────────────────────────────────────────────────────────────────────
# Feature engineering
# ─────────────────────────────────────────────────────────────────────────────

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Bollinger Band pozíció (0=alsó sáv, 1=felső sáv)
    bb_range = df["bb_upper"] - df["bb_lower"]
    df["bb_position"] = np.where(
        bb_range > 0,
        (df["close_price"] - df["bb_lower"]) / bb_range,
        float("nan")
    )

    # Momentum konzisztencia: MACD + RSI + Stochastic irányai összhangja
    df["mom_alignment"] = (
        np.sign(df["macd_hist"]).fillna(0) +
        np.sign(50 - df["rsi"]).fillna(0) +
        np.sign(50 - df["stoch_k"]).fillna(0)
    )

    # Trend erősség irányával
    df["trend_score"] = np.where(
        df["sma_50"].notna() & df["close_price"].notna(),
        np.sign(df["close_price"] - df["sma_50"]),
        float("nan")
    )

    # Ár vs SMA200 (strukturális trend)
    df["above_sma200"] = np.where(
        df["sma_200"].notna() & df["close_price"].notna(),
        (df["close_price"] > df["sma_200"]).astype(float),
        float("nan")
    )

    # Ár vs SMA20
    df["above_sma20"] = np.where(
        df["sma_20"].notna() & df["close_price"].notna(),
        (df["close_price"] > df["sma_20"]).astype(float),
        float("nan")
    )

    # Score abszolút értéke (extremitás)
    df["abs_combined_score"] = df["combined_score"].abs()

    # RSI zóna
    def rsi_zone(v):
        if pd.isna(v):
            return float("nan")
        if v < 30:
            return -2
        if v < 45:
            return -1
        if v < 55:
            return 0
        if v < 70:
            return 1
        return 2

    df["rsi_zone"] = df["rsi"].apply(rsi_zone)

    # Napszak (UTC, 0-23)
    df["hour_utc"] = df["signal_timestamp"].dt.hour

    # Hét napja (0=H, 4=P)
    df["weekday"] = df["signal_timestamp"].dt.weekday

    # Support/resistance proximité (%-ban)
    df["dist_to_support_pct"] = np.where(
        df["nearest_support"].notna() & (df["close_price"] > 0),
        (df["close_price"] - df["nearest_support"]) / df["close_price"] * 100,
        float("nan")
    )
    df["dist_to_resistance_pct"] = np.where(
        df["nearest_resistance"].notna() & (df["close_price"] > 0),
        (df["nearest_resistance"] - df["close_price"]) / df["close_price"] * 100,
        float("nan")
    )

    # RSI oversold + MACD pozitív (dupla bullish)
    df["rsi_oversold_macd_pos"] = (
        (df["rsi"] < 35) & (df["macd_hist"] > 0)
    ).astype(float)

    # RSI overbought + MACD negatív (dupla bearish)
    df["rsi_overbought_macd_neg"] = (
        (df["rsi"] > 65) & (df["macd_hist"] < 0)
    ).astype(float)

    # BUY/SELL bináris (HOLD=nan)
    df["is_buy"] = np.where(df["decision"] == "BUY", 1.0,
                   np.where(df["decision"] == "SELL", -1.0, float("nan")))

    return df


def add_news_timing(df: pd.DataFrame, news_df: pd.DataFrame) -> pd.DataFrame:
    """
    Signalonként: mennyi perc telt el az utolsó hír és a signal között?
    Mennyi friss hír volt az elmúlt 1h-ban?
    """
    news_delay_list = []
    news_count_1h_list = []
    news_avg_score_1h_list = []

    # Tickerenkénti hírindex
    news_by_ticker = {}
    for ticker, grp in news_df.groupby("ticker_symbol"):
        news_by_ticker[ticker] = grp.sort_values("published_at")

    for row in df.itertuples():
        ticker = row.ticker_symbol
        sig_dt = row.signal_timestamp
        if pd.isna(sig_dt) or ticker not in news_by_ticker:
            news_delay_list.append(float("nan"))
            news_count_1h_list.append(float("nan"))
            news_avg_score_1h_list.append(float("nan"))
            continue

        ndf = news_by_ticker[ticker]
        before = ndf[ndf["published_at"] <= sig_dt]
        if before.empty:
            news_delay_list.append(float("nan"))
        else:
            last_news_dt = before["published_at"].iloc[-1]
            delay_min = (sig_dt - last_news_dt).total_seconds() / 60
            news_delay_list.append(delay_min)

        # 1h-ban megjelent hírek
        window_start = sig_dt - timedelta(hours=1)
        recent = ndf[(ndf["published_at"] >= window_start) & (ndf["published_at"] <= sig_dt)]
        news_count_1h_list.append(len(recent))
        if len(recent) > 0:
            news_avg_score_1h_list.append(float(recent["active_score"].mean()))
        else:
            news_avg_score_1h_list.append(float("nan"))

    df = df.copy()
    df["news_delay_min"] = news_delay_list
    df["news_count_1h"] = news_count_1h_list
    df["news_avg_score_1h"] = news_avg_score_1h_list
    return df


# ─────────────────────────────────────────────────────────────────────────────
# US piaci szűrő
# ─────────────────────────────────────────────────────────────────────────────

def is_us_market_hours(dt: pd.Timestamp) -> bool:
    if pd.isna(dt):
        return False
    wd = dt.weekday()
    if wd >= 5:
        return False
    h, m = dt.hour, dt.minute
    open_min = US_OPEN_H * 60 + US_OPEN_M
    close_min = US_CLOSE_H * 60
    return open_min <= h * 60 + m < close_min


# ─────────────────────────────────────────────────────────────────────────────
# Elemzési modulok
# ─────────────────────────────────────────────────────────────────────────────

def section(title: str, width: int = 78):
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def subsection(title: str):
    print(f"\n--- {title} ---")


def analyze_data_quality(df: pd.DataFrame, out_tickers: list):
    section("1. ADATMINŐSÉG FELMÉRÉS")

    print(f"\n  Tickers elemzésben: {', '.join(out_tickers)}")
    print(f"  Összes signal: {len(df):,}")

    for ticker in out_tickers:
        sub = df[df["ticker_symbol"] == ticker]
        ts = sub["signal_timestamp"]
        n_buy = (sub["decision"] == "BUY").sum()
        n_sell = (sub["decision"] == "SELL").sum()
        n_hold = (sub["decision"] == "HOLD").sum()
        fwd_ok = sub["fwd_ret_2h"].notna().sum()
        print(f"\n  [{ticker}]")
        print(f"    Signalok:   {len(sub):,}  (BUY={n_buy:,} SELL={n_sell:,} HOLD={n_hold:,})")
        print(f"    Időszak:    {ts.min()} -> {ts.max()}")
        print(f"    Fwd ret 2h adat: {fwd_ok:,} ({fwd_ok/len(sub)*100:.1f}%)")

    print()
    # Forward return eloszlás
    for col in ["fwd_ret_1h", "fwd_ret_2h", "fwd_ret_4h", "fwd_ret_1d"]:
        v = df[col].dropna()
        if len(v) == 0:
            continue
        print(f"  {col:<15} n={len(v):>6,}  "
              f"mean={v.mean():>+7.3f}%  "
              f"std={v.std():>6.3f}%  "
              f"win_rate={win_rate(v)*100:.1f}%  "
              f"p25={v.quantile(.25):>+7.3f}  p75={v.quantile(.75):>+7.3f}")


def analyze_univariate(df: pd.DataFrame, horizon: str, min_n: int = 30):
    col = f"fwd_ret_{horizon}"
    df_valid = df[df[col].notna()].copy()

    section(f"2. UNIVARIÁT KORRELÁCIÓ – KIMENET: {col}  (n={len(df_valid):,})")

    # ─── Folytonos feature-ök ───────────────────────────────────────────────
    continuous_features = [
        # Score-ok
        ("combined_score",        "Kombinált score (-100..+100)"),
        ("base_combined_score",   "Alap combined score (alignment előtt)"),
        ("sentiment_score",       "Sentiment score"),
        ("technical_score",       "Technical score"),
        ("risk_score",            "Risk score"),
        ("abs_combined_score",    "Kombinált score abs értéke"),
        ("overall_confidence",    "Overall confidence"),
        ("sentiment_confidence",  "Sentiment confidence"),
        ("technical_confidence",  "Technical confidence"),
        # Technikai indikátorok
        ("rsi",                   "RSI (14)"),
        ("macd_hist",             "MACD histogram"),
        ("macd",                  "MACD"),
        ("atr_pct",               "ATR % (volatilitás)"),
        ("bb_position",           "Bollinger Band pozíció (0=alsó, 1=felső)"),
        ("stoch_k",               "Stochastic %K"),
        ("mom_alignment",         "Momentum konzisztencia (-3..+3)"),
        ("above_sma200",          "Ár > SMA200 (trend)"),
        ("above_sma20",           "Ár > SMA20"),
        ("dist_to_support_pct",   "Távolság supporttól (%)"),
        ("dist_to_resistance_pct","Távolság resistance-tól (%)"),
        ("news_count",            "Hírek száma (signal inputja)"),
        ("news_delay_min",        "Perc az utolsó hír óta"),
        ("news_count_1h",         "Hírek száma az elmúlt 1h-ban"),
        ("news_avg_score_1h",     "Átlagos hír score az elmúlt 1h-ban"),
        ("risk_reward_ratio",     "Risk/reward arány"),
        ("hour_utc",              "Napszak (UTC óra)"),
        ("weekday",               "Hét napja (0=H)"),
    ]

    print(f"\n  {'Feature':<35} {'n':>6}  {'Pearson r':>10}  {'Spearman ρ':>11}  "
          f"{'p':>7}  {'sig':>4}  {'dir_acc':>8}")
    print("  " + "-" * 88)

    results = []
    for feat, desc in continuous_features:
        if feat not in df_valid.columns:
            continue
        sub = df_valid[[feat, col]].dropna()
        if len(sub) < min_n:
            continue
        x = sub[feat].values.astype(float)
        y = sub[col].values.astype(float)
        r, p = pearson_r(x, y)
        rho, _ = spearman_r(x, y)
        dacc = direction_accuracy(x, y, threshold=0.05)
        sig = _sig_star(p)
        results.append((abs(r), feat, desc, len(sub), r, rho, p, sig, dacc))

    # Abszolút r szerint rendezve
    results.sort(reverse=True)
    for _, feat, desc, n, r, rho, p, sig, dacc in results:
        dacc_str = f"{dacc*100:.1f}%" if not math.isnan(dacc) else "  N/A"
        print(f"  {desc:<35} {n:>6,}  {r:>+10.4f}  {rho:>+11.4f}  "
              f"{p:>7.4f}  {sig}  {dacc_str:>8}")

    # ─── Kategorikus feature-ök ─────────────────────────────────────────────
    subsection("Kategorikus változók")

    categorical_features = [
        ("decision",          "Decision (BUY/SELL/HOLD)"),
        ("strength",          "Signal strength"),
        ("rsi_zone",          "RSI zóna (-2..+2)"),
    ]

    for feat, desc in categorical_features:
        if feat not in df_valid.columns:
            continue
        print(f"\n  {desc}:")
        print(f"  {'Kategória':<25} {'n':>6}  {'mean_ret':>9}  {'win_rate':>9}  {'dir_acc':>9}")
        print("  " + "-" * 62)
        for cat, grp in df_valid.groupby(feat, observed=True):
            y = grp[col].dropna().values
            if len(y) < min_n:
                continue
            x = grp["combined_score"].dropna().values if "combined_score" in grp.columns else np.zeros(len(y))
            wr = win_rate(y) * 100
            mr = y.mean()
            da = direction_accuracy(x[:len(y)], y, threshold=0.05) * 100 if len(x) >= len(y) else float("nan")
            da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
            print(f"  {str(cat):<25} {len(y):>6,}  {mr:>+9.4f}  {wr:>8.1f}%  {da_str:>9}")


def analyze_score_buckets(df: pd.DataFrame, horizon: str, min_n: int = 20):
    col = f"fwd_ret_{horizon}"
    df_valid = df[df[col].notna()].copy()

    section(f"3. SCORE BUCKET ELEMZÉS – {col}")

    # combined_score buckets
    subsection("Combined score buckets")
    print(f"  {'Bucket':<30} {'n':>6}  {'mean_ret':>9}  {'win_rate':>9}  {'dir_acc':>9}  {'std':>7}")
    print("  " + "-" * 75)

    buckets = [
        ("Erős LONG  score >= 65",   df_valid["combined_score"] >= 65),
        ("Közepes LONG  50..65",     (df_valid["combined_score"] >= 50) & (df_valid["combined_score"] < 65)),
        ("Gyenge LONG   25..50",     (df_valid["combined_score"] >= 25) & (df_valid["combined_score"] < 50)),
        ("Semleges     -25..25",     df_valid["combined_score"].abs() < 25),
        ("Gyenge SHORT -50..-25",    (df_valid["combined_score"] <= -25) & (df_valid["combined_score"] > -50)),
        ("Közepes SHORT-65..-50",    (df_valid["combined_score"] <= -50) & (df_valid["combined_score"] > -65)),
        ("Erős SHORT  score <= -65", df_valid["combined_score"] <= -65),
    ]

    for label, mask in buckets:
        grp = df_valid[mask][col].dropna()
        if len(grp) < min_n:
            continue
        scores = df_valid[mask]["combined_score"].values
        wr = win_rate(grp.values) * 100
        mr = grp.mean()
        da = direction_accuracy(scores[:len(grp)], grp.values, threshold=0.05) * 100
        da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
        print(f"  {label:<30} {len(grp):>6,}  {mr:>+9.4f}  {wr:>8.1f}%  {da_str:>9}  {grp.std():>7.4f}")

    # Sentiment vs technical score irány egyezés
    subsection("Sentiment–Technical irány egyezés vs. kimenet")
    df_valid["sent_tech_agree"] = (
        np.sign(df_valid["sentiment_score"]) == np.sign(df_valid["technical_score"])
    )
    for agree, label in [(True, "Sentiment + Technical AZONOS irányú"),
                          (False, "Sentiment + Technical ELLENTÉTES irányú")]:
        grp = df_valid[df_valid["sent_tech_agree"] == agree][col].dropna()
        if len(grp) < min_n:
            continue
        wr = win_rate(grp.values) * 100
        mr = grp.mean()
        print(f"  {label:<45} n={len(grp):>5,}  mean={mr:>+8.4f}%  win_rate={wr:.1f}%")


def analyze_interactions(df: pd.DataFrame, horizon: str, min_n: int = 30):
    col = f"fwd_ret_{horizon}"
    df_valid = df[df[col].notna()].copy()

    section(f"4. INTERAKCIÓS ANALÍZIS – {col}")

    # RSI × Momentum alignment heatmap (szöveges)
    subsection("RSI zóna × Momentum alignment -> mean forward return")

    rsi_bins = [(-2, "RSI<30 "), (-1, "30-45  "), (0, "45-55  "), (1, "55-70  "), (2, "RSI>70 ")]
    mom_bins = [(-3, "mom=-3"), (-2, "mom=-2"), (-1, "mom=-1"),
                (0, "mom= 0"), (1, "mom=+1"), (2, "mom=+2"), (3, "mom=+3")]

    header = f"  {'RSI \\ Mom':<10}" + "".join(f"  {b[1]:>8}" for b in mom_bins)
    print(header)
    print("  " + "-" * (10 + 10 * len(mom_bins)))
    for rv, rl in rsi_bins:
        row_str = f"  {rl:<10}"
        for mv, ml in mom_bins:
            mask = (df_valid["rsi_zone"] == rv) & (df_valid["mom_alignment"] == mv)
            grp = df_valid[mask][col].dropna()
            if len(grp) < min_n:
                row_str += f"  {'  ---':>8}"
            else:
                row_str += f"  {grp.mean():>+8.3f}"
        print(row_str)

    # Decision × technikai trend
    subsection("Signal decision × above_sma200 -> kimenet")
    print(f"  {'Decision':<10} {'Trend':>12} {'n':>6}  {'mean_ret':>9}  {'win_rate':>9}  {'dir_acc':>9}")
    print("  " + "-" * 60)
    for dec in ["BUY", "SELL", "HOLD"]:
        for above in [1.0, 0.0]:
            mask = (df_valid["decision"] == dec) & (df_valid["above_sma200"] == above)
            grp = df_valid[mask][col].dropna()
            if len(grp) < min_n:
                continue
            trend_lbl = "trend UP" if above == 1.0 else "trend DOWN"
            scores = df_valid[mask]["combined_score"].values
            wr = win_rate(grp.values) * 100
            mr = grp.mean()
            da = direction_accuracy(scores[:len(grp)], grp.values, threshold=0.05) * 100
            da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
            print(f"  {dec:<10} {trend_lbl:>12} {len(grp):>6,}  {mr:>+9.4f}  {wr:>8.1f}%  {da_str:>9}")

    # Dupla bullish / dupla bearish setup
    subsection("Különleges setupok")
    setups = [
        ("RSI<35 + MACD_hist>0 (bullish reversal)", df_valid["rsi_oversold_macd_pos"] == 1),
        ("RSI>65 + MACD_hist<0 (bearish reversal)",  df_valid["rsi_overbought_macd_neg"] == 1),
        ("|combined_score|>65 (extrém jel)",          df_valid["abs_combined_score"] > 65),
        ("Momentum alignment = +3 (minden bullish)",  df_valid["mom_alignment"] == 3),
        ("Momentum alignment = -3 (minden bearish)",  df_valid["mom_alignment"] == -3),
    ]
    # News-timing függő setupok csak ha az adat betöltve
    if "news_count_1h" in df_valid.columns:
        setups += [
            ("news_count_1h>2 + |score|>40",
             (df_valid["news_count_1h"] > 2) & (df_valid["abs_combined_score"] > 40)),
            ("news_delay<30min + |score|>40",
             (df_valid["news_delay_min"] < 30) & (df_valid["abs_combined_score"] > 40)),
        ]
    print(f"\n  {'Setup':<50} {'n':>6}  {'mean_ret':>9}  {'win_rate':>9}")
    print("  " + "-" * 80)
    for label, mask in setups:
        grp = df_valid[mask][col].dropna()
        if len(grp) < min_n:
            print(f"  {label:<50} {'n<' + str(min_n):>6}")
            continue
        wr = win_rate(grp.values) * 100
        mr = grp.mean()
        print(f"  {label:<50} {len(grp):>6,}  {mr:>+9.4f}  {wr:>8.1f}%")


def analyze_time_patterns(df: pd.DataFrame, horizon: str, min_n: int = 50):
    col = f"fwd_ret_{horizon}"
    df_valid = df[df[col].notna()].copy()

    section(f"5. IDŐBELI MINTÁK – {col}")

    # Napszak
    subsection("Napszak (UTC óra) hatása")
    print(f"  {'Óra':>5}  {'n':>6}  {'mean_ret':>9}  {'win_rate':>9}  {'dir_acc':>9}")
    print("  " + "-" * 48)
    for h in range(13, 21):
        mask = df_valid["hour_utc"] == h
        grp = df_valid[mask][col].dropna()
        if len(grp) < min_n:
            continue
        scores = df_valid[mask]["combined_score"].dropna().values
        wr = win_rate(grp.values) * 100
        mr = grp.mean()
        da = direction_accuracy(scores[:len(grp)], grp.values, threshold=0.05) * 100
        da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
        print(f"  {h:>5}h  {len(grp):>6,}  {mr:>+9.4f}  {wr:>8.1f}%  {da_str:>9}")

    # Hét napja
    subsection("Hét napja")
    day_names = ["Hétfő", "Kedd", "Szerda", "Csütörtök", "Péntek"]
    print(f"  {'Nap':<12}  {'n':>6}  {'mean_ret':>9}  {'win_rate':>9}")
    print("  " + "-" * 42)
    for d in range(5):
        grp = df_valid[df_valid["weekday"] == d][col].dropna()
        if len(grp) < min_n:
            continue
        print(f"  {day_names[d]:<12}  {len(grp):>6,}  {grp.mean():>+9.4f}  {win_rate(grp.values)*100:>8.1f}%")


def analyze_per_ticker(df: pd.DataFrame, horizon: str, min_n: int = 30):
    col = f"fwd_ret_{horizon}"
    df_valid = df[df[col].notna()].copy()

    section(f"6. TICKER-SZINTŰ BONTÁS – {col}")

    print(f"\n  {'Ticker':<10} {'n':>7}  {'Pearson r':>10}  {'p':>7}  {'sig':>4}  "
          f"{'mean_ret':>9}  {'win_rate':>9}  {'dir_acc':>9}")
    print("  " + "-" * 80)

    for ticker in sorted(df_valid["ticker_symbol"].unique()):
        sub = df_valid[df_valid["ticker_symbol"] == ticker]
        scores = sub["combined_score"].dropna().values
        rets = sub[col].dropna().values
        # Csak ahol mindkét adat megvan
        both = sub[["combined_score", col]].dropna()
        if len(both) < min_n:
            continue
        x = both["combined_score"].values
        y = both[col].values
        r, p = pearson_r(x, y)
        sig = _sig_star(p)
        wr = win_rate(y) * 100
        mr = y.mean()
        da = direction_accuracy(x, y, threshold=0.05) * 100
        da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
        print(f"  {ticker:<10} {len(both):>7,}  {r:>+10.4f}  {p:>7.4f}  {sig}  "
              f"{mr:>+9.4f}  {wr:>8.1f}%  {da_str:>9}")


def analyze_existing_trades(conn: sqlite3.Connection, tickers: list):
    """A szimulált kereskedések 2h irányponcosságának mélyebb elemzése."""
    section("7. ARCHIVE SZIMULÁLT KERESKEDÉSEK ELEMZÉSE")

    ph = ",".join("?" * len(tickers))
    df = pd.read_sql_query(f"""
        SELECT ticker_symbol, direction, exit_reason, pnl_percent, pnl_net_percent,
               combined_score, overall_confidence, is_real_trade,
               direction_2h_eligible, direction_2h_correct, direction_2h_pct,
               duration_bars
        FROM archive_simulated_trades
        WHERE status='CLOSED' AND ticker_symbol IN ({ph})
    """, conn, params=tickers)

    df["dir_signed_score"] = np.where(
        df["direction"] == "LONG", df["combined_score"], -df["combined_score"]
    )

    print(f"\n  Összes zárt kereskedés: {len(df):,}")

    subsection("Exit reason megoszlás + átlagos P&L")
    print(f"  {'Exit reason':<25} {'n':>7}  {'mean_pnl%':>10}  {'win_rate':>9}")
    print("  " + "-" * 55)
    for reason, grp in df.groupby("exit_reason"):
        wr = (grp["pnl_percent"] > 0).mean() * 100
        print(f"  {reason:<25} {len(grp):>7,}  {grp['pnl_percent'].mean():>+10.4f}  {wr:>8.1f}%")

    subsection("2h iránypontosság – score quartilisek szerint")
    eligible = df[df["direction_2h_eligible"] == 1].copy()
    if len(eligible) < 10:
        print("  Nincs elég 2h-eligible adat.")
        return

    try:
        eligible["score_quartile"] = pd.qcut(
            eligible["dir_signed_score"], q=4,
            labels=["Q1 (leggyengébb)", "Q2", "Q3", "Q4 (legerősebb)"],
            duplicates="drop"
        )
    except Exception:
        eligible["score_quartile"] = pd.cut(
            eligible["dir_signed_score"],
            bins=4, labels=["Q1", "Q2", "Q3", "Q4"]
        )

    print(f"\n  {'Score quartilis':<20} {'n':>7}  {'dir_2h_acc':>11}  {'mean_2h_pct':>12}")
    print("  " + "-" * 54)
    for q, grp in eligible.groupby("score_quartile", observed=True):
        acc = grp["direction_2h_correct"].mean() * 100
        mean_pct = grp["direction_2h_pct"].mean()
        print(f"  {str(q):<20} {len(grp):>7,}  {acc:>10.1f}%  {mean_pct:>+12.4f}%")

    subsection("is_real_trade (|score|>=25) vs. alacsony score")
    for rt, label in [(1, "Valós trade (|score|>=25)"), (0, "Alacsony score")]:
        grp = df[df["is_real_trade"] == rt]
        el = grp[grp["direction_2h_eligible"] == 1]
        if len(el) < 5:
            continue
        acc = el["direction_2h_correct"].mean() * 100
        wr = (grp["pnl_percent"] > 0).mean() * 100
        print(f"  {label:<30} n={len(grp):>5,}  "
              f"2h_acc={acc:.1f}%  win_rate={wr:.1f}%  "
              f"mean_pnl={grp['pnl_percent'].mean():>+.4f}%")


def print_summary(df: pd.DataFrame, horizon: str, min_n: int = 30):
    col = f"fwd_ret_{horizon}"
    section("8. ÖSSZEFOGLALÓ RANGLISTA")

    df_valid = df[df[col].notna()].copy()

    features = [
        "combined_score", "sentiment_score", "technical_score", "risk_score",
        "rsi", "macd_hist", "bb_position", "mom_alignment",
        "above_sma200", "stoch_k", "atr_pct", "news_delay_min",
        "news_count_1h", "news_avg_score_1h", "abs_combined_score",
        "overall_confidence", "dist_to_support_pct", "dist_to_resistance_pct",
    ]

    print(f"\n  Korreláció a '{col}' kimenettel (Pearson r, abszolút érték szerint rendezve):\n")
    print(f"  {'#':>3}  {'Feature':<30} {'n':>7}  {'|r|':>7}  {'Spearman':>9}  {'p':>7}  {'sig':>4}")
    print("  " + "-" * 72)

    rows = []
    for feat in features:
        if feat not in df_valid.columns:
            continue
        sub = df_valid[[feat, col]].dropna()
        if len(sub) < min_n:
            continue
        x = sub[feat].values.astype(float)
        y = sub[col].values.astype(float)
        r, p = pearson_r(x, y)
        rho, _ = spearman_r(x, y)
        rows.append((abs(r), feat, len(sub), r, rho, p))

    rows.sort(reverse=True)
    for i, (absr, feat, n, r, rho, p) in enumerate(rows, 1):
        sig = _sig_star(p)
        print(f"  {i:>3}.  {feat:<30} {n:>7,}  {absr:>7.4f}  {rho:>+9.4f}  {p:>7.4f}  {sig}")

    # Legígéretesebb kombinációk
    print()
    subsection("Megállapítások")

    sig_feats = [(feat, r, p) for _, feat, n, r, rho, p in rows if p < 0.05]
    if sig_feats:
        print(f"\n  Szignifikáns (p<0.05) feature-ök: {len(sig_feats)}")
        for feat, r, p in sig_feats[:5]:
            dir_lbl = "pozitív" if r > 0 else "negatív"
            print(f"    • {feat}: r={r:+.4f} ({dir_lbl} összefüggés, p={p:.4f})")
    else:
        print("\n  Egyetlen feature sem mutat szignifikáns korrelációt az összes signal esetén.")
        print("  -> Érdemes ticker-enként és szűkített (US óra) szubszeten vizsgálni!")

    highly_sig = [(feat, r, p) for feat, r, p in sig_feats if p < 0.01]
    if highly_sig:
        print(f"\n  Erősen szignifikáns (p<0.01): {len(highly_sig)}")
        for feat, r, p in highly_sig:
            print(f"    • {feat}: r={r:+.4f}  p={p:.4f}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TrendSignal korreláció-elemzés")
    parser.add_argument("--ticker", nargs="+", default=None,
                        help="Ticker(ek), pl. AAPL MSFT (default: minden US ticker)")
    parser.add_argument("--horizon", default="2h",
                        choices=["1h", "2h", "4h", "1d"],
                        help="Fő forward return horizont (default: 2h)")
    parser.add_argument("--us-only", action="store_true", default=True,
                        help="Csak US piaci óra signalok (13:30-20:00 UTC)")
    parser.add_argument("--min-n", type=int, default=30,
                        help="Minimális elemszám egy csoporthoz (default: 30)")
    parser.add_argument("--skip-news-timing", action="store_true", default=False,
                        help="Hír-timing analízis kihagyása (gyorsabb futás)")
    args = parser.parse_args()

    print("=" * 78)
    print("  TrendSignal — Korreláció-keresési elemzés")
    print(f"  Dátum: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 78)

    conn = sqlite3.connect(DB_PATH)

    # Tickers
    all_us = ["AAPL", "AMZN", "GOOGL", "IBM", "META", "MSFT", "NVDA", "TSLA"]
    tickers = args.ticker if args.ticker else all_us
    print(f"\n  Betöltés: {', '.join(tickers)}")

    # Adatbetöltés
    print("  [1/5] Archive signals betöltése...")
    df = load_signals(conn, tickers)
    print(f"         {len(df):,} signal")

    print("  [2/5] Árfolyam adatok betöltése (15m)...")
    price_map = load_price_map(conn, tickers)
    print(f"         {sum(len(v) for v in price_map.values()):,} 15m gyertya")

    print("  [3/5] Napi árak betöltése (1d)...")
    daily_map = load_daily_price_map(conn, tickers)

    print("  [4/5] Forward return számítás...")
    df = compute_forward_returns(df, price_map, daily_map)
    fwd_ok = df["fwd_ret_2h"].notna().sum()
    print(f"         2h forward return: {fwd_ok:,} db ({fwd_ok/len(df)*100:.1f}%)")

    if not args.skip_news_timing:
        print("  [5/5] Hír-timing adatok betöltése...")
        news_df = load_news_timing(conn, tickers)
        print(f"         {len(news_df):,} archív hír")
        df = add_news_timing(df, news_df)
    else:
        print("  [5/5] Hír-timing kihagyva (--skip-news-timing)")

    # Feature engineering
    df = engineer_features(df)

    # US piaci óra szűrő
    if args.us_only:
        us_mask = df["signal_timestamp"].apply(is_us_market_hours)
        n_before = len(df)
        df = df[us_mask].copy()
        print(f"\n  US piaci óra szűrő: {n_before:,} -> {len(df):,} signal")

    # ─── Elemzések ───────────────────────────────────────────────────────────
    analyze_data_quality(df, tickers)
    analyze_univariate(df, args.horizon, args.min_n)
    analyze_score_buckets(df, args.horizon, args.min_n)
    analyze_interactions(df, args.horizon, args.min_n)
    analyze_time_patterns(df, args.horizon, args.min_n)
    analyze_per_ticker(df, args.horizon, args.min_n)
    analyze_existing_trades(conn, tickers)
    print_summary(df, args.horizon, args.min_n)

    conn.close()

    print("\n" + "=" * 78)
    print("  KÉSZ")
    print("  Tipp: futtasd más horizontokra is:")
    print("    python one_offs/correlation_analysis.py --horizon 1h")
    print("    python one_offs/correlation_analysis.py --horizon 4h")
    print("    python one_offs/correlation_analysis.py --horizon 1d")
    print("    python one_offs/correlation_analysis.py --ticker NVDA --horizon 2h")
    print("=" * 78)


if __name__ == "__main__":
    main()
