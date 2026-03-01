"""
TrendSignal – Tier 1 RSS Kollektorok
Valós idejű, korlátlan, ingyenes hírforrások.

Források:
  - SEC EDGAR RSS  – US 8-K filingok (credibility: 0.95)
  - Nasdaq News RSS – Tőzsdei hírek ticker-specifikusan (credibility: 0.90)
  - BÉT RSS        – Budapest Értéktőzsde közlemények (credibility: 0.95)
  - Seeking Alpha  – Ticker-specifikus elemzések (credibility: 0.82)
  - StockTwits     – Retail social sentiment (credibility: 0.50)

Verzió: 1.1 | 2026-03-01
Változások:
  - SEC EDGAR: requests + kötelező User-Agent (email), feedparser.parse(content) mode
  - BÉT RSS: requests + charset recovery (UTF-8 → ISO-8859-2 → Windows-1250 fallback)
  - Nasdaq RSS: requests + browser User-Agent (Nasdaq blokkolja a feedparser UA-t)
"""

import feedparser
import requests
import socket
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, TYPE_CHECKING
import time

# Windows cp1250 konzol: emoji printok UnicodeEncodeError-t dobnának.
# errors='replace' → ? jelként jelenik meg a nem kódolható karakter, nem crashel.
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(errors='replace')
    except Exception:
        pass

# Globális socket timeout – minden feedparser.parse() hívásra vonatkozik.
# Seeking Alpha néha lassan / soha sem válaszol → 8 másodperc elég.
_FEEDPARSER_TIMEOUT = 8  # másodperc

# SEC EDGAR kötelező User-Agent (email-lel): https://www.sec.gov/os/webmaster-faq#xml-feeds
_SEC_EDGAR_USER_AGENT = "TrendSignal/2.0 contact@trendsignal.app"

# Browser-szerű User-Agent Nasdaq és más bot-szűrő oldalakhoz
_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

if TYPE_CHECKING:
    from src.sentiment_analyzer import NewsItem
    from src.multilingual_sentiment import MultilingualSentimentAnalyzer


# ------------------------------------------------------------------
# CIK mapping – US ticker → SEC EDGAR CIK szám
# ------------------------------------------------------------------
SEC_CIK_MAP: Dict[str, str] = {
    "AAPL": "0000320193",
    "TSLA": "0001318605",
    "MSFT": "0000789019",
    "NVDA": "0001045810",
    "META": "0001326801",
    "AMZN": "0001018724",
    "IBM": "0000051143",
    "GOOGL": "0001652044",
    "GOOG": "0001652044",
    "NFLX": "0001065280",
    "AMD": "0000002488",
    "INTC": "0000050863",
}

# BÉT ticker → keresési kulcsszavak (RSS szűréshez)
BET_KEYWORDS: Dict[str, List[str]] = {
    "MOL.BD": ["MOL", "MOL Nyrt", "MOL Group", "Hernádi"],
    "OTP.BD": ["OTP", "OTP Bank", "OTP Nyrt", "Csányi"],
}

# Seeking Alpha RSS URL sablon
SEEKING_ALPHA_URL = "https://seekingalpha.com/symbol/{ticker}.xml"

# Nasdaq RSS URL sablon
NASDAQ_RSS_URL = "https://www.nasdaq.com/feed/rssoutbound?symbol={ticker}"

# SEC EDGAR RSS (összes 8-K, globális feed)
SEC_EDGAR_RSS_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar"
    "?action=getcurrent&type=8-K&dateb=&owner=include&count=40&output=atom"
)

# BÉT RSS URL – bet.hu/rss már 404-et ad (2025-től).
# Csere: Portfolio.hu gazdasági RSS (UTF-8, ~20 bejegyzés, MOL/OTP közlemények is megjelennek)
BET_RSS_URL = "https://www.portfolio.hu/rss/gazdasag.xml"

# StockTwits API URL sablon
STOCKTWITS_URL = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"


def _parse_feed_with_timeout(url: str, timeout: int = _FEEDPARSER_TIMEOUT, **kwargs) -> object:
    """
    feedparser.parse() hívás globális socket timeout-tal.
    Preventing hanging on slow/unresponsive RSS servers (Seeking Alpha, SEC EDGAR).
    """
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        return feedparser.parse(url, **kwargs)
    finally:
        socket.setdefaulttimeout(old_timeout)


