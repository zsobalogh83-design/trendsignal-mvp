"""
TrendSignal MVP – News Collector v3.0
Tier-vezérelt, valós idejű, kvóta-tudatos hírgyűjtés.

Stratégia (v2.0 – TrendSignal_Hir_Strategia.docx):
  TIER 1 – Korlátlan, mindig fut:
    - SEC EDGAR RSS  (US 8-K, credibility 0.95)
    - Nasdaq News RSS (US ticker-specifikus, credibility 0.90)
    - BÉT RSS        (HU tőzsdei közlemények, credibility 0.95)
    - Seeking Alpha  (US elemzések, credibility 0.82)
    - Yahoo Finance  (US fallback, credibility 0.90)
    - Magyar RSS     (HU portfolio/telex/hvg, credibility 0.85)

  TIER 2 – Rate-limited (60/perc), de bőséges:
    - Finnhub

  TIER 3 – Napi limit, csak ha Tier 1-2 nem elég:
    - Marketaux (batch mód: 1-2 req/ciklus, 100/nap)
    - GNews     (100/nap)

Kizárva (free tier delay):
  - NewsAPI    (akár 1 hónapos késleltetés)
  - AlphaVantage (több órás-napos + 25 req/nap)

Deduplikáció: URL + Jaccard title-similarity (≥0.80, 30 perc ablak)

Verzió: 3.0 | 2026-02-25
"""

import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, TYPE_CHECKING
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import TrendSignalConfig, get_config
from src.sentiment_analyzer import NewsItem

# Import Hungarian collector
try:
    from src.hungarian_news import HungarianNewsCollector
    HAS_HUNGARIAN = True
except ImportError:
    HAS_HUNGARIAN = False
    print("⚠️ Hungarian news module not available")

# Import Yahoo Finance collector
try:
    from src.yahoo_collector import YahooFinanceCollector
    HAS_YAHOO = True
except ImportError:
    HAS_YAHOO = False
    print("⚠️ Yahoo Finance module not available")

# Import Finnhub collector
try:
    from src.finnhub_collector import FinnhubCollector
    HAS_FINNHUB = True
except ImportError:
    HAS_FINNHUB = False
    print("⚠️ Finnhub module not available")

# Import Marketaux collector
try:
    from src.marketaux_collector import MarketauxCollector
    HAS_MARKETAUX = True
except ImportError:
    HAS_MARKETAUX = False
    print("⚠️ Marketaux module not available")

# Import GNews collector
try:
    from src.gnews_collector import GNewsCollector
    HAS_GNEWS = True
except ImportError:
    HAS_GNEWS = False
    print("⚠️ GNews module not available")

# Import RSS collectors (Tier 1)
try:
    from src.rss_collector import (
        SecEdgarCollector,
        NasdaqRssCollector,
        BetRssCollector,
        SeekingAlphaRssCollector,
    )
    HAS_RSS = True
except ImportError:
    HAS_RSS = False
    print("⚠️ RSS collector module not available")

# Import QuotaManager
try:
    from src.quota_manager import QuotaManager
    HAS_QUOTA_MANAGER = True
except ImportError:
    HAS_QUOTA_MANAGER = False
    print("⚠️ QuotaManager not available")

# Import BatchNewsCache
try:
    from src.batch_news_cache import BatchNewsCache
    HAS_BATCH_CACHE = True
except ImportError:
    HAS_BATCH_CACHE = False
    print("⚠️ BatchNewsCache not available")

if TYPE_CHECKING:
    from src.multilingual_sentiment import MultilingualSentimentAnalyzer

# Jaccard deduplikáció paraméterei
_JACCARD_THRESHOLD = 0.80   # 80%-os hasonlóság
_JACCARD_TIME_WINDOW = 1800  # 30 perc (másodperc)


