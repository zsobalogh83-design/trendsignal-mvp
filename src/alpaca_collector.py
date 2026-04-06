"""
Alpaca Historical Price Data Collector

Fetches OHLCV bars from Alpaca Markets API and saves to price_data table.

Usage (standalone):
    ALPACA_API_KEY=... ALPACA_API_SECRET=... python -m src.alpaca_collector

Usage (from code):
    from src.alpaca_collector import fetch_and_save
    from datetime import datetime, timezone

    fetch_and_save(
        symbols=["AAPL", "TSLA", "NVDA"],
        interval="1d",
        start=datetime(2022, 1, 1, tzinfo=timezone.utc),
        end=datetime(2025, 1, 1, tzinfo=timezone.utc),
        api_key="...",
        api_secret="...",
    )

Supported intervals (same as yfinance convention):
    1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo

Notes:
    - Only US stocks are supported (Alpaca covers NYSE/NASDAQ/etc.)
    - BÉT tickers (e.g. OTP.BD) are NOT supported
    - Free tier uses IEX feed; set feed="sip" if you have a live/paid account
    - Timestamps stored as naive UTC (matches existing price_data convention)
"""

import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

import requests

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Constants ─────────────────────────────────────────────────────────────────

ALPACA_BASE_URL = "https://data.alpaca.markets/v2"

# yfinance interval → Alpaca timeframe
INTERVAL_MAP = {
    "1m":  "1Min",
    "5m":  "5Min",
    "15m": "15Min",
    "30m": "30Min",
    "1h":  "1Hour",
    "1d":  "1Day",
    "1wk": "1Week",
    "1mo": "1Month",
}


# ── Table setup ───────────────────────────────────────────────────────────────

def create_table(db_path: str = "trendsignal.db") -> None:
    """Ensures the unique index exists on price_data (no-op if already present)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_price_data_symbol_ts_interval
            ON price_data (ticker_symbol, timestamp, interval);
    """)
    conn.commit()
    conn.close()
    print("✅ price_data table ready")


# ── Alpaca API ────────────────────────────────────────────────────────────────

def fetch_alpaca_bars(
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    api_key: str,
    api_secret: str,
    feed: str = "iex",
) -> list[dict]:
    """
    Fetch OHLCV bars from Alpaca Market Data API with automatic pagination.

    Args:
        symbol:     Ticker symbol (e.g. "AAPL")
        interval:   yfinance-style interval ("1m", "5m", "15m", "1h", "1d", ...)
        start/end:  UTC datetime range (timezone-aware)
        api_key:    Alpaca API Key ID
        api_secret: Alpaca API Secret Key
        feed:       "iex" (free) or "sip" (paid/live account)

    Returns:
        List of raw bar dicts from Alpaca API
    """
    alpaca_tf = INTERVAL_MAP.get(interval)
    if not alpaca_tf:
        raise ValueError(
            f"Unsupported interval '{interval}'. "
            f"Supported: {list(INTERVAL_MAP.keys())}"
        )

    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
    }

    url = f"{ALPACA_BASE_URL}/stocks/{symbol}/bars"
    bars: list[dict] = []
    next_page_token = None

    while True:
        params = {
            "timeframe": alpaca_tf,
            "start":     start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end":       end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "limit":     10000,
            "feed":      feed,
            "sort":      "asc",
        }
        if next_page_token:
            params["page_token"] = next_page_token

        resp = requests.get(url, headers=headers, params=params, timeout=30)

        if resp.status_code == 403:
            raise PermissionError(
                f"Alpaca 403 – check API keys or try feed='iex' instead of '{feed}'"
            )
        if resp.status_code == 422:
            detail = resp.json()
            raise ValueError(f"Alpaca 422 for {symbol}: {detail}")

        resp.raise_for_status()
        data = resp.json()

        batch = data.get("bars") or []
        bars.extend(batch)

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break

        time.sleep(0.05)   # stay well under rate limits

    return bars


# ── DB persistence ────────────────────────────────────────────────────────────