def _parse_feed_date(entry) -> datetime:
    """Feedparser entry published dátumának UTC datetime-má alakítása."""
    # feedparser published_parsed: time.struct_time UTC-ben
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _make_news_item(
    title: str,
    description: str,
    url: str,
    published_at: datetime,
    source: str,
    credibility: float,
    sentiment_analyzer: Optional['MultilingualSentimentAnalyzer'] = None,
    ticker_symbol: str = "",
) -> 'NewsItem':
    """NewsItem konstruktor helper."""
    from src.sentiment_analyzer import NewsItem as NI

    sentiment_score = 0.0
    sentiment_confidence = 0.5
    sentiment_label = "neutral"

    if sentiment_analyzer and ticker_symbol:
        text = f"{title}. {description}"
        try:
            result = sentiment_analyzer.analyze_text(text, ticker_symbol)
            sentiment_score = result['score']
            sentiment_confidence = result['confidence']
            sentiment_label = result['label']
        except Exception:
            pass

    return NI(
        title=title,
        description=description,
        url=url,
        published_at=published_at,
        source=source,
        sentiment_score=sentiment_score,
        sentiment_confidence=sentiment_confidence,
        sentiment_label=sentiment_label,
        credibility=credibility,
    )


# ------------------------------------------------------------------
# SEC EDGAR in-process feed cache – 1 request / 60s az összes tickernek
# ------------------------------------------------------------------
import threading as _threading

_sec_edgar_lock = _threading.Lock()
_sec_edgar_cache: Dict = {"feed": None, "fetched_at": 0.0}
_SEC_EDGAR_CACHE_TTL = 60  # másodperc – az összes ticker 1 requestből kap adatot


def _get_sec_edgar_feed() -> object:
    """
    SEC EDGAR globális 8-K feed – in-process cache-sel (TTL: 60s).
    9 ticker × collect_news() helyett csak 1 HTTP kérés / ciklus.

    SEC.gov kötelező User-Agent policy (2023+):
      User-Agent: <AppName>/<version> <contact-email>
    Feedparser alapértelmezett UA-ja nincs email → 403 / garbled XML.
    Megoldás: requests-szel töltjük le, feedparser.parse(content) módban dolgozzuk fel.
    """
    import time
    now = time.monotonic()
    with _sec_edgar_lock:
        if _sec_edgar_cache["feed"] is not None and (now - _sec_edgar_cache["fetched_at"]) < _SEC_EDGAR_CACHE_TTL:
            return _sec_edgar_cache["feed"]
        # Cache lejárt vagy üres → frissítés
        try:
            resp = requests.get(
                SEC_EDGAR_RSS_URL,
                headers={"User-Agent": _SEC_EDGAR_USER_AGENT, "Accept-Encoding": "gzip"},
                timeout=10,
            )
            resp.raise_for_status()
            # feedparser.parse() elfogad bytes-t is – így megkerüljük az UA-problémát
            feed = feedparser.parse(resp.content)
        except Exception as exc:
            # Fallback: közvetlen feedparser (esetleg szintén 403, de megpróbáljuk)
            print(f"  [WARN] SEC EDGAR requests hiba: {exc}, fallback feedparser")
            feed = _parse_feed_with_timeout(SEC_EDGAR_RSS_URL, timeout=12)
        _sec_edgar_cache["feed"] = feed
        _sec_edgar_cache["fetched_at"] = now
        return feed


# ==================================================================
# SEC EDGAR RSS Collector
# ==================================================================

