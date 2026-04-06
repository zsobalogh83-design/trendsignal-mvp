"""
TrendSignal - price_data_alpaca -> price_data merge

A price_data_alpaca tábla (US historikus Alpaca-letöltés, 2024-03-11..2026-03-06)
tartalmát beolvassa a price_data táblába, majd opcionálisan törli a forrástáblát.

Miért kellett két tábla?
  Az Alpaca-ból visszamenőleg letöltött adatok kerültek a price_data_alpaca-ba,
  a live price feed a price_data-ba. BD tickerek (MOL.BD, OTP.BD) csak price_data-ban
  vannak. Az archive_backtest_service eddig price_data_alpaca-t olvasott, ezért BD
  tickereken nem tudott dolgozni.

A merge után:
  - price_data tartalmaz MINDEN ticker MINDEN bar-ját
  - archive_backtest_service price_data-t olvas (már javítva)
  - price_data_alpaca törölhető

Overlap-ellenőrzés:
  A két tábla US tickereinél nincs timestamp-átfedés (alpaca max: 2026-03-06,
  price_data US min: 2026-01-27). Ha mégis lenne duplikátum (ticker+timestamp+interval),
  az INSERT OR IGNORE kihagyja.

Usage:
    python one_offs/merge_price_data_alpaca.py           # interaktív megerősítés
    python one_offs/merge_price_data_alpaca.py --confirm # prompt nélkül
    python one_offs/merge_price_data_alpaca.py --dry-run # csak számol, nem ír
    python one_offs/merge_price_data_alpaca.py --no-drop # merge után ne törölje az alpaca táblát
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trendsignal.db")

DRY_RUN  = "--dry-run"  in sys.argv
CONFIRM  = "--confirm"  in sys.argv
NO_DROP  = "--no-drop"  in sys.argv


def main():
    print("=" * 60)
    print("TrendSignal - price_data_alpaca -> price_data MERGE")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # ── Állapot-összefoglaló ─────────────────────────────────────────────────
    alpaca_count = conn.execute("SELECT COUNT(*) FROM price_data_alpaca").fetchone()[0]
    pd_count     = conn.execute("SELECT COUNT(*) FROM price_data").fetchone()[0]

    print(f"\nprice_data_alpaca : {alpaca_count:,} sor")
    print(f"price_data        : {pd_count:,} sor")

    # Overlap ellenőrzés
    overlap = conn.execute("""
        SELECT COUNT(*) FROM price_data p
        JOIN price_data_alpaca a
          ON p.ticker_symbol = a.ticker_symbol
         AND p.timestamp     = a.timestamp
         AND p.interval      = a.interval
    """).fetchone()[0]
    print(f"Duplikalt sorok   : {overlap:,}")

    # Alpaca ticker lista
    alpaca_tickers = [r[0] for r in conn.execute(
        "SELECT DISTINCT ticker_symbol FROM price_data_alpaca ORDER BY ticker_symbol"
    ).fetchall()]
    print(f"Alpaca tickerek   : {', '.join(alpaca_tickers)}")

    if DRY_RUN:
        print("\n[DRY-RUN] Nem ír semmit.")
        conn.close()
        return

    if not CONFIRM:
        print(f"\nFolytatod a merge-t? ({alpaca_count:,} sor -> price_data) [y/N] ", end="")
        ans = input().strip().lower()
        if ans != "y":
            print("Megszakítva.")
            conn.close()
            return

    # ── Unique constraint hozzáadása price_data-hoz (ha még nincs) ──────────
    existing_indexes = [r[1] for r in conn.execute("PRAGMA index_list(price_data)").fetchall()]
    uq_name = "uq_price_data_symbol_ts_interval"
    if uq_name not in existing_indexes:
        print(f"\nUnique constraint létrehozása: {uq_name} ...")
        # SQLite-ban CREATE UNIQUE INDEX-szel pótoljuk
        # Előbb ellenőrizzük, hogy a meglévő price_data-ban sincs duplikátum
        dup_count = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT ticker_symbol, timestamp, interval, COUNT(*) as cnt
                FROM price_data
                GROUP BY ticker_symbol, timestamp, interval
                HAVING cnt > 1
            )
        """).fetchone()[0]
        if dup_count > 0:
            print(f"  FIGYELEM: {dup_count} duplikált (ticker,timestamp,interval) kombináció van price_data-ban!")
            print("  Törlöm a duplikátumokat (csak a kisebb id-jűeket hagyom meg)...")
            conn.execute("""
                DELETE FROM price_data WHERE id NOT IN (
                    SELECT MIN(id) FROM price_data
                    GROUP BY ticker_symbol, timestamp, interval
                )
            """)
            conn.commit()
            print(f"  Duplikátumok törölve. Maradék: {conn.execute('SELECT COUNT(*) FROM price_data').fetchone()[0]:,}")

        conn.execute(f"""
            CREATE UNIQUE INDEX {uq_name}
            ON price_data (ticker_symbol, timestamp, interval)
        """)
        conn.commit()
        print(f"  OK: {uq_name} létrehozva.")
    else:
        print(f"\nUnique constraint már létezik: {uq_name}")

    # ── Merge: INSERT OR IGNORE ──────────────────────────────────────────────
    print(f"\nMerge indítása ({alpaca_count:,} sor)...")
    t0 = time.time()

    # Batch-enként, tickerenként (kevesebb memória, jobb progress)
    inserted_total = 0
    for ticker in alpaca_tickers:
        t_count = conn.execute(
            "SELECT COUNT(*) FROM price_data_alpaca WHERE ticker_symbol = ?", (ticker,)
        ).fetchone()[0]

        conn.execute("""
            INSERT OR IGNORE INTO price_data
                (ticker_id, ticker_symbol, timestamp, interval,
                 open, high, low, close, volume,
                 price_change, price_change_pct, fetched_at)
            SELECT
                ticker_id, ticker_symbol, timestamp, interval,
                open, high, low, close, volume,
                price_change, price_change_pct, fetched_at
            FROM price_data_alpaca
            WHERE ticker_symbol = ?
        """, (ticker,))
        conn.commit()

        inserted_ticker = conn.execute(
            "SELECT COUNT(*) FROM price_data WHERE ticker_symbol = ?", (ticker,)
        ).fetchone()[0]
        print(f"  {ticker}: {t_count:,} alpaca sor -> price_data mostani: {inserted_ticker:,}")
        inserted_total += t_count

    elapsed = time.time() - t0
    new_pd_count = conn.execute("SELECT COUNT(*) FROM price_data").fetchone()[0]
    print(f"\nMerge kész ({elapsed:.1f}s). price_data: {pd_count:,} -> {new_pd_count:,} sor")

    # ── Drop alpaca tábla ────────────────────────────────────────────────────
    if NO_DROP:
        print("\n[--no-drop] price_data_alpaca megmarad.")
    else:
        print("\nprice_data_alpaca törlése...")
        conn.execute("DROP TABLE price_data_alpaca")
        conn.commit()
        print("price_data_alpaca törölve.")

    print("\n[OK] Merge befejezve.")
    conn.close()


if __name__ == "__main__":
    main()
