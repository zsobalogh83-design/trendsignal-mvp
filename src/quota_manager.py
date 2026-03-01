"""
TrendSignal – Centrális API Quota Manager
SQLite perzisztenciával: backend újraindítás után sem vesznek el a számlálók.

Kezelt források:
  - marketaux: 100 req/nap (95 + 5 buffer)
  - gnews:     100 req/nap (95 + 5 buffer)
  - finnhub:   60 req/perc (55 + 5 buffer)

Verzió: 1.0 | 2026-02-25
"""

import threading
from datetime import datetime, date, timezone
from typing import Dict

from sqlalchemy.orm import Session

# Napi limitek (source → max)
DAILY_LIMITS: Dict[str, int] = {
    "marketaux": 95,   # 100/nap – 5 buffer
    "gnews": 95,       # 100/nap – 5 buffer
}

# Percenkénti rate limitek
RATE_LIMITS: Dict[str, int] = {
    "finnhub": 55,     # 60/perc – 5 buffer
}


class QuotaManager:
    """
    Centrális quota tracker az összes rate-limited API forráshoz.

    Használat:
        qm = QuotaManager(db_session)  # vagy QuotaManager() in-memory módban
        if qm.can_use("marketaux"):
            ...  # API hívás
        qm.record_use("marketaux")
    """

    def __init__(self, db: Session = None):
        """
        Args:
            db: SQLAlchemy session a perzisztenciához.
                Ha None, in-memory (thread-safe) módban fut.
        """
        self.db = db
        self._lock = threading.Lock()

        # In-memory gyorsítótár: {source: {date: count}}
        self._daily_cache: Dict[str, Dict[date, int]] = {}

        # Percenkénti rate tracking: {source: [(timestamp, count), ...]}
        self._rate_cache: Dict[str, list] = {}

        # DB-ből betöltjük a mai napot induláskor
        if self.db:
            self._load_from_db()

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def can_use(self, source: str) -> bool:
        """True ha az adott forrásnak van szabad kvótája."""
        with self._lock:
            if source in DAILY_LIMITS:
                return self._get_daily_count(source) < DAILY_LIMITS[source]
            if source in RATE_LIMITS:
                return self._get_rate_count(source) < RATE_LIMITS[source]
            # Korlátlan forrás (pl. RSS)
            return True

    def record_use(self, source: str):
        """Egy felhasználást rögzít az adott forráshoz."""
        with self._lock:
            if source in DAILY_LIMITS:
                self._increment_daily(source)
            elif source in RATE_LIMITS:
                self._increment_rate(source)

    def get_daily_remaining(self, source: str) -> int:
        """Visszaadja a mai napon még felhasználható kérések számát."""
        with self._lock:
            if source not in DAILY_LIMITS:
                return 999999
            used = self._get_daily_count(source)
            return max(0, DAILY_LIMITS[source] - used)

    def get_daily_used(self, source: str) -> int:
        """Visszaadja a mai napon eddig felhasznált kérések számát."""
        with self._lock:
            return self._get_daily_count(source)

    def status(self) -> Dict[str, Dict]:
        """Visszaadja az összes forrás aktuális állapotát."""
        result = {}
        with self._lock:
            for source, limit in DAILY_LIMITS.items():
                used = self._get_daily_count(source)
                result[source] = {
                    "type": "daily",
                    "limit": limit,
                    "used": used,
                    "remaining": max(0, limit - used),
                    "available": used < limit,
                }
            for source, limit in RATE_LIMITS.items():
                used = self._get_rate_count(source)
                result[source] = {
                    "type": "rate_per_minute",
                    "limit": limit,
                    "used": used,
                    "remaining": max(0, limit - used),
                    "available": used < limit,
                }
        return result

    # ------------------------------------------------------------------
    # INTERNAL – DAILY
    # ------------------------------------------------------------------

    def _get_daily_count(self, source: str) -> int:
        today = date.today()
        cache = self._daily_cache.get(source, {})
        return cache.get(today, 0)

    def _increment_daily(self, source: str):
        today = date.today()
        if source not in self._daily_cache:
            self._daily_cache[source] = {}
        # Reset ha új nap
        if today not in self._daily_cache[source]:
            self._daily_cache[source] = {today: 0}
        self._daily_cache[source][today] += 1

        # DB perzisztencia
        if self.db:
            self._persist_daily(source, today, self._daily_cache[source][today])

    def _load_from_db(self):
        """Mai napi számláló betöltése a DB-ből induláskor."""
        try:
            from src.models import ApiQuota
            today = date.today()
            rows = self.db.query(ApiQuota).filter(ApiQuota.date == today).all()
            for row in rows:
                if row.source not in self._daily_cache:
                    self._daily_cache[row.source] = {}
                self._daily_cache[row.source][today] = row.daily_count
        except Exception as e:
            print(f"⚠️ QuotaManager: DB betöltés sikertelen – in-memory módban fut: {e}")

    def _persist_daily(self, source: str, day: date, count: int):
        """Napi számláló írása/frissítése a DB-be."""
        try:
            from src.models import ApiQuota
            row = self.db.query(ApiQuota).filter(
                ApiQuota.source == source,
                ApiQuota.date == day
            ).first()
            if row:
                row.daily_count = count
                row.updated_at = datetime.now(timezone.utc)
            else:
                row = ApiQuota(
                    source=source,
                    date=day,
                    daily_count=count,
                    last_reset_at=datetime.now(timezone.utc),
                )
                self.db.add(row)
            self.db.commit()
        except Exception as e:
            print(f"⚠️ QuotaManager: DB írás sikertelen ({source}): {e}")
            try:
                self.db.rollback()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # INTERNAL – RATE (percenkénti)
    # ------------------------------------------------------------------

    def _get_rate_count(self, source: str) -> int:
        """Az elmúlt 60 másodpercben tett kérések száma."""
        now = datetime.now(timezone.utc).timestamp()
        window_start = now - 60.0
        events = self._rate_cache.get(source, [])
        # Régi eseményeket eltávolítjuk
        fresh = [t for t in events if t >= window_start]
        self._rate_cache[source] = fresh
        return len(fresh)

    def _increment_rate(self, source: str):
        now = datetime.now(timezone.utc).timestamp()
        if source not in self._rate_cache:
            self._rate_cache[source] = []
        self._rate_cache[source].append(now)
        # Trim régi eseményeket (>60s)
        window_start = now - 60.0
        self._rate_cache[source] = [t for t in self._rate_cache[source] if t >= window_start]


# ------------------------------------------------------------------
# Singleton (opcionális, scheduler számára)
# ------------------------------------------------------------------
_global_quota_manager: QuotaManager = None
_global_lock = threading.Lock()


def get_quota_manager(db: Session = None) -> QuotaManager:
    """
    Globális QuotaManager singleton.
    Az első hívásnál jön létre db sessionnel, utána mindig ugyanazt adja vissza.
    """
    global _global_quota_manager
    with _global_lock:
        if _global_quota_manager is None:
            _global_quota_manager = QuotaManager(db)
        return _global_quota_manager


if __name__ == "__main__":
    qm = QuotaManager()
    print("QuotaManager teszt (in-memory):")
    print(f"  marketaux can_use: {qm.can_use('marketaux')}")
    for i in range(96):
        qm.record_use("marketaux")
    print(f"  marketaux can_use after 96 uses: {qm.can_use('marketaux')}")
    print(f"  Status: {qm.status()}")
