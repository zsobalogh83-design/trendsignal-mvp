"""
Alpha Vantage News Sentiment – historikus backfill

Letölti az összes US ticker releváns híreit az elmúlt 2 évre és elmenti az
archive_news_items táblába. A tábla struktúra kompatibilis a backtest
pipeline-nal: minden cikk-ticker párhoz egy sor, AV sentiment adatokkal.

API limit (free tier): 25 req/nap  → a script automatikusan lassít ha közel
                        van a limithez, és leáll ha elérte.

Futtatás:
    python fetch_av_news_history.py

Response struktúra (Alpha Vantage NEWS_SENTIMENT):
    {
      "items": "50",
      "feed": [
        {
          "title": "...",
          "url": "...",
          "time_published": "20231015T143000",   ← YYYYMMDDTHHMMSS
          "authors": ["..."],
          "summary": "...",
          "source": "Zacks Commentary",
          "source_domain": "www.zacks.com",
          "category_within_source": "...",
          "banner_image": "...",
          "topics": [
            { "topic": "Earnings", "relevance_score": "0.9" }
          ],
          "overall_sentiment_score": 0.215,
          "overall_sentiment_label": "Somewhat-Bullish",
          "ticker_sentiment": [
            {
              "ticker": "AAPL",
              "relevance_score": "0.85",
              "ticker_sentiment_score": "0.2153",
              "ticker_sentiment_label": "Somewhat-Bullish"
            }
          ]
        }
      ]
    }
"""

import hashlib
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf_8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Konfiguráció ──────────────────────────────────────────────────────────────

AV_BASE_URL = "https://www.alphavantage.co/query"

# Minimum relevance_score, ami alatt nem mentjük el a cikket egy tickerhez
MIN_RELEVANCE = 0.1

# Ha a response pontosan limit db cikket ad vissza, lehet több is van →
# félbe osztjuk az időablakot (rekurzív)
MAX_WINDOW_ARTICLES = 1000


# ── Tábla létrehozás ──────────────────────────────────────────────────────────