class SecEdgarCollector:
    """
    US 8-K filingok valós időben az SEC EDGAR globális RSS feedjéből.
    Egyetlen request lefedi az összes US tickert.
    Credibility: 0.95 (hivatalos tőzsdei dokumentum)
    """

    CREDIBILITY = 0.95
    SOURCE_NAME = "SEC EDGAR"
    # Fontos 8-K kategóriák
    IMPORTANT_FORMS = {"8-K", "8-K/A"}

    def collect(
        self,
        tickers: List[str],
        lookback_hours: int = 48,
        sentiment_analyzer: Optional['MultilingualSentimentAnalyzer'] = None,
    ) -> Dict[str, List['NewsItem']]:
        """
        Lekéri az SEC EDGAR 8-K feed-et és tikkerenként szétosztja.

        Returns:
            Dict[ticker_symbol → List[NewsItem]]
        """
        result: Dict[str, List] = {t: [] for t in tickers}
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        try:
            # In-process cache: 60s TTL → 9 ticker helyett 1 HTTP request / ciklus
            feed = _get_sec_edgar_feed()
            if feed.bozo and not feed.entries:
                print(f"  ⚠️ SEC EDGAR RSS parse hiba: {feed.bozo_exception}")
                return result

            # CIK → ticker visszamap
            cik_to_ticker: Dict[str, str] = {}
            for ticker in tickers:
                ticker_upper = ticker.replace(".BD", "").upper()
                cik = SEC_CIK_MAP.get(ticker_upper)
                if cik:
                    # Normalizálás: vezető nullák eltávolítása
                    cik_to_ticker[cik.lstrip("0")] = ticker

            for entry in feed.entries:
                published_at = _parse_feed_date(entry)
                if published_at < cutoff:
                    continue

                title = entry.get('title', '')
                link = entry.get('link', '')
                summary = entry.get('summary', '')

                # CIK kinyerése az URL-ből pl. ".../data/320193/..."
                matched_ticker = None
                if '/data/' in link:
                    parts = link.split('/data/')
                    if len(parts) > 1:
                        cik_in_url = parts[1].split('/')[0].lstrip('0')
                        matched_ticker = cik_to_ticker.get(cik_in_url)

                if not matched_ticker:
                    continue

                item = _make_news_item(
                    title=title,
                    description=summary,
                    url=link,
                    published_at=published_at,
                    source=self.SOURCE_NAME,
                    credibility=self.CREDIBILITY,
                    sentiment_analyzer=sentiment_analyzer,
                    ticker_symbol=matched_ticker,
                )
                result[matched_ticker].append(item)

        except Exception as e:
            print(f"  ❌ SEC EDGAR hiba: {e}")

        total = sum(len(v) for v in result.values())
        if total > 0:
            print(f"  ✅ SEC EDGAR: {total} filing ({len(tickers)} ticker, 1 request)")
        return result


# ==================================================================
# Nasdaq News RSS Collector
# ==================================================================

class NasdaqRssCollector:
    """
    Nasdaq hivatalos tőzsdei hírek ticker-specifikus RSS URL-eken.
    Credibility: 0.90
    """

    CREDIBILITY = 0.90

    def collect_for_ticker(
        self,
        ticker_symbol: str,
        lookback_hours: int = 48,
        sentiment_analyzer: Optional['MultilingualSentimentAnalyzer'] = None,
    ) -> List['NewsItem']:
        """Egy ticker Nasdaq RSS-ét lekéri és visszaadja."""
        # BÉT tickerekre nem alkalmazható
        if ticker_symbol.endswith('.BD'):
            return []

        clean_ticker = ticker_symbol.upper()
        url = NASDAQ_RSS_URL.format(ticker=clean_ticker)
        source_name = f"Nasdaq RSS ({clean_ticker})"
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        try:
            # Nasdaq blokkolja a feedparser alapértelmezett UA-t.
            # requests-szel töltjük le browser UA-val, majd bytes-t adunk feedparser-nek.
            try:
                resp = requests.get(
                    url,
                    headers={"User-Agent": _BROWSER_USER_AGENT},
                    timeout=8,
                )
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
            except Exception as req_exc:
                print(f"  [WARN] Nasdaq RSS requests hiba ({clean_ticker}): {req_exc}, fallback")
                feed = _parse_feed_with_timeout(url)

            if feed.bozo and not feed.entries:
                return []

            items = []
            for entry in feed.entries:
                published_at = _parse_feed_date(entry)
                if published_at < cutoff:
                    continue

                title = entry.get('title', '')
                link = entry.get('link', entry.get('id', ''))
                summary = entry.get('summary', entry.get('description', ''))

                item = _make_news_item(
                    title=title,
                    description=summary,
                    url=link,
                    published_at=published_at,
                    source=source_name,
                    credibility=self.CREDIBILITY,
                    sentiment_analyzer=sentiment_analyzer,
                    ticker_symbol=ticker_symbol,
                )
                items.append(item)

            if items:
                print(f"  ✅ Nasdaq RSS ({clean_ticker}): {len(items)} cikk")
            return items

        except Exception as e:
            print(f"  ❌ Nasdaq RSS hiba ({ticker_symbol}): {e}")
            return []


# ==================================================================
# BÉT RSS Collector
# ==================================================================

