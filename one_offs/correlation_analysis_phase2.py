"""
TrendSignal - Korreláció-elemzés Phase 2: Mélyanalízis
=======================================================

Phase 1 főbb leletei alapján:
  1. combined_score NEGATÍVAN korrelál a hozammal -> inverzió vizsgálat
  2. Erős SELL signalok (score<=-65) 64.9% iránypontossággal -> ez jó, miért rontja az eredményt?
  3. OPPOSING_SIGNAL exit: 29.5% win rate -> az exitjelek rontják a rendszert
  4. dist_to_resistance: legerősebb predictor (+0.076)
  5. A modell score-kvartilisek mentén EGYFORMA iránypontosságot mutat

Ez a script mélyebben elemzi:
  A) BUY vs SELL szeparált analízis (külön-külön milyen minőségűek?)
  B) Score inverzió teszt (mi lenne ha megfordítjuk a jeleket?)
  C) Időbeli stabilitás (30 napos gördülő pontosság)
  D) OPPOSING_SIGNAL dinamika (a kivezető jel helyes volt-e?)
  E) Volatilitás rezsim (high-vol vs low-vol piac)
  F) Score-komponens dekompozíció (mikor van igaza a sentiment vs technical-nak?)
  G) Legfontosabb szegmens azonosítása (hol a legjobb és legrosszabb subpopuláció?)

Futtatás:
    python one_offs/correlation_analysis_phase2.py
    python one_offs/correlation_analysis_phase2.py --ticker NVDA
    python one_offs/correlation_analysis_phase2.py --horizon 4h > results_phase2.txt
"""

import sqlite3
import math
import argparse
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import numpy as np
import pandas as pd

DB_PATH = "trendsignal.db"


# ─────────────────────────────────────────────────────────────────────────────
# Statisztikai segédek
# ─────────────────────────────────────────────────────────────────────────────

def _t_to_p(t_stat: float, df: int) -> float:
    z = abs(t_stat) * (1 - 1 / (4 * max(df, 1)))
    return min(1.0, 2.0 * 0.5 * math.erfc(z / math.sqrt(2)))


def pearson_r(x: np.ndarray, y: np.ndarray):
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
    return round(r, 4), round(_t_to_p(t, n - 2), 4)


def spearman_r(x: np.ndarray, y: np.ndarray):
    rx = pd.Series(x).rank().values.astype(float)
    ry = pd.Series(y).rank().values.astype(float)
    return pearson_r(rx, ry)


def _sig_star(p: float) -> str:
    if p < 0.001: return "***"
    if p < 0.01:  return "** "
    if p < 0.05:  return "*  "
    return "   "


def direction_accuracy(signals: np.ndarray, returns: np.ndarray, threshold: float = 0.05) -> float:
    mask = np.abs(returns) > threshold
    if mask.sum() < 5:
        return float("nan")
    return float((np.sign(signals[mask]) == np.sign(returns[mask])).mean())


def win_rate(y: np.ndarray) -> float:
    if len(y) == 0:
        return float("nan")
    return float((y > 0).mean())


