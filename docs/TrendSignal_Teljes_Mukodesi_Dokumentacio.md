# TrendSignal MVP - Teljes Működési Dokumentáció

**Verzió:** 1.0  
**Dátum:** 2025-01-31  
**Állapot:** Production Ready  

---

## 📋 Tartalomjegyzék

1. [Rendszer Áttekintés](#1-rendszer-áttekintés)
2. [Architektúra](#2-architektúra)
3. [Backend Modulok](#3-backend-modulok)
4. [Sentiment Analízis Rendszer](#4-sentiment-analízis-rendszer)
5. [Technikai Analízis Rendszer](#5-technikai-analízis-rendszer)
6. [Risk Management Rendszer](#6-risk-management-rendszer)
7. [Signal Generálás](#7-signal-generálás)
8. [Konfigurációs Rendszer](#8-konfigurációs-rendszer)
9. [Frontend Alkalmazás](#9-frontend-alkalmazás)
10. [Adatbázis Struktúra](#10-adatbázis-struktúra)
11. [API Endpointok](#11-api-endpointok)
12. [Kalkulációs Formulák](#12-kalkulációs-formulák)
13. [Telepítés és Használat](#13-telepítés-és-használat)

---

## 1. Rendszer Áttekintés

### 1.1 Fő Funkció

A TrendSignal egy **sentiment-driven trading signal generáló alkalmazás**, amely kombinált scoring rendszert használ day trading és swing trading célokra.

**Scoring Súlyok (konfigurálható):**
- **70% Sentiment** - Hírfolyam alapú AI analízis (FinBERT)
- **20% Technical** - Technikai indikátorok (7 indikátor, multi-timeframe)
- **10% Risk** - Kockázat menedzsment (volatilitás, S/R proximity)

### 1.2 Támogatott Piacok

**US Blue-Chip Részvények:**
- AAPL (Apple Inc.)
- TSLA (Tesla Inc.)
- MSFT (Microsoft Corp.)
- NVDA (Nvidia Corp.)

**Magyar BÉT Részvények:**
- MOL.BD (MOL Magyar Olaj- és Gázipari Nyrt.)
- OTP.BD (OTP Bank Nyrt.)

### 1.3 Kulcs Jellemzők

✅ **FinBERT AI sentiment analysis** - ProsusAI/finbert model  
✅ **Time-decay model** - 24 órás időablak, exponenciális súlycsökkenés  
✅ **Multi-timeframe technical analysis** - 5m/1h/1d/15m kombinált elemzés  
✅ **ATR-based stop loss/take profit** - Volatilitás-alapú szintek  
✅ **Dinamikus konfiguráció** - Real-time súlymódosítás backend restart nélkül  
✅ **Multi-source news** - GNews, Alpha Vantage, NewsAPI, Magyar RSS feedek  
✅ **Support/Resistance detection** - DBSCAN clustering algoritmus  

---

## 2. Architektúra

### 2.1 Technológiai Stack

**Backend:**
```
- Python 3.10+
- FastAPI (REST API framework)
- SQLAlchemy (ORM)
- SQLite/PostgreSQL (Database)
- FinBERT (transformers, PyTorch)
- yfinance (Market data)
- scikit-learn (DBSCAN clustering)
```

**Frontend:**
```
- React 18 + TypeScript
- Vite (Build tool)
- TailwindCSS (Styling)
- React Query (State management)
- Lucide React (Icons)
```

### 2.2 Rendszer Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                         │
│  - Dashboard (Signal lista, filterek)                       │
│  - Configuration (Súlyok, thresholds)                       │
│  - News Feed (Hírfolyam megjelenítés)                       │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API (HTTP/JSON)
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  BACKEND (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API Layer (api.py, config_api.py, signals_api.py) │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        ↓                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │        Business Logic (signal_generator.py)         │   │
│  └─────────────────────┬───────────────────────────────┘   │
│                        ↓                                    │
│  ┌──────────────┬──────────────────┬────────────────────┐  │
│  │  Sentiment   │   Technical      │   Risk             │  │
│  │  Analyzer    │   Analyzer       │   Calculator       │  │
│  └──────┬───────┴────────┬─────────┴─────────┬──────────┘  │
│         ↓                ↓                   ↓              │
│  ┌──────────────┬──────────────────┬────────────────────┐  │
│  │ News         │ Market Data      │ Technical          │  │
│  │ Collector    │ (yfinance)       │ Indicators         │  │
│  └──────────────┴──────────────────┴────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              DATABASE (SQLite/PostgreSQL)                   │
│  - Tickers                                                  │
│  - NewsItems                                                │
│  - Signals                                                  │
│  - TechnicalIndicators                                      │
│  - PriceData                                                │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Fájlstruktúra

```
trendsignal-mvp/
├── src/                              # Backend core
│   ├── config.py                     # Konfiguráció (weights, thresholds)
│   ├── signal_generator.py           # Fő signal logika
│   ├── sentiment_analyzer.py         # Sentiment számítás
│   ├── finbert_analyzer.py           # FinBERT wrapper
│   ├── multilingual_sentiment.py     # Nyelv routing (en/hu)
│   ├── technical_analyzer.py         # Technikai indikátorok
│   ├── news_collector.py             # Multi-source news
│   ├── hungarian_news.py             # Magyar RSS feedek
│   ├── ticker_keywords.py            # Magyar kulcsszavak
│   ├── models.py                     # SQLAlchemy modellek
│   ├── db_helpers.py                 # Database utilities
│   └── utils.py                      # Helper functions
│
├── api.py                            # FastAPI main app
├── config_api.py                     # Config REST endpoints
├── signals_api.py                    # Signal REST endpoints
├── main.py                           # Batch analysis
├── config.json                       # Perzisztált config
├── requirements.txt                  # Python deps
│
└── frontend/                         # React app
    ├── src/
    │   ├── pages/
    │   │   ├── Dashboard.tsx         # Signal dashboard
    │   │   ├── Configuration.tsx     # Config UI
    │   │   └── News.tsx              # News feed
    │   ├── hooks/
    │   │   └── useApi.ts             # React Query hooks
    │   ├── components/
    │   │   └── SignalCard.tsx        # Signal display
    │   └── App.tsx                   # Main routing
    ├── package.json
    └── vite.config.ts
```

---

## 3. Backend Modulok

### 3.1 config.py - Konfigurációs Rendszer

**Felelősség:** Központi konfiguráció kezelése, perzisztencia, dinamikus reload.

**Főbb Paraméterek:**

```python
@dataclass
class TrendSignalConfig:
    # API Keys
    newsapi_key: str
    alphavantage_key: str
    gnews_api_key: str
    
    # Component Weights (DINAMIKUS - config.json-ból betöltődik)
    sentiment_weight: float = 0.70    # 70%
    technical_weight: float = 0.20    # 20%
    risk_weight: float = 0.10         # 10%
    
    # Time Decay Model (24h ablak)
    decay_weights: Dict[str, float] = {
        '0-2h': 1.00,     # Fresh news - teljes súly
        '2-6h': 0.85,     # Még nagyon releváns
        '6-12h': 0.60,    # Intraday news
        '12-24h': 0.35    # Overnight news (fontos day trading-hez!)
    }
    
    # Decision Thresholds
    strong_buy_score: float = 65
    strong_buy_confidence: float = 0.75
    moderate_buy_score: float = 50
    moderate_buy_confidence: float = 0.65
    strong_sell_score: float = -65
    strong_sell_confidence: float = 0.75
    moderate_sell_score: float = -50
    moderate_sell_confidence: float = 0.65
    
    # Technical Indicator Periods
    sma_periods: Dict = {'short': 20, 'medium': 50, 'long': 200}
    macd_params: Dict = {'fast': 12, 'slow': 26, 'signal': 9}
    rsi_period: int = 14
    atr_period: int = 14
```

**Kritikus Funkciók:**

```python
def reload(self):
    """
    Config újratöltése config.json-ból
    MINDEN signal generálás előtt meghívódik!
    """
    saved_config = load_config_from_file()
    if saved_config:
        self.sentiment_weight = saved_config.get("SENTIMENT_WEIGHT", 0.70)
        self.technical_weight = saved_config.get("TECHNICAL_WEIGHT", 0.20)
        self.risk_weight = saved_config.get("RISK_WEIGHT", 0.10)
        # ... további paraméterek
```

**Perzisztencia:**
- **Mentés:** Frontend módosítások → PUT /api/v1/config/signal → `save_config_to_file()`
- **Betöltés:** Signal generálás előtt → `config.reload()` → Friss súlyok használata
- **Fájl:** `config.json` (JSON formátum, root mappában)

### 3.2 news_collector.py - News Aggregáció

**Felelősség:** Multi-source hírgyűjtés, deduplikáció, időalapú szűrés.

**Támogatott Források:**

| Forrás | Tickers | Delay | Credibility |
|--------|---------|-------|-------------|
| **GNews API** | US | 0h (real-time) | 0.85 |
| **Alpha Vantage** | US | 0h | 0.90 |
| **NewsAPI** | US | 24h (Free tier) | 0.75 |
| **Portfolio.hu RSS** | HU | 0h | 0.90 |
| **Telex/HVG/Index RSS** | HU | 0h | 0.80 |

**Stratégia:**
- **US tickers:** GNews (prioritás) + Alpha Vantage (pénzügyi fókusz)
- **HU tickers:** Magyar RSS feedek (Portfolio.hu, Telex, HVG, Index)

**Főbb Metódusok:**

```python
def collect_news(
    ticker_symbol: str,
    company_name: str,
    lookback_hours: int = 24,
    save_to_db: bool = True
) -> List[NewsItem]:
    """
    Összegyűjti az összes releváns hírt
    - Timezone-aware datetime-ok (UTC)
    - Deduplikáció (URL hash alapján)
    - Credibility weighting
    - Database mentés (opcionális)
    """
```

**NewsItem Struktúra:**
```python
@dataclass
class NewsItem:
    title: str
    description: str
    url: str
    published_at: datetime  # UTC timezone-aware
    source: str             # "GNews", "Alpha Vantage", stb.
    sentiment_score: float  # -1.0 to +1.0 (FinBERT)
    sentiment_confidence: float  # 0.0 to 1.0
    sentiment_label: str    # "positive", "negative", "neutral"
    credibility: float      # Source hitelessége (0.75-0.95)
    language: str = "en"    # "en" vagy "hu"
```

### 3.3 sentiment_analyzer.py - Sentiment Számítás

**Felelősség:** FinBERT-based sentiment analysis, keyword-based fallback (magyar).

**FinBERT Model:**
- **Model:** `ProsusAI/finbert` (Financial BERT)
- **Training:** 10,000+ financial news corpus
- **Output:** Positive/Negative/Neutral probabilities

**Sentiment Score Formula:**
```python
sentiment_score = (pos_prob - neg_prob) * (1 - neu_prob)

# Példa:
# pos=0.85, neg=0.03, neu=0.12
# sentiment = (0.85 - 0.03) * (1 - 0.12) = 0.72
```

**Indoklás:**
- `(pos_prob - neg_prob)` → Nettó sentiment irány
- `(1 - neu_prob)` → Neutral súlycsökkentés (bizonytalan hírek kevésbé befolyásolnak)

**Time Decay Aggregáció:**
```python
def aggregate_sentiment_from_news(news_items: List[NewsItem]) -> Dict:
    """
    Weighted average sentiment time decay-jel
    
    Folyamat:
    1. Minden hír kora (órákban) → Decay weight
    2. Credibility weight kombináció
    3. Weighted average számítás
    4. Confidence számítás (FinBERT + volume + consistency)
    """
    
    weighted_scores = []
    weights_sum = 0
    
    for item in news_items:
        age_hours = (now - item.published_at).total_seconds() / 3600
        
        # Decay weight kiválasztása
        if age_hours < 2:
            decay = 1.00
        elif age_hours < 6:
            decay = 0.85
        elif age_hours < 12:
            decay = 0.60
        else:  # 12-24h
            decay = 0.35
        
        # Final weight = decay * credibility
        weight = decay * item.credibility
        weighted_scores.append(item.sentiment_score * weight)
        weights_sum += weight
    
    weighted_avg = sum(weighted_scores) / weights_sum if weights_sum > 0 else 0
    
    return {
        "weighted_avg": weighted_avg,  # -1.0 to +1.0
        "confidence": calculate_confidence(...),
        "news_count": len(news_items)
    }
```

**Sentiment Confidence Komponensek:**

```python
confidence = (
    finbert_confidence * 0.40 +      # Model bizonyossága
    volume_factor * 0.35 +            # Hírek száma (10+ = 100%)
    consistency * 0.25                # Sentiment szórás (alacsony = jó)
)
```

### 3.4 technical_analyzer.py - Technikai Indikátorok

**Felelősség:** Multi-timeframe technical analysis, indikátor számítás, S/R detektálás.

**Multi-Timeframe Stratégia:**

| Timeframe | Adatmennyiség | Célterület |
|-----------|---------------|------------|
| **5m (Intraday)** | 50 candle | RSI, SMA20, current price |
| **1h (Trend)** | 720 candle (30 day) | SMA50, ADX |
| **1d (Daily)** | 126 candle (6 mo) | ATR (volatilitás) |
| **15m (S/R)** | 288 candle (3 day) | Support/Resistance pivots |

**Számított Indikátorok:**

1. **SMA (Simple Moving Average)**
   ```python
   sma_20 = close.rolling(window=20).mean()
   sma_50 = close.rolling(window=50).mean()
   sma_200 = close.rolling(window=200).mean()
   ```
   - **Golden Cross:** SMA20 > SMA50 > SMA200 → Bullish
   - **Death Cross:** SMA20 < SMA50 < SMA200 → Bearish

2. **RSI (Relative Strength Index)**
   ```python
   delta = close.diff()
   gain = delta.where(delta > 0, 0).rolling(14).mean()
   loss = -delta.where(delta < 0, 0).rolling(14).mean()
   rs = gain / loss
   rsi = 100 - (100 / (1 + rs))
   ```
   - **Oversold:** RSI < 30 → Buy signal
   - **Overbought:** RSI > 70 → Sell signal

3. **MACD (Moving Average Convergence Divergence)**
   ```python
   ema_12 = close.ewm(span=12).mean()
   ema_26 = close.ewm(span=26).mean()
   macd = ema_12 - ema_26
   signal = macd.ewm(span=9).mean()
   histogram = macd - signal
   ```
   - **Bullish:** MACD > Signal
   - **Bearish:** MACD < Signal

4. **ATR (Average True Range)** - KRITIKUS: Daily data-ból!
   ```python
   tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
   atr = tr.rolling(window=14).mean()
   atr_pct = (atr / close) * 100  # Volatilitás százalékban
   ```
   - **Használat:** Stop loss = Entry - (2 × ATR)
   - **Take profit:** Entry + (3 × ATR)

5. **ADX (Average Directional Index)**
   ```python
   # Trend erősség: 0-100
   # ADX < 25: Weak trend (ranging)
   # ADX 25-50: Strong trend
   # ADX > 50: Very strong trend
   ```

6. **Bollinger Bands**
   ```python
   middle = close.rolling(20).mean()
   std = close.rolling(20).std()
   upper = middle + (2 * std)
   lower = middle - (2 * std)
   ```

7. **Support/Resistance (DBSCAN Clustering)**
   ```python
   from sklearn.cluster import DBSCAN
   
   # Pivot pontok (local min/max)
   pivot_highs = high[(high.shift(1) < high) & (high.shift(-1) < high)]
   pivot_lows = low[(low.shift(1) > low) & (low.shift(-1) > low)]
   
   # Clustering (közeli pivotok összevonása)
   all_levels = pd.concat([pivot_highs, pivot_lows]).values
   clustering = DBSCAN(eps=0.04*close, min_samples=3, order=7)
   labels = clustering.fit_predict(all_levels)
   
   # Cluster centroids = S/R szintek
   support = [mean(cluster) for cluster in clusters if mean < price]
   resistance = [mean(cluster) for cluster in clusters if mean > price]
   ```

**Technical Score Kalkuláció:**

```python
technical_score = (
    trend_score * 0.40 +        # SMA alignment, MACD
    momentum_score * 0.30 +     # RSI, Stochastic
    volatility_score * 0.20 +   # Bollinger, ATR
    volume_score * 0.10         # Volume confirmation
)
# Range: -100 to +100
```

**Trend Score Részletes Kalkuláció:**
```python
def _calculate_trend_score(indicators: Dict, df: pd.DataFrame) -> float:
    """
    Trend komponens score (-100 to +100)
    
    Vizsgált jelzések:
    1. SMA alignment (Golden/Death Cross)
    2. MACD crossover
    3. Price vs SMA20 position
    """
    score = 0
    signals = 0
    
    # 1. SMA Alignment (Golden Cross / Death Cross)
    if all([indicators['sma_20'], indicators['sma_50'], indicators['sma_200']]):
        if (indicators['sma_20'] > indicators['sma_50'] > indicators['sma_200']):
            # Golden Cross: SMA20 > SMA50 > SMA200
            score += 100  # Erősen bullish
            signals += 1
        elif (indicators['sma_20'] < indicators['sma_50'] < indicators['sma_200']):
            # Death Cross: SMA20 < SMA50 < SMA200
            score -= 100  # Erősen bearish
            signals += 1
        else:
            # Partial alignment
            if indicators['sma_20'] > indicators['sma_50']:
                score += 50  # Közepes bullish
            else:
                score -= 50  # Közepes bearish
            signals += 1
    
    # 2. MACD Crossover
    if indicators['macd'] is not None and indicators['macd_signal'] is not None:
        if indicators['macd'] > indicators['macd_signal']:
            score += 100  # Bullish crossover
        else:
            score -= 100  # Bearish crossover
        signals += 1
    
    # 3. Price vs SMA20
    if indicators['sma_20'] is not None:
        if indicators['close'] > indicators['sma_20']:
            score += 50   # Ár SMA20 felett (short-term bullish)
        else:
            score -= 50   # Ár SMA20 alatt (short-term bearish)
        signals += 1
    
    # Átlagolás (tipikusan 3 jelzés van)
    return score / signals if signals > 0 else 0

# Példa output:
# - Golden Cross + Bullish MACD + Price > SMA20
#   = (100 + 100 + 50) / 3 = +83.3 (erősen bullish)
# - Death Cross + Bearish MACD + Price < SMA20
#   = (-100 - 100 - 50) / 3 = -83.3 (erősen bearish)
# - Mixed signals: SMA20>50 + Bearish MACD + Price > SMA20
#   = (50 - 100 + 50) / 3 = 0 (neutral)
```

**Momentum Score Részletes Kalkuláció:**
```python
def _calculate_momentum_score(indicators: Dict) -> float:
    """
    Momentum komponens score (-100 to +100)
    
    Vizsgált jelzések:
    1. RSI oversold/overbought
    2. Stochastic crossover
    """
    score = 0
    signals = 0
    
    # 1. RSI (Relative Strength Index)
    if indicators['rsi'] is not None:
        rsi = indicators['rsi']
        
        if rsi < 30:
            # Oversold zone → Buy opportunity
            score += 100
        elif rsi > 70:
            # Overbought zone → Sell signal
            score -= 100
        elif rsi > 50:
            # Above midline → Bullish momentum
            score += 50
        else:
            # Below midline → Bearish momentum
            score -= 50
        
        signals += 1
    
    # 2. Stochastic Oscillator
    if indicators['stoch_k'] is not None and indicators['stoch_d'] is not None:
        if indicators['stoch_k'] > indicators['stoch_d']:
            # %K > %D → Bullish crossover
            score += 100
        else:
            # %K < %D → Bearish crossover
            score -= 100
        
        signals += 1
    
    return score / signals if signals > 0 else 0

# Példa output:
# - RSI = 25 (oversold) + Stochastic bullish crossover
#   = (100 + 100) / 2 = +100 (max bullish momentum)
# - RSI = 75 (overbought) + Stochastic bearish crossover
#   = (-100 - 100) / 2 = -100 (max bearish momentum)
# - RSI = 55 + Stochastic bullish
#   = (50 + 100) / 2 = +75 (strong bullish momentum)
```

**Volatility Score Részletes Kalkuláció:**
```python
def _calculate_volatility_score(indicators: Dict, df: pd.DataFrame) -> float:
    """
    Volatilitás komponens score (-100 to +100)
    
    Vizsgált jelzések:
    1. Bollinger Bands position
    2. ATR level (lower is better for entry)
    """
    score = 0
    signals = 0
    
    # 1. Bollinger Bands Position
    if all([indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower']]):
        close = indicators['close']
        
        # Pozíció a bandok között (0-1 range)
        bb_position = (close - indicators['bb_lower']) / \
                      (indicators['bb_upper'] - indicators['bb_lower'])
        
        if bb_position > 0.8:
            # Felső band közelében → Overbought
            score -= 50
        elif bb_position < 0.2:
            # Alsó band közelében → Oversold (buy opportunity)
            score += 50
        else:
            # Középső zóna → Neutral-positive
            score += 20
        
        signals += 1
    
    # 2. ATR (Average True Range) Level
    if indicators['atr'] is not None:
        # ATR százalékban (volatilitás)
        atr_pct = (indicators['atr'] / indicators['close']) * 100
        
        if atr_pct < 2.0:
            # Alacsony volatilitás → Jó entry pont
            score += 50
        elif atr_pct > 5.0:
            # Magas volatilitás → Kockázatos
            score -= 50
        else:
            # Normál volatilitás → Neutral
            score += 0
        
        signals += 1
    
    return score / signals if signals > 0 else 0

# Példa output:
# - BB position = 0.15 (alsó band közel) + ATR = 1.8%
#   = (50 + 50) / 2 = +50 (good entry, low volatility)
# - BB position = 0.85 (felső band közel) + ATR = 5.5%
#   = (-50 - 50) / 2 = -50 (overbought + high volatility)
```

**Volume Score Részletes Kalkuláció:**
```python
def _calculate_volume_score(indicators: Dict, df: pd.DataFrame) -> float:
    """
    Volume komponens score (-100 to +100)
    
    Vizsgált jelzés:
    - Volume vs Volume SMA (confirmation)
    """
    score = 0
    signals = 0
    
    if indicators['volume'] is not None and indicators['volume_sma'] is not None:
        volume = indicators['volume']
        volume_sma = indicators['volume_sma']
        
        if volume > volume_sma * 1.5:
            # Erős volume (1.5x felett) → Trend confirmation
            score += 100
        elif volume < volume_sma * 0.5:
            # Gyenge volume (0.5x alatt) → Lack of conviction
            score -= 50
        else:
            # Normál volume → Neutral
            score += 0
        
        signals += 1
    
    return score / signals if signals > 0 else 0

# Példa output:
# - Volume = 2.0 × Volume_SMA → +100 (strong confirmation)
# - Volume = 0.4 × Volume_SMA → -50 (weak, low conviction)
# - Volume = 1.2 × Volume_SMA → 0 (normal)
```

**Technical Confidence:**
```python
def calculate_technical_confidence(indicators: Dict) -> float:
    """
    Indikátorok egybehangzósága alapján
    """
    bullish_signals = 0
    bearish_signals = 0
    
    # SMA trend
    if sma_20 > sma_50: bullish_signals += 1
    else: bearish_signals += 1
    
    # MACD
    if macd > macd_signal: bullish_signals += 1
    else: bearish_signals += 1
    
    # RSI
    if rsi < 30: bullish_signals += 1
    elif rsi > 70: bearish_signals += 1
    
    # Alignment
    dominant = max(bullish_signals, bearish_signals)
    alignment = dominant / total_signals
    
    # ADX bonus (erős trend növeli confidence-t)
    if adx > 25:
        confidence = alignment
    else:
        confidence = alignment * 0.8  # Gyenge trend csökkenti
    
    return min(confidence, 1.0)
```

---

## 4. Sentiment Analízis Rendszer

### 4.1 FinBERT Neural Network

**Architektúra:**
- **Base Model:** BERT (Bidirectional Encoder Representations from Transformers)
- **Fine-tuning:** 10,000+ financial news corpus
- **Output Layer:** 3-class softmax (Positive, Negative, Neutral)

**Inference Folyamat:**
```python
# Input: News text
text = "Apple beats earnings expectations, stock surges"

# FinBERT forward pass
inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
outputs = model(**inputs)
logits = outputs.logits
probs = torch.softmax(logits, dim=1)

# Output probabilities
{
    "positive": 0.87,
    "negative": 0.02,
    "neutral": 0.11
}

# Sentiment score
sentiment = (pos - neg) * (1 - neu) = (0.87 - 0.02) * (1 - 0.11) = 0.76
```

### 4.2 Magyar Nyelv Kezelés

**Probléma:** FinBERT csak angol szövegeket kezel.

**Megoldás:** Enhanced Keyword-Based System

**ticker_keywords.py:**
```python
TICKER_KEYWORDS = {
    "MOL.BD": {
        "positive": [
            "növekedés", "rekord", "nyereség", "profit",
            "olajár emelkedés", "divdendnövelés", "bővítés"
        ],
        "negative": [
            "veszteség", "olajár csökkenés", "kockázat",
            "sztrájk", "korrupció", "bírság"
        ],
        "neutral": ["tartja", "stabil", "változatlan"]
    },
    "OTP.BD": {
        "positive": [
            "profit", "kamatbevétel", "hitelportfólió növekedés",
            "tőkeerősítés", "osztalék"
        ],
        "negative": [
            "rossz hitelek", "NPL", "veszteség",
            "bírság", "kamatkockázat"
        ]
    }
}
```

**Relevanciaszámítás:**
```python
def calculate_relevance_score(text: str, ticker: str) -> float:
    """
    Hír relevanciája adott tickerhez
    """
    keywords = get_ticker_keywords(ticker)
    all_keywords = keywords["positive"] + keywords["negative"] + keywords["neutral"]
    
    matches = sum(1 for kw in all_keywords if kw.lower() in text.lower())
    relevance = min(matches / 5, 1.0)  # 5+ match = 100% releváns
    
    return relevance
```

**Sentiment score (keyword-based):**
```python
positive_count = sum(1 for kw in positive_kw if kw in text)
negative_count = sum(1 for kw in negative_kw if kw in text)
neutral_count = sum(1 for kw in neutral_kw if kw in text)

total = positive_count + negative_count + neutral_count
if total == 0:
    return 0.0

sentiment = (positive_count - negative_count) / total
# Range: -1.0 to +1.0
```

---

## 5. Technikai Analízis Rendszer

### 5.1 Support/Resistance Detektálás (DBSCAN) - RÉSZLETES MŰKÖDÉS

**DBSCAN (Density-Based Spatial Clustering of Applications with Noise):**

**Miért DBSCAN, nem K-Means?**
- ✅ Automatikusan megtalálja a cluster-eket (nincs szükség előre megadott K-ra)
- ✅ Outlier detektálás (noise pontok kiszűrése)
- ✅ Tetszőleges alakú cluster-ek (nem csak körök)
- ✅ Nem feltételezi, hogy minden pont egy cluster-be tartozik

**Paraméterek (KRITIKUS):**
```python
eps = 0.04 * current_price  # Epsilon: max távolság cluster tagok között (4%)
min_samples = 3              # Min 3 pivot kell egy cluster-hez
order = 7                    # Pivot detektáláshoz: 7-day window
lookback = 180               # 180 nap (6 hónap) historikus data
```

**TELJES MŰKÖDÉS LÉPÉSRŐL-LÉPÉSRE:**

#### **1. Lépés: Pivot Pontok Detektálása**

```python
def detect_pivot_points(df: pd.DataFrame, order: int = 7) -> Tuple[pd.Series, pd.Series]:
    """
    Local min/max pontok (pivot points) detektálása
    
    order = 7: Azt jelenti, hogy 7 nappal előtte ÉS 7 nappal utána 
               nézünk, hogy tényleg local extremum-e
    """
    high = df['High']
    low = df['Low']
    
    # Pivot High (Resistance candidate)
    # Feltétel: high[t] > high[t-order] ÉS high[t] > high[t+order]
    pivot_highs = high[
        (high.shift(order) < high) &   # Magasabb mint order nappal ezelőtt
        (high.shift(-order) < high)    # Magasabb mint order nappal később
    ]
    
    # Pivot Low (Support candidate)
    # Feltétel: low[t] < low[t-order] ÉS low[t] < low[t+order]
    pivot_lows = low[
        (low.shift(order) > low) &     # Alacsonyabb mint order nappal ezelőtt
        (low.shift(-order) > low)      # Alacsonyabb mint order nappal később
    ]
    
    return pivot_highs, pivot_lows

# Példa output (AAPL, 180 nap, order=7):
# pivot_highs: [185.20, 182.50, 186.10, 183.40, 188.00, ...]  (~15-20 pont)
# pivot_lows:  [168.30, 171.20, 169.80, 172.50, 167.90, ...]  (~15-20 pont)
```

**Vizualizáció:**
```
Price Chart (simplified):

190 |                                      X (188.00)
185 |        X (185.20)    X (186.10)    /
180 |       / \           / \           /
175 |      /   \         /   \         /
170 |     /     X       /     X       /
165 |    /    (182.50) /   (183.40) /
160 | --X----------------X------------X---
      (168.30)        (169.80)    (167.90)

X = Pivot point (order=7 confirmed local extremum)
```

#### **2. Lépés: DBSCAN Clustering**

```python
from sklearn.cluster import DBSCAN
import numpy as np

def cluster_pivots(pivot_highs: pd.Series, pivot_lows: pd.Series, 
                   current_price: float, eps_pct: float = 0.04, 
                   min_samples: int = 3) -> Dict:
    """
    DBSCAN clustering a pivot pontokon
    
    Cél: Közeli pivot pontok összevonása egy S/R szintté
    """
    # Összes pivot pont egyetlen listába
    all_levels = pd.concat([pivot_highs, pivot_lows])
    
    # Reshape for sklearn (expects 2D array)
    X = all_levels.values.reshape(-1, 1)
    
    # DBSCAN params
    eps = eps_pct * current_price  # 4% * 175.00 = 7.00 (max distance)
    
    # Run DBSCAN
    clustering = DBSCAN(eps=eps, min_samples=min_samples)
    labels = clustering.fit_predict(X)
    
    # labels example: [-1, 0, 0, 1, -1, 1, 1, 2, 2, 2, -1]
    # -1 = noise (outlier, nem tartozik cluster-be)
    # 0, 1, 2 = cluster IDs
    
    return labels, X

# Példa AAPL (current_price = $175.00):
# eps = 0.04 * 175.00 = $7.00
# 
# All levels: [185.20, 182.50, 186.10, 183.40, 188.00,  # highs
#              168.30, 171.20, 169.80, 172.50, 167.90]  # lows
# 
# DBSCAN output labels:
# [0, 0, 0, 0, 1,      # Cluster 0: ~183-186 range, Cluster 1: 188 (noise?)
#  2, 3, 2, 3, 2]      # Cluster 2: ~168-170, Cluster 3: ~171-172
```

**Hogyan működik a DBSCAN?**
```
Step 1: Minden ponthoz számoljuk, hogy hány szomszédja van eps távolságon belül

Point 185.20: Szomszédok (eps=7.00 belül): 182.50, 186.10, 183.40 → 3 szomszéd
Point 188.00: Szomszédok: NONE (>7.00 mindenkitől) → OUTLIER

Step 2: Ha min_samples (3) szomszédja van → Core point (cluster mag)
Step 3: Core pointok és szomszédaik → Cluster
Step 4: Nem elég szomszéddal rendelkező pontok → Noise (-1 label)
```

#### **3. Lépés: S/R Szintek Kinyerése**

```python
def extract_sr_levels(labels: np.array, X: np.array, current_price: float) -> Dict:
    """
    Cluster centroids = S/R szintek
    """
    sr_levels = []
    
    for label in set(labels):
        if label == -1:
            # Outlier, skip
            continue
        
        # Cluster pontok
        cluster_points = X[labels == label]
        
        # Cluster centroid (átlag)
        sr_level = cluster_points.mean()
        
        # Távolság current price-tól
        distance_pct = abs((sr_level - current_price) / current_price) * 100
        
        sr_levels.append({
            "price": sr_level,
            "distance_pct": distance_pct,
            "cluster_size": len(cluster_points)  # Hány pivot pont van ebben a cluster-ben
        })
    
    # Szétválasztás support/resistance
    support = [lvl for lvl in sr_levels if lvl["price"] < current_price]
    resistance = [lvl for lvl in sr_levels if lvl["price"] > current_price]
    
    # Rendezés: legközelebbi először
    support.sort(key=lambda x: x["distance_pct"])
    resistance.sort(key=lambda x: x["distance_pct"])
    
    return {
        "support": support[:3],      # Top 3 legközelebbi támasz
        "resistance": resistance[:3]  # Top 3 legközelebbi ellenállás
    }

# Példa output (AAPL, current_price = $175.00):
{
    "support": [
        {"price": 170.12, "distance_pct": 2.79, "cluster_size": 4},
        {"price": 165.80, "distance_pct": 5.26, "cluster_size": 3},
        {"price": 160.50, "distance_pct": 8.29, "cluster_size": 5}
    ],
    "resistance": [
        {"price": 182.75, "distance_pct": 4.43, "cluster_size": 5},
        {"price": 188.20, "distance_pct": 7.54, "cluster_size": 3},
        {"price": 195.00, "distance_pct": 11.43, "cluster_size": 2}
    ]
}
```

**Vizualizáció - Final S/R Levels:**
```
Price Chart with S/R Levels:

195 |                                      ━━━━ R3 ($195.00)
190 |
188 |                                      ━━━━ R2 ($188.20)
185 |        X     X     X     X    
183 |                                      ━━━━ R1 ($182.75)
180 |       / \   / \   / \   / \   
175 | ────────────── CURRENT PRICE ($175.00) ──────────────
170 |      /   \ /   \ /   \ /   \         ━━━━ S1 ($170.12)
168 |     X     X     X     X      
166 |                                      ━━━━ S2 ($165.80)
165 |    /     \     /     \       
160 | --X-------X---X-------X-------       ━━━━ S3 ($160.50)

X = Individual pivot points
━━━━ = Clustered S/R level (DBSCAN centroid)
```

**Miért jobb ez, mint egyszerű min/max?**

**Egyszerű min/max (ROSSZ):**
```
Support = min(last_90_days_lows) = $167.50
Resistance = max(last_90_days_highs) = $188.50

Probléma:
- Csak 1 szint mindkét oldalon
- Outlier-ek torzítanak (egy extrém low/high)
- Nem veszi figyelembe, hogy többször tesztelte-e az árat
```

**DBSCAN clustering (JÓ):**
```
Support levels:
- $170.12 (4 pivot → erős szint, többször tesztelve)
- $165.80 (3 pivot → közepes erősség)
- $160.50 (5 pivot → nagyon erős szint!)

Resistance levels:
- $182.75 (5 pivot → nagyon erős ellenállás)
- $188.20 (3 pivot → közepes)
- $195.00 (2 pivot → gyenge, csak 2x tesztelve)

Előny:
- Több szint mindkét oldalon
- Cluster size = szint erőssége
- Outlier-ek kiszűrve (noise)
- Realisztikus swing trading szintek
```

#### **4. Lépés: Setup Quality Assessment**

```python
def assess_sr_setup_quality(support: List[Dict], resistance: List[Dict], 
                            current_price: float) -> str:
    """
    S/R setup minőség értékelése
    """
    if not support or not resistance:
        return "POOR: No clear S/R levels"
    
    nearest_support_dist = support[0]["distance_pct"]
    nearest_resistance_dist = resistance[0]["distance_pct"]
    
    if nearest_support_dist < 1.0 or nearest_resistance_dist < 1.0:
        return "POOR: Tight consolidation (<1% to S/R), low profit potential"
    
    if 2.0 <= nearest_support_dist <= 5.0 and 2.0 <= nearest_resistance_dist <= 8.0:
        return "GOOD: Normal swing trading range, good profit potential"
    
    if nearest_support_dist > 8.0 or nearest_resistance_dist > 10.0:
        return "WIDE: Large range, high profit potential but risky"
    
    return "ACCEPTABLE: Usable setup"

# Példa AAPL:
# S1 = 2.79%, R1 = 4.43%
# → "GOOD: Normal swing trading range, good profit potential"

# Példa OTP.BD:
# S1 = 0.03%, R1 = 0.31%
# → "POOR: Tight consolidation (<1% to S/R), low profit potential"
```

**Működés:**
1. **Pivot pontok detektálása:**
   ```python
   # Local maximum (resistance candidate)
   pivot_high = high[(high.shift(order) < high) & (high.shift(-order) < high)]
   
   # Local minimum (support candidate)
   pivot_low = low[(low.shift(order) > low) & (low.shift(-order) > low)]
   ```

2. **Clustering:**
   ```python
   all_levels = pd.concat([pivot_highs, pivot_lows])
   clustering = DBSCAN(eps=eps, min_samples=min_samples)
   labels = clustering.fit_predict(all_levels.values.reshape(-1, 1))
   ```

3. **S/R szintek:**
   ```python
   for label in set(labels):
       if label != -1:  # Outlier-ek kizárása
           cluster_points = all_levels[labels == label]
           sr_level = cluster_points.mean()
   ```

**Output Format:**
```python
{
    "support": [
        {"price": 2850.0, "distance_pct": 2.93},  # 2.93% távolság
        {"price": 2780.0, "distance_pct": 5.31}
    ],
    "resistance": [
        {"price": 3020.0, "distance_pct": 2.86},
        {"price": 3150.0, "distance_pct": 7.29}
    ]
}
```

### 5.2 Multi-Timeframe Analízis

**Adatlekérés (yfinance):**
```python
import yfinance as yf

def fetch_multi_timeframe_data(ticker: str) -> Dict:
    """
    Több timeframe letöltése párhuzamosan
    """
    ticker_obj = yf.Ticker(ticker)
    
    # Intraday (5 perc)
    df_5m = ticker_obj.history(period="1d", interval="5m")  # 50 candle
    
    # Trend (1 óra)
    df_1h = ticker_obj.history(period="30d", interval="1h")  # 720 candle
    
    # Daily (napi)
    df_1d = ticker_obj.history(period="6mo", interval="1d")  # ~126 candle
    
    # S/R (15 perc)
    df_15m = ticker_obj.history(period="3d", interval="15m")  # 288 candle
    
    return {
        "intraday": df_5m,
        "trend": df_1h,
        "daily": df_1d,
        "support_resistance": df_15m
    }
```

**Használat:**
- **5m:** RSI oversold/overbought gyors detektálás
- **1h:** Középtávú trend irány (SMA50, ADX)
- **1d:** Volatilitás mérés (ATR) - KRITIKUS: Daily ATR-t használunk!
- **15m:** Swing trading szintek (S/R pivots)

---

## 6. Risk Management Rendszer

### 6.1 Risk Score Komponensek

**3-komponensű risk rendszer:**

```python
risk_score = (
    volatility_risk * 0.40 +      # ATR % alapján
    proximity_risk * 0.35 +        # S/R távolság alapján
    trend_strength_risk * 0.25     # ADX alapján
)
# Range: -100 to +100
```

### 6.2 Volatility Risk (ATR-Based) - RÉSZLETES

```python
def calculate_volatility_risk(atr_pct: float) -> float:
    """
    ATR % → Volatilitási kockázat score
    
    Logika:
    - Alacsony volatilitás (<2%) = Stabil ár mozgás = Alacsony kockázat (pozitív score)
    - Magas volatilitás (>5%) = Hektikus ár mozgás = Magas kockázat (negatív score)
    
    Returns: -100 to +100
    """
    if atr_pct < 1.5:
        return 100   # Nagyon stabil (best case)
    elif atr_pct < 2.5:
        return 50    # Stabil (good for trading)
    elif atr_pct < 3.5:
        return 0     # Normál (neutral)
    elif atr_pct < 5.0:
        return -50   # Volatilis (risky)
    else:
        return -100  # Nagyon volatilis (worst case)

# ATR % kalkuláció:
# atr_pct = (atr / current_price) * 100
# 
# Példa: AAPL
# - Current price: $175.00
# - ATR (14-day): $3.50
# - ATR %: (3.50 / 175.00) * 100 = 2.0%
# - Volatility Risk: 50 (stabil)

# Példa: TSLA
# - Current price: $250.00
# - ATR (14-day): $12.00
# - ATR %: (12.00 / 250.00) * 100 = 4.8%
# - Volatility Risk: -50 (volatilis)

# Példa: NVDA
# - Current price: $850.00
# - ATR (14-day): $52.70
# - ATR %: (52.70 / 850.00) * 100 = 6.2%
# - Volatility Risk: -100 (nagyon volatilis)
```

**Miért fontos az ATR % (nem abszolút ATR)?**
- Abszolút ATR ($10) más jelentést hordoz $50-os vs $500-as részvénynél
- ATR % normalizálja a volatilitást → összehasonlítható tickerek között
- 2% ATR mindenhol ugyanazt jelenti: "átlagosan 2%-ot mozog naponta"

### 6.3 Proximity Risk (S/R Distance)

```python
def calculate_proximity_risk(
    current_price: float,
    support: List[Dict],
    resistance: List[Dict]
) -> float:
    """
    S/R távolság alapján kockázat
    
    Logika:
    - Támasz/ellenállás közel (<1%) → Magas kockázat (rejection risk)
    - Középső zónában (30-70%) → Alacsony kockázat
    """
    nearest_support = support[0]["price"] if support else price * 0.95
    nearest_resistance = resistance[0]["price"] if resistance else price * 1.05
    
    support_dist_pct = ((price - nearest_support) / price) * 100
    resistance_dist_pct = ((nearest_resistance - price) / price) * 100
    
    # KRITIKUS: Ha S/R túl közel (<1%)
    if support_dist_pct < 1.0 or resistance_dist_pct < 1.0:
        return -80  # Nagyon kockázatos (szűk range)
    
    # Optimális zóna: 30-70% pozíció a range-ben
    total_range = support_dist_pct + resistance_dist_pct
    position = support_dist_pct / total_range if total_range > 0 else 0.5
    
    if 0.3 <= position <= 0.7:
        return 100  # Safe zone
    elif 0.2 <= position <= 0.8:
        return 50   # Elfogadható
    else:
        return -50  # S/R közelében (kockázatos)
```

### 6.4 Trend Strength Risk (ADX-Based)

```python
def calculate_trend_strength_risk(adx: Optional[float]) -> float:
    """
    ADX → Trend megbízhatóság
    
    Erős trend = Alacsony kockázat
    Gyenge trend (ranging) = Magas kockázat
    """
    if adx is None:
        return 0  # Neutral
    
    if adx > 50:
        return 100   # Nagyon erős trend (alacsony kockázat)
    elif adx > 35:
        return 50    # Erős trend
    elif adx > 25:
        return 0     # Közepes trend
    else:
        return -50   # Gyenge/nincs trend (ranging market, magas kockázat)
```

### 6.5 Stop Loss és Take Profit Számítás

**Stop Loss (BUY signal):**
```python
# Opció 1: S/R-based stop
if nearest_support:
    sr_stop = nearest_support - (0.5 * atr)  # 0.5x ATR buffer
else:
    sr_stop = entry * 0.95  # Fallback: 5% below

# Opció 2: ATR-based stop (2x standard)
atr_stop = entry - (2 * atr)

# HASZNÁLAT: Amelyik távolabbi (konzervatívabb)
stop_loss = min(sr_stop, atr_stop)

# Sanity check: min 0.5% távolság
if (entry - stop_loss) / entry < 0.005:
    stop_loss = entry * 0.995
```

**Take Profit (BUY signal):**
```python
# Opció 1: Resistance-based target
if nearest_resistance:
    sr_target = nearest_resistance
else:
    sr_target = entry * 1.08  # Fallback: 8% above

# Opció 2: ATR-based target (3x, 1.5:1 R:R cél)
atr_target = entry + (3 * atr)

# HASZNÁLAT: Amelyik közelebbi (reálisabb)
take_profit = min(sr_target, atr_target)

# Sanity check: min 1% profit
if (take_profit - entry) / entry < 0.01:
    take_profit = entry * 1.01
```

**Risk:Reward Ratio:**
```python
risk = entry - stop_loss
reward = take_profit - entry
rr_ratio = reward / risk

# Minimális követelmény: R:R >= 1.5:1
```

---

## 7. Signal Generálás

### 7.1 Combined Score Kalkuláció

**3-komponensű weighted scoring:**

```python
def generate_signal(
    sentiment_data: Dict,
    technical_data: Dict,
    risk_data: Dict
) -> TradingSignal:
    # 1. Component scores (-100 to +100)
    sentiment_score = sentiment_data["weighted_avg"] * 100
    technical_score = technical_data["score"]
    risk_score = risk_data["score"]
    
    # 2. Dynamic weights (config.json-ból)
    config = get_config()
    config.reload()  # KRITIKUS: Friss súlyok betöltése!
    
    sentiment_weight = config.sentiment_weight  # Default: 0.70
    technical_weight = config.technical_weight  # Default: 0.20
    risk_weight = config.risk_weight            # Default: 0.10
    
    # 3. Weighted contributions
    sentiment_contribution = sentiment_score * sentiment_weight
    technical_contribution = technical_score * technical_weight
    risk_contribution = risk_score * risk_weight
    
    # 4. Combined score
    combined_score = (
        sentiment_contribution +
        technical_contribution +
        risk_contribution
    )
    
    return combined_score  # Range: -100 to +100
```

**Példa Kalkuláció:**
```
Sentiment: +65 (strong positive news)
Technical: +42 (golden cross, bullish RSI)
Risk: -18 (moderate volatility, OK S/R distance)

Weights: 70% / 20% / 10%

Contributions:
- Sentiment: +65 * 0.70 = +45.5
- Technical: +42 * 0.20 = +8.4
- Risk: -18 * 0.10 = -1.8

Combined Score: 45.5 + 8.4 - 1.8 = +52.1
→ MODERATE BUY (score >= 50 threshold)
```

### 7.2 Részletes Példa - AAPL Signal Generálás

**Input Adatok:**
```python
# Sentiment Data
sentiment_data = {
    "weighted_avg": 0.68,  # +68/100 after *100 conversion
    "confidence": 0.85,
    "news_count": 15,
    "key_news": [
        "Apple beats Q4 earnings expectations",
        "iPhone 16 sales exceed analyst predictions",
        "Services revenue hits record high"
    ]
}

# Technical Data
technical_data = {
    "score": 45.2,  # Calculated from components
    "confidence": 0.72,
    "current_price": 175.50,
    "rsi": 58.3,
    "sma_20": 173.20,
    "sma_50": 168.40,
    "sma_200": 165.10,
    "macd": 2.15,
    "macd_signal": 1.80,
    "atr": 3.51,
    "atr_pct": 2.0,
    "adx": 28.5
}

# Risk Data
risk_data = {
    "score": -15.0,
    "volatility": 2.0,  # ATR %
    "nearest_support": 170.00,
    "nearest_resistance": 182.00,
    "components": {
        "volatility_risk": 50,     # 2% ATR → stable
        "proximity_risk": 100,     # 42% position → safe zone
        "trend_strength_risk": 0   # ADX 28.5 → moderate trend
    }
}
```

**Step 1: Component Scores**
```python
# Convert sentiment to -100/+100 scale
sentiment_score = sentiment_data["weighted_avg"] * 100 = 68.0

# Technical score (already calculated)
technical_score = technical_data["score"] = 45.2

# Risk score (already calculated)
risk_score = risk_data["score"] = -15.0
```

**Step 2: Get Dynamic Weights**
```python
config.reload()  # Load from config.json
sentiment_weight = 0.70
technical_weight = 0.20
risk_weight = 0.10
```

**Step 3: Calculate Contributions**
```python
sentiment_contribution = 68.0 * 0.70 = 47.6
technical_contribution = 45.2 * 0.20 = 9.0
risk_contribution = -15.0 * 0.10 = -1.5
```

**Step 4: Combined Score**
```python
combined_score = 47.6 + 9.0 + (-1.5) = 55.1
```

**Step 5: Entry/Exit Levels**
```python
entry_price = 175.50

# Stop Loss (BUY signal)
nearest_support = 170.00
atr = 3.51

sr_stop = 170.00 - (0.5 * 3.51) = 168.24
atr_stop = 175.50 - (2 * 3.51) = 168.48

stop_loss = min(168.24, 168.48) = 168.24
stop_loss_pct = ((175.50 - 168.24) / 175.50) * 100 = 4.14%

# Take Profit (BUY signal)
nearest_resistance = 182.00
atr_target = 175.50 + (3 * 3.51) = 186.03

take_profit = min(182.00, 186.03) = 182.00
take_profit_pct = ((182.00 - 175.50) / 175.50) * 100 = 3.70%

# Risk:Reward Ratio
risk = 175.50 - 168.24 = 7.26
reward = 182.00 - 175.50 = 6.50
rr_ratio = 6.50 / 7.26 = 0.90  # <2.0 → Not ideal R:R
```

**Step 6: Overall Confidence**
```python
sentiment_conf = 0.85
technical_conf = 0.72
volume_factor = min(15 / 10, 1.0) = 1.0  # 15 news → 100%
rr_bonus = 0  # R:R < 2.0 → No bonus

overall_confidence = (
    0.85 * 0.40 +    # 0.34
    0.72 * 0.30 +    # 0.216
    1.0 * 0.20 +     # 0.20
    0 * 0.10         # 0
) = 0.756 (75.6%)
```

**Step 7: Decision Logic**
```python
combined_score = 55.1
confidence = 0.756
rr_ratio = 0.90

# Check STRONG BUY
if combined_score >= 65 and confidence >= 0.75:
    if rr_ratio >= 2.0:
        decision = "STRONG BUY"
    else:
        decision = "MODERATE BUY"  # Downgrade due to poor R:R
# Combined score 55.1 < 65 → Not strong

# Check MODERATE BUY
if combined_score >= 50 and confidence >= 0.65:
    decision = "MODERATE BUY"  # ✅ Matches!

→ Final: MODERATE BUY, Confidence 75.6%
```

**Végeredmény:**
```json
{
  "ticker_symbol": "AAPL",
  "ticker_name": "Apple Inc.",
  "decision": "BUY",
  "strength": "MODERATE",
  "combined_score": 55.1,
  "sentiment_score": 68.0,
  "technical_score": 45.2,
  "risk_score": -15.0,
  "overall_confidence": 0.756,
  "sentiment_confidence": 0.85,
  "technical_confidence": 0.72,
  "entry_price": 175.50,
  "stop_loss": 168.24,
  "take_profit": 182.00,
  "risk_reward_ratio": 0.90,
  "news_count": 15,
  "timestamp": "2025-01-31T14:30:00Z"
}
```

**Reasoning (Indoklás a felhasználónak):**
```
✅ MODERATE BUY Signal for AAPL

Sentiment (70% weight): +68/100
  - 15 fresh news articles (strong volume)
  - FinBERT confidence: 85%
  - Key themes: Earnings beat, strong iPhone sales

Technical (20% weight): +45/100
  - Golden Cross in progress (SMA20 > SMA50 > SMA200)
  - Bullish MACD crossover
  - RSI at 58 (neutral-bullish, not overbought)
  - Moderate ADX (28.5) → trend forming

Risk (10% weight): -15/100
  - Volatility: 2.0% ATR (stable, low risk)
  - S/R position: 42% in range (safe zone)
  - ADX: 28.5 (moderate trend strength)

Entry & Exit:
  Entry:       $175.50
  Stop-Loss:   $168.24 (-4.14%)  ← Based on support $170.00 - 0.5×ATR buffer
  Take-Profit: $182.00 (+3.70%)  ← Based on resistance
  Risk:Reward: 0.90:1  ⚠️ Below 2:1 ideal

⚠️ Note: R:R ratio is below ideal 2:1. Consider waiting for better setup
or widening take-profit target.
```

### 7.2 Overall Confidence Számítás

**Multi-factor confidence:**

```python
def calculate_overall_confidence(
    sentiment_confidence: float,
    technical_confidence: float,
    news_count: int,
    rr_ratio: Optional[float] = None
) -> float:
    """
    Weighted confidence kombinációja
    
    Komponensek:
    - Sentiment confidence (40%) - FinBERT model bizonyossága
    - Technical confidence (30%) - Indikátor egybehangzóság
    - News volume (20%) - Hírek száma
    - Risk:Reward ratio (10%) - Setup minőség
    """
    # Base confidences
    sent_conf = sentiment_confidence
    tech_conf = technical_confidence
    
    # Volume factor (10+ news = 100%)
    volume_factor = min(news_count / 10, 1.0)
    
    # R:R bonus (if >= 2.0)
    if rr_ratio and rr_ratio >= 2.0:
        rr_bonus = min((rr_ratio - 1.0) / 2.0, 0.3)  # Max +30%
    else:
        rr_bonus = 0
    
    # Weighted combination
    overall_conf = (
        sent_conf * 0.40 +
        tech_conf * 0.30 +
        volume_factor * 0.20 +
        rr_bonus * 0.10
    )
    
    # Cap at 95% (soha nem 100%)
    overall_conf = min(overall_conf, 0.95)
    
    return overall_conf
```

**Példa:**
```
Sentiment Conf: 0.88 (FinBERT 88% biztos)
Technical Conf: 0.72 (72% indikátor alignment)
News Count: 12 (10+ = 100% volume factor)
R:R Ratio: 2.3 (good setup, +bonus)

Calculation:
= 0.88 * 0.40 + 0.72 * 0.30 + 1.0 * 0.20 + 0.15 * 0.10
= 0.352 + 0.216 + 0.20 + 0.015
= 0.783 (78.3%)
```

### 7.3 Decision Logic

**Thresholds (config.json):**
```json
{
  "STRONG_BUY_SCORE": 65,
  "STRONG_BUY_CONFIDENCE": 0.75,
  "MODERATE_BUY_SCORE": 50,
  "MODERATE_BUY_CONFIDENCE": 0.65,
  "STRONG_SELL_SCORE": -65,
  "STRONG_SELL_CONFIDENCE": 0.75,
  "MODERATE_SELL_SCORE": -50,
  "MODERATE_SELL_CONFIDENCE": 0.65
}
```

**Decision Tree:**
```python
def determine_decision(
    combined_score: float,
    confidence: float,
    rr_ratio: Optional[float] = None
) -> Tuple[str, str]:
    """
    Returns: (decision, strength)
    - decision: "BUY", "SELL", "HOLD"
    - strength: "STRONG", "MODERATE", "WEAK"
    """
    config = get_config()
    
    # STRONG BUY
    if (combined_score >= config.strong_buy_score and
        confidence >= config.strong_buy_confidence):
        
        # Setup quality check
        if rr_ratio and rr_ratio >= 2.0:
            return ("BUY", "STRONG")
        else:
            return ("BUY", "MODERATE")  # Downgrade ha rossz R:R
    
    # MODERATE BUY
    elif (combined_score >= config.moderate_buy_score and
          confidence >= config.moderate_buy_confidence):
        return ("BUY", "MODERATE")
    
    # STRONG SELL
    elif (combined_score <= config.strong_sell_score and
          confidence >= config.strong_sell_confidence):
        
        if rr_ratio and rr_ratio >= 2.0:
            return ("SELL", "STRONG")
        else:
            return ("SELL", "MODERATE")
    
    # MODERATE SELL
    elif (combined_score <= config.moderate_sell_score and
          confidence >= config.moderate_sell_confidence):
        return ("SELL", "MODERATE")
    
    # WEAK signals (nem tradeable)
    elif combined_score > 0:
        return ("BUY", "WEAK")
    elif combined_score < 0:
        return ("SELL", "WEAK")
    else:
        return ("HOLD", "NEUTRAL")
```

### 7.4 Signal Archiválás

**Duplicate Prevention:**
```python
def archive_previous_signals(ticker_symbol: str, db: Session):
    """
    Előző active signalok archiválása új generálás előtt
    
    Szabály: 1 ticker = 1 active signal egyszerre
    """
    previous = db.query(Signal).filter(
        Signal.ticker_symbol == ticker_symbol,
        Signal.status == "active"
    ).all()
    
    for signal in previous:
        signal.status = "archived"
        signal.archived_at = datetime.now(timezone.utc)
    
    db.commit()
```

---

## 8. Konfigurációs Rendszer

### 8.1 Config Lifecycle

```
┌─────────────────────────────────────────────────────┐
│  1. STARTUP: config.json betöltése                  │
│     - TrendSignalConfig.__post_init__()             │
│     - Ha létezik → load_config_from_file()          │
│     - Ha nem → Default értékek                      │
└──────────────────────┬──────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│  2. USER MODIFICATION: Frontend → PUT request       │
│     - Configuration.tsx slider változás             │
│     - PUT /api/v1/config/signal                     │
│     - Backend: save_config_to_file()                │
└──────────────────────┬──────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────┐
│  3. SIGNAL GENERATION: Config reload                │
│     - signal_generator.generate_signal()            │
│     - config.reload()  ← KRITIKUS!                  │
│     - Friss súlyok használata                       │
└─────────────────────────────────────────────────────┘
```

### 8.2 Config Persistence (config.json)

**Példa config.json:**
```json
{
  "SENTIMENT_WEIGHT": 0.70,
  "TECHNICAL_WEIGHT": 0.20,
  "RISK_WEIGHT": 0.10,
  "DECAY_WEIGHTS": {
    "0-2h": 1.00,
    "2-6h": 0.85,
    "6-12h": 0.60,
    "12-24h": 0.35
  },
  "STRONG_BUY_SCORE": 65,
  "STRONG_BUY_CONFIDENCE": 0.75,
  "MODERATE_BUY_SCORE": 50,
  "MODERATE_BUY_CONFIDENCE": 0.65,
  "STRONG_SELL_SCORE": -65,
  "STRONG_SELL_CONFIDENCE": 0.75,
  "MODERATE_SELL_SCORE": -50,
  "MODERATE_SELL_CONFIDENCE": 0.65
}
```

**Save funkcionalitás:**
```python
def save_config_to_file(config: TrendSignalConfig) -> bool:
    """
    Config perzisztálása JSON fájlba
    """
    config_dict = {
        "SENTIMENT_WEIGHT": config.sentiment_weight,
        "TECHNICAL_WEIGHT": config.technical_weight,
        "RISK_WEIGHT": config.risk_weight,
        "DECAY_WEIGHTS": config.decay_weights,
        "STRONG_BUY_SCORE": config.strong_buy_score,
        "STRONG_BUY_CONFIDENCE": config.strong_buy_confidence,
        # ...
    }
    
    with open("config.json", "w") as f:
        json.dump(config_dict, f, indent=2)
    
    return True
```

**Load funkcionalitás:**
```python
def load_config_from_file() -> Optional[Dict]:
    """
    Config betöltése JSON fájlból
    """
    if Path("config.json").exists():
        with open("config.json", "r") as f:
            return json.load(f)
    return None
```

### 8.3 Dynamic Reload Mechanizmus

**KRITIKUS:** Backend újraindítás NÉLKÜL működik!

```python
# signal_generator.py

def generate_signal(self, ...):
    # ===== CONFIG RELOAD =====
    from src.config import get_config
    self.config = get_config()
    
    if hasattr(self.config, 'reload'):
        self.config.reload()  # ← Itt tölti újra!
    
    # Most már friss súlyokat használ
    sentiment_weight = self.config.sentiment_weight
    technical_weight = self.config.technical_weight
    risk_weight = self.config.risk_weight
    
    # ...
```

**Miért működik?**
1. Frontend módosít → PUT /api/v1/config/signal
2. Backend menti → `save_config_to_file()` → config.json frissül
3. Következő signal generálás → `config.reload()` → Új értékek betöltése
4. ✅ **Nincs szükség backend restart-ra!**

---

## 9. Frontend Alkalmazás

### 9.1 React Komponens Struktúra

**App.tsx (Main Router):**
```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/settings" element={<Configuration />} />
        <Route path="/news" element={<News />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### 9.2 Dashboard (Signal Lista)

**Features:**
- Signal generálás (Refresh button)
- Filterek: All / Buy Only / Sell Only / Strong Only
- Real-time display
- Score breakdown

**useApi.ts (React Query Hooks):**
```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_BASE = 'http://localhost:8000/api/v1';

// Signal lista lekérdezése
export function useSignals() {
  return useQuery({
    queryKey: ['signals'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/signals`);
      return response.json();
    },
    refetchInterval: 60000,  // Auto-refresh minden percben
  });
}

// Signal generálás
export function useGenerateSignals() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (tickers: string[]) => {
      const response = await fetch(`${API_BASE}/signals/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers })
      });
      return response.json();
    },
    onSuccess: () => {
      // Invalidate cache → újra lekérdezi a signalokat
      queryClient.invalidateQueries({ queryKey: ['signals'] });
    }
  });
}
```

**Dashboard.tsx:**
```tsx
function Dashboard() {
  const [filter, setFilter] = useState<'all' | 'buy' | 'sell' | 'strong'>('all');
  const { data: signals, isLoading } = useSignals();
  const generateMutation = useGenerateSignals();
  
  const handleRefresh = () => {
    const tickers = ['AAPL', 'TSLA', 'MOL.BD', 'OTP.BD'];
    generateMutation.mutate(tickers);
  };
  
  const filteredSignals = signals?.filter(signal => {
    if (filter === 'buy') return signal.decision === 'BUY';
    if (filter === 'sell') return signal.decision === 'SELL';
    if (filter === 'strong') return signal.strength === 'STRONG';
    return true;
  });
  
  return (
    <div className="container mx-auto p-6">
      <header className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">TrendSignal Dashboard</h1>
        <button 
          onClick={handleRefresh}
          disabled={generateMutation.isPending}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          {generateMutation.isPending ? 'Generating...' : 'Refresh Signals'}
        </button>
      </header>
      
      <div className="flex gap-2 mb-6">
        <button 
          onClick={() => setFilter('all')}
          className={filter === 'all' ? 'active' : ''}
        >
          All
        </button>
        <button 
          onClick={() => setFilter('buy')}
          className={filter === 'buy' ? 'active' : ''}
        >
          Buy Only
        </button>
        <button 
          onClick={() => setFilter('sell')}
          className={filter === 'sell' ? 'active' : ''}
        >
          Sell Only
        </button>
        <button 
          onClick={() => setFilter('strong')}
          className={filter === 'strong' ? 'active' : ''}
        >
          Strong Only
        </button>
      </div>
      
      {isLoading && <div>Loading signals...</div>}
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredSignals?.map(signal => (
          <SignalCard key={signal.id} signal={signal} />
        ))}
      </div>
    </div>
  );
}
```

### 9.3 Configuration Page

**Features:**
- Signal weights sliders (Sentiment / Technical / Risk)
- Decay weights sliders (0-2h / 2-6h / 6-12h / 12-24h)
- Decision thresholds (Strong/Moderate Buy/Sell)
- Real-time backend sync

**Configuration.tsx:**
```tsx
function Configuration() {
  const [sentimentWeight, setSentimentWeight] = useState(0.70);
  const [technicalWeight, setTechnicalWeight] = useState(0.20);
  const [riskWeight, setRiskWeight] = useState(0.10);
  
  // Load current config
  const { data: config, isLoading } = useQuery({
    queryKey: ['config'],
    queryFn: async () => {
      const response = await fetch('http://localhost:8000/api/v1/config/signal');
      return response.json();
    }
  });
  
  // Update config mutation
  const updateMutation = useMutation({
    mutationFn: async (updates: any) => {
      const response = await fetch('http://localhost:8000/api/v1/config/signal', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      return response.json();
    }
  });
  
  // Initialize from backend
  useEffect(() => {
    if (config) {
      setSentimentWeight(config.SENTIMENT_WEIGHT);
      setTechnicalWeight(config.TECHNICAL_WEIGHT);
      setRiskWeight(config.RISK_WEIGHT);
    }
  }, [config]);
  
  const handleSave = () => {
    updateMutation.mutate({
      SENTIMENT_WEIGHT: sentimentWeight,
      TECHNICAL_WEIGHT: technicalWeight,
      RISK_WEIGHT: riskWeight,
      // ... további paraméterek
    });
  };
  
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Configuration</h1>
      
      <section className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Signal Component Weights</h2>
        <p className="text-sm text-gray-600 mb-4">
          Must sum to 100%
        </p>
        
        <div className="space-y-6">
          <div>
            <label className="block mb-2">
              Sentiment: {(sentimentWeight * 100).toFixed(0)}%
            </label>
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={sentimentWeight * 100}
              onChange={(e) => setSentimentWeight(parseFloat(e.target.value) / 100)}
              className="w-full"
            />
          </div>
          
          <div>
            <label className="block mb-2">
              Technical: {(technicalWeight * 100).toFixed(0)}%
            </label>
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={technicalWeight * 100}
              onChange={(e) => setTechnicalWeight(parseFloat(e.target.value) / 100)}
              className="w-full"
            />
          </div>
          
          <div>
            <label className="block mb-2">
              Risk: {(riskWeight * 100).toFixed(0)}%
            </label>
            <input 
              type="range" 
              min="0" 
              max="100" 
              value={riskWeight * 100}
              onChange={(e) => setRiskWeight(parseFloat(e.target.value) / 100)}
              className="w-full"
            />
          </div>
          
          <div className="text-sm text-gray-600">
            Total: {((sentimentWeight + technicalWeight + riskWeight) * 100).toFixed(0)}%
          </div>
        </div>
      </section>
      
      <button 
        onClick={handleSave}
        disabled={updateMutation.isPending}
        className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700"
      >
        {updateMutation.isPending ? 'Saving...' : 'Save All Changes'}
      </button>
      
      {updateMutation.isSuccess && (
        <div className="mt-4 p-4 bg-green-100 text-green-800 rounded">
          ✓ Configuration saved successfully!
        </div>
      )}
    </div>
  );
}
```

---

## 10. Adatbázis Struktúra

### 10.1 Tickers Tábla
```sql
CREATE TABLE tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(20) UNIQUE NOT NULL,    -- "AAPL", "MOL.BD"
    name VARCHAR(200),                      -- "Apple Inc."
    market VARCHAR(10),                     -- "US" vagy "HU"
    sector VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 10.2 NewsItems Tábla
```sql
CREATE TABLE news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    url TEXT UNIQUE NOT NULL,
    url_hash VARCHAR(32) UNIQUE,           -- MD5 hash (deduplikáció)
    published_at TIMESTAMP NOT NULL,
    source VARCHAR(100),                    -- "GNews", "Alpha Vantage"
    sentiment_score FLOAT,                  -- -1.0 to +1.0
    sentiment_confidence FLOAT,             -- 0.0 to 1.0
    sentiment_label VARCHAR(20),            -- "positive", "negative", "neutral"
    credibility FLOAT DEFAULT 0.8,
    language VARCHAR(10) DEFAULT 'en',      -- "en" vagy "hu"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 10.3 Signals Tábla
```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker_id INTEGER NOT NULL,
    signal_type VARCHAR(10) NOT NULL,       -- "BUY" vagy "SELL"
    strength VARCHAR(20),                    -- "STRONG" vagy "MODERATE"
    combined_score FLOAT,                    -- -100 to +100
    confidence FLOAT,                        -- 0.0 to 1.0
    entry_price FLOAT,
    stop_loss FLOAT,
    take_profit FLOAT,
    risk_reward_ratio FLOAT,
    news_count INTEGER DEFAULT 0,
    reasoning JSON,                          -- Score breakdown
    status VARCHAR(20) DEFAULT 'active',     -- "active" vagy "archived"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived_at TIMESTAMP,
    FOREIGN KEY (ticker_id) REFERENCES tickers(id)
);
```

### 10.4 TechnicalIndicators Tábla
```sql
CREATE TABLE technical_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker_id INTEGER NOT NULL,
    rsi FLOAT,
    macd FLOAT,
    macd_signal FLOAT,
    macd_hist FLOAT,
    sma_20 FLOAT,
    sma_50 FLOAT,
    sma_200 FLOAT,
    ema_12 FLOAT,
    ema_26 FLOAT,
    bb_upper FLOAT,
    bb_middle FLOAT,
    bb_lower FLOAT,
    atr FLOAT,
    atr_pct FLOAT,
    adx FLOAT,
    support_level FLOAT,
    resistance_level FLOAT,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ticker_id) REFERENCES tickers(id)
);
```

---

## 11. API Endpointok

### 11.1 Signals API

**POST /api/v1/signals/generate**
```
Request:
{
  "tickers": ["AAPL", "MOL.BD", "OTP.BD"]
}

Response:
{
  "signals": [
    {
      "ticker_symbol": "AAPL",
      "decision": "BUY",
      "strength": "STRONG",
      "combined_score": 68.5,
      "confidence": 0.82,
      "entry_price": 175.50,
      "stop_loss": 172.30,
      "take_profit": 180.80,
      "risk_reward_ratio": 2.1,
      "news_count": 15,
      "components": {
        "sentiment": { "score": 72, "weight": 0.7, "contribution": 50.4 },
        "technical": { "score": 45, "weight": 0.2, "contribution": 9.0 },
        "risk": { "score": -20, "weight": 0.1, "contribution": -2.0 }
      }
    }
  ],
  "generated_at": "2025-01-31T10:30:00Z"
}
```

**GET /api/v1/signals**
```
Query Params:
- status: "active" (default) | "archived"

Response:
{
  "signals": [...],
  "count": 3
}
```

**GET /api/v1/signals/{ticker}**
```
Response:
{
  "signal": { ... }
}
```

### 11.2 Configuration API

**GET /api/v1/config/signal**
```
Response:
{
  "SENTIMENT_WEIGHT": 0.70,
  "TECHNICAL_WEIGHT": 0.20,
  "RISK_WEIGHT": 0.10,
  "STRONG_BUY_SCORE": 65,
  "STRONG_BUY_CONFIDENCE": 0.75,
  ...
}
```

**PUT /api/v1/config/signal**
```
Request:
{
  "SENTIMENT_WEIGHT": 0.60,
  "TECHNICAL_WEIGHT": 0.30,
  "RISK_WEIGHT": 0.10
}

Response:
{
  "message": "Configuration updated",
  "updated_fields": ["SENTIMENT_WEIGHT", "TECHNICAL_WEIGHT", "RISK_WEIGHT"]
}
```

---

## 12. Kalkulációs Formulák

### 12.1 Sentiment Score
```
sentiment_score = (pos_prob - neg_prob) × (1 - neu_prob)
```

### 12.2 Weighted Sentiment (Time Decay)
```
weighted_avg = Σ(sentiment_i × decay_i × credibility_i) / Σ(decay_i × credibility_i)
```

### 12.3 Technical Score
```
technical_score = trend × 0.40 + momentum × 0.30 + volatility × 0.20 + volume × 0.10
```

### 12.4 Risk Score
```
risk_score = volatility_risk × 0.40 + proximity_risk × 0.35 + trend_strength_risk × 0.25
```

### 12.5 Combined Score
```
combined_score = sentiment × W_s + technical × W_t + risk × W_r
```
ahol W_s, W_t, W_r = konfigurálható súlyok (default: 0.70, 0.20, 0.10)

### 12.6 Overall Confidence
```
confidence = sentiment_conf × 0.40 + technical_conf × 0.30 + volume_factor × 0.20 + rr_bonus × 0.10
```

### 12.7 Stop Loss (BUY)
```
stop_loss = min(support - 0.5×ATR, entry - 2×ATR)
```

### 12.8 Take Profit (BUY)
```
take_profit = min(resistance, entry + 3×ATR)
```

### 12.9 Risk:Reward Ratio
```
R:R = (take_profit - entry) / (entry - stop_loss)
```

---

## 13. Telepítés és Használat

### 13.1 Backend Telepítés

```bash
# 1. Repo klónozása
git clone https://github.com/your-repo/trendsignal-mvp.git
cd trendsignal-mvp

# 2. Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# vagy: venv\Scripts\activate  # Windows

# 3. Dependencies
pip install -r requirements.txt

# 4. API kulcsok (src/config.py)
NEWSAPI_KEY = "your_key"
ALPHAVANTAGE_KEY = "your_key"
GNEWS_API_KEY = "your_key"

# 5. Database init
python -c "from models import init_db; init_db()"

# 6. Backend indítás
python api.py
```

### 13.2 Frontend Telepítés

```bash
# 1. Frontend mappa
cd frontend

# 2. Dependencies
npm install

# 3. Dev server
npm run dev
```

### 13.3 Első Használat

1. Backend: `python api.py` (http://localhost:8000)
2. Frontend: `npm run dev` (http://localhost:5173)
3. Dashboard megnyitása → Refresh Signals gomb
4. Configuration oldal → Súlyok módosítása
5. Dashboard → Újra Refresh → Új súlyokkal generált signalok

---

## 14. Összefoglalás

### 14.1 Főbb Komponensek

✅ **Sentiment Analízis** - FinBERT AI + Time Decay Model  
✅ **Technical Analízis** - Multi-timeframe (5m/1h/1d/15m), 7 indikátor  
✅ **Risk Management** - ATR-based, S/R proximity, ADX trend strength  
✅ **Signal Generálás** - 3-komponensű weighted scoring  
✅ **Dinamikus Config** - Real-time módosítás, backend restart nélkül  
✅ **Multi-Source News** - GNews, Alpha Vantage, NewsAPI, Magyar RSS  
✅ **Frontend Dashboard** - React + TypeScript, real-time updates  

### 14.2 Kulcs Kalkulációk

- **Combined Score:** Sentiment (70%) + Technical (20%) + Risk (10%)
- **Time Decay:** 0-2h (100%) → 12-24h (35%)
- **Stop Loss:** min(Support - 0.5×ATR, Entry - 2×ATR)
- **Take Profit:** min(Resistance, Entry + 3×ATR)
- **Confidence:** Multi-factor (FinBERT + Technical + Volume + R:R)

### 14.3 Státusz

**MVP Status:** ✅ **PRODUCTION READY**

---

**Dokumentum vége**