class NewsCollector:
    """
    Tier-vezérelt, kvóta-tudatos hírgyűjtő.

    TIER 1 (korlátlan) → TIER 2 (rate-limited) → TIER 3 (csak ha szükséges)
    Jaccard title-similarity deduplikáció (URL + szöveg alapján).
    """

    def __init__(
        self,
        config: Optional[TrendSignalConfig] = None,
        db: Optional[Session] = None,
        quota_manager: Optional['QuotaManager'] = None,
        batch_cache: Optional['BatchNewsCache'] = None,
    ):
        self.config = config or get_config()
        self.db = db

        # QuotaManager – ha nincs megadva, in-memory módban hozzuk létre
        if quota_manager is not None:
            self.quota_manager = quota_manager
        elif HAS_QUOTA_MANAGER:
            self.quota_manager = QuotaManager(db)
        else:
            self.quota_manager = None

        # BatchNewsCache – shared instance (külső scheduler injektálhatja)
        if batch_cache is not None:
            self.batch_cache = batch_cache
        elif HAS_BATCH_CACHE:
            self.batch_cache = BatchNewsCache()
        else:
            self.batch_cache = None

        # ── TIER 1 kollektorok ──────────────────────────────────────
        self.yahoo_collector = None
        if HAS_YAHOO:
            try:
                self.yahoo_collector = YahooFinanceCollector()
            except Exception as e:
                print(f"⚠️ Yahoo collector init failed: {e}")

        self.sec_edgar_collector = None
        self.nasdaq_rss_collector = None
        self.bet_rss_collector = None
        self.seeking_alpha_collector = None
        if HAS_RSS:
            try:
                self.sec_edgar_collector = SecEdgarCollector()
                self.nasdaq_rss_collector = NasdaqRssCollector()
                self.bet_rss_collector = BetRssCollector()
                self.seeking_alpha_collector = SeekingAlphaRssCollector()
            except Exception as e:
                print(f"⚠️ RSS collector init failed: {e}")

        self.hungarian_collector = None
        if HAS_HUNGARIAN:
            try:
                self.hungarian_collector = HungarianNewsCollector(config, db=self.db)
            except Exception as e:
                print(f"⚠️ Hungarian collector init failed: {e}")

        # ── TIER 2 kollektorok ──────────────────────────────────────
        self.finnhub_collector = None
        if HAS_FINNHUB and self.config.finnhub_api_key:
            try:
                self.finnhub_collector = FinnhubCollector(self.config.finnhub_api_key)
            except Exception as e:
                print(f"⚠️ Finnhub collector init failed: {e}")

        # ── TIER 3 kollektorok ──────────────────────────────────────
        self.marketaux_collector = None
        if HAS_MARKETAUX and self.config.marketaux_api_key:
            try:
                self.marketaux_collector = MarketauxCollector(
                    self.config.marketaux_api_key,
                    quota_manager=self.quota_manager,
                )
            except Exception as e:
                print(f"⚠️ Marketaux collector init failed: {e}")

        self.gnews_collector = None
        if HAS_GNEWS and self.config.gnews_api_key:
            try:
                self.gnews_collector = GNewsCollector(self.config.gnews_api_key)
            except Exception as e:
                print(f"⚠️ GNews collector init failed: {e}")

    # ------------------------------------------------------------------
    # PUBLIC: collect_news()
    # ------------------------------------------------------------------

    def collect_news(
        self,
        ticker_symbol: str,
        company_name: str,
        lookback_hours: int = 72,
        save_to_db: bool = True,
    ) -> List[NewsItem]:
        """
        Tier-vezérelt hírgyűjtés egyetlen tickerhez.

        1. TIER 1 (korlátlan) – párhuzamosan
        2. TIER 2 (Finnhub, rate-limited) – ha van kvótája
        3. TIER 3 (Marketaux/GNews) – csak ha Tier1+2 nem adott elég friss hírt

        Args:
            ticker_symbol: Tőzsdei jelölő (pl. AAPL, MOL.BD)
            company_name:  Cég neve (keresési kulcsszóhoz)
            lookback_hours: Visszatekintési ablak
            save_to_db:    Mentés DB-be (ha van session)

        Returns:
            List[NewsItem] – deduplikált, dátum szerint csökkentő sorrendben
        """
        from src.multilingual_sentiment import MultilingualSentimentAnalyzer
        sentiment_analyzer = MultilingualSentimentAnalyzer(self.config, ticker_symbol)

        is_us_ticker = not ticker_symbol.endswith('.BD')
        all_news: List[NewsItem] = []

        # ════════════════════════════════════════════════════════════
        # TIER 1 – Korlátlan, mindig fut
        # ════════════════════════════════════════════════════════════
        tier1_tasks: Dict[str, callable] = {}

        if is_us_ticker:
            if self.sec_edgar_collector:
                # SEC EDGAR globális (1 req / összes ticker) – egyszerűsített hívás 1 tickerrel
                tier1_tasks['sec_edgar'] = lambda: self._collect_from_sec_edgar(
                    ticker_symbol, lookback_hours, sentiment_analyzer
                )
            if self.nasdaq_rss_collector:
                tier1_tasks['nasdaq_rss'] = lambda: self.nasdaq_rss_collector.collect_for_ticker(
                    ticker_symbol, lookback_hours, sentiment_analyzer
                )
            if self.seeking_alpha_collector:
                tier1_tasks['seeking_alpha'] = lambda: self.seeking_alpha_collector.collect_for_ticker(
                    ticker_symbol, lookback_hours, sentiment_analyzer
                )
            if self.yahoo_collector:
                tier1_tasks['yahoo'] = lambda: self._collect_from_yahoo(
                    ticker_symbol, lookback_hours, sentiment_analyzer
                )
        else:
            # BÉT
            if self.bet_rss_collector:
                tier1_tasks['bet_rss'] = lambda: self._collect_from_bet(
                    ticker_symbol, lookback_hours, sentiment_analyzer
                )
            if self.hungarian_collector:
                tier1_tasks['hungarian'] = lambda: self.hungarian_collector.collect_news(
                    ticker_symbol=ticker_symbol,
                    company_name=company_name,
                    lookback_hours=lookback_hours,
                )

        if tier1_tasks:
            # Tier 1 timeout: 15 mp/forrás, összesen max 20 mp/forrás
            # Az overall TimeoutError-t elkapjuk: a már begyűjtött hírek megmaradnak
            _TIER1_TASK_TIMEOUT = 15
            _TIER1_OVERALL_TIMEOUT = _TIER1_TASK_TIMEOUT * max(2, len(tier1_tasks))
            with ThreadPoolExecutor(max_workers=len(tier1_tasks)) as executor:
                futures = {executor.submit(fn): name for name, fn in tier1_tasks.items()}
                try:
                    for future in as_completed(futures, timeout=_TIER1_OVERALL_TIMEOUT):
                        source_name = futures[future]
                        try:
                            items = future.result(timeout=_TIER1_TASK_TIMEOUT)
                            all_news.extend(items)
                            print(f"  📰 {source_name}: {len(items)} cikk")
                        except TimeoutError:
                            print(f"  ⏱️ {source_name} timeout ({_TIER1_TASK_TIMEOUT}s), skip")
                        except Exception as e:
                            print(f"  ⚠️ {source_name} hiba: {e}")
                except TimeoutError:
                    # Néhány Tier 1 forrás nem végzett időben – folytatás a már begyűjtött hírekkel
                    remaining = [name for fut, name in futures.items() if not fut.done()]
                    for name in remaining:
                        print(f"  ⏱️ {name} overall timeout – skip")

        # ════════════════════════════════════════════════════════════
        # TIER 2 – Finnhub (rate-limited, 60/perc)
        # ════════════════════════════════════════════════════════════
        if is_us_ticker and self.finnhub_collector:
            can_use_finnhub = True
            if self.quota_manager:
                can_use_finnhub = self.quota_manager.can_use("finnhub")
                if can_use_finnhub:
                    self.quota_manager.record_use("finnhub")
            if can_use_finnhub:
                try:
                    finnhub_items = self._collect_from_finnhub(
                        ticker_symbol, lookback_hours, sentiment_analyzer
                    )
                    all_news.extend(finnhub_items)
                    print(f"  📰 finnhub: {len(finnhub_items)} cikk")
                except Exception as e:
                    print(f"  ⚠️ finnhub hiba: {e}")

        # ════════════════════════════════════════════════════════════
        # TIER 3 – Marketaux / GNews (csak ha kevés friss hír van)
        # ════════════════════════════════════════════════════════════
        if is_us_ticker:
            min_fresh = getattr(self.config, 'min_fresh_news_count', 3)
            fresh_count = self._count_fresh_news(all_news, hours=2)

            if fresh_count < min_fresh:
                print(f"  ℹ️ Tier 3 aktiválás: {fresh_count} friss hír < {min_fresh} küszöb")

                # Marketaux batch cache ellenőrzés
                if self.marketaux_collector and self.batch_cache:
                    cached = self.batch_cache.get_for_ticker(ticker_symbol)
                    if cached:
                        all_news.extend(cached)
                        print(f"  📰 marketaux_cache: {len(cached)} cikk")
                    elif self.quota_manager is None or self.quota_manager.can_use("marketaux"):
                        marketaux_items = self._collect_from_marketaux(ticker_symbol, lookback_hours)
                        all_news.extend(marketaux_items)
                        print(f"  📰 marketaux: {len(marketaux_items)} cikk")
                elif self.marketaux_collector:
                    marketaux_items = self._collect_from_marketaux(ticker_symbol, lookback_hours)
                    all_news.extend(marketaux_items)
                    print(f"  📰 marketaux: {len(marketaux_items)} cikk")

                # GNews fallback
                elif self.gnews_collector:
                    can_use_gnews = True
                    if self.quota_manager:
                        can_use_gnews = self.quota_manager.can_use("gnews")
                        if can_use_gnews:
                            self.quota_manager.record_use("gnews")
                    if can_use_gnews:
                        try:
                            gnews_items = self._collect_from_gnews(
                                ticker_symbol, sentiment_analyzer
                            )
                            all_news.extend(gnews_items)
                            print(f"  📰 gnews: {len(gnews_items)} cikk")
                        except Exception as e:
                            print(f"  ⚠️ gnews hiba: {e}")

        # ════════════════════════════════════════════════════════════
        # POST-PROCESS
        # ════════════════════════════════════════════════════════════
        all_news = self._deduplicate_news(all_news)
        all_news.sort(key=lambda x: x.published_at, reverse=True)

        # LLM Context Check – deduplikacio utan, DB mentes elott
        self._run_llm_context_check(all_news, ticker_symbol, company_name)

        if save_to_db and self.db and all_news:
            self._save_news_to_db(all_news, ticker_symbol)

        return all_news

    # ------------------------------------------------------------------
    # TIER 1 helpers
    # ------------------------------------------------------------------

    def _collect_from_sec_edgar(
        self,
        ticker_symbol: str,
        lookback_hours: int,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer',
    ) -> List[NewsItem]:
        """SEC EDGAR – egyetlen ticker wrapper (globális feed 1 kérésből)."""
        try:
            result = self.sec_edgar_collector.collect(
                tickers=[ticker_symbol],
                lookback_hours=lookback_hours,
                sentiment_analyzer=sentiment_analyzer,
            )
            return result.get(ticker_symbol, [])
        except Exception as e:
            print(f"  ❌ SEC EDGAR hiba ({ticker_symbol}): {e}")
            return []

    def _collect_from_bet(
        self,
        ticker_symbol: str,
        lookback_hours: int,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer',
    ) -> List[NewsItem]:
        """BÉT RSS – egyetlen ticker wrapper."""
        try:
            result = self.bet_rss_collector.collect(
                tickers=[ticker_symbol],
                lookback_hours=lookback_hours,
                sentiment_analyzer=sentiment_analyzer,
            )
            return result.get(ticker_symbol, [])
        except Exception as e:
            print(f"  ❌ BÉT RSS hiba ({ticker_symbol}): {e}")
            return []

    def _collect_from_yahoo(
        self,
        ticker_symbol: str,
        lookback_hours: int,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer',
    ) -> List[NewsItem]:
        """Yahoo Finance RSS (korlátlan, Tier 1 fallback)."""
        try:
            news_items = self.yahoo_collector.collect_news(
                ticker_symbol=ticker_symbol,
                max_articles=20,
            )
            analyzed_items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            for item in news_items:
                if item['published_at'] < cutoff_time:
                    continue
                text = f"{item['title']}. {item.get('description', '')}"
                sentiment = sentiment_analyzer.analyze_text(text, ticker_symbol)
                analyzed_items.append(NewsItem(
                    title=item['title'],
                    description=item.get('description', ''),
                    url=item['url'],
                    published_at=item['published_at'],
                    source="Yahoo Finance",
                    sentiment_score=sentiment['score'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_label=sentiment['label'],
                    credibility=0.90,
                ))
            return analyzed_items
        except Exception as e:
            print(f"  ❌ Yahoo Finance hiba: {e}")
            return []

    # ------------------------------------------------------------------
    # TIER 2 helpers
    # ------------------------------------------------------------------

    def _collect_from_finnhub(
        self,
        ticker_symbol: str,
        lookback_hours: int,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer',
    ) -> List[NewsItem]:
        """Finnhub API (60 req/perc)."""
        try:
            lookback_days = max(1, lookback_hours // 24)
            news_items = self.finnhub_collector.collect_news(
                ticker_symbol=ticker_symbol,
                lookback_days=lookback_days,
                max_articles=20,
            )
            analyzed_items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            for item in news_items:
                if item['published_at'] < cutoff_time:
                    continue
                text = f"{item['title']}. {item.get('description', '')}"
                sentiment = sentiment_analyzer.analyze_text(text, ticker_symbol)
                analyzed_items.append(NewsItem(
                    title=item['title'],
                    description=item.get('description', ''),
                    url=item['url'],
                    published_at=item['published_at'],
                    source=f"Finnhub-{item['source']}",
                    sentiment_score=sentiment['score'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_label=sentiment['label'],
                    credibility=0.85,
                ))
            return analyzed_items
        except Exception as e:
            print(f"  ❌ Finnhub hiba: {e}")
            return []

    # ------------------------------------------------------------------
    # TIER 3 helpers
    # ------------------------------------------------------------------

    def _collect_from_marketaux(
        self,
        ticker_symbol: str,
        lookback_hours: int,
    ) -> List[NewsItem]:
        """Marketaux API (100 req/nap, beépített AI sentiment)."""
        try:
            lookback_days = max(1, lookback_hours // 24)
            news_items = self.marketaux_collector.collect_news(
                ticker_symbol=ticker_symbol,
                lookback_days=lookback_days,
                max_articles=20,
            )
            analyzed_items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            for item in news_items:
                if item['published_at'] < cutoff_time:
                    continue
                sentiment_score = item.get('sentiment_score', 0.0)
                if sentiment_score > 0.3:
                    label, conf = 'positive', min(abs(sentiment_score), 1.0)
                elif sentiment_score < -0.3:
                    label, conf = 'negative', min(abs(sentiment_score), 1.0)
                else:
                    label, conf = 'neutral', 0.5
                analyzed_items.append(NewsItem(
                    title=item['title'],
                    description=item.get('description', ''),
                    url=item['url'],
                    published_at=item['published_at'],
                    source=f"Marketaux-{item['source']}",
                    sentiment_score=sentiment_score,
                    sentiment_confidence=conf,
                    sentiment_label=label,
                    credibility=item.get('credibility', 0.88),
                ))
            return analyzed_items
        except Exception as e:
            print(f"  ❌ Marketaux hiba: {e}")
            return []

    def _collect_from_gnews(
        self,
        ticker_symbol: str,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer',
    ) -> List[NewsItem]:
        """GNews API (100 req/nap)."""
        try:
            news_items = self.gnews_collector.collect_news(
                ticker_symbol=ticker_symbol,
                max_articles=10,
            )
            analyzed_items = []
            for item in news_items:
                text = f"{item.get('title', '')}. {item.get('description', '')}"
                sentiment = sentiment_analyzer.analyze_text(text, ticker_symbol)
                published_str = item.get('published_at', '')
                if isinstance(published_str, str):
                    try:
                        published_at = datetime.fromisoformat(
                            published_str.replace('Z', '+00:00')
                        )
                    except Exception:
                        published_at = datetime.now(timezone.utc)
                else:
                    published_at = published_str or datetime.now(timezone.utc)

                analyzed_items.append(NewsItem(
                    title=item.get('title', ''),
                    description=item.get('description', ''),
                    url=item.get('url', ''),
                    published_at=published_at,
                    source="GNews",
                    sentiment_score=sentiment['score'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_label=sentiment['label'],
                    credibility=0.75,
                ))
            return analyzed_items
        except Exception as e:
            print(f"  ❌ GNews hiba: {e}")
            return []

    # ------------------------------------------------------------------
    # DISABLED (fizetős upgrade esetére megőrizve)
    # ------------------------------------------------------------------

    def _collect_from_alphavantage(
        self,
        ticker_symbol: str,
        lookback_hours: int,
        sentiment_analyzer: 'MultilingualSentimentAnalyzer',
    ) -> List[NewsItem]:
        """
        DISABLED – Alpha Vantage free tier: több órás-napos késleltetés + 25 req/nap limit.
        Kód megmarad fizetős upgrade esetére (v2.0 stratégia, Fázis 1).
        NEM hívódik a collect_news() flow-ból.
        """
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'NEWS_SENTIMENT',
            'tickers': ticker_symbol,
            'apikey': self.config.alphavantage_key,
            'limit': 50,
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            news_items = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
            for item in data.get('feed', []):
                time_str = item.get('time_published', '')
                if time_str:
                    time_published = datetime.strptime(time_str, '%Y%m%dT%H%M%S')
                    time_published = time_published.replace(tzinfo=timezone.utc)
                else:
                    time_published = datetime.now(timezone.utc)
                if time_published < cutoff_time:
                    continue
                text = f"{item.get('title', '')}. {item.get('summary', '')}"
                sentiment = sentiment_analyzer.analyze_text(text, ticker_symbol)
                news_items.append(NewsItem(
                    title=item.get('title', ''),
                    description=item.get('summary', ''),
                    url=item.get('url', ''),
                    published_at=time_published,
                    source='Alpha Vantage',
                    sentiment_score=sentiment['score'],
                    sentiment_confidence=sentiment['confidence'],
                    sentiment_label=sentiment['label'],
                    credibility=0.80,
                ))
            return news_items
        except Exception as e:
            print(f"❌ Alpha Vantage error: {e}")
            return []

    # ------------------------------------------------------------------
    # Deduplikáció (URL + Jaccard title-similarity)
    # ------------------------------------------------------------------

    def _deduplicate_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        Duplikáció szűrés két szinten:
        1. Pontos URL egyezés
        2. Jaccard title-similarity ≥ 0.80 AND ≤ 30 perces időablak
           → magasabb credibility-jű marad meg
        """
        # 1. URL-alapú szűrés
        seen_urls: set = set()
        url_unique: List[NewsItem] = []
        for item in news_items:
            if item.url and item.url not in seen_urls:
                seen_urls.add(item.url)
                url_unique.append(item)

        # 2. Jaccard title-similarity szűrés
        final: List[NewsItem] = []
        for candidate in url_unique:
            is_dup = False
            for existing in final:
                if self._is_jaccard_duplicate(candidate, existing):
                    # A magasabb credibility-jűt tartjuk meg
                    if candidate.credibility > existing.credibility:
                        final.remove(existing)
                        # nem breakelünk, hátha több duplikátumal is egyezik
                    else:
                        is_dup = True
                    break
            if not is_dup:
                final.append(candidate)

        removed = len(news_items) - len(final)
        if removed > 0:
            print(f"🔄 Deduplikáció: {removed} duplikátum eltávolítva (URL+Jaccard)")
        return final

    @staticmethod
    def _is_jaccard_duplicate(
        item1: NewsItem,
        item2: NewsItem,
        threshold: float = _JACCARD_THRESHOLD,
        time_window_sec: int = _JACCARD_TIME_WINDOW,
    ) -> bool:
        """
        True ha a két cikk valószínűleg ugyanaz a tartalom.

        Feltételek (mindkettő teljesüljön):
        - Jaccard(title1, title2) ≥ threshold
        - |published_at1 - published_at2| ≤ time_window_sec
        """
        words1 = set(item1.title.lower().split())
        words2 = set(item2.title.lower().split())
        union = words1 | words2
        if not union:
            return False
        jaccard = len(words1 & words2) / len(union)
        if jaccard < threshold:
            return False
        # Időablak ellenőrzés
        try:
            time_diff = abs((item1.published_at - item2.published_at).total_seconds())
            return time_diff <= time_window_sec
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Segédfüggvények
    # ------------------------------------------------------------------

    def _count_fresh_news(self, news_items: List[NewsItem], hours: int = 2) -> int:
        """Az elmúlt `hours` órában megjelent cikkek száma."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return sum(1 for item in news_items if item.published_at >= cutoff)

    def _run_llm_context_check(
        self,
        news_items: List[NewsItem],
        ticker_symbol: str,
        company_name: str,
    ) -> None:
        """
        LLM arfolyamhatas scoring – deduplikacio utan, DB mentes elott.
        FinBERT parallellel fut: az active_score az LLM vagy FinBERT score lesz.
        Ha LLM ki van kapcsolva vagy hiba van, active_score = sentiment_score.
        """
        if not news_items:
            return

        # LLM disabled: active_score = finbert (sentiment_score)
        if not self.config.llm_context_enabled:
            for item in news_items:
                if getattr(item, 'active_score', None) is None:
                    item.active_score = item.sentiment_score
                    item.active_score_source = 'finbert'
            return

        from src.config import LLM_API_KEY
        from src.llm_context_checker import LLMContextChecker

        try:
            checker = LLMContextChecker(
                api_key=LLM_API_KEY,
                model=self.config.llm_model,
                timeout=self.config.llm_timeout,
                max_concurrent=self.config.llm_max_concurrent,
            )
            results = checker.check_batch(news_items, ticker_symbol, company_name)

            llm_ok = 0
            llm_fail = 0
            for item, result in zip(news_items, results):
                if result.success:
                    item.active_score = result.llm_score
                    item.active_score_source = 'llm'
                    item.llm_impact_duration = result.impact_duration
                    # Extra mezok DB-be
                    item.llm_score = result.llm_score
                    item.llm_price_impact = result.price_impact
                    item.llm_impact_level = result.impact_level
                    item.llm_catalyst_type = result.catalyst_type
                    item.llm_priced_in = result.priced_in
                    item.llm_confidence = result.confidence
                    item.llm_reason = result.reason
                    item.llm_latency_ms = result.latency_ms
                    llm_ok += 1
                else:
                    item.active_score = item.sentiment_score
                    item.active_score_source = 'finbert'
                    llm_fail += 1

            print(f"  [LLM] {ticker_symbol}: {llm_ok} OK, {llm_fail} fallback-to-FinBERT")

        except Exception as e:
            print(f"  [LLM] Batch check failed for {ticker_symbol}: {e} -- fallback to FinBERT")
            for item in news_items:
                item.active_score = item.sentiment_score
                item.active_score_source = 'finbert'

    def _save_news_to_db(self, news_items: List[NewsItem], ticker_symbol: str):
        """Hírek mentése az adatbázisba."""
        try:
            from src.db_helpers import save_news_item_to_db
            saved_count = sum(
                1 for item in news_items
                if save_news_item_to_db(item, ticker_symbol, self.db)
            )
            if saved_count > 0:
                print(f"💾 Mentve: {saved_count} hír az adatbázisba")
        except Exception as e:
            print(f"⚠️ DB mentés sikertelen: {e}")


if __name__ == "__main__":
    print("✅ TrendSignal News Collector v3.0 – Tier-vezérelt stratégia")
    print("📊 TIER 1: SEC EDGAR + Nasdaq RSS + BÉT RSS + Seeking Alpha + Yahoo (korlátlan)")
    print("📊 TIER 2: Finnhub (60/perc)")
    print("📊 TIER 3: Marketaux batch (100/nap) + GNews (100/nap) – csak ha szükséges")
    print("🚫 KIZÁRVA: NewsAPI (1 hónapos delay) + AlphaVantage (napos delay + 25 req/nap)")
    print("🔄 Deduplikáció: URL + Jaccard ≥0.80, 30 perces ablak")