def section(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def subsection(title: str):
    print(f"\n--- {title} ---")


# ─────────────────────────────────────────────────────────────────────────────
# Adatbetöltés
# ─────────────────────────────────────────────────────────────────────────────

def load_signals(conn, tickers):
    ph = ",".join("?" * len(tickers))
    df = pd.read_sql_query(f"""
        SELECT id, ticker_symbol, signal_timestamp, decision, strength,
               combined_score, sentiment_score, technical_score, risk_score,
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


def load_15m_prices(conn, tickers):
    ph = ",".join("?" * len(tickers))
    rows = conn.execute(f"""
        SELECT ticker_symbol, timestamp, close
        FROM price_data WHERE interval='15m' AND ticker_symbol IN ({ph})
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
        SELECT ticker_symbol, timestamp, close
        FROM price_data WHERE interval='1d' AND ticker_symbol IN ({ph})
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
        SELECT ast.*, asig.combined_score as signal_combined_score,
               asig.sentiment_score as signal_sentiment,
               asig.technical_score as signal_technical,
               asig.risk_score as signal_risk,
               asig.rsi as signal_rsi,
               asig.atr_pct as signal_atr_pct,
               asig.sma_200 as signal_sma200,
               asig.close_price as signal_close
        FROM archive_simulated_trades ast
        LEFT JOIN archive_signals asig ON ast.archive_signal_id = asig.id
        WHERE ast.ticker_symbol IN ({ph}) AND ast.status = 'CLOSED'
        ORDER BY ast.ticker_symbol, ast.entry_time
    """, conn, params=tickers)
    for col in ["entry_time", "exit_time"]:
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Forward return számítás
# ─────────────────────────────────────────────────────────────────────────────

def _find_after(bars, target_dt):
    lo, hi = 0, len(bars) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if bars[mid][0] < target_dt:
            lo = mid + 1
        else:
            hi = mid - 1
    return bars[lo][1] if lo < len(bars) else None


def _find_before_or_at(bars, target_dt):
    lo, hi, result = 0, len(bars) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if bars[mid][0] <= target_dt:
            result = bars[mid][1]
            lo = mid + 1
        else:
            hi = mid - 1
    return result


def compute_forward_returns(df, pm_15m, pm_1d, horizons_bars):
    """horizons_bars: dict label -> n_bars (None = next day)"""
    cols = {h: [] for h in horizons_bars}
    for row in df.itertuples():
        bars = pm_15m.get(row.ticker_symbol, [])
        p0 = _find_after(bars, row.signal_timestamp)
        if p0 is None or p0 == 0:
            for h in cols:
                cols[h].append(float("nan"))
            continue
        for h, nb in horizons_bars.items():
            if nb is None:
                daily = pm_1d.get(row.ticker_symbol, [])
                next_day = (row.signal_timestamp + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0)
                p1 = _find_after(daily, next_day)
            else:
                target = row.signal_timestamp + timedelta(minutes=15 * nb)
                p1 = _find_before_or_at(bars, target)
            cols[h].append((p1 - p0) / p0 * 100 if p1 and p0 > 0 else float("nan"))
    for h, vals in cols.items():
        df = df.copy()
        df[f"fwd_{h}"] = vals
    return df


def is_us_hours(dt):
    if pd.isna(dt):
        return False
    return dt.weekday() < 5 and (13 * 60 + 30) <= (dt.hour * 60 + dt.minute) < 20 * 60


# ─────────────────────────────────────────────────────────────────────────────
# A) BUY vs SELL szeparált analízis
# ─────────────────────────────────────────────────────────────────────────────

def analyze_buy_vs_sell(df, horizon):
    col = f"fwd_{horizon}"
    section(f"A) BUY vs SELL SZEPARÁLT ANALÍZIS  [{col}]")

    print(f"\n  Kérdés: a BUY és SELL signalok külön-külön helyes irányba mutatnak-e?")
    print(f"  Várható: BUY -> pozitív return, SELL -> negatív return\n")

    header = f"  {'Csoport':<40} {'n':>7}  {'mean_ret':>9}  {'win_rate':>9}  {'dir_acc':>9}  {'r':>7}  {'p':>7}  {'sig':>4}"
    print(header)
    print("  " + "-" * 95)

    groups = [
        ("Összes signal",                   df[col].notna()),
        (" BUY signalok (score>0)",         (df["decision"] == "BUY") & df[col].notna()),
        ("  BUY WEAK (25-50)",              (df["decision"] == "BUY") & (df["combined_score"].between(25, 50)) & df[col].notna()),
        ("  BUY MODERATE (50-65)",          (df["decision"] == "BUY") & (df["combined_score"].between(50, 65)) & df[col].notna()),
        ("  BUY STRONG (>=65)",             (df["decision"] == "BUY") & (df["combined_score"] >= 65) & df[col].notna()),
        (" SELL signalok (score<0)",        (df["decision"] == "SELL") & df[col].notna()),
        ("  SELL WEAK (-50..-25)",          (df["decision"] == "SELL") & (df["combined_score"].between(-50, -25)) & df[col].notna()),
        ("  SELL MODERATE (-65..-50)",      (df["decision"] == "SELL") & (df["combined_score"].between(-65, -50)) & df[col].notna()),
        ("  SELL STRONG (<=-65)",           (df["decision"] == "SELL") & (df["combined_score"] <= -65) & df[col].notna()),
        (" HOLD signalok",                  (df["decision"] == "HOLD") & df[col].notna()),
    ]

    for label, mask in groups:
        sub = df[mask]
        if len(sub) < 30:
            print(f"  {label:<40} {'n<30':>7}")
            continue
        y = sub[col].values
        x = sub["combined_score"].values
        r, p = pearson_r(x, y)
        sig = _sig_star(p)
        wr = win_rate(y) * 100
        mr = y.mean()
        # Iránypontosság: BUY-nál score>0, SELL-nél score<0 - a score-t használjuk jelként
        da = direction_accuracy(x, y, threshold=0.05) * 100
        da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
        print(f"  {label:<40} {len(sub):>7,}  {mr:>+9.4f}  {wr:>8.1f}%  {da_str:>9}  {r:>+7.4f}  {p:>7.4f}  {sig}")

    # Spearman a SELL szegmensben
    subsection("Spearman ρ a SELL szegmensben (score < 0)")
    sell_df = df[(df["decision"] == "SELL") & df[col].notna()].copy()
    if len(sell_df) > 30:
        y = sell_df[col].values
        for feat in ["combined_score", "sentiment_score", "technical_score", "risk_score",
                     "rsi", "macd_hist", "atr_pct"]:
            if feat not in sell_df.columns:
                continue
            sub = sell_df[[feat, col]].dropna()
            if len(sub) < 30:
                continue
            rho, p = spearman_r(sub[feat].values.astype(float), sub[col].values.astype(float))
            print(f"  {feat:<30} rho={rho:>+7.4f}  p={p:.4f}  {_sig_star(p)}")


# ─────────────────────────────────────────────────────────────────────────────
# B) Score inverzió teszt
# ─────────────────────────────────────────────────────────────────────────────

def analyze_score_inversion(df, horizon):
    col = f"fwd_{horizon}"
    section(f"B) SCORE INVERZIÓ TESZT  [{col}]")

    print(f"\n  Kérdés: mi lenne, ha a combined_score előjelét megfordítjuk?")
    print(f"  Ha az inverzió jobb -> a modell FORDÍTVA ad jelet!\n")

    valid = df[df[col].notna()].copy()
    valid = valid[valid["decision"].isin(["BUY", "SELL"])].copy()
    valid["inverted_score"] = -valid["combined_score"]

    # Eredeti score iránypontossága
    x_orig = valid["combined_score"].values
    x_inv = valid["inverted_score"].values
    y = valid[col].values

    da_orig = direction_accuracy(x_orig, y, threshold=0.05) * 100
    da_inv = direction_accuracy(x_inv, y, threshold=0.05) * 100
    r_orig, p_orig = pearson_r(x_orig, y)
    r_inv, p_inv = pearson_r(x_inv, y)

    print(f"  {'Metrika':<35} {'Eredeti':>12}  {'Invertált':>12}")
    print("  " + "-" * 62)
    print(f"  {'Direction accuracy':<35} {da_orig:>11.1f}%  {da_inv:>11.1f}%")
    print(f"  {'Pearson r':<35} {r_orig:>+12.4f}  {r_inv:>+12.4f}")
    print(f"  {'p-érték':<35} {p_orig:>12.4f}  {p_inv:>12.4f}")

    # P&L szimuláció: ha a BUY/SELL jeleket felcseréljük
    print()
    subsection("Szimulált P&L: eredeti vs. invertált jelek")
    print(f"  {'Scenario':<35} {'mean_ret':>10}  {'win_rate':>10}  {'dir_acc':>10}")
    print("  " + "-" * 68)

    scenarios = [
        ("Eredeti jelek (BUY=long, SELL=short)",  valid["combined_score"]),
        ("Invertált jelek (BUY=short, SELL=long)", valid["inverted_score"]),
    ]
    for label, scores in scenarios:
        x = scores.values
        da = direction_accuracy(x, y, threshold=0.05) * 100
        # Szimulált hozam: ha long, vesszük y-t; ha short, -y-t
        sim_ret = np.where(x > 0, y, -y)
        wr = win_rate(sim_ret) * 100
        mr = sim_ret.mean()
        print(f"  {label:<35} {mr:>+10.4f}  {wr:>9.1f}%  {da:>9.1f}%")

    # Küszöb szerinti bontás
    subsection("Küszöb szerinti szimulált P&L (eredeti vs. invertált)")
    thresholds = [15, 25, 40, 50, 65]
    print(f"\n  {'Threshold':<12} {'n':>7}  {'Eredeti hozam':>14}  {'Invertált hozam':>16}  {'Jobb?':>6}")
    print("  " + "-" * 60)
    for thr in thresholds:
        mask = valid["abs_combined_score"].fillna(0) >= thr if "abs_combined_score" in valid else (
            valid["combined_score"].abs() >= thr)
        sub = valid[mask]
        if len(sub) < 30:
            continue
        xs = sub["combined_score"].values
        xs_inv = -xs
        ys = sub[col].values
        sim_orig = np.where(xs > 0, ys, -ys)
        sim_inv = np.where(xs_inv > 0, ys, -ys)
        mr_orig = sim_orig.mean()
        mr_inv = sim_inv.mean()
        winner = "INV" if mr_inv > mr_orig else "ORIG"
        print(f"  |score|>={thr:<5} {len(sub):>7,}  {mr_orig:>+14.4f}  {mr_inv:>+16.4f}  {winner:>6}")

    valid["abs_combined_score"] = valid["combined_score"].abs()


# ─────────────────────────────────────────────────────────────────────────────
# C) Időbeli stabilitás
# ─────────────────────────────────────────────────────────────────────────────

def analyze_temporal_stability(df, horizon, window_days=30):
    col = f"fwd_{horizon}"
    section(f"C) IDŐBELI STABILITÁS  [{col}]  (gördülő {window_days} napos ablak)")

    valid = df[df[col].notna() & df["decision"].isin(["BUY", "SELL"])].copy()
    valid = valid.sort_values("signal_timestamp")
    valid["date"] = valid["signal_timestamp"].dt.date

    dates = sorted(valid["date"].unique())
    if len(dates) < window_days * 2:
        print("  Nincs elég adat az időbeli elemzéshez.")
        return

    print(f"\n  {'Időszak vége':<14}  {'n':>6}  {'dir_acc':>9}  {'mean_ret':>10}  {'win_rate':>9}  {'Pearson r':>10}")
    print("  " + "-" * 65)

    # Havi összesítők (gördülő ablak helyett)
    valid["ym"] = valid["signal_timestamp"].dt.to_period("M")
    monthly_results = []

    for ym, grp in valid.groupby("ym"):
        y = grp[col].values
        x = grp["combined_score"].values
        if len(grp) < 30:
            continue
        da = direction_accuracy(x, y, threshold=0.05) * 100
        wr = win_rate(y) * 100
        mr = y.mean()
        r, p = pearson_r(x, y)
        monthly_results.append((str(ym), len(grp), da, mr, wr, r, p))
        sig = _sig_star(p)
        da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
        print(f"  {str(ym):<14}  {len(grp):>6,}  {da_str:>9}  {mr:>+10.4f}  {wr:>8.1f}%  {r:>+10.4f}  {sig}")

    if len(monthly_results) >= 3:
        # Trend a dir_acc-ban
        das = [r[2] for r in monthly_results if not math.isnan(r[2])]
        if len(das) >= 3:
            slope, _ = np.polyfit(range(len(das)), das, 1)
            trend = "JAVULO" if slope > 0.2 else ("ROMLO" if slope < -0.2 else "STAGNALO")
            print(f"\n  Trend (dir_acc havonta): {slope:>+.3f}%/ho  -> {trend}")

        # Legjobb és legrosszabb honap
        by_da = sorted(monthly_results, key=lambda x: x[2] if not math.isnan(x[2]) else 0)
        print(f"\n  Legjobb honap:  {by_da[-1][0]}  dir_acc={by_da[-1][2]:.1f}%  mean_ret={by_da[-1][3]:+.4f}%")
        print(f"  Legrosszabb:    {by_da[0][0]}   dir_acc={by_da[0][2]:.1f}%  mean_ret={by_da[0][3]:+.4f}%")


# ─────────────────────────────────────────────────────────────────────────────
# D) OPPOSING_SIGNAL dinamika
# ─────────────────────────────────────────────────────────────────────────────

def analyze_opposing_signal(df_trades, df_signals, pm_15m, horizon):
    col = f"fwd_{horizon}"
    section("D) OPPOSING_SIGNAL EXIT DINAMIKA")

    print("\n  Kérdés: amikor egy kereskedés OPPOSING_SIGNAL miatt zárul,")
    print("  az ellentétes jel valóban helyes irányba mutatott-e?\n")

    opp = df_trades[df_trades["exit_reason"] == "OPPOSING_SIGNAL"].copy()
    if len(opp) < 10:
        print("  Nincs elég OPPOSING_SIGNAL exit.")
        return

    print(f"  Összes OPPOSING_SIGNAL exit: {len(opp):,}")
    print(f"  Átlagos P&L: {opp['pnl_percent'].mean():+.4f}%")
    print(f"  Win rate: {(opp['pnl_percent'] > 0).mean()*100:.1f}%")

    # Az exit jel iránypontossága: az exit signalra nézzük a következő return-t
    subsection("Az exit jel irányának validálása")

    # Keressük meg az exit signalt
    if "exit_time" not in opp.columns:
        print("  Nincs exit_time oszlop.")
        return

    valid_count = 0
    correct_exit = 0
    exit_rets = []

    for row in opp.itertuples():
        ticker = row.ticker_symbol
        exit_dt = row.exit_time
        entry_price = row.entry_price
        exit_price = row.exit_price

        if pd.isna(exit_dt):
            continue

        bars = pm_15m.get(ticker, [])
        # Mekkora volt a hozam az exit pont után?
        # Az exit signal iránya = ellentéte az eredeti kereskedésnek
        original_dir = row.direction  # LONG vagy SHORT
        exit_signal_dir = "SHORT" if original_dir == "LONG" else "LONG"

        # Forward return az exit pontból
        n_bars = {"1h": 4, "2h": 8, "4h": 16}.get(horizon, 8)
        p0 = _find_after(bars, exit_dt)
        target = exit_dt + timedelta(minutes=15 * n_bars)
        p1 = _find_before_or_at(bars, target)

        if p0 and p1 and p0 > 0:
            exit_fwd_ret = (p1 - p0) / p0 * 100
            # A kilépési jel helyes volt-e?
            # Ha az exit SHORT: a kilépés után az ár kellett volna leessen
            # Ha az exit LONG: a kilépés után az ár kellett volna felemelkedjen
            correct = (exit_signal_dir == "SHORT" and exit_fwd_ret < 0) or \
                      (exit_signal_dir == "LONG" and exit_fwd_ret > 0)
            correct_exit += int(correct)
            exit_rets.append(exit_fwd_ret)
            valid_count += 1

    if valid_count > 0:
        print(f"\n  Vizsgált exit jelek: {valid_count:,}")
        print(f"  Exit jel helyes irányban: {correct_exit:,} ({correct_exit/valid_count*100:.1f}%)")
        exit_arr = np.array(exit_rets)
        print(f"  Átlagos hozam az exit pont után ({horizon}): {exit_arr.mean():>+.4f}%")
        print(f"  Ez azt jelenti: az exit jel {'HELYES' if correct_exit/valid_count > 0.55 else 'HELYTELEN'} irányba mutatott.")

    # Exit típus + irány kombináció elemzés
    subsection("Exit reason x Direction P&L bontás")
    print(f"\n  {'Exit reason':<25} {'Direction':>10}  {'n':>7}  {'mean_pnl%':>10}  {'win_rate':>9}")
    print("  " + "-" * 65)
    for reason, r_grp in df_trades.groupby("exit_reason"):
        for direction, d_grp in r_grp.groupby("direction"):
            if len(d_grp) < 10:
                continue
            wr = (d_grp["pnl_percent"] > 0).mean() * 100
            mr = d_grp["pnl_percent"].mean()
            print(f"  {reason:<25} {direction:>10}  {len(d_grp):>7,}  {mr:>+10.4f}  {wr:>8.1f}%")


# ─────────────────────────────────────────────────────────────────────────────
# E) Volatilitás rezsim elemzés
# ─────────────────────────────────────────────────────────────────────────────

def analyze_volatility_regime(df, horizon):
    col = f"fwd_{horizon}"
    section(f"E) VOLATILITÁS REZSIM ELEMZÉS  [{col}]")

    print("\n  Kérdés: a modell jobban működik magas vagy alacsony volatilitásban?")
    print("  (ATR% alapján szegmentálva)\n")

    valid = df[df[col].notna() & df["atr_pct"].notna()].copy()
    if len(valid) < 100:
        print("  Nincs elég adat.")
        return

    try:
        valid["atr_quartile"] = pd.qcut(
            valid["atr_pct"], q=4,
            labels=["Q1 (alacsony vol)", "Q2", "Q3", "Q4 (magas vol)"],
            duplicates="drop"
        )
    except Exception:
        valid["atr_quartile"] = pd.cut(valid["atr_pct"], bins=4,
                                        labels=["Q1", "Q2", "Q3", "Q4"])

    print(f"  {'ATR quartilis':<22}  {'n':>7}  {'dir_acc':>9}  {'mean_ret':>10}  {'Pearson r':>10}  {'p':>7}  {'sig':>4}")
    print("  " + "-" * 72)

    for q, grp in valid.groupby("atr_quartile", observed=True):
        y = grp[col].values
        x = grp["combined_score"].values
        both = grp[["combined_score", col]].dropna()
        if len(both) < 30:
            continue
        r, p = pearson_r(both["combined_score"].values, both[col].values)
        da = direction_accuracy(x[:len(y)], y, threshold=0.05) * 100
        wr = win_rate(y) * 100
        da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
        print(f"  {str(q):<22}  {len(grp):>7,}  {da_str:>9}  {grp[col].mean():>+10.4f}  {r:>+10.4f}  {p:>7.4f}  {_sig_star(p)}")

    # ATR percentilis körüli összefüggés részleteiben
    subsection("Score x Volatilitás interakció")
    high_vol = valid[valid["atr_quartile"].isin(["Q3", "Q4 (magas vol)", "Q4"])]
    low_vol  = valid[valid["atr_quartile"].isin(["Q1 (alacsony vol)", "Q2", "Q1"])]

    for label, sub in [("Magas volatilitás (Q3-Q4)", high_vol),
                        ("Alacsony volatilitás (Q1-Q2)", low_vol)]:
        sub_valid = sub[sub["decision"].isin(["BUY", "SELL"])]
        if len(sub_valid) < 30:
            continue
        buy = sub_valid[sub_valid["decision"] == "BUY"][col].dropna()
        sell = sub_valid[sub_valid["decision"] == "SELL"][col].dropna()
        print(f"\n  {label}:")
        print(f"    BUY  signals: n={len(buy):,}  mean_ret={buy.mean():+.4f}%  win_rate={win_rate(buy.values)*100:.1f}%")
        print(f"    SELL signals: n={len(sell):,}  mean_ret={sell.mean():+.4f}%  win_rate={win_rate(sell.values)*100:.1f}%")


# ─────────────────────────────────────────────────────────────────────────────
# F) Score-komponens dekompozíció
# ─────────────────────────────────────────────────────────────────────────────

def analyze_component_decomposition(df, horizon):
    col = f"fwd_{horizon}"
    section(f"F) SCORE-KOMPONENS DEKOMPOZÍCIÓ  [{col}]")

    print("\n  Kérdés: sentiment vs. technical vs. risk — melyik komponens")
    print("  mutat helyes irányt, és melyik rontja el az összesített jelet?\n")

    valid = df[df[col].notna() & df["decision"].isin(["BUY", "SELL"])].copy()
    if len(valid) < 30:
        print("  Nincs elég adat.")
        return

    y = valid[col].values

    print(f"  {'Komponens':<30} {'Pearson r':>10}  {'Spearman':>10}  {'p':>8}  {'sig':>4}  {'dir_acc':>9}")
    print("  " + "-" * 78)

    components = [
        ("combined_score",    "Kombinált score (70/20/10)"),
        ("sentiment_score",   "Sentiment score (70% súly)"),
        ("technical_score",   "Technical score (20% súly)"),
        ("risk_score",        "Risk score (10% súly)"),
        ("overall_confidence","Overall confidence"),
    ]
    for feat, label in components:
        sub = valid[[feat, col]].dropna()
        if len(sub) < 30:
            continue
        x = sub[feat].values.astype(float)
        yy = sub[col].values.astype(float)
        r, p = pearson_r(x, yy)
        rho, _ = spearman_r(x, yy)
        da = direction_accuracy(x, yy, threshold=0.05) * 100
        da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
        print(f"  {label:<30} {r:>+10.4f}  {rho:>+10.4f}  {p:>8.4f}  {_sig_star(p)}  {da_str:>9}")

    # Conflict analízis: mikor mond mást a sentiment és a technical
    subsection("Sentiment-Technical konflikt esetei")
    valid["sent_pos"] = valid["sentiment_score"] > 0
    valid["tech_pos"]  = valid["technical_score"] > 0

    cases = [
        ("Sentiment+ & Technical+",  valid["sent_pos"] & valid["tech_pos"]),
        ("Sentiment+ & Technical-",  valid["sent_pos"] & ~valid["tech_pos"]),
        ("Sentiment- & Technical+",  ~valid["sent_pos"] & valid["tech_pos"]),
        ("Sentiment- & Technical-",  ~valid["sent_pos"] & ~valid["tech_pos"]),
    ]

    print(f"\n  {'Eset':<35}  {'n':>7}  {'mean_ret':>10}  {'win_rate':>9}  {'dir_acc':>9}")
    print("  " + "-" * 72)

    for label, mask in cases:
        sub = valid[mask & valid[col].notna()]
        if len(sub) < 30:
            continue
        y = sub[col].values
        x = sub["combined_score"].values
        da = direction_accuracy(x, y, threshold=0.05) * 100
        da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
        print(f"  {label:<35}  {len(sub):>7,}  {sub[col].mean():>+10.4f}  {win_rate(y)*100:>8.1f}%  {da_str:>9}")

    # Melyik komponens predikál jobban csak BUY esetén
    subsection("BUY signalokon belül: sentiment vs technical iránypontossága")
    buy_only = valid[valid["decision"] == "BUY"].copy()
    if len(buy_only) > 30:
        for feat, label in [("sentiment_score", "Sentiment"), ("technical_score", "Technical")]:
            sub = buy_only[[feat, col]].dropna()
            x = sub[feat].values.astype(float)
            y_b = sub[col].values.astype(float)
            da = direction_accuracy(x, y_b, threshold=0.05) * 100
            r, p = pearson_r(x, y_b)
            print(f"  {label:<20} r={r:>+7.4f}  dir_acc={da:.1f}%  p={p:.4f}  {_sig_star(p)}")


# ─────────────────────────────────────────────────────────────────────────────
# G) Legjobb subpopuláció azonosítása
# ─────────────────────────────────────────────────────────────────────────────

def analyze_best_segments(df, horizon):
    col = f"fwd_{horizon}"
    section(f"G) LEGJOBB ÉS LEGROSSZABB SZEGMENSEK  [{col}]")

    print("\n  Cél: megtalálni azt a signal-kombinációt, ahol a dir_acc > 55%,")
    print("  és legalább 200 mintán alapul (statisztikailag megbízható).\n")

    valid = df[df[col].notna()].copy()
    valid["abs_score"] = valid["combined_score"].abs()

    # Grid search: feature párok kombinációi
    filters = {
        "decision=BUY":              valid["decision"] == "BUY",
        "decision=SELL":             valid["decision"] == "SELL",
        "STRONG":                    valid["strength"] == "STRONG",
        "above_sma200":              valid["close_price"] > valid["sma_200"].fillna(0),
        "below_sma200":              valid["close_price"] < valid["sma_200"].fillna(1e9),
        "RSI<40":                    valid["rsi"] < 40,
        "RSI>60":                    valid["rsi"] > 60,
        "RSI 40-60":                 valid["rsi"].between(40, 60),
        "MACD_hist>0":               valid["macd_hist"] > 0,
        "MACD_hist<0":               valid["macd_hist"] < 0,
        "|score|>40":                valid["abs_score"] > 40,
        "|score|>60":                valid["abs_score"] > 60,
        "low_vol (atr_pct<1)":       valid["atr_pct"] < 1,
        "high_vol (atr_pct>2)":      valid["atr_pct"] > 2,
        "news_count>=3":             valid["news_count"] >= 3,
    }

    # Egyszerű (nem páros) szegmensek
    results = []
    for label, mask in filters.items():
        sub = valid[mask][col].dropna()
        if len(sub) < 100:
            continue
        x = valid[mask]["combined_score"].dropna().values
        y = sub.values
        da = direction_accuracy(x[:len(y)], y, threshold=0.05) * 100
        mr = y.mean()
        wr = win_rate(y) * 100
        results.append((da, label, len(sub), mr, wr))

    results.sort(reverse=True)

    print(f"  {'Szegmens':<35}  {'n':>7}  {'dir_acc':>9}  {'mean_ret':>10}  {'win_rate':>9}")
    print("  " + "-" * 75)
    for da, label, n, mr, wr in results:
        da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
        flag = "  <<< FIGYELEMRE MELTO" if (not math.isnan(da) and da > 54) else ""
        print(f"  {label:<35}  {n:>7,}  {da_str:>9}  {mr:>+10.4f}  {wr:>8.1f}%{flag}")

    # Legjobb páros kombinációk
    subsection("Páros kombinációk (legígéretesebb párok)")

    pair_filters = [
        ("SELL + above_sma200",        (valid["decision"] == "SELL") & (valid["close_price"] > valid["sma_200"].fillna(0))),
        ("SELL + RSI>60",              (valid["decision"] == "SELL") & (valid["rsi"] > 60)),
        ("SELL + MACD_hist<0",         (valid["decision"] == "SELL") & (valid["macd_hist"] < 0)),
        ("SELL + |score|>40",          (valid["decision"] == "SELL") & (valid["abs_score"] > 40)),
        ("BUY + RSI<40",               (valid["decision"] == "BUY")  & (valid["rsi"] < 40)),
        ("BUY + MACD_hist>0",          (valid["decision"] == "BUY")  & (valid["macd_hist"] > 0)),
        ("BUY + below_sma200",         (valid["decision"] == "BUY")  & (valid["close_price"] < valid["sma_200"].fillna(1e9))),
        ("BUY + |score|>40",           (valid["decision"] == "BUY")  & (valid["abs_score"] > 40)),
        ("SELL + STRONG + RSI>60",     (valid["decision"] == "SELL") & (valid["strength"] == "STRONG") & (valid["rsi"] > 60)),
        ("SELL + STRONG + MACD<0",     (valid["decision"] == "SELL") & (valid["strength"] == "STRONG") & (valid["macd_hist"] < 0)),
        ("BUY + STRONG + RSI<40",      (valid["decision"] == "BUY")  & (valid["strength"] == "STRONG") & (valid["rsi"] < 40)),
        ("BUY + STRONG + MACD>0",      (valid["decision"] == "BUY")  & (valid["strength"] == "STRONG") & (valid["macd_hist"] > 0)),
        ("SELL + RSI>60 + MACD<0",     (valid["decision"] == "SELL") & (valid["rsi"] > 60) & (valid["macd_hist"] < 0)),
        ("BUY + RSI<40 + MACD>0",      (valid["decision"] == "BUY")  & (valid["rsi"] < 40) & (valid["macd_hist"] > 0)),
    ]

    pair_results = []
    for label, mask in pair_filters:
        sub = valid[mask][col].dropna()
        if len(sub) < 50:
            continue
        x = valid[mask]["combined_score"].dropna().values
        y = sub.values
        da = direction_accuracy(x[:len(y)], y, threshold=0.05) * 100
        mr = y.mean()
        wr = win_rate(y) * 100
        pair_results.append((da, label, len(sub), mr, wr))

    pair_results.sort(reverse=True)
    print(f"\n  {'Kombináció':<40}  {'n':>7}  {'dir_acc':>9}  {'mean_ret':>10}  {'win_rate':>9}")
    print("  " + "-" * 80)
    for da, label, n, mr, wr in pair_results:
        da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
        flag = "  <<< ERŐS" if (not math.isnan(da) and da > 55) else ""
        print(f"  {label:<40}  {n:>7,}  {da_str:>9}  {mr:>+10.4f}  {wr:>8.1f}%{flag}")


# ─────────────────────────────────────────────────────────────────────────────
# H) Ticker-szintű rejtett összefüggések
# ─────────────────────────────────────────────────────────────────────────────

def analyze_ticker_deep(df, horizon):
    col = f"fwd_{horizon}"
    section(f"H) TICKER-SZINTŰ MÉLYANALÍZIS  [{col}]")

    print("\n  Egyes tickerekre lehet, hogy erősebb összefüggés van —")
    print("  nézzük meg, hogy melyik komponens melyik tickeren jó!\n")

    valid = df[df[col].notna()].copy()

    features = ["combined_score", "sentiment_score", "technical_score", "risk_score"]

    for ticker in sorted(valid["ticker_symbol"].unique()):
        sub = valid[valid["ticker_symbol"] == ticker]
        if len(sub) < 100:
            continue
        print(f"\n  [{ticker}]  n={len(sub):,}")
        for feat in features:
            fsub = sub[[feat, col]].dropna()
            if len(fsub) < 30:
                continue
            x = fsub[feat].values.astype(float)
            y = fsub[col].values.astype(float)
            r, p = pearson_r(x, y)
            da = direction_accuracy(x, y, threshold=0.05) * 100
            da_str = f"{da:.1f}%" if not math.isnan(da) else " N/A"
            print(f"    {feat:<25} r={r:>+7.4f}  dir_acc={da_str}  p={p:.4f}  {_sig_star(p)}")


# ─────────────────────────────────────────────────────────────────────────────
# Összefoglaló diagnózis
# ─────────────────────────────────────────────────────────────────────────────

def print_diagnosis(df, horizon):
    col = f"fwd_{horizon}"
    section("DIAGNÓZIS ÉS KÖVETKEZTETÉSEK")

    valid = df[df[col].notna()].copy()
    buy = valid[valid["decision"] == "BUY"]
    sell = valid[valid["decision"] == "SELL"]

    buy_da = direction_accuracy(buy["combined_score"].values, buy[col].values, 0.05) * 100 if len(buy) > 30 else float("nan")
    sell_da = direction_accuracy(sell["combined_score"].values, sell[col].values, 0.05) * 100 if len(sell) > 30 else float("nan")
    all_da = direction_accuracy(valid["combined_score"].values, valid[col].values, 0.05) * 100 if len(valid) > 30 else float("nan")

    print(f"""
  ALAP METRIKÁK ({col}):
    Összes signal dir_acc:  {all_da:.1f}%  (random = 50%)
    BUY signalok dir_acc:   {buy_da:.1f}%
    SELL signalok dir_acc:  {sell_da:.1f}%
""")

    print("  FONTOSABB MEGÁLLAPÍTÁSOK:")

    r_combined, p_combined = pearson_r(
        valid["combined_score"].dropna().values,
        valid[col][valid["combined_score"].notna()].values
    )

    findings = []

    if r_combined < -0.005 and p_combined < 0.05:
        findings.append(("KRITIKUS", "A combined_score NEGATÍVAN korrelal a hozammal "
                         f"(r={r_combined:+.4f}, p={p_combined:.4f}). "
                         "A jel iranya FORDITOTT! Ez a legalapvetobb problema."))
    elif abs(r_combined) < 0.02:
        findings.append(("FIGYELMEZTES", "A combined_score lenyegeben NEM korrelaL a hozammal "
                         f"(r={r_combined:+.4f}). A jel teljesen hasznalhatatlan."))

    if not math.isnan(sell_da) and sell_da > 55:
        findings.append(("LEHETOSEG", f"A SELL signalok {sell_da:.1f}%-os iranypontossaggal birnak. "
                         "Ez hasznosithato! Szeljuk le a SELL jeleket es vizsgaljuk kulon."))

    if not math.isnan(buy_da) and buy_da < 48:
        findings.append(("KRITIKUS", f"A BUY signalok csak {buy_da:.1f}%-os iranypontosak. "
                         "Ez elmarad a random 50%-tol is! A BUY logika fordított."))

    for level, msg in findings:
        print(f"\n  [{level}]")
        for i in range(0, len(msg), 78):
            print(f"    {msg[i:i+78]}")

    print(f"""
  JAVASOLT KÖVETKEZŐ LÉPÉSEK:
    1. Ha combined_score negatív korrelációjú -> vizsgáld a score súlyokat
       (sentiment 70%: ez dominálja, és lehet hogy fordítva van kódolva)
    2. Ha SELL pontosabb mint BUY -> érdemes SELL-only stratégiát tesztelni
    3. Az OPPOSING_SIGNAL exitek P&L-t rombolnak -> tiltsd le ezt az exit módot
    4. A dist_to_resistance_pct a legjobb predictor -> ezt kell erősebben súlyozni
    5. Időbeli instabilitás esetén -> fontold meg a modell periodikus újratanítását
""")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", nargs="+", default=None)
    parser.add_argument("--horizon", default="2h", choices=["1h", "2h", "4h", "1d"])
    parser.add_argument("--min-n", type=int, default=30)
    args = parser.parse_args()

    print("=" * 80)
    print("  TrendSignal — Phase 2 Mélyanalízis")
    print(f"  Dátum: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)

    all_us = ["AAPL", "AMZN", "GOOGL", "IBM", "META", "MSFT", "NVDA", "TSLA"]
    tickers = args.ticker if args.ticker else all_us

    conn = sqlite3.connect(DB_PATH)

    print(f"\n  Betöltés: {', '.join(tickers)}")
    print("  [1/4] Signalok...")
    df = load_signals(conn, tickers)

    print("  [2/4] 15m árak...")
    pm_15m = load_15m_prices(conn, tickers)

    print("  [3/4] 1d árak...")
    pm_1d  = load_daily_prices(conn, tickers)

    print("  [4/4] Kereskedések...")
    df_trades = load_trades(conn, tickers)
    conn.close()

    # Forward returns
    print("  Forward return számítás...")
    horizons = {"1h": 4, "2h": 8, "4h": 16, "1d": None}
    df = compute_forward_returns(df, pm_15m, pm_1d, horizons)

    # US piaci szűrő
    us_mask = df["signal_timestamp"].apply(is_us_hours)
    df = df[us_mask].copy()
    print(f"  US piaci szűrő után: {len(df):,} signal\n")

    # Elemzések
    h = args.horizon
    analyze_buy_vs_sell(df, h)
    analyze_score_inversion(df, h)
    analyze_temporal_stability(df, h)
    analyze_opposing_signal(df_trades, df, pm_15m, h)
    analyze_volatility_regime(df, h)
    analyze_component_decomposition(df, h)
    analyze_best_segments(df, h)
    analyze_ticker_deep(df, h)
    print_diagnosis(df, h)

    print("\n" + "=" * 80)
    print("  KÉSZ")
    print("  Futtasd különböző horizonokra:")
    print("    python one_offs/correlation_analysis_phase2.py --horizon 4h > phase2_4h.txt")
    print("    python one_offs/correlation_analysis_phase2.py --horizon 1d > phase2_1d.txt")
    print("=" * 80)


if __name__ == "__main__":
    main()
