"""
Signal Direction Analysis — 2H Price Window
============================================
Vizsgálja, hogy a signalok mekkora arányban találják el a helyes árirányt
a belépéstől számított 2 órán belül.

Szabályok:
- Belépés = signal.created_at + 15 perc
- Csak kereskedési órákban lévő belépések (hétvége / after-hours kizárva)
- Kilépési referencia: entry_time + 2 óra, vagy piacvégi zárás ha közelebb
- Score klaszterek: 5 pontonként (|score| >= 15-től)

Futtatás:
    cd <project_root>
    python analyze_signal_direction.py
"""

import sys
import os
# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models import Signal, PriceData


# ============================================================
# HELPERS
# ============================================================

def is_weekend(utc_time: datetime) -> bool:
    return utc_time.weekday() >= 5


def is_trading_hours(utc_time: datetime, symbol: str) -> bool:
    """BÉT: 08:00–16:00 UTC  |  US: 14:30–21:00 UTC"""
    t = utc_time.hour + utc_time.minute / 60.0
    if symbol.endswith('.BD'):
        return 8.0 <= t < 16.0
    else:
        return 14.5 <= t < 21.0


def market_close_utc(ref_time: datetime, symbol: str) -> datetime:
    """Napi piacvégi időpont UTC-ben (ugyanaz a nap mint ref_time)."""
    if symbol.endswith('.BD'):
        return ref_time.replace(hour=16, minute=0, second=0, microsecond=0)
    else:
        return ref_time.replace(hour=21, minute=0, second=0, microsecond=0)


def get_nearest_candle(db: Session, symbol: str, target: datetime,
                       tolerance_min: int = 20):
    """
    Visszaadja a target időponthoz legközelebbi 5m gyertyát
    a ±tolerance_min ablakban. Ha nincs adat, None-t ad vissza.
    """
    t_low  = target - timedelta(minutes=tolerance_min)
    t_high = target + timedelta(minutes=tolerance_min)

    candles = db.query(PriceData).filter(
        PriceData.ticker_symbol == symbol,
        PriceData.interval == '5m',
        PriceData.timestamp >= t_low,
        PriceData.timestamp <= t_high
    ).all()

    if not candles:
        return None

    # Legközelebb a target-hez
    return min(candles, key=lambda c: abs((c.timestamp - target).total_seconds()))


