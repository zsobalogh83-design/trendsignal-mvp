"""
Alpaca historikus adatok tömeges letöltése

Letölti az összes US ticker árfolyamadatát az összes használt intervallumra,
2 évre visszamenőleg, és elmenti a price_data_alpaca táblába.

Futtatás:
    python fetch_alpaca_history.py

A kulcsokat a .env fájlba kell beírni:
    ALPACA_API_KEY=PKxxxxxxxxxx
    ALPACA_API_SECRET=xxxxxxxxxx
"""

import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

load_dotenv()

from src.alpaca_collector import fetch_and_save

# ── Konfiguráció ───────────────────────────────────────────────────────────────

DB_PATH = "trendsignal.db"

# 2 év visszamenőleg
END   = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
START = END - timedelta(days=365 * 2)

# A kódbázisban használt intervallumok (utils.py alapján)
INTERVALS = ["5m", "15m", "1h", "1d"]

# ── Tickers betöltése DB-ből (csak US piac) ────────────────────────────────────

def get_us_tickers(db_path: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol FROM tickers
        WHERE market NOT LIKE '%BET%'
          AND market NOT LIKE '%B_T%'
          AND symbol NOT LIKE '%.BD'
        ORDER BY symbol
    """)
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()
    return symbols

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    api_key    = os.environ.get("ALPACA_API_KEY", "").strip()
    api_secret = os.environ.get("ALPACA_API_SECRET", "").strip()

    if not api_key or not api_secret:
        print("HIBA: Hianyzo Alpaca kulcsok!")
        print("  Ird be a .env fajlba:")
        print("    ALPACA_API_KEY=PKxxxxxxxxxx")
        print("    ALPACA_API_SECRET=xxxxxxxxxx")
        sys.exit(1)

    symbols = get_us_tickers(DB_PATH)
    if not symbols:
        print("HIBA: Nincsenek US tickerek az adatbazisban!")
        sys.exit(1)

    print(f"Tickerek ({len(symbols)}): {', '.join(symbols)}")
    print(f"Idoszak: {START.date()} -> {END.date()}")
    print(f"Intervallumok: {', '.join(INTERVALS)}")
    print("-" * 60)

    grand_total = 0

    for interval in INTERVALS:
        print(f"\n{'=' * 60}")
        print(f"INTERVALLUM: {interval}")
        print(f"{'=' * 60}")

        results = fetch_and_save(
            symbols=symbols,
            interval=interval,
            start=START,
            end=END,
            api_key=api_key,
            api_secret=api_secret,
            db_path=DB_PATH,
            feed="iex",
        )
        grand_total += sum(results.values())

    print(f"\n{'=' * 60}")
    print(f"KESZ! Osszes betoltott sor: {grand_total}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
