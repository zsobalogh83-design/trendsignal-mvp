"""
Alpha Vantage historikus news backfill – munkaheti ablakok

Strategia:
  - 1 API hivas = 1 munkahét (H-P), mind a 8 US ticker egyszerre
  - ~104 ablak 2 évre = ~5 nap a 25 req/nap free limiten
  - Resume: mar letoltott heteket athagyta
  - Automatikus varakozas ha napi limit eléré

Futtatás:
    python fetch_av_news_history.py
"""

from dotenv import load_dotenv
load_dotenv()

import os, sqlite3, sys
from datetime import datetime, timezone, timedelta
from src.alphavantage_news_backfill import backfill_workweeks

api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
if not api_key:
    print("HIBA: Hianyzo ALPHAVANTAGE_API_KEY a .env fajlban!")
    sys.exit(1)

# US tickerek a DB-ből (BÉT kizárva)
conn = sqlite3.connect("trendsignal.db")
cur = conn.cursor()
cur.execute("""
    SELECT symbol FROM tickers
    WHERE symbol NOT LIKE '%.BD'
      AND (market NOT LIKE '%BET%' AND market NOT LIKE '%B_T%')
    ORDER BY symbol
""")
symbols = [r[0] for r in cur.fetchall()]
conn.close()

print(f"Tickerek: {symbols}")

END   = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
START = END - timedelta(days=365 * 2)

backfill_workweeks(
    symbols=symbols,
    start=START,
    end=END,
    api_key=api_key,
    requests_per_day=24,   # 1-et meghagyjuk tartaléknak a napi 25-ből
)
