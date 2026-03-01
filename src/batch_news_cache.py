"""
TrendSignal – Batch News Cache
TTL-alapú cache a Marketaux multi-ticker batch kérésekhez.

Cél: 7 egyedi kérés helyett 1-2 batch kérés → ~72% kvóta megtakarítás.
TTL: 900 másodperc (1 scheduler ciklus ideje alatt érvényes).

Működés:
  1. Az első ticker hívja a batch-et és tölti a cache-t.
  2. A többi ticker a cache-ből veszi ki a saját cikkeit.
  3. 900s után a cache érvénytelen, a következő kérés új batch-et indít.

Verzió: 1.0 | 2026-02-25
"""

import threading
import time
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.sentiment_analyzer import NewsItem

# Cache élettartam másodpercben (1 scheduler ciklus)
CACHE_TTL_SECONDS = 900


class BatchNewsCache:
    """
    Thread-safe TTL cache Marketaux batch eredményekhez.

    Egy batch response-ból az entities.symbol mezőre szűrve
    szétosztja a cikkeket az egyes tickerek között.
    """

    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS):
        self._lock = threading.Lock()
        self._ttl = ttl_seconds
        # {ticker_symbol: List[NewsItem]}
        self._cache: Dict[str, List] = {}
        self._populated_at: float = 0.0
        self._batch_tickers: List[str] = []

    def is_valid(self) -> bool:
        """True ha a cache még érvényes (TTL nem járt le)."""
        return (time.monotonic() - self._populated_at) < self._ttl

    def is_empty(self) -> bool:
        """True ha a cache üres VAGY lejárt."""
        return not self._cache or not self.is_valid()

    def get_for_ticker(self, ticker: str) -> List['NewsItem']:
        """A cache-ből visszaadja az adott ticker cikkeit (ha érvényes)."""
        with self._lock:
            if not self.is_valid():
                return []
            return list(self._cache.get(ticker, []))

    def populate(self, batch_result: Dict[str, List['NewsItem']]):
        """
        Feltölti a cache-t egy batch eredménnyel.

        Args:
            batch_result: Dict[ticker → List[NewsItem]] (MarketauxCollector.collect_batch()-ból)
        """
        with self._lock:
            self._cache = {k: list(v) for k, v in batch_result.items()}
            self._populated_at = time.monotonic()
            self._batch_tickers = list(batch_result.keys())

    def invalidate(self):
        """Kényszer-érvényteleníti a cache-t."""
        with self._lock:
            self._cache = {}
            self._populated_at = 0.0

    @property
    def age_seconds(self) -> float:
        """Cache kora másodpercben."""
        return time.monotonic() - self._populated_at

    @property
    def remaining_ttl(self) -> float:
        """Hátralévő érvényességi idő másodpercben."""
        return max(0.0, self._ttl - self.age_seconds)

    def __repr__(self):
        return (
            f"<BatchNewsCache tickers={self._batch_tickers} "
            f"valid={self.is_valid()} age={self.age_seconds:.0f}s>"
        )


if __name__ == "__main__":
    cache = BatchNewsCache(ttl_seconds=10)
    print(f"Üres cache: {cache}")
    print(f"is_empty: {cache.is_empty()}")
    cache.populate({"AAPL": [], "TSLA": []})
    print(f"Feltöltött cache: {cache}")
    print(f"is_empty: {cache.is_empty()}")
    print(f"AAPL: {cache.get_for_ticker('AAPL')}")