def create_table(db_path: str = "trendsignal.db") -> None:
    """
    Létrehozza az archive_news_items táblát.

    Egy sor = egy (cikk × ticker) pár, ahol a ticker relevance_score > MIN_RELEVANCE.
    Így egy cikk több tickerhez is tartozhat (pl. AAPL–MSFT összehasonlítós cikk).
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS archive_news_items (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Azonosítók
            url_hash                VARCHAR(32) NOT NULL,
            ticker_symbol           VARCHAR(10) NOT NULL,

            -- Cikk metaadatok
            title                   TEXT NOT NULL,
            url                     TEXT NOT NULL,
            published_at            DATETIME NOT NULL,
            source                  VARCHAR(100),
            source_domain           VARCHAR(100),
            authors                 TEXT,           -- JSON tömb ["John Doe", ...]
            summary                 TEXT,
            category                VARCHAR(100),   -- category_within_source
            banner_image            TEXT,

            -- Témák (AV topics array)
            topics_json             TEXT,           -- [{"topic":"Earnings","relevance_score":"0.9"}, ...]

            -- Overall sentiment (cikk szintű)
            overall_sentiment_score FLOAT,
            overall_sentiment_label VARCHAR(30),

            -- Ticker-specifikus sentiment
            av_relevance_score      FLOAT,          -- mennyire releváns EZ a ticker
            av_sentiment_score      FLOAT,          -- ticker szintű sentiment [-1, +1]
            av_sentiment_label      VARCHAR(30),    -- Bearish / Bullish / stb.

            -- Összes ticker amit a cikk említ (teljes AV ticker_sentiment tömb)
            ticker_sentiment_json   TEXT,

            -- Melyik ticker lekérdezése hozta be ezt a sort (resume tracking)
            -- ticker_symbol = a cikkben említett ticker
            -- queried_ticker = amire az API hívás ment (lehet más, ha spillover)
            queried_ticker          VARCHAR(10),

            -- Metaadatok
            fetched_at              DATETIME DEFAULT CURRENT_TIMESTAMP,

            -- ── news_items kompatibilis mezők (LLM elemzéshez) ──────────────
            full_text               TEXT,           -- teljes cikkszöveg (ha elérhető)
            language                VARCHAR(10),    -- pl. "en"
            is_relevant             BOOLEAN,        -- relevancia flag
            sentiment_confidence    FLOAT,          -- sentiment confidence score
            is_duplicate            BOOLEAN DEFAULT 0,
            duplicate_of            INTEGER,        -- FK archive_news_items(id)
            cluster_id              VARCHAR(50),    -- cikk klaszter azonosító

            -- FinBERT sentiment
            finbert_score           FLOAT,

            -- LLM elemzés (azonos struktúra mint news_items)
            llm_score               FLOAT,          -- [-1, +1]
            llm_price_impact        VARCHAR(20),    -- BULLISH / BEARISH / NEUTRAL
            llm_impact_level        INTEGER,        -- 1-5
            llm_impact_duration     VARCHAR(20),    -- SHORT / MEDIUM / LONG
            llm_catalyst_type       VARCHAR(30),    -- EARNINGS / PRODUCT / MACRO / stb.
            llm_priced_in           BOOLEAN,        -- már árazva van-e
            llm_confidence          VARCHAR(10),    -- LOW / MEDIUM / HIGH
            llm_reason              VARCHAR(100),   -- rövid indoklás
            llm_latency_ms          INTEGER,        -- LLM válaszidő ms-ben

            -- Aktív score (FinBERT vagy LLM alapján)
            active_score            FLOAT,
            active_score_source     VARCHAR(10),    -- "finbert" / "llm" / "av"

            -- Dedup: (cikk × ticker) egyedi
            UNIQUE (url_hash, ticker_symbol)
        );

        CREATE INDEX IF NOT EXISTS ix_archive_news_ticker_symbol
            ON archive_news_items (ticker_symbol);
        CREATE INDEX IF NOT EXISTS ix_archive_news_published_at
            ON archive_news_items (published_at);
        CREATE INDEX IF NOT EXISTS ix_archive_news_url_hash
            ON archive_news_items (url_hash);
        CREATE INDEX IF NOT EXISTS ix_archive_news_ticker_published
            ON archive_news_items (ticker_symbol, published_at);
        CREATE INDEX IF NOT EXISTS ix_archive_news_queried_ticker
            ON archive_news_items (queried_ticker);
    """)
    conn.commit()
    conn.close()
    print("[OK] archive_news_items tabla kesz")


# ── Alpha Vantage API hívás ───────────────────────────────────────────────────

