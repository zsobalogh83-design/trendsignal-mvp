# Magyar Hírforrások Használati Útmutató

## 🇭🇺 Elérhető Magyar RSS Feed-ek

### Portfolio.hu (Legjobb BÉT ticker-ekhez)
- **Befektetés:** https://www.portfolio.hu/rss/befektetes.xml (credibility: 90%)
- **Bank:** https://www.portfolio.hu/rss/bank.xml (credibility: 90%)
- **Gazdaság:** https://www.portfolio.hu/rss/gazdasag.xml (credibility: 85%)
- **Üzlet:** https://www.portfolio.hu/rss/uzlet.xml (credibility: 85%)

### Egyéb Magyar Források
- **Telex.hu:** https://telex.hu/rss (credibility: 80%)
- **HVG.hu:** https://hvg.hu/rss (credibility: 85%)
- **Index.hu:** https://index.hu/24ora/rss/ (credibility: 75%)

---

## 🚀 Használat Colab-ban

### 1. Telepítés

```python
# Install feedparser (RSS parsing)
!pip install feedparser --quiet

# Pull latest code
%cd /content/trendsignal-mvp
!git pull origin main

# Reload modules
import sys
if 'hungarian_news' in sys.modules:
    del sys.modules['hungarian_news']

sys.path.insert(0, '/content/trendsignal-mvp/src')
```

### 2. Csak Magyar Hírek

```python
from hungarian_news import HungarianNewsCollector
from config import get_config

config = get_config()
collector = HungarianNewsCollector(config)

# OTP Bank magyar hírei
news = collector.collect_news(
    ticker_symbol='OTP.BD',
    company_name='OTP Bank',
    lookback_hours=24
)

print(f"Collected {len(news)} Hungarian news items")

# Display first 3
for i, item in enumerate(news[:3]):
    print(f"\n{i+1}. {item.title}")
    print(f"   Sentiment: {item.sentiment_score:+.2f} ({item.sentiment_label})")
    print(f"   Source: {item.source}")
    print(f"   Age: {item.get_age_hours():.1f}h ago")
```

### 3. Kombinált (Angol + Magyar)

```python
from hungarian_news import EnhancedNewsCollector

collector = EnhancedNewsCollector(config)

# Minden forrásból (NewsAPI + Alpha Vantage + Portfolio.hu + Telex + stb.)
news = collector.collect_all_news(
    ticker_symbol='OTP.BD',
    company_name='OTP Bank',
    lookback_hours=24,
    include_hungarian=True,  # Magyar források
    include_english=True     # Angol források
)

print(f"\nTotal: {len(news)} news items")
```

### 4. Teljes Signal Generation Magyar Hírekkel

```python
from hungarian_news import EnhancedNewsCollector
from signal_generator import SignalGenerator
from utils import fetch_price_data

# Collect news (magyar + angol)
collector = EnhancedNewsCollector(config)
news = collector.collect_all_news('OTP.BD', 'OTP Bank', lookback_hours=24)

# Fetch price data
prices = fetch_price_data('OTP.BD', interval='1d', period='3mo')

# Generate signal
generator = SignalGenerator(config)
signal = generator.generate_signal('OTP.BD', 'OTP Bank', news, prices)

# Display
signal.display()
```

---

## 📊 BÉT Ticker Keywords

A rendszer automatikusan keresi ezeket a kulcsszavakat:

```python
OTP.BD      → 'otp', 'otp bank'
MOL.BD      → 'mol', 'mol nyrt', 'mol group'
RICHTER.BD  → 'richter', 'richter gedeon', 'gedeon richter'
MTELEKOM.BD → 'magyar telekom', 'telekom', 'mtelekom'
4IG.BD      → '4ig', 'jászai gellért', '4ig csoport'
```

---

## 🧪 Tesztelés

### Gyors RSS Teszt

```python
# Run test script
!python tests/test_hungarian_rss.py
```

### Portfolio.hu Befektetés Feed Ellenőrzés

```python
import feedparser

feed = feedparser.parse('https://www.portfolio.hu/rss/befektetes.xml')
print(f"Feed title: {feed.feed.title}")
print(f"Total entries: {len(feed.entries)}")
print(f"\nLatest 5 articles:")

for i, entry in enumerate(feed.entries[:5]):
    print(f"\n{i+1}. {entry.title}")
    print(f"   Published: {entry.published}")
```

---

## 🎯 Példa Output

```
📰 Collecting Hungarian news for OTP.BD...

✅ Portfolio.hu Befektetés: Collected 2 relevant items
✅ Portfolio.hu Bank: Collected 1 relevant items
✅ Portfolio.hu Gazdaság: Collected 0 relevant items
✅ Telex.hu: Collected 1 relevant items
🔄 Removed 0 duplicate Hungarian news items

✅ Hungarian RSS: Collected 4 total news items

📊 Total collected: 4 news items
   English: 0
   Hungarian: 4
```

---

## ⚙️ Konfiguráció

Ha csak bizonyos forrásokat akarsz:

```python
collector = HungarianNewsCollector(config)

# Csak Portfolio.hu Befektetés
news = collector.collect_news(
    ticker_symbol='OTP.BD',
    company_name='OTP Bank',
    sources=['portfolio_befektetes']  # Csak ez
)
```

---

## 🔍 Relevancia Szűrés

**MVP:** Egyszerű keyword matching
- Ticker szimbólum (pl. "otp")
- Cég név részek (pl. "otp bank")

**Phase 2:** (később)
- NER (Named Entity Recognition)
- Zero-shot classification
- Multilingual embeddings

---

**Last Updated:** 2024-12-27  
**Status:** Ready for testing! 🚀
