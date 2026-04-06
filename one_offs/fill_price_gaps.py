"""
TrendSignal - Price Data Gap Filler (yfinance)

Megkeresi a price_data táblában a hiányzó / csonka kereskedési napokat,
majd yfinance-on keresztül letölti a hiányzó barokat és közvetlenül
a price_data táblába menti.

Logika:
  - US tickers: NYSE/NASDAQ kereskedési napok (9:30-16:00 ET)
    Teljes nap = 26 bar (15m), 78 bar (5m), 7 bar (1h)
    Early close napok (júl 3, Black Friday, dec 24) = kevesebb bar — SKIP
  - BD tickers: kihagyva (BÉT adathoz yfinance más logika kell)
  - Teljes hiányos napok ÉS csonka napok egyaránt javítva
  - INSERT OR IGNORE → idempotens, bátran újrafuttatható

Futtatás:
    python one_offs/fill_price_gaps.py                # összes US ticker, összes interval
    python one_offs/fill_price_gaps.py --dry-run      # csak kijelzi a lyukakat
    python one_offs/fill_price_gaps.py --ticker NVDA  # csak egy ticker
    python one_offs/fill_price_gaps.py --interval 15m # csak egy interval
    python one_offs/fill_price_gaps.py --from 2026-03-01

Megjegyzés:
  yfinance intraday adat (5m, 15m) max ~60 napra visszamenőleg elérhető.
  1d és 1h adathoz nincs visszamenőleges limit.
"""

import os
import sys
import sqlite3
import time
from datetime import datetime, timedelta, date
from typing import List, Dict, Tuple

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yfinance as yf

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trendsignal.db")

# NYSE/NASDAQ holidays 2024-2026
US_HOLIDAYS = {
    # 2024
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27",
    "2024-06-19", "2024-07-04", "2024-09-02", "2024-11-28", "2024-12-25",
    # 2025
    "2025-01-01", "2025-01-09",  # Carter temetés (market closed)
    "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
    "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
    # 2026
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
    "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
}

# yfinance intraday max visszamenőleges napok
# 5m, 15m: ~60 nap; 1h: ~730 nap; 1d: korlátlan
YF_MAX_DAYS = {
    "5m":  58,
    "15m": 58,
    "1h":  729,
    "1d":  9999,
}

EXPECTED_BARS = {
    "5m":  78,
    "15m": 26,
    "1h":  7,
    "1d":  1,
}


def _is_early_close(d: str) -> bool:
    """July 3, Black Friday (Thanksgiving + 1 nap), Dec 24."""
    dt = datetime.strptime(d, "%Y-%m-%d")
    if dt.month == 7 and dt.day == 3:
        return True
    if dt.month == 12 and dt.day == 24:
        return True
    # Black Friday: Thanksgiving (nov 4. csüt = 22-28) utáni péntek = 23-29
    if dt.month == 11 and dt.weekday() == 4 and 23 <= dt.day <= 29:
        return True
    return False


def is_trading_day(d: str) -> bool:
    dt = datetime.strptime(d, "%Y-%m-%d")
    return dt.weekday() < 5 and d not in US_HOLIDAYS


# ── Gap detection ─────────────────────────────────────────────────────────────

def find_gaps(
    conn: sqlite3.Connection,
    ticker: str,
    interval: str,
    date_from: str,
    date_to: str,
) -> List[str]:
    """
    Visszaadja azokat a kereskedési napokat (YYYY-MM-DD), ahol a bar count
    kisebb az elvártnál — kivéve early close napokat és a mai napot.
    """
    expected = EXPECTED_BARS.get(interval, 26)
    today = date.today().isoformat()

    rows = conn.execute("""
        SELECT DATE(timestamp) as day, COUNT(*) as cnt
        FROM price_data
        WHERE ticker_symbol = ? AND interval = ?
          AND timestamp >= ? AND timestamp < ?
        GROUP BY DATE(timestamp)
    """, (ticker, interval, date_from, date_to)).fetchall()
    existing: Dict[str, int] = {r["day"]: r["cnt"] for r in rows}

    d = datetime.strptime(date_from, "%Y-%m-%d")
    end = datetime.strptime(date_to, "%Y-%m-%d")
    gaps = []

    while d <= end:
        ds = d.strftime("%Y-%m-%d")
        if is_trading_day(ds) and ds != today and not _is_early_close(ds):
            cnt = existing.get(ds, 0)
            if cnt < expected:
                gaps.append(ds)
        d += timedelta(days=1)

    return sorted(gaps)