def _av_request(
    tickers: list[str],
    time_from: datetime,
    time_to: datetime,
    api_key: str,
    sort: str = "EARLIEST",
    limit: int = 1000,
) -> dict:
    """
    Egy API hívás az AV NEWS_SENTIMENT végponthoz.

    Returns:
        A teljes API response dict, vagy {} hiba esetén.

    Raises:
        RuntimeError: ha napi API limit elérve
    """
    params = {
        "function":  "NEWS_SENTIMENT",
        "tickers":   ",".join(tickers),
        "time_from": time_from.strftime("%Y%m%dT%H%M"),
        "time_to":   time_to.strftime("%Y%m%dT%H%M"),
        "sort":      sort,
        "limit":     limit,
        "apikey":    api_key,
    }

    resp = requests.get(AV_BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Limit / authentication hiba detektálás
    if "Note" in data:
        raise RuntimeError(f"AV rate limit: {data['Note']}")
    if "Information" in data:
        raise RuntimeError(f"AV limit/auth: {data['Information']}")

    return data


def fetch_window(
    tickers: list[str],
    time_from: datetime,
    time_to: datetime,
    api_key: str,
    _depth: int = 0,
) -> list[dict]:
    """
    Lekéri az összes cikket egy időablakra.
    Ha a visszakapott cikkek száma == MAX_WINDOW_ARTICLES, az ablakot
    félbefelezi (bináris felosztás), hogy ne maradjon ki cikk.

    Returns:
        Lista az összes cikkből az adott ablakban.
    """
    if _depth > 6:  # max rekurzió – ~1.5 óra ablak 2 napos kezdőből
        print(f"   [WARN] Max rekurzio mélysége elérve: {time_from} - {time_to}")
        return []

    data = _av_request(tickers, time_from, time_to, api_key)
    feed = data.get("feed") or []

    if len(feed) < MAX_WINDOW_ARTICLES:
        return feed

    # Teljes – félbevágjuk az időablakot
    mid = time_from + (time_to - time_from) / 2
    print(f"   [SPLIT] {len(feed)} cikk → ablak felosztás {time_from.date()} / {mid.date()} / {time_to.date()}")
    left  = fetch_window(tickers, time_from, mid,     api_key, _depth + 1)
    right = fetch_window(tickers, mid,       time_to, api_key, _depth + 1)
    return left + right


# ── DB mentés ─────────────────────────────────────────────────────────────────

def _parse_published_at(ts_str: str) -> Optional[datetime]:
    """Konvertálja az AV YYYYMMDDTHHMMSS formátumot naive UTC datetime-ra."""
    try:
        dt = datetime.strptime(ts_str, "%Y%m%dT%H%M%S")
        return dt  # naive – de az AV UTC-t ad vissza
    except ValueError:
        try:
            dt = datetime.strptime(ts_str[:13], "%Y%m%dT%H%M")
            return dt
        except ValueError:
            return None


def save_articles(
    articles: list[dict],
    us_symbols: set[str],
    db_path: str = "trendsignal.db",
    queried_ticker: Optional[str] = None,
) -> tuple[int, int]:
    """
    Elmenti a cikkeket az archive_news_items táblába.

    Egy cikkből több sor is keletkezhet (egy per releváns ticker).

    Returns:
        (inserted, skipped) tuple
    """
    if not articles:
        return 0, 0

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for article in articles:
        url = article.get("url", "")
        if not url:
            continue

        url_hash = hashlib.md5(url.encode()).hexdigest()
        title    = article.get("title", "")
        pub_str  = article.get("time_published", "")
        pub_at   = _parse_published_at(pub_str)
        if pub_at is None:
            continue

        source   = article.get("source", "")
        src_dom  = article.get("source_domain", "")
        authors  = json.dumps(article.get("authors", []))
        summary  = article.get("summary", "")
        category = article.get("category_within_source", "")
        banner   = article.get("banner_image", "")
        topics   = json.dumps(article.get("topics", []))
        overall_score = article.get("overall_sentiment_score")
        overall_label = article.get("overall_sentiment_label", "")
        ts_json  = json.dumps(article.get("ticker_sentiment", []))

        # Egy sor per releváns US ticker
        for ts in article.get("ticker_sentiment", []):
            ticker = ts.get("ticker", "")
            if ticker not in us_symbols:
                continue  # nem US ticker amit figyelünk

            relevance = float(ts.get("relevance_score", 0))
            if relevance < MIN_RELEVANCE:
                continue  # nem elég releváns

            av_score = ts.get("ticker_sentiment_score")
            av_label = ts.get("ticker_sentiment_label", "")
            if av_score is not None:
                av_score = float(av_score)

            try:
                cur.execute(
                    """
                    INSERT INTO archive_news_items (
                        url_hash, ticker_symbol, title, url, published_at,
                        source, source_domain, authors, summary, category, banner_image,
                        topics_json, overall_sentiment_score, overall_sentiment_label,
                        av_relevance_score, av_sentiment_score, av_sentiment_label,
                        ticker_sentiment_json, queried_ticker
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        url_hash, ticker, title, url, pub_at,
                        source, src_dom, authors, summary, category, banner,
                        topics, overall_score, overall_label,
                        relevance, av_score, av_label,
                        ts_json, queried_ticker,
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1  # már megvan (url_hash, ticker_symbol) kombináció

    conn.commit()
    conn.close()
    return inserted, skipped


# ── Fő backfill logika ────────────────────────────────────────────────────────

def backfill(
    symbols: list[str],
    start: datetime,
    end: datetime,
    api_key: str,
    db_path: str = "trendsignal.db",
    requests_per_day: int = 24,   # maradj 24-nél, hogy a 25/nap limit alatt legyél
) -> None:
    """
    Backfill az összes US ticker híreit start→end tartományra, havi bontásban.

    A free tier 25 req/nap limitje miatt az egyes havi ablakok között
    automatikus késleltetés van ha a napi quota közel van.

    Args:
        symbols:           US ticker lista
        start/end:         UTC datetime tartomány
        api_key:           Alpha Vantage API kulcs
        db_path:           SQLite DB útvonal
        requests_per_day:  Max napi kérés (alapból 24 → 1 marad tartaléknak)
    """
    create_table(db_path)

    us_symbols = set(symbols)
    print(f"Tickerek: {', '.join(sorted(us_symbols))}")
    print(f"Idoszak: {start.date()} -> {end.date()}")
    print("-" * 60)

    # Havi ablakok generálása
    windows: list[tuple[datetime, datetime]] = []
    cursor = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    while cursor < end:
        # Hó vége
        if cursor.month == 12:
            next_month = cursor.replace(year=cursor.year + 1, month=1)
        else:
            next_month = cursor.replace(month=cursor.month + 1)
        window_end = min(next_month, end)
        windows.append((cursor, window_end))
        cursor = next_month

    total_windows = len(windows)
    print(f"Havi ablakok: {total_windows}")
    print(f"Becsult API kerések: ~{total_windows} (ha nincs ablak-felosztás)")
    print(f"Napi limit: {requests_per_day} req/nap → ~{total_windows // requests_per_day + 1} nap")
    print("=" * 60)

    # Napi kérésszám követés
    today = datetime.now(timezone.utc).date()
    daily_requests = 0

    grand_inserted = 0
    grand_skipped  = 0

    for i, (w_from, w_to) in enumerate(windows):
        # Nap váltás ellenőrzés
        now_date = datetime.now(timezone.utc).date()
        if now_date != today:
            today = now_date
            daily_requests = 0

        # Napi limit check
        if daily_requests >= requests_per_day:
            midnight = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
            wait_sec = (midnight - datetime.now(timezone.utc)).total_seconds() + 60
            print(f"\n[LIMIT] Napi {requests_per_day} kerés elérve. Varakozas {wait_sec/3600:.1f} oraig...")
            time.sleep(wait_sec)
            daily_requests = 0

        print(f"\n[{i+1}/{total_windows}] {w_from.strftime('%Y-%m')}  ({w_from.date()} - {w_to.date()})")

        try:
            articles = fetch_window(symbols, w_from, w_to, api_key)
            daily_requests += 1

            ins, skp = save_articles(articles, us_symbols, db_path)
            grand_inserted += ins
            grand_skipped  += skp

            print(f"   {len(articles)} cikk -> {ins} mentve, {skp} mar megvolt")

            # Polite delay az API iránt
            time.sleep(1.5)

        except RuntimeError as e:
            print(f"   [STOP] {e}")
            print("   Allitsd be az ALPHAVANTAGE_API_KEY-t és próbáld újra holnap.")
            break
        except Exception as e:
            print(f"   [HIBA] {w_from.date()}: {e}")
            time.sleep(5)
            continue

    print(f"\n{'=' * 60}")
    print(f"KESZ! Osszes mentve: {grand_inserted}, mar megvolt: {grand_skipped}")
    print(f"{'=' * 60}")


# ── Tickerenkénti lapozásos backfill ─────────────────────────────────────────
#
# Miért NEM működik a multi-ticker lekérdezés?
#   Az AV tickers paramétere AND logikával szűr: csak olyan cikkeket ad vissza,
#   amelyek az ÖSSZES megadott tickert egyszerre tartalmazzák → 0 találat.
#
# Miért NEM jó a topic-alapú workweek megközelítés?
#   Egy munkahéten topic-szűrővel is eléri az 1000-es limitet (minden hétben
#   ~1000 találat), így cikkek vesznek el, és a relevancia csak ~15%.
#
# Helyes stratégia: tickerenként külön lekérdezés, időben lapozva
#   - 1 API hívás = 1 ticker, 1000 cikk csomag
#   - Ha 1000 cikket kap vissza, a legutolsó cikk idejétől folytatja
#   - Resume: DB-ből olvassa az adott ticker legrégebbi published_at-ját
#   - Egy ticker ~2 éves adat: ~6-17 kérés
#   - 8 ticker × ~10 kérés = ~80 kérés összesen = ~4 nap
#   - BÓNUSZ: egy cikk több tickert is érinthet → az összes US ticker
#     mentésre kerül a ticker_sentiment alapján, nem csak a lekérdezett

def _ticker_resume_point(symbol: str, end: datetime, db_path: str) -> datetime:
    """
    Visszaadja azt az időpontot, ahonnan folytatni kell a letöltést.
    Ha már van adat a DB-ben: a legrégebbi published_at - 1 nap (átfedés).
    Ha nincs adat: end (a legfrissebbtől indul visszafelé).
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # FONTOS: csak a közvetlen lekérdezéseket nézzük (queried_ticker = symbol)
    # A spillover sorok (más ticker query hozta be) NEM számítanak resume szempontból
    cur.execute(
        "SELECT MIN(published_at) FROM archive_news_items WHERE queried_ticker = ?",
        (symbol,),
    )
    row = cur.fetchone()
    conn.close()

    if row and row[0]:
        min_dt = datetime.fromisoformat(str(row[0]))
        # A tört napot teljes egészében újra lekérdezzük:
        # levágunk az adott nap elejére (00:00:00), így a nap összes cikke
        # biztosan beleesik az új requestbe. A már meglévő cikkek a UNIQUE
        # index miatt skip-elve lesznek, duplikáció nem keletkezik.
        return min_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return end  # nincs közvetlen lekérdezés → a legfrissebbtől indulunk


def _fetch_ticker_page(
    symbol: str,
    time_from: datetime,
    time_to: datetime,
    api_key: str,
) -> list[dict]:
    """
    Egy lap lekérése adott ticker + időablakra (max 1000 cikk, LATEST→régebbi).
    """
    data = _av_request([symbol], time_from, time_to, api_key, sort="LATEST", limit=1000)
    return data.get("feed") or []


def _rate_limit_wait(daily_requests: int, requests_per_day: int, today) -> tuple[int, object]:
    """Napi limit ellenőrzés és overnight wait ha szükséges. Returns (daily_requests, today)."""
    now_date = datetime.now(timezone.utc).date()
    if now_date != today:
        return 0, now_date

    if daily_requests >= requests_per_day:
        midnight = (
            datetime.now(timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            + timedelta(days=1)
        )
        wait_sec = (midnight - datetime.now(timezone.utc)).total_seconds() + 60
        print(f"\n[LIMIT] Napi {requests_per_day} keres elérve. Varakozas {wait_sec/3600:.1f} oraig...")
        time.sleep(wait_sec)
        return 0, datetime.now(timezone.utc).date()

    return daily_requests, today


def backfill_workweeks(
    symbols: list[str],
    start: datetime,
    end: datetime,
    api_key: str,
    db_path: str = "trendsignal.db",
    requests_per_day: int = 24,
) -> None:
    """
    Backfill tickerenként, időben lapozva (legfrissebbtől visszafelé).

    Stratégia:
    - 1 API hivas = 1 ticker, LATEST sort, max 1000 cikk
    - Ha 1000 cikk jott: a legrégebbi cikk idejétől folytatja (lapoz)
    - Ha < 1000: az adott ticker kész, következő tickerre lép
    - Resume: DB-ből olvassa tickerenkent az eddig letöltött legrégebbi datumot
    - Egy cikk több US tickert is menthet (ticker_sentiment alapján)
    - Becsult: ~10 keres/ticker × 8 ticker = ~80 keres = ~4 nap

    Args:
        symbols:           US ticker lista (sorrendben dolgozza fel)
        start/end:         UTC datetime tartomány
        api_key:           Alpha Vantage API kulcs
        db_path:           SQLite DB utvonal
        requests_per_day:  Max napi keres (24 = 1 tartalek a 25/nap limitbol)
    """
    create_table(db_path)
    us_symbols = set(symbols)

    # Egységesítés: mindent naive UTC-re konvertálunk (a DB is így tárolja)
    start = start.replace(tzinfo=None)
    end   = end.replace(tzinfo=None)

    print(f"Tickerek ({len(symbols)}): {', '.join(sorted(us_symbols))}")
    print(f"Idoszak: {start.date()} -> {end.date()}")
    print(f"Strategia: tickerenkent lapozva (LATEST), ~10 keres/ticker")
    print("-" * 60)

    today = datetime.now(timezone.utc).date()
    daily_requests = 0
    grand_inserted = 0
    grand_skipped  = 0

    for symbol in symbols:
        # Resume: honnan folytassuk ezt a tickert?
        resume_to = _ticker_resume_point(symbol, end, db_path)

        if resume_to <= start:
            print(f"\n[KESZ] {symbol} - mar teljes 2 ev megvan")
            continue

        print(f"\n{'=' * 60}")
        print(f"TICKER: {symbol}  ({start.date()} -> {resume_to.date()})")
        print(f"{'=' * 60}")

        current_end = resume_to
        page = 0

        while current_end > start:
            # Rate limit
            daily_requests, today = _rate_limit_wait(daily_requests, requests_per_day, today)

            page += 1
            print(f"  [{symbol} lap {page}] ... -> {current_end.date()}", end="", flush=True)

            try:
                articles = _fetch_ticker_page(symbol, start, current_end, api_key)
                daily_requests += 1

                if not articles:
                    print(f" | 0 cikk -> {symbol} kész")
                    break

                ins, skp = save_articles(articles, us_symbols, db_path, queried_ticker=symbol)
                grand_inserted += ins
                grand_skipped  += skp

                oldest_str = articles[-1].get("time_published", "")
                oldest_dt  = _parse_published_at(oldest_str)
                print(f" | {len(articles)} cikk, legrégebbi: {oldest_str[:8]} -> {ins} mentve, {skp} skip")

                if len(articles) < 1000:
                    # Minden cikk megvan ettől a ponttól
                    print(f"  [{symbol}] Teljes tortenelem letoltve")
                    break

                if oldest_dt is None or oldest_dt >= current_end:
                    print(f"  [{symbol}] Lapozas megrekedne, megallunk")
                    break

                # Lapozás: folytatás a legrégebbi cikk időpontjától
                current_end = oldest_dt - timedelta(seconds=1)
                time.sleep(1.5)

            except RuntimeError as e:
                print(f"\n  [STOP] {e}")
                print("  Holnap ujra futtathatod - folytatja ahol abbahagyta.")
                print(f"\n{'=' * 60}")
                print(f"KESZ! Osszes mentve: {grand_inserted}, skip: {grand_skipped}")
                print(f"{'=' * 60}")
                return
            except Exception as e:
                print(f"\n  [HIBA] {symbol} lap {page}: {e}")
                time.sleep(5)
                break

    print(f"\n{'=' * 60}")
    print(f"KESZ! Osszes mentve: {grand_inserted}, mar megvolt: {grand_skipped}")
    print(f"{'=' * 60}")


# ── Standalone futtatás ───────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    import sqlite3 as _sq

    load_dotenv()

    api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "").strip()
    if not api_key:
        print("HIBA: Hianyzo ALPHAVANTAGE_API_KEY a .env fajlban!")
        print("  Szerezz ingyenes kulcsot: https://www.alphavantage.co/support/#api-key")
        sys.exit(1)

    # US tickerek a DB-ből
    conn = _sq.connect("trendsignal.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol FROM tickers
        WHERE symbol NOT LIKE '%.BD'
          AND (market NOT LIKE '%BET%' AND market NOT LIKE '%B_T%')
        ORDER BY symbol
    """)
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()

    END   = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    START = END - timedelta(days=365 * 2)

    backfill(
        symbols=symbols,
        start=START,
        end=END,
        api_key=api_key,
    )