class BetRssCollector:
    """
    Budapest Értéktőzsde hivatalos közlemények RSS feedből.
    Credibility: 0.95 – Egyetlen globális feed, Python-oldalon szűrve.
    """

    CREDIBILITY = 0.95
    SOURCE_NAME = "BÉT RSS"

    def collect(
        self,
        tickers: List[str],
        lookback_hours: int = 48,
        sentiment_analyzer: Optional['MultilingualSentimentAnalyzer'] = None,
    ) -> Dict[str, List['NewsItem']]:
        """
        BÉT RSS lekérése és ticker-specifikus szűrés kulcsszó alapján.

        Returns:
            Dict[ticker_symbol → List[NewsItem]]
        """
        # Csak .BD tickerekre
        bet_tickers = [t for t in tickers if t.endswith('.BD')]
        result: Dict[str, List] = {t: [] for t in bet_tickers}
        if not bet_tickers:
            return result

        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        try:
            # BÉT RSS kódolási hiba workaround:
            # bet.hu sokszor Windows-1250 / ISO-8859-2 kódolású XML-t küld,
            # de az XML header UTF-8-at deklarál → feedparser "invalid token" (bozo).
            # Megoldás: requests-szel töltjük le, explicit kódolást detektálunk,
            # majd a javított bytes-t adjuk feedparser.parse()-nek.
            try:
                resp = requests.get(
                    BET_RSS_URL,
                    headers={"User-Agent": _BROWSER_USER_AGENT},
                    timeout=8,
                )
                resp.raise_for_status()
                raw_bytes = resp.content
                # Kódolás detektálás: próbáljuk a response headerben megadottat,
                # aztán ISO-8859-2 / Windows-1250 / latin-1 fallback sorrendben.
                detected_enc = resp.apparent_encoding or "utf-8"
                for enc in [detected_enc, "iso-8859-2", "windows-1250", "latin-1", "utf-8"]:
                    try:
                        raw_bytes.decode(enc)
                        # Ha sikerül, adjuk át feedparser-nek mint bytes
                        # (feedparser maga kezeli a belső XML deklarációt)
                        feed = feedparser.parse(raw_bytes)
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                else:
                    feed = feedparser.parse(raw_bytes)
            except Exception as req_exc:
                print(f"  [WARN] BET RSS requests hiba: {req_exc}, fallback feedparser")
                feed = _parse_feed_with_timeout(BET_RSS_URL)

            if feed.bozo and not feed.entries:
                print(f"  ⚠️ BÉT RSS parse hiba: {feed.bozo_exception}")
                return result

            for entry in feed.entries:
                published_at = _parse_feed_date(entry)
                if published_at < cutoff:
                    continue

                title = entry.get('title', '')
                link = entry.get('link', entry.get('id', ''))
                summary = entry.get('summary', entry.get('description', ''))
                text_lower = f"{title} {summary}".lower()

                for ticker in bet_tickers:
                    keywords = BET_KEYWORDS.get(ticker, [])
                    if any(kw.lower() in text_lower for kw in keywords):
                        item = _make_news_item(
                            title=title,
                            description=summary,
                            url=link,
                            published_at=published_at,
                            source=self.SOURCE_NAME,
                            credibility=self.CREDIBILITY,
                            sentiment_analyzer=sentiment_analyzer,
                            ticker_symbol=ticker,
                        )
                        result[ticker].append(item)

        except Exception as e:
            print(f"  ❌ BÉT RSS hiba: {e}")

        total = sum(len(v) for v in result.values())
        if total > 0:
            print(f"  ✅ BÉT RSS: {total} közlemény ({len(bet_tickers)} ticker, 1 request)")
        return result


# ==================================================================
# Seeking Alpha RSS Collector
# ==================================================================