# ── yfinance fetch ────────────────────────────────────────────────────────────

def fetch_yf_bars(
    symbol: str,
    interval: str,
    start: str,
    end: str,
) -> List[dict]:
    """
    Letölti a barokat yfinance-on keresztül a megadott dátumtartományra.
    start/end: 'YYYY-MM-DD' string (end exclusive)

    Returns: lista dict-ekkel (timestamp naive UTC, o, h, l, c, v)
    """
    try:
        df = yf.download(
            symbol,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
    except Exception as e:
        print(f"    yfinance hiba: {e}")
        return []

    if df is None or df.empty:
        return []

    # Flatten multi-level columns (yfinance v0.2+)
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)

    # Timezone → naive UTC
    if hasattr(df.index, "tz") and df.index.tz is not None:
        df.index = df.index.tz_convert("UTC").tz_localize(None)

    bars = []
    for ts, row in df.iterrows():
        try:
            bars.append({
                "t": ts.to_pydatetime(),
                "o": float(row["Open"]),
                "h": float(row["High"]),
                "l": float(row["Low"]),
                "c": float(row["Close"]),
                "v": int(row.get("Volume", 0)),
            })
        except Exception:
            continue

    return bars


# ── DB save ───────────────────────────────────────────────────────────────────

def save_bars(
    conn: sqlite3.Connection,
    symbol: str,
    interval: str,
    bars: List[dict],
) -> Tuple[int, int]:
    """INSERT OR IGNORE → price_data. Returns (inserted, skipped)."""
    if not bars:
        return 0, 0

    row = conn.execute("SELECT id FROM tickers WHERE symbol = ?", (symbol,)).fetchone()
    ticker_id = row["id"] if row else None

    inserted = skipped = 0
    for i, bar in enumerate(bars):
        ts = bar["t"]
        if isinstance(ts, datetime):
            ts = ts.replace(tzinfo=None)

        o, h, l, c, v = bar["o"], bar["h"], bar["l"], bar["c"], bar["v"]
        prev_c = bars[i - 1]["c"] if i > 0 else None
        price_change = round(c - prev_c, 6) if prev_c else None
        price_change_pct = round((c - prev_c) / prev_c * 100, 4) if prev_c else None

        try:
            conn.execute("""
                INSERT OR IGNORE INTO price_data
                    (ticker_id, ticker_symbol, timestamp, interval,
                     open, high, low, close, volume,
                     price_change, price_change_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ticker_id, symbol, ts, interval, o, h, l, c, v,
                  price_change, price_change_pct))
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    return inserted, skipped


# ── Helpers ───────────────────────────────────────────────────────────────────

def _group_to_ranges(days: List[str]) -> List[Tuple[str, str]]:
    """
    Szomszédos kereskedési napokat egy range-be csoportosítja.
    Max 14 nap egy range-ben.
    """
    if not days:
        return []

    MAX_SPAN = 14
    ranges = []
    start = days[0]
    prev = days[0]

    for d in days[1:]:
        span = (datetime.strptime(d, "%Y-%m-%d") -
                datetime.strptime(start, "%Y-%m-%d")).days
        gap = (datetime.strptime(d, "%Y-%m-%d") -
               datetime.strptime(prev, "%Y-%m-%d")).days

        if gap <= 5 and span <= MAX_SPAN:
            prev = d
        else:
            ranges.append((start, prev))
            start = d
            prev = d

    ranges.append((start, prev))
    return ranges


def _is_within_yf_limit(day_str: str, interval: str) -> bool:
    """Visszaadja, hogy a nap a yfinance visszamenőleges limitjén belül van-e."""
    max_days = YF_MAX_DAYS.get(interval, 9999)
    cutoff = (date.today() - timedelta(days=max_days)).isoformat()
    return day_str >= cutoff


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",  action="store_true", help="Csak kijelzi a lyukakat")
    parser.add_argument("--ticker",   help="Csak ezt a ticker-t")
    parser.add_argument("--interval", help="Csak ezt az intervallt (5m, 15m, 1h, 1d)")
    parser.add_argument("--from",     dest="date_from", default="2024-03-01",
                        help="Keresés kezdete YYYY-MM-DD (default: 2024-03-01)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Unique constraint ellenőrzés / létrehozás
    existing_indexes = [r[1] for r in conn.execute("PRAGMA index_list(price_data)").fetchall()]
    if "uq_price_data_symbol_ts_interval" not in existing_indexes:
        print("Unique constraint létrehozása price_data-n...")
        dup_count = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT ticker_symbol, timestamp, interval, COUNT(*) as cnt
                FROM price_data GROUP BY ticker_symbol, timestamp, interval HAVING cnt > 1
            )
        """).fetchone()[0]
        if dup_count > 0:
            print(f"  {dup_count} duplikát sor törlése...")
            conn.execute("""
                DELETE FROM price_data WHERE id NOT IN (
                    SELECT MIN(id) FROM price_data
                    GROUP BY ticker_symbol, timestamp, interval
                )
            """)
            conn.commit()
        conn.execute("""
            CREATE UNIQUE INDEX uq_price_data_symbol_ts_interval
            ON price_data (ticker_symbol, timestamp, interval)
        """)
        conn.commit()
        print("OK.")

    # Tickers
    if args.ticker:
        us_tickers = [args.ticker.upper()]
    else:
        us_tickers = [r["symbol"] for r in conn.execute(
            "SELECT symbol FROM tickers WHERE symbol NOT LIKE '%.BD' ORDER BY symbol"
        ).fetchall()]

    # 5m nem kell a visszamenoleges signal/trade szimulaciohoz
    intervals = [args.interval] if args.interval else ["15m", "1h", "1d"]

    date_from = args.date_from
    date_to   = date.today().isoformat()

    print(f"Gap elemzés: {date_from} → {date_to}")
    print(f"Tickerek: {', '.join(us_tickers)}")
    print(f"Intervallumok: {', '.join(intervals)}")
    if args.dry_run:
        print("[DRY-RUN] Csak elemzés, nem tölt le semmit.")
    print("=" * 60)

    total_inserted = 0
    total_skipped_old = 0

    for interval in intervals:
        max_days = YF_MAX_DAYS[interval]
        yf_cutoff = (date.today() - timedelta(days=max_days)).isoformat()

        print(f"\n--- {interval} (yfinance limit: {max_days} nap visszamenőleg = {yf_cutoff}) ---")

        for ticker in us_tickers:
            gaps = find_gaps(conn, ticker, interval, date_from, date_to)
            if not gaps:
                print(f"  {ticker}: OK")
                continue

            # Szétválasztjuk: elérhető vs. túl régi
            fetchable = [d for d in gaps if d >= yf_cutoff]
            too_old   = [d for d in gaps if d < yf_cutoff]

            status_parts = []
            if fetchable:
                status_parts.append(f"{len(fetchable)} letöltendő")
            if too_old:
                status_parts.append(f"{len(too_old)} túl régi (>{max_days} nap)")
            print(f"  {ticker}: {len(gaps)} gap — {', '.join(status_parts)}")

            if too_old:
                print(f"    ⚠️  yfinance-szal nem elérhető (túl régi): {too_old[:5]}{'...' if len(too_old)>5 else ''}")
                total_skipped_old += len(too_old)

            if args.dry_run or not fetchable:
                continue

            # Csoportosítás → letöltés
            ranges = _group_to_ranges(fetchable)
            for (r_from, r_to) in ranges:
                # end exclusive: r_to + 1 nap
                end_dt = (datetime.strptime(r_to, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

                print(f"    ⬇️  {ticker} {interval}: {r_from} → {r_to} ...", end=" ", flush=True)
                bars = fetch_yf_bars(ticker, interval, r_from, end_dt)

                if not bars:
                    print("0 bar (nincs adat)")
                    continue

                ins, skp = save_bars(conn, ticker, interval, bars)
                total_inserted += ins
                print(f"{len(bars)} bar → {ins} új, {skp} már megvolt")
                time.sleep(0.5)

    print("\n" + "=" * 60)
    if args.dry_run:
        print("[DRY-RUN] Kész. Futtasd --dry-run nélkül a tényleges letöltéshez.")
    else:
        print(f"Kész! {total_inserted} új sor a price_data táblában.")
    if total_skipped_old:
        print(f"⚠️  {total_skipped_old} gap túl régi a yfinance számára (intraday max ~60 nap).")
        print("   Ezekhez más adatforrás kell (pl. korábbi yfinance mentés vagy Alpaca paid feed).")
    conn.close()


if __name__ == "__main__":
    main()