def score_bin(score_abs: float) -> str:
    """
    |score| → '15-20', '20-25', ... '95-100', '100+'
    Minimum 15 (alatta nem hívjuk meg).
    """
    lower = int(score_abs // 5) * 5
    if lower >= 100:
        return '100+'
    return f"{lower}-{lower + 5}"


def print_table(header: list, rows: list, col_widths: list):
    """Egyszerű táblázat kiíró."""
    fmt = "  " + "  ".join(f"{{:>{w}}}" for w in col_widths)
    sep = "  " + "  ".join("-" * w for w in col_widths)
    print(fmt.format(*header))
    print(sep)
    for row in rows:
        print(fmt.format(*row))


# ============================================================
# MAIN ANALYSIS
# ============================================================

def main():
    db = SessionLocal()

    try:
        print("=" * 72)
        print("  SIGNAL DIRECTION ANALYSIS — 2H PRICE WINDOW")
        print("=" * 72)

        # ----------------------------------------------------------
        # 1. SIGNALOK BETÖLTÉSE (|score| >= 15, nem HOLD)
        # ----------------------------------------------------------
        raw_signals = (
            db.query(Signal)
            .filter(
                Signal.combined_score.isnot(None),
                Signal.decision != 'HOLD'
            )
            .order_by(Signal.created_at)
            .all()
        )

        # Csak |score| >= 15
        signals = [s for s in raw_signals if abs(s.combined_score) >= 15]
        print(f"\n  Betoltott signal (|score|>=15): {len(signals)}")

        # ----------------------------------------------------------
        # 2. ITERÁCIÓ
        # ----------------------------------------------------------
        records      = []
        skip_hours   = 0   # Hétvége / after-hours belépés
        skip_entry   = 0   # Nincs entry candle
        skip_exit    = 0   # Nincs exit candle
        skip_window  = 0   # <5 perc kereskedési idő maradt

        for sig in signals:
            score   = sig.combined_score
            symbol  = sig.ticker_symbol
            entry_t = sig.created_at + timedelta(minutes=15)

            # --- SZŰRŐ: csak kereskedési órákban lévő belépések ---
            if is_weekend(entry_t) or not is_trading_hours(entry_t, symbol):
                skip_hours += 1
                continue

            # --- BELÉPÉSI GYERTYA ---
            entry_candle = get_nearest_candle(db, symbol, entry_t, tolerance_min=20)
            if not entry_candle:
                skip_entry += 1
                continue
            entry_price = entry_candle.close

            # --- KILÉPÉSI IDŐ: entry + 2h, de max EOD - 5 perc ---
            eod = market_close_utc(entry_t, symbol)
            raw_exit_t  = entry_t + timedelta(hours=2)
            exit_t      = min(raw_exit_t, eod - timedelta(minutes=5))

            if (exit_t - entry_t).total_seconds() < 300:   # < 5 perc maradt
                skip_window += 1
                continue

            hit_eod = raw_exit_t > eod

            # --- KILÉPÉSI GYERTYA ---
            exit_candle = get_nearest_candle(db, symbol, exit_t, tolerance_min=20)
            if not exit_candle:
                skip_exit += 1
                continue
            exit_price = exit_candle.close

            # --- IRÁNY ÉS HELYESSÉG ---
            direction = 'BUY' if score >= 15 else 'SELL'
            pct_change = (exit_price - entry_price) / entry_price * 100

            if direction == 'BUY':
                correct = exit_price > entry_price
            else:
                correct = exit_price < entry_price

            # Normalizált mozgás: pozitív = helyes irány
            norm_move = pct_change if direction == 'BUY' else -pct_change

            # Tényleges ablak percben
            window_min = (exit_t - entry_t).total_seconds() / 60

            records.append({
                'signal_id'   : sig.id,
                'symbol'      : symbol,
                'created_at'  : sig.created_at,
                'score'       : score,
                'score_abs'   : abs(score),
                'score_bin'   : score_bin(abs(score)),
                'strength'    : sig.strength or 'N/A',
                'direction'   : direction,
                'entry_price' : entry_price,
                'exit_price'  : exit_price,
                'pct_change'  : pct_change,
                'norm_move'   : norm_move,
                'correct'     : correct,
                'window_min'  : window_min,
                'hit_eod'     : hit_eod,
                'stop_loss'   : sig.stop_loss,
                'take_profit' : sig.take_profit,
            })

        print(f"  Kizárva (after-hours):     {skip_hours}")
        print(f"  Kizárva (nincs entry adat):{skip_entry}")
        print(f"  Kizárva (nincs exit adat): {skip_exit}")
        print(f"  Kizárva (<5 perc ablak):   {skip_window}")
        print(f"  Elemzett signalok:         {len(records)}")

        if not records:
            print("\n  ⚠️  Nincs elemezhető adat!")
            return

        df = pd.DataFrame(records)

        # ----------------------------------------------------------
        # 3. ÖSSZESÍTETT STATISZTIKA
        # ----------------------------------------------------------
        total   = len(df)
        correct = int(df['correct'].sum())
        wrong   = total - correct

        print(f"\n{'=' * 72}")
        print(f"  ÖSSZESÍTETT IRÁNYPRECIZITÁS")
        print(f"{'=' * 72}")
        print(f"  Összes elemzett signal :  {total}")
        print(f"  Helyes irány           :  {correct}  ({correct/total*100:.1f}%)")
        print(f"  Rossz irány            :  {wrong}  ({wrong/total*100:.1f}%)")
        print(f"  Átlag normalizált mozgás: {df['norm_move'].mean():+.3f}%")
        print(f"  Medián normalizált mozgás:{df['norm_move'].median():+.3f}%")
        print(f"  EOD-zárón alapuló exit :  {int(df['hit_eod'].sum())}  ({df['hit_eod'].mean()*100:.1f}%)")

        # ----------------------------------------------------------
        # 4. BUY vs SELL
        # ----------------------------------------------------------
        print(f"\n{'=' * 72}")
        print(f"  IRÁNY SZERINT (BUY / SELL)")
        print(f"{'=' * 72}")
        hdr = ['Irány', 'N', 'Helyes', 'Pontosság', 'Átlag mozgás']
        cw  = [6, 5, 7, 10, 13]
        rows = []
        for direction in ['BUY', 'SELL']:
            sub = df[df['direction'] == direction]
            if len(sub) == 0:
                continue
            acc = sub['correct'].mean() * 100
            avg = sub['norm_move'].mean()
            rows.append([direction, len(sub), int(sub['correct'].sum()),
                         f"{acc:.1f}%", f"{avg:+.3f}%"])
        print_table(hdr, rows, cw)

        # ----------------------------------------------------------
        # 5. SCORE BIN TÁBLÁZAT (5 pontonként)
        # ----------------------------------------------------------
        print(f"\n{'=' * 72}")
        print(f"  SCORE KLASZTEREK (5 pontonként, |score|)")
        print(f"{'=' * 72}")

        hdr = ['|Score|', 'N', 'BUY', 'SELL', 'Helyes', 'Pontosság', 'Átlag mozgás', 'Medián']
        cw  = [9, 5, 5, 5, 7, 10, 13, 9]

        all_bins = sorted(df['score_bin'].unique(),
                          key=lambda x: int(x.split('-')[0]) if x != '100+' else 100)
        rows = []
        for b in all_bins:
            sub   = df[df['score_bin'] == b]
            n     = len(sub)
            buy_n = int((sub['direction'] == 'BUY').sum())
            sel_n = int((sub['direction'] == 'SELL').sum())
            corr  = int(sub['correct'].sum())
            acc   = corr / n * 100
            avg   = sub['norm_move'].mean()
            med   = sub['norm_move'].median()
            rows.append([b, n, buy_n, sel_n, corr, f"{acc:.1f}%",
                         f"{avg:+.3f}%", f"{med:+.3f}%"])
        print_table(hdr, rows, cw)

        # ----------------------------------------------------------
        # 6. SZIMBÓLUM TÁBLÁZAT (min. 5 signal)
        # ----------------------------------------------------------
        print(f"\n{'=' * 72}")
        print(f"  SZIMBÓLUM SZERINT (min. 5 signal, pontosság szerint rendezve)")
        print(f"{'=' * 72}")

        hdr = ['Symbol', 'N', 'BUY', 'SELL', 'Helyes', 'Pontosság', 'Átlag mozgás']
        cw  = [10, 5, 5, 5, 7, 10, 13]
        rows = []
        sym_grp = (
            df.groupby('symbol')
            .agg(
                n        = ('correct', 'count'),
                buy_n    = ('direction', lambda x: (x == 'BUY').sum()),
                sell_n   = ('direction', lambda x: (x == 'SELL').sum()),
                corr     = ('correct', 'sum'),
                avg_move = ('norm_move', 'mean'),
            )
        )
        sym_grp['acc'] = sym_grp['corr'] / sym_grp['n'] * 100
        sym_grp = sym_grp.sort_values('acc', ascending=False)

        for sym, row in sym_grp[sym_grp['n'] >= 5].iterrows():
            rows.append([sym, int(row['n']), int(row['buy_n']), int(row['sell_n']),
                         int(row['corr']), f"{row['acc']:.1f}%",
                         f"{row['avg_move']:+.3f}%"])
        print_table(hdr, rows, cw)

        # ----------------------------------------------------------
        # 7. SIGNAL STRENGTH TÁBLÁZAT
        # ----------------------------------------------------------
        if df['strength'].notna().any():
            print(f"\n{'=' * 72}")
            print(f"  SIGNAL ERŐSSÉG SZERINT")
            print(f"{'=' * 72}")
            hdr = ['Strength', 'N', 'Helyes', 'Pontosság', 'Átlag mozgás']
            cw  = [10, 5, 7, 10, 13]
            rows = []
            for s in ['STRONG', 'MODERATE', 'WEAK', 'NEUTRAL', 'N/A']:
                sub = df[df['strength'] == s]
                if len(sub) < 3:
                    continue
                acc = sub['correct'].mean() * 100
                avg = sub['norm_move'].mean()
                rows.append([s, len(sub), int(sub['correct'].sum()),
                             f"{acc:.1f}%", f"{avg:+.3f}%"])
            print_table(hdr, rows, cw)

        # ----------------------------------------------------------
        # 8. MOZGÁS HISTOGRAM (normalizált: pozitív = helyes irány)
        # ----------------------------------------------------------
        print(f"\n{'=' * 72}")
        print(f"  ÁRELMOZGÁS ELOSZLÁS — 2H ABLAKBAN")
        print(f"  (pozitív = helyes irányba ment, negatív = rossz irány)")
        print(f"{'=' * 72}")

        bins   = [-999, -5, -3, -2, -1, -0.5, 0, 0.5, 1, 2, 3, 5, 999]
        labels = ['< -5%', '-5~-3%', '-3~-2%', '-2~-1%', '-1~-0.5%',
                  '-0.5~0%', '0~0.5%', '0.5~1%', '1~2%', '2~3%', '3~5%', '> 5%']

        df['move_bucket'] = pd.cut(df['norm_move'], bins=bins, labels=labels)
        counts = df['move_bucket'].value_counts()
        max_cnt = max(counts.values) if len(counts) > 0 else 1

        for lbl in labels:
            cnt  = int(counts.get(lbl, 0))
            bar  = '█' * int(cnt / max_cnt * 35)
            sign = '✓' if lbl.startswith('0') or lbl.startswith('0.5') \
                         or lbl.startswith('1') or lbl.startswith('2') \
                         or lbl.startswith('3') or lbl.startswith('> ') \
                       else '✗'
            print(f"  {sign} {lbl:>11}: {cnt:>4}  {bar}")

        # ----------------------------------------------------------
        # 9. SL / TP ELÉRÉS 2H-N BELÜL (exit_price alapján közelítve)
        # ----------------------------------------------------------
        df_st = df[(df['stop_loss'].notna()) & (df['take_profit'].notna())].copy()
        if len(df_st) > 0:
            def sltp_flags(row):
                if row['direction'] == 'BUY':
                    return pd.Series({
                        'hit_tp': row['exit_price'] >= row['take_profit'],
                        'hit_sl': row['exit_price'] <= row['stop_loss'],
                    })
                else:
                    return pd.Series({
                        'hit_tp': row['exit_price'] <= row['take_profit'],
                        'hit_sl': row['exit_price'] >= row['stop_loss'],
                    })

            df_st = df_st.join(df_st.apply(sltp_flags, axis=1))

            print(f"\n{'=' * 72}")
            print(f"  SL / TP ELÉRÉS 2H-N BELÜL  (exit_price vs szintek — közelítő)")
            print(f"{'=' * 72}")
            n_st = len(df_st)
            tp_n = int(df_st['hit_tp'].sum())
            sl_n = int(df_st['hit_sl'].sum())
            print(f"  Signalok SL/TP adattal  : {n_st}")
            print(f"  TP elérve 2h-n belül    : {tp_n:>4}  ({tp_n/n_st*100:.1f}%)")
            print(f"  SL elérve 2h-n belül    : {sl_n:>4}  ({sl_n/n_st*100:.1f}%)")
            print(f"  Sem SL sem TP           : {n_st-tp_n-sl_n:>4}  ({(n_st-tp_n-sl_n)/n_st*100:.1f}%)")

            # Breakdown by direction
            print()
            for d in ['BUY', 'SELL']:
                sub = df_st[df_st['direction'] == d]
                if len(sub) == 0:
                    continue
                print(f"    {d}: TP={int(sub['hit_tp'].sum())} ({sub['hit_tp'].mean()*100:.1f}%) "
                      f"| SL={int(sub['hit_sl'].sum())} ({sub['hit_sl'].mean()*100:.1f}%) "
                      f"| egyéb={int((~sub['hit_tp'] & ~sub['hit_sl']).sum())}")

        # ----------------------------------------------------------
        # ZÁRÓ
        # ----------------------------------------------------------
        print(f"\n{'=' * 72}")
        print(f"  ELEMZÉS KÉSZ  —  {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
        print(f"{'=' * 72}\n")

    finally:
        db.close()


if __name__ == '__main__':
    main()