class SeekingAlphaRssCollector:
    """
    Ticker-specifikus elemzések Seeking Alpha RSS feedből.
    Credibility: 0.82 – Gazdagabb szöveg, jobb FinBERT input.
    """

    CREDIBILITY = 0.82

    def collect_for_ticker(
        self,
        ticker_symbol: str,
        lookback_hours: int = 48,
        sentiment_analyzer: Optional['MultilingualSentimentAnalyzer'] = None,
    ) -> List['NewsItem']:
        """Egy ticker Seeking Alpha RSS-ét lekéri."""
        if ticker_symbol.endswith('.BD'):
            return []

        clean_ticker = ticker_symbol.upper()
        url = SEEKING_ALPHA_URL.format(ticker=clean_ticker)
        source_name = f"Seeking Alpha ({clean_ticker})"
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        try:
            # Seeking Alpha bot-detection ellen User-Agent header szükséges.
            # Timeout: 6 másodperc – SA néha nem válaszol vagy 403-at ad.
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; TrendSignal/2.0; +https://trendsignal.app)'
            }
            feed = _parse_feed_with_timeout(url, timeout=6, request_headers=headers)

            # Seeking Alpha sokszor 403/429-et ad – ilyenkor entries üres
            if not feed.entries:
                return []
            if feed.bozo and not feed.entries:
                return []

            items = []
            for entry in feed.entries:
                published_at = _parse_feed_date(entry)
                if published_at < cutoff:
                    continue

                title = entry.get('title', '')
                link = entry.get('link', entry.get('id', ''))
                summary = entry.get('summary', entry.get('description', ''))

                item = _make_news_item(
                    title=title,
                    description=summary,
                    url=link,
                    published_at=published_at,
                    source=source_name,
                    credibility=self.CREDIBILITY,
                    sentiment_analyzer=sentiment_analyzer,
                    ticker_symbol=ticker_symbol,
                )
                items.append(item)

            if items:
                print(f"  ✅ Seeking Alpha ({clean_ticker}): {len(items)} cikk")
            return items

        except Exception as e:
            print(f"  ❌ Seeking Alpha RSS hiba ({ticker_symbol}): {e}")
            return []


# ==================================================================
# StockTwits Collector (opcionális, alacsony prioritás)
# ==================================================================

class StockTwitsCollector:
    """
    Retail social sentiment StockTwitsről.
    Credibility: 0.50 – Kontraindikátorként és megerősítőként.
    Autentikáció nélkül is elérhető (korlátlan alap endpoint).
    """

    CREDIBILITY = 0.50

    def collect_for_ticker(
        self,
        ticker_symbol: str,
        sentiment_analyzer: Optional['MultilingualSentimentAnalyzer'] = None,
    ) -> List['NewsItem']:
        """Egy ticker legutóbbi StockTwits üzeneteit lekéri."""
        if ticker_symbol.endswith('.BD'):
            return []

        clean_ticker = ticker_symbol.upper()
        url = STOCKTWITS_URL.format(ticker=clean_ticker)
        source_name = f"StockTwits ({clean_ticker})"

        try:
            headers = {'User-Agent': 'TrendSignal/2.0'}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()

            messages = data.get('messages', [])
            items = []
            now = datetime.now(timezone.utc)

            for msg in messages:
                # created_at pl. "2025-01-15T14:30:00Z"
                created_str = msg.get('created_at', '')
                try:
                    published_at = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                except Exception:
                    published_at = now

                body = msg.get('body', '')
                if not body:
                    continue

                # StockTwits saját sentiment (bullish/bearish)
                entities = msg.get('entities', {})
                st_sentiment = entities.get('sentiment', {})
                st_label = st_sentiment.get('basic', '') if isinstance(st_sentiment, dict) else ''

                if st_label == 'Bullish':
                    score, label, conf = 0.6, 'positive', 0.65
                elif st_label == 'Bearish':
                    score, label, conf = -0.6, 'negative', 0.65
                else:
                    score, label, conf = 0.0, 'neutral', 0.50

                from src.sentiment_analyzer import NewsItem as NI
                item = NI(
                    title=body[:120],
                    description=body,
                    url=f"https://stocktwits.com/message/{msg.get('id', '')}",
                    published_at=published_at,
                    source=source_name,
                    sentiment_score=score,
                    sentiment_confidence=conf,
                    sentiment_label=label,
                    credibility=self.CREDIBILITY,
                )
                items.append(item)

            if items:
                print(f"  ✅ StockTwits ({clean_ticker}): {len(items)} üzenet")
            return items

        except Exception as e:
            print(f"  ❌ StockTwits hiba ({ticker_symbol}): {e}")
            return []


if __name__ == "__main__":
    print("RSS Collector teszt")
    print(f"  SEC EDGAR URL: {SEC_EDGAR_RSS_URL}")
    print(f"  BÉT RSS URL:   {BET_RSS_URL}")
    print(f"  Nasdaq URL:    {NASDAQ_RSS_URL.format(ticker='AAPL')}")
    print(f"  SeekAlpha URL: {SEEKING_ALPHA_URL.format(ticker='AAPL')}")