def save_bars(
    symbol: str,
    interval: str,
    bars: list[dict],
    db_path: str = "trendsignal.db",
) -> int:
    """
    Save Alpaca bars to price_data table.

    Returns:
        Number of rows inserted
    """
    if not bars:
        print(f"   ⚠️  No bars for {symbol}")
        return 0

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Resolve ticker_id (optional FK – may be NULL for symbols not in tickers table)
    cur.execute("SELECT id FROM tickers WHERE symbol = ?", (symbol,))
    row = cur.fetchone()
    ticker_id = row[0] if row else None

    inserted = 0
    skipped = 0

    for i, bar in enumerate(bars):
        # Parse ISO 8601 timestamp → naive UTC
        ts_str = bar["t"]
        if ts_str.endswith("Z"):
            ts = datetime.fromisoformat(ts_str[:-1]).replace(tzinfo=timezone.utc)
        else:
            ts = datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        ts_naive = ts.replace(tzinfo=None)

        o, h, l, c, v = bar["o"], bar["h"], bar["l"], bar["c"], bar["v"]

        prev_close = bars[i - 1]["c"] if i > 0 else None
        price_change = round(c - prev_close, 6) if prev_close is not None else None
        price_change_pct = (
            round((c - prev_close) / prev_close * 100, 4)
            if prev_close else None
        )

        try:
            cur.execute(
                """
                INSERT INTO price_data
                    (ticker_id, ticker_symbol, timestamp, interval,
                     open, high, low, close, volume,
                     price_change, price_change_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ticker_id, symbol, ts_naive, interval,
                 o, h, l, c, v, price_change, price_change_pct),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1    # duplicate (unique index hit)

    conn.commit()
    conn.close()

    print(f"   ✅ {symbol} ({interval}): {inserted} inserted, {skipped} skipped")
    return inserted


# ── Main entry point ──────────────────────────────────────────────────────────

def fetch_and_save(
    symbols: list[str],
    interval: str,
    start: datetime,
    end: datetime,
    api_key: str,
    api_secret: str,
    db_path: str = "trendsignal.db",
    feed: str = "iex",
) -> dict[str, int]:
    """
    Fetch historical bars from Alpaca and persist to price_data.

    Args:
        symbols:    List of ticker symbols (US stocks only)
        interval:   yfinance-style interval ("1m","5m","15m","1h","1d",...)
        start/end:  UTC datetime range (timezone-aware recommended)
        api_key:    Alpaca API Key ID
        api_secret: Alpaca API Secret Key
        db_path:    Path to SQLite database
        feed:       "iex" (free) or "sip" (paid)

    Returns:
        Dict {symbol: rows_inserted}
    """
    create_table(db_path)

    results: dict[str, int] = {}

    for symbol in symbols:
        print(f"\n📥 {symbol} [{interval}]  {start.date()} → {end.date()}")
        try:
            bars = fetch_alpaca_bars(symbol, interval, start, end, api_key, api_secret, feed)
            print(f"   📊 {len(bars)} bars fetched from Alpaca")
            inserted = save_bars(symbol, interval, bars, db_path)
            results[symbol] = inserted
        except Exception as e:
            print(f"   ❌ {symbol}: {e}")
            results[symbol] = 0

    total = sum(results.values())
    print(f"\n🏁 Done. Total inserted: {total} rows across {len(symbols)} symbols")
    return results


# ── Standalone run ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _key    = os.environ.get("ALPACA_API_KEY", "")
    _secret = os.environ.get("ALPACA_API_SECRET", "")

    if not _key or not _secret:
        print("❌ Set ALPACA_API_KEY and ALPACA_API_SECRET environment variables")
        raise SystemExit(1)

    fetch_and_save(
        symbols=["AAPL", "TSLA", "NVDA", "META", "AMZN"],
        interval="1d",
        start=datetime(2022, 1, 1, tzinfo=timezone.utc),
        end=datetime(2025, 1, 1, tzinfo=timezone.utc),
        api_key=_key,
        api_secret=_secret,
        feed="iex",
    )
