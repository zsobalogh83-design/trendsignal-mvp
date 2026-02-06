# TrendSignal MVP - Komolyabb Módosítások Összefoglalója

*Visszamenőlegesen összegyűjtött dokumentáció a projekt fejlesztési történetéből*

---

## 📋 Tartalomjegyzék

1. [Sentiment Decay Model 24h Ablakra Bővítése](#1-sentiment-decay-model-24h-ablakra-bővítése)
2. [FinBERT Sentiment Formula Javítása](#2-finbert-sentiment-formula-javítása)
3. [Technical Indicators Manual Implementáció](#3-technical-indicators-manual-implementáció)
4. [Database Struktúra és Persistence](#4-database-struktúra-és-persistence)
5. [Signal Generation Architecture](#5-signal-generation-architecture)
6. [Risk Score Komponensek Bővítése](#6-risk-score-komponensek-bővítése)
7. [Technical Indicators Time Series Tárolás](#7-technical-indicators-time-series-tárolás)
8. [Ticker Configuration Database-Driven System](#8-ticker-configuration-database-driven-system)
9. [Konfigurációs Paraméterek UI-ról Kezelése](#9-konfigurációs-paraméterek-ui-ról-kezelése)
10. [Frontend-Backend Architektúra](#10-frontend-backend-architektúra)

---

## 1. Sentiment Decay Model 24h Ablakra Bővítése

### Probléma
Az eredeti specifikáció 2-4-8-12 órás decay ablakokkal számolt, ami nem fedte le az overnight news hatását a reggeli kereskedésre.

### Megoldás
**Új 4 ablakos decay model implementálása:**

```python
DECAY_WEIGHTS = {
    '0-2h': 1.00,    # 100% - Fresh news (friss hírek)
    '2-6h': 0.85,    # 85% - Strong relevance (erős relevancia)
    '6-12h': 0.60,   # 60% - Intraday news (nap közbeni)
    '12-24h': 0.35,  # 35% - Overnight news (előző napi)
}
```

### Indoklás
- Day trading kontextusban az overnight news kritikus a reggeli nyitáskor
- 24 órás ablak biztosítja, hogy az előző esti hírek is beépüljenek a signal-be
- Time decay realisztikusabb: exponenciális csökkenés helyett lépcsős

### Érintett Fájlok
- `sentiment_analyzer.py` - Decay számítás
- `config.py` - DECAY_WEIGHTS konstans
- Specifikáció: Section 3.2 (Sentiment Decay Model)

### Referencia
Chat: "Python implementációhoz specifikációk frissítése" (2025-12-27)

---

## 2. FinBERT Sentiment Formula Javítása

### Probléma
Eredeti formula figyelmen kívül hagyta a neutral probability-t:
```python
# HIBÁS
sentiment_score = pos - neg  # -1 to +1
```

### Megoldás
**Neutral probability beépítése a normalizálásba:**

```python
# HELYES
sentiment_score = (pos - neg) / (pos + neu + neg)
# Normalizált skála: -1.0 to +1.0
```

### Indoklás
- Ha `pos=0.4, neu=0.5, neg=0.1`:
  - Régi: `0.4 - 0.1 = +0.3` (túl optimista)
  - Új: `(0.4 - 0.1) / 1.0 = +0.3` de a confidence számításban a neutral csökkenti a bizonyosságot
- Magas neutral érték (pl. 0.7) jelzi a bizonytalanságot → kevesebb false signal

### Confidence Számítás
```python
# A dominant probability és a második legnagyobb közötti különbség
confidence = max(pos, neu, neg) - sorted([pos, neu, neg])[1]
```

### Érintett Fájlok
- `sentiment_analyzer.py` - FinBERT score calculation
- UC-3.1 specifikációban dokumentálva

### Referencia
Chat: "Python implementációhoz specifikációk frissítése" (2025-12-27)

---

## 3. Technical Indicators Manual Implementáció

### Probléma
`pandas-ta` library dependency conflicts Google Colab környezetben.

### Megoldás
**Manual implementation pure numpy/pandas-al:**

```python
def calculate_rsi(data, period=14):
    """RSI calculation without external libraries"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    """MACD calculation"""
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist
```

### Implementált Indikátorok
- ✅ SMA (20, 50, 200)
- ✅ EMA (12, 26)
- ✅ RSI (14)
- ✅ MACD (12, 26, 9)
- ✅ ATR (14)
- ✅ Bollinger Bands (20, 2)
- ✅ Stochastic Oscillator
- ✅ CCI (Commodity Channel Index)
- ✅ ADX (Average Directional Index)
- ✅ OBV (On-Balance Volume)
- ✅ Support/Resistance (DBSCAN clustering)

### Multi-Timeframe Support
```python
TIMEFRAMES = {
    'sma_short': ('5m', 2),      # 5 min candles, 2 days lookback
    'sma_medium': ('1h', 30),    # 1h candles, 30 days
    'sma_long': ('1d', 180),     # Daily candles, 180 days
    'rsi': ('5m', 2),
    'macd': ('15m', 3),
    'bollinger': ('1h', 7),
    'atr': ('1d', 180),          # ATR always on daily!
}
```

### Megjegyzés
Phase 2-ben upgrade pandas-ta-ra production környezetben.

### Érintett Fájlok
- `technical_analysis.py` - Manual calculations
- `signal_generator.py` - Indicator orchestration
- UC-4.2 specifikációban

### Referencia
Chat: "Python implementációhoz specifikációk frissítése" (2025-12-27)

---

## 4. Database Struktúra és Persistence

### Áttekintés
SQLite-based persistence FastAPI backend-ben, SQLAlchemy ORM-mel.

### Database Modellek

#### Tickers
```python
class Ticker(Base):
    __tablename__ = "tickers"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    exchange = Column(String(10))
    
    # Ticker-specific configuration
    primary_language = Column(String(5), default='en')
    sector = Column(String(50))
    currency = Column(String(3))
    
    # Keyword-based filtering (JSON arrays as TEXT)
    relevance_keywords = Column(Text)  # ["oil", "gas", "energy"]
    sentiment_keywords_positive = Column(Text)  # ["profit", "growth"]
    sentiment_keywords_negative = Column(Text)  # ["loss", "decline"]
    
    # News source preferences
    news_sources_preferred = Column(Text)  # ["reuters", "bloomberg"]
    news_sources_blocked = Column(Text)    # ["spam.com"]
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

#### NewsItem
```python
class NewsItem(Base):
    __tablename__ = "news_items"
    
    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"))
    ticker_symbol = Column(String(10), index=True)
    
    # News metadata
    title = Column(Text, nullable=False)
    url = Column(String(500), unique=True, index=True)
    source = Column(String(100))
    published_at = Column(DateTime, index=True)
    
    # Sentiment scores
    sentiment_score = Column(Float)  # -1.0 to +1.0
    sentiment_label = Column(String(10))  # positive/neutral/negative
    confidence = Column(Float)  # 0.0 to 1.0
    
    # Decay tracking
    hours_old = Column(Float)
    decay_weight = Column(Float)  # Based on age
    weighted_sentiment = Column(Float)  # score × decay_weight
    
    # Language detection
    detected_language = Column(String(5))
    
    # Content (optional - can be large)
    content = Column(Text)
    
    fetched_at = Column(DateTime, server_default=func.now())
```

#### PriceData
```python
class PriceData(Base):
    __tablename__ = "price_data"
    
    id = Column(Integer, primary_key=True)
    ticker_symbol = Column(String(10), index=True)
    interval = Column(String(5), index=True)  # 5m, 15m, 1h, 1d
    timestamp = Column(DateTime, index=True)
    
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    
    price_change = Column(Float)
    price_change_pct = Column(Float)
    
    fetched_at = Column(DateTime, server_default=func.now())
```

#### TechnicalIndicator
```python
class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"
    
    id = Column(Integer, primary_key=True)
    ticker_symbol = Column(String(10), index=True)
    interval = Column(String(5))
    timestamp = Column(DateTime, index=True)
    
    # Trend indicators
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    ema_12 = Column(Float)
    ema_26 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    adx = Column(Float)
    
    # Momentum indicators
    rsi = Column(Float)
    stoch_k = Column(Float)
    stoch_d = Column(Float)
    cci = Column(Float)
    
    # Volatility indicators
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    atr = Column(Float)
    
    # Volume indicators
    volume_sma = Column(BigInteger)
    obv = Column(BigInteger)
    
    close_price = Column(Float)
    technical_score = Column(Float)
    technical_confidence = Column(Float)
    score_components = Column(Text)  # JSON
    
    calculated_at = Column(DateTime, server_default=func.now())
```

#### Signal
```python
class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"))
    ticker_symbol = Column(String(10), index=True)
    
    # Link to technical indicators snapshot
    technical_indicator_id = Column(Integer, ForeignKey("technical_indicators.id"))
    
    # Decision
    decision = Column(String(20), nullable=False)  # BUY/SELL/HOLD
    strength = Column(String(20))  # STRONG/MODERATE/WEAK
    
    # Scores
    combined_score = Column(Float)
    sentiment_score = Column(Float)
    technical_score = Column(Float)
    risk_score = Column(Float)
    
    # Confidence
    overall_confidence = Column(Float)
    sentiment_confidence = Column(Float)
    technical_confidence = Column(Float)
    risk_confidence = Column(Float)
    
    # Component details (structured)
    sentiment_score_pos = Column(Float)
    sentiment_score_neg = Column(Float)
    sentiment_score_neu = Column(Float)
    technical_score_trend = Column(Float)
    technical_score_momentum = Column(Float)
    technical_score_volatility = Column(Float)
    technical_score_volume = Column(Float)
    risk_score_volatility = Column(Float)
    risk_score_proximity = Column(Float)
    risk_score_trend_strength = Column(Float)
    
    # Entry/Exit levels
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    risk_reward_ratio = Column(Float)
    
    # Support/Resistance
    nearest_support = Column(Float)
    support_distance_pct = Column(Float)
    nearest_resistance = Column(Float)
    resistance_distance_pct = Column(Float)
    
    # Reasoning (JSON string for debugging)
    reasoning_json = Column(Text)
    
    # Lifecycle
    status = Column(String(20), default='active', index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    expires_at = Column(DateTime)
    archived_at = Column(DateTime)
```

### Database Migration Példa
```python
# migrate_add_technical_columns.py
import sqlite3

conn = sqlite3.connect("trendsignal.db")
cursor = conn.cursor()

# Add new column to existing table
cursor.execute("""
    ALTER TABLE signals 
    ADD COLUMN technical_indicator_id INTEGER 
    REFERENCES technical_indicators(id)
""")

conn.commit()
```

### Érintett Fájlok
- `models.py` - SQLAlchemy models
- `database.py` - Engine & session config
- `db_helpers.py` - CRUD operations
- Migration scripts: `migrate_*.py`

### Referencia
Chat: "Signal decision thresholds parameterization" (2026-02-01)
Chat: "Frontend indítási parancs" (2025-12-30)

---

## 5. Signal Generation Architecture

### Component-Based Scoring System

#### 1. Sentiment Component (70% súly)
```python
def calculate_sentiment_score(news_items: List[NewsItem]) -> Dict:
    """
    Sentiment scoring with decay model
    
    Returns:
        {
            'score': -100 to +100,
            'confidence': 0.0 to 1.0,
            'reasoning': {...}
        }
    """
    weighted_scores = []
    
    for news in news_items:
        # Apply time decay
        hours_old = (datetime.now() - news.published_at).total_seconds() / 3600
        decay_weight = get_decay_weight(hours_old)
        
        # Weight by decay
        weighted_score = news.sentiment_score * decay_weight
        weighted_scores.append((weighted_score, news.confidence))
    
    # Aggregate
    if weighted_scores:
        avg_sentiment = sum(s for s, _ in weighted_scores) / len(weighted_scores)
        avg_confidence = sum(c for _, c in weighted_scores) / len(weighted_scores)
        
        # Scale to -100..+100
        sentiment_score = avg_sentiment * 100
    else:
        sentiment_score = 0
        avg_confidence = 0
    
    return {
        'score': sentiment_score,
        'confidence': avg_confidence,
        'reasoning': {...}
    }
```

#### 2. Technical Component (20% súly)

**Sub-components:**
- Trend (40%): SMA alignment, MACD
- Momentum (30%): RSI, Stochastic
- Volatility (20%): Bollinger Bands, ATR
- Volume (10%): OBV, Volume SMA

```python
def calculate_technical_score(indicators: Dict) -> Dict:
    """
    Technical score from multiple indicators
    
    Returns:
        {
            'score': -100 to +100,
            'confidence': 0.0 to 1.0,
            'components': {...}
        }
    """
    # Trend signals
    trend_score = 0
    if indicators['sma_20'] > indicators['sma_50'] > indicators['sma_200']:
        trend_score += 100  # Golden Cross
    elif indicators['sma_20'] < indicators['sma_50'] < indicators['sma_200']:
        trend_score -= 100  # Death Cross
    
    # MACD
    if indicators['macd'] > indicators['macd_signal']:
        trend_score += 100
    else:
        trend_score -= 100
    
    # Average
    trend_score /= 2  # -100 to +100
    
    # Momentum signals
    momentum_score = 0
    rsi = indicators['rsi']
    
    if rsi > 70:
        momentum_score -= 100  # Overbought
    elif rsi < 30:
        momentum_score += 100  # Oversold (bullish reversal)
    else:
        momentum_score = (50 - rsi) * 2  # Linear interpolation
    
    # ... (Volatility, Volume similarly)
    
    # Weighted combination
    technical_score = (
        trend_score * 0.40 +
        momentum_score * 0.30 +
        volatility_score * 0.20 +
        volume_score * 0.10
    )
    
    # Confidence based on alignment
    signals = [trend_score > 0, momentum_score > 0, ...]
    alignment = sum(1 for s in signals if s) / len(signals)
    confidence = alignment  # 0.0 to 1.0
    
    return {
        'score': technical_score,
        'confidence': confidence,
        'components': {
            'trend': trend_score,
            'momentum': momentum_score,
            ...
        }
    }
```

#### 3. Risk Component (10% súly)

**Sub-components:**
- Volatility (40%): ATR-based risk
- Proximity (35%): S/R distance
- Trend Strength (25%): ADX

```python
def calculate_risk_score(indicators: Dict, current_price: float) -> Dict:
    """
    Risk scoring based on volatility, S/R proximity, and trend strength
    
    Returns:
        {
            'score': -50 to +50 (not -100 to +100!),
            'confidence': 0.0 to 1.0,
            'components': {...}
        }
    """
    # 1. Volatility risk (ATR-based)
    atr = indicators['atr']
    atr_pct = (atr / current_price) * 100
    
    if atr_pct < 2.0:
        volatility_risk = +0.5  # Low volatility = low risk
    elif atr_pct < 4.0:
        volatility_risk = 0.0   # Medium
    else:
        volatility_risk = -0.5  # High volatility = high risk
    
    # 2. S/R proximity risk
    support_dist = ((current_price - indicators['nearest_support']) / current_price) * 100
    resistance_dist = ((indicators['nearest_resistance'] - current_price) / current_price) * 100
    
    if support_dist > 2.0 and resistance_dist > 2.0:
        proximity_risk = +0.5  # Safe zone
    elif min(support_dist, resistance_dist) < 1.0:
        proximity_risk = -0.3  # Too close to S/R
    else:
        proximity_risk = 0.0   # Neutral
    
    # 3. Trend strength risk (ADX-based)
    adx = indicators['adx']
    
    if adx > 25:
        trend_strength_risk = +0.4  # Strong trend = lower risk
    elif adx > 20:
        trend_strength_risk = +0.2  # Medium trend
    else:
        trend_strength_risk = -0.2  # Weak trend = higher risk
    
    # Weighted combination
    risk_score = (
        volatility_risk * 0.40 +
        proximity_risk * 0.35 +
        trend_strength_risk * 0.25
    ) * 100  # Scale to -50..+50
    
    # Confidence from R:R ratio
    r_r_ratio = indicators['risk_reward_ratio']
    if r_r_ratio >= 2.0:
        confidence = 0.90
    elif r_r_ratio >= 1.5:
        confidence = 0.80
    elif r_r_ratio >= 1.0:
        confidence = 0.65
    else:
        confidence = 0.50
    
    return {
        'score': risk_score,
        'confidence': confidence,
        'components': {
            'volatility': volatility_risk * 100,
            'proximity': proximity_risk * 100,
            'trend_strength': trend_strength_risk * 100
        }
    }
```

#### 4. Combined Signal

```python
def generate_signal(sentiment_data, technical_data, risk_data, config) -> Signal:
    """
    Generate final trading signal
    
    Weights:
        - Sentiment: 70%
        - Technical: 20%
        - Risk: 10%
    """
    # Extract scores
    sentiment_score = sentiment_data['score']
    technical_score = technical_data['score']
    risk_score = risk_data['score']
    
    # Combined score
    combined_score = (
        sentiment_score * config.SENTIMENT_WEIGHT +
        technical_score * config.TECHNICAL_WEIGHT +
        risk_score * config.RISK_WEIGHT
    )
    
    # Overall confidence
    overall_confidence = (
        sentiment_data['confidence'] * config.SENTIMENT_WEIGHT +
        technical_data['confidence'] * config.TECHNICAL_WEIGHT +
        risk_data['confidence'] * config.RISK_WEIGHT
    )
    
    # Decision logic
    if combined_score >= config.STRONG_BUY_SCORE and overall_confidence >= config.STRONG_BUY_CONFIDENCE:
        decision = "STRONG BUY"
    elif combined_score >= config.MODERATE_BUY_SCORE and overall_confidence >= config.MODERATE_BUY_CONFIDENCE:
        decision = "MODERATE BUY"
    elif combined_score <= config.STRONG_SELL_SCORE and overall_confidence >= config.STRONG_SELL_CONFIDENCE:
        decision = "STRONG SELL"
    elif combined_score <= config.MODERATE_SELL_SCORE and overall_confidence >= config.MODERATE_SELL_CONFIDENCE:
        decision = "MODERATE SELL"
    else:
        decision = "HOLD"
    
    # Calculate entry/exit levels
    entry_price = current_price
    stop_loss = calculate_stop_loss(current_price, indicators, decision)
    take_profit = calculate_take_profit(current_price, indicators, decision)
    
    return Signal(
        decision=decision,
        combined_score=combined_score,
        sentiment_score=sentiment_score,
        technical_score=technical_score,
        risk_score=risk_score,
        overall_confidence=overall_confidence,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        ...
    )
```

### Érintett Fájlok
- `signal_generator.py` - Main orchestration
- `sentiment_analyzer.py` - Sentiment component
- `technical_analysis.py` - Technical component
- `config.py` - Weights & thresholds

### Referencia
Chat: "Signal súlyok nem frissítik a score értéket" (2025-12-28)

---

## 6. Risk Score Komponensek Bővítése

### Eredeti Probléma
Kezdeti risk score csak stop-loss távolságot vizsgálta, nem volt szofisztikált.

### Implementált Megoldás

**3 komponensű risk scoring:**

1. **Volatility Risk (40%)** - ATR-based
   ```python
   atr_pct = (atr / current_price) * 100
   
   if atr_pct < 2.0:
       volatility_risk = +0.5   # Low vol
   elif atr_pct < 4.0:
       volatility_risk = 0.0    # Medium
   else:
       volatility_risk = -0.5   # High vol
   ```

2. **Proximity Risk (35%)** - S/R distance
   ```python
   support_dist_pct = ((price - support) / price) * 100
   resistance_dist_pct = ((resistance - price) / price) * 100
   
   if both > 2.0:
       proximity_risk = +0.5   # Safe zone
   elif either < 1.0:
       proximity_risk = -0.3   # Too close
   else:
       proximity_risk = 0.0
   ```

3. **Trend Strength Risk (25%)** - ADX
   ```python
   if adx > 25:
       trend_strength_risk = +0.4   # Strong trend
   elif adx > 20:
       trend_strength_risk = +0.2   # Medium
   else:
       trend_strength_risk = -0.2   # Weak
   ```

**Risk Score Range:** -50 to +50 (nem -100 to +100!)

### Risk Confidence Enhancement
```python
# R:R ratio alapú confidence
if risk_reward_ratio >= 2.0:
    risk_confidence = 0.90
elif risk_reward_ratio >= 1.5:
    risk_confidence = 0.80
elif risk_reward_ratio >= 1.0:
    risk_confidence = 0.65
else:
    risk_confidence = 0.50
```

### Érintett Fájlok
- `signal_generator.py` - `calculate_risk_score()`
- `config.py` - Risk component weights

### Referencia
Chat: "Signal súlyok nem frissítik a score értéket" (2025-12-28)

---

## 7. Technical Indicators Time Series Tárolás

### Probléma
Kezdetben a technical indicator számítások nem voltak perzisztálva, csak on-the-fly kalkuláció történt.

### Megoldás: Time Series Approach

**Dedicated TechnicalIndicator tábla:**
```python
class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"
    
    id = Column(Integer, primary_key=True)
    ticker_symbol = Column(String(10), index=True)
    interval = Column(String(5))      # 5m, 15m, 1h, 1d
    timestamp = Column(DateTime, index=True)
    
    # 20+ indicator columns (RSI, MACD, SMA, BB, ATR, etc.)
    ...
    
    calculated_at = Column(DateTime, server_default=func.now())
```

**Signal ↔ TechnicalIndicator Linking:**
```python
class Signal(Base):
    # Link to snapshot
    technical_indicator_id = Column(
        Integer, 
        ForeignKey("technical_indicators.id"),
        nullable=True
    )
```

### Database Migration
```sql
ALTER TABLE signals 
ADD COLUMN technical_indicator_id INTEGER 
REFERENCES technical_indicators(id);

ALTER TABLE signals 
ADD COLUMN technical_score_trend FLOAT;

ALTER TABLE signals 
ADD COLUMN technical_score_momentum FLOAT;

ALTER TABLE signals 
ADD COLUMN technical_score_volatility FLOAT;

ALTER TABLE signals 
ADD COLUMN technical_score_volume FLOAT;
```

### Implementation Pattern
```python
# 1. Calculate indicators
indicators = calculate_all_indicators(df)

# 2. Save to database
tech_indicator_id = save_technical_indicators_to_db(
    ticker_symbol=symbol,
    indicators=indicators,
    db=db_session
)

# 3. Link to signal
signal = Signal(
    ticker_symbol=symbol,
    technical_indicator_id=tech_indicator_id,  # Link!
    technical_score=tech_score,
    ...
)
```

### Előnyök
- ✅ Historical tracking (backtesting)
- ✅ Audit trail (debugging)
- ✅ Performance analytics
- ✅ Signal-indicator traceability

### Érintett Fájlok
- `models.py` - TechnicalIndicator model + Foreign Key
- `db_helpers.py` - `save_technical_indicators_to_db()`
- `signal_generator.py` - Linking logic
- `signals_api.py` - API endpoints
- `migrate_add_technical_columns.py` - Migration script

### Referencia
Chat: "Signal decision thresholds parameterization" (2026-02-01)

---

## 8. Ticker Configuration Database-Driven System

### Probléma
Ticker-specifikus konfigurációk (keywords, preferred sources) hardcoded-ként voltak a Python fájlokban.

### Megoldás: Database-Driven Config

**Bővített Ticker Model:**
```python
class Ticker(Base):
    __tablename__ = "tickers"
    
    # Basic info
    symbol = Column(String(10), unique=True, index=True)
    name = Column(String(100))
    exchange = Column(String(10))
    
    # Configuration
    primary_language = Column(String(5), default='en')
    sector = Column(String(50))
    currency = Column(String(3))
    
    # Keywords (JSON arrays stored as TEXT)
    relevance_keywords = Column(Text)  # ["oil", "gas", "energy"]
    sentiment_keywords_positive = Column(Text)
    sentiment_keywords_negative = Column(Text)
    
    # News sources
    news_sources_preferred = Column(Text)  # ["reuters", "bloomberg"]
    news_sources_blocked = Column(Text)
    
    is_active = Column(Boolean, default=True)
```

**Helper Functions:**
```python
# ticker_config.py
class TickerConfig:
    @staticmethod
    def get_sentiment_keywords(ticker_symbol: str, db) -> Dict:
        """Load ticker keywords from database"""
        ticker = db.query(Ticker).filter_by(symbol=ticker_symbol).first()
        
        if ticker:
            return {
                'positive': json.loads(ticker.sentiment_keywords_positive or "[]"),
                'negative': json.loads(ticker.sentiment_keywords_negative or "[]"),
                'relevance': json.loads(ticker.relevance_keywords or "[]")
            }
        return None
    
    @staticmethod
    def get_news_sources(ticker_symbol: str, db) -> Dict:
        """Load preferred/blocked sources"""
        ticker = db.query(Ticker).filter_by(symbol=ticker_symbol).first()
        
        if ticker:
            return {
                'preferred': json.loads(ticker.news_sources_preferred or "[]"),
                'blocked': json.loads(ticker.news_sources_blocked or "[]")
            }
        return None
```

### Data Migration
```python
# migrate_ticker_data.py
from ticker_keywords import TICKER_KEYWORDS  # Old hardcoded data

for symbol, config in TICKER_KEYWORDS.items():
    ticker = db.query(Ticker).filter_by(symbol=symbol).first()
    
    if ticker:
        ticker.relevance_keywords = json.dumps(config['relevance'])
        ticker.sentiment_keywords_positive = json.dumps(config['sentiment']['positive'])
        ticker.sentiment_keywords_negative = json.dumps(config['sentiment']['negative'])
        
db.commit()
```

### SQLAlchemy Registry Conflict Fix
**Probléma:** Circular imports és `relationship()` conflicts.

**Megoldás:** Relationships eltávolítása, explicit Foreign Key használata:
```python
# ELŐTTE (ROSSZ - circular dependency)
class Ticker(Base):
    signals = relationship("Signal", back_populates="ticker")

class Signal(Base):
    ticker = relationship("Ticker", back_populates="signals")

# UTÁNA (JÓ - simple FK)
class Signal(Base):
    ticker_id = Column(Integer, ForeignKey("tickers.id"))
    ticker_symbol = Column(String(10), index=True)
    # NO relationship()!
```

### Érintett Fájlok
- `models.py` - Bővített Ticker model (NO relationships!)
- `ticker_config.py` - Helper functions
- `sentiment_analyzer.py` - DB-driven keywords
- `hungarian_news.py` - DB-driven sources
- `migrate_ticker_schema.py` - Schema migration
- `migrate_ticker_data.py` - Data migration
- `database.py` - Fixed init_db()

### Referencia
Chat: "Signal generálás szimmetriájának ellenőrzése" (2026-02-04)

---

## 9. Konfigurációs Paraméterek UI-ról Kezelése

### Áttekintés
Production-ready config management backend-ben + frontend UI-val.

### Backend Architecture

#### Config.py - Centralized Configuration
```python
class ConfigManager:
    """Singleton config manager with persistence"""
    
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.load_from_file()
    
    def load_from_file(self):
        """Load config from JSON file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                saved_config = json.load(f)
                self.sentiment_weight = saved_config.get("SENTIMENT_WEIGHT", 0.70)
                self.technical_weight = saved_config.get("TECHNICAL_WEIGHT", 0.20)
                # ... 50+ paraméter
    
    def save_to_file(self):
        """Persist config to JSON"""
        config_dict = {
            "SENTIMENT_WEIGHT": self.sentiment_weight,
            "TECHNICAL_WEIGHT": self.technical_weight,
            # ...
        }
        with open(self.config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def reload(self):
        """Hot reload without restarting backend"""
        self.load_from_file()
        print("🔄 Config reloaded from file")

# Global instance
config = ConfigManager()
```

#### Config API Endpoints (config_api.py)

**1. Signal Weights & Thresholds:**
```python
@router.get("/api/v1/config/signal")
def get_signal_config():
    return {
        "sentiment_weight": config.sentiment_weight,
        "technical_weight": config.technical_weight,
        "risk_weight": config.risk_weight,
        "strong_buy_score": config.strong_buy_score,
        "strong_buy_confidence": config.strong_buy_confidence,
        # ... 11 paraméter
    }

@router.put("/api/v1/config/signal")
def update_signal_config(update: SignalConfigUpdate):
    config.sentiment_weight = update.sentiment_weight
    config.technical_weight = update.technical_weight
    # ...
    config.save_to_file()
    return {"status": "success"}
```

**2. Technical Indicator Parameters:**
```python
@router.get("/api/v1/config/indicator-parameters")
def get_indicator_params():
    return {
        "rsi_period": config.rsi_period,
        "rsi_timeframe": config.rsi_timeframe,
        "sma_short_period": config.sma_short_period,
        # ... 27 paraméter
    }

@router.put("/api/v1/config/indicator-parameters")
def update_indicator_params(update: IndicatorParametersUpdate):
    # Validáció
    if not (5 <= update.rsi_period <= 30):
        raise HTTPException(400, "RSI period must be 5-30")
    
    config.rsi_period = update.rsi_period
    # ...
    config.save_to_file()
    config.reload()  # Hot reload
    return {"status": "success"}
```

**3. Technical Component Weights:**
```python
@router.get("/api/v1/config/technical-component-weights")
def get_tech_component_weights():
    return {
        "tech_macd_weight": config.tech_macd_weight,
        "tech_bollinger_weight": config.tech_bollinger_weight,
        # ... 6 weight paraméter
    }

@router.put("/api/v1/config/technical-component-weights")
def update_tech_component_weights(update: TechnicalComponentWeightsUpdate):
    # Validáció: összeg = 1.0
    total = (update.tech_macd_weight + update.tech_bollinger_weight + ...)
    if not (0.99 <= total <= 1.01):
        raise HTTPException(400, "Weights must sum to 1.0")
    
    config.tech_macd_weight = update.tech_macd_weight
    # ...
    config.save_to_file()
    return {"status": "success"}
```

**4. Technical Signal Weights:**
```python
@router.get("/api/v1/config/technical-weights")
def get_technical_weights():
    return {
        "tech_sma20_bullish": config.tech_sma20_bullish,
        "tech_sma20_bearish": config.tech_sma20_bearish,
        "tech_rsi_overbought": config.tech_rsi_overbought,
        # ... 11 signal score paraméter
    }

@router.put("/api/v1/config/technical-weights")
def update_technical_weights(update: TechnicalWeightsUpdate):
    config.tech_sma20_bullish = update.tech_sma20_bullish
    # ...
    config.save_to_file()
    return {"status": "success"}
```

**5. Risk Parameters:**
```python
@router.get("/api/v1/config/risk-parameters")
def get_risk_params():
    return {
        "risk_volatility_weight": config.risk_volatility_weight,
        "risk_proximity_weight": config.risk_proximity_weight,
        "stop_loss_atr_mult": config.stop_loss_atr_mult,
        # ... 10 paraméter
    }

@router.put("/api/v1/config/risk-parameters")
def update_risk_params(update: RiskParametersUpdate):
    # Validáció
    total_weight = (update.risk_volatility_weight + 
                    update.risk_proximity_weight + 
                    update.risk_trend_strength_weight)
    if not (0.99 <= total_weight <= 1.01):
        raise HTTPException(400, "Risk weights must sum to 1.0")
    
    config.risk_volatility_weight = update.risk_volatility_weight
    # ...
    config.save_to_file()
    return {"status": "success"}
```

### Frontend Implementation (Configuration.tsx)

**State Management:**
```typescript
const Configuration: React.FC = () => {
  // 1. Component Weights (Signal Config)
  const [componentWeights, setComponentWeights] = useState({
    sentiment: 70,
    technical: 20,
    risk: 10
  });
  
  // 2. Decision Thresholds
  const [decisionThresholds, setDecisionThresholds] = useState({
    strongBuyScore: 65,
    strongBuyConfidence: 0.75,
    // ... 8 paraméter
  });
  
  // 3. Technical Indicator Periods & Timeframes
  const [indicatorParams, setIndicatorParams] = useState({
    rsiPeriod: 14,
    rsiTimeframe: '5m',
    rsiLookback: '2d',
    // ... 27 paraméter
  });
  
  // 4. Technical Component Weights (%)
  const [technicalComponentWeights, setTechnicalComponentWeights] = useState({
    macdWeight: 0.15,
    bollingerWeight: 0.15,
    // ... 6 weight
  });
  
  // 5. Technical Signal Weights (score impact)
  const [technicalWeights, setTechnicalWeights] = useState({
    sma20Bullish: 25,
    rsiOverbought: -25,
    // ... 11 signal score
  });
  
  // 6. Risk Parameters
  const [riskParams, setRiskParams] = useState({
    volatilityWeight: 0.40,
    proximityWeight: 0.35,
    stopLossAtrMult: 2.0,
    // ... 10 paraméter
  });
}
```

**API Integration:**
```typescript
// Load configuration on mount
useEffect(() => {
  loadAllConfigs();
}, []);

const loadAllConfigs = async () => {
  try {
    // 1. Signal config
    const signalRes = await fetch('http://localhost:8000/api/v1/config/signal');
    const signalData = await signalRes.json();
    setComponentWeights({
      sentiment: Math.round(signalData.sentiment_weight * 100),
      technical: Math.round(signalData.technical_weight * 100),
      risk: Math.round(signalData.risk_weight * 100)
    });
    setDecisionThresholds({ /* map data */ });
    
    // 2. Indicator params
    const indicatorRes = await fetch('http://localhost:8000/api/v1/config/indicator-parameters');
    const indicatorData = await indicatorRes.json();
    setIndicatorParams({ /* map data */ });
    
    // 3. Technical component weights
    const tcwRes = await fetch('http://localhost:8000/api/v1/config/technical-component-weights');
    const tcwData = await tcwRes.json();
    setTechnicalComponentWeights({ /* map data */ });
    
    // 4. Technical signal weights
    const twRes = await fetch('http://localhost:8000/api/v1/config/technical-weights');
    const twData = await twRes.json();
    setTechnicalWeights({ /* map data */ });
    
    // 5. Risk parameters
    const riskRes = await fetch('http://localhost:8000/api/v1/config/risk-parameters');
    const riskData = await riskRes.json();
    setRiskParams({ /* map data */ });
    
  } catch (error) {
    console.error('Error loading configs:', error);
  }
};

// Save all configs
const handleSaveAll = async () => {
  try {
    // 1. Signal config
    await fetch('http://localhost:8000/api/v1/config/signal', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sentiment_weight: componentWeights.sentiment / 100,
        technical_weight: componentWeights.technical / 100,
        risk_weight: componentWeights.risk / 100,
        strong_buy_score: decisionThresholds.strongBuyScore,
        // ...
      })
    });
    
    // 2. Indicator params
    await fetch('http://localhost:8000/api/v1/config/indicator-parameters', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        rsi_period: indicatorParams.rsiPeriod,
        rsi_timeframe: indicatorParams.rsiTimeframe,
        // ...
      })
    });
    
    // 3-5. Similar pattern
    
    toast.success('All configurations saved!');
  } catch (error) {
    console.error('Error saving configs:', error);
    toast.error('Failed to save configuration');
  }
};
```

**UI Layout (Tabbed Interface):**
```typescript
return (
  <div className="configuration-page">
    <h1>Configuration</h1>
    
    {/* Tab Navigation */}
    <div className="tabs">
      <button onClick={() => setActiveTab('signal')}>
        Signal Config
      </button>
      <button onClick={() => setActiveTab('technical')}>
        Technical Config
      </button>
      <button onClick={() => setActiveTab('risk')}>
        Risk Config
      </button>
    </div>
    
    {/* Tab Content */}
    {activeTab === 'signal' && (
      <div className="tab-content">
        {/* Component Weights Sliders */}
        <Section title="Component Weights">
          <Slider 
            label="Sentiment Weight (%)"
            value={componentWeights.sentiment}
            onChange={(v) => setComponentWeights({...componentWeights, sentiment: v})}
            min={0} max={100}
          />
          {/* ... */}
        </Section>
        
        {/* Decision Thresholds */}
        <Section title="Decision Thresholds">
          <Input
            label="Strong Buy Score"
            type="number"
            value={decisionThresholds.strongBuyScore}
            onChange={(e) => setDecisionThresholds({
              ...decisionThresholds,
              strongBuyScore: parseFloat(e.target.value)
            })}
          />
          {/* ... */}
        </Section>
      </div>
    )}
    
    {activeTab === 'technical' && (
      <div className="tab-content">
        {/* Indicator Parameters */}
        <Section title="Indicator Periods & Timeframes">
          <div className="indicator-group">
            <h3>RSI</h3>
            <Input label="Period" value={indicatorParams.rsiPeriod} />
            <Select label="Timeframe" value={indicatorParams.rsiTimeframe}>
              <option value="5m">5 min</option>
              <option value="15m">15 min</option>
              <option value="1h">1 hour</option>
            </Select>
            <Select label="Lookback" value={indicatorParams.rsiLookback}>
              <option value="2d">2 days</option>
              <option value="7d">7 days</option>
            </Select>
          </div>
          {/* Repeat for SMA, MACD, Bollinger, ATR, Stochastic, ADX */}
        </Section>
        
        {/* Technical Component Weights */}
        <Section title="Technical Component Weights">
          <Slider 
            label="MACD Weight"
            value={technicalComponentWeights.macdWeight * 100}
            onChange={(v) => setTechnicalComponentWeights({
              ...technicalComponentWeights,
              macdWeight: v / 100
            })}
            min={0} max={100}
          />
          {/* ... 6 weights */}
        </Section>
        
        {/* Technical Signal Weights */}
        <Section title="Technical Signal Weights">
          <Input
            label="Price > SMA20 (Bullish)"
            type="number"
            value={technicalWeights.sma20Bullish}
            onChange={(e) => setTechnicalWeights({
              ...technicalWeights,
              sma20Bullish: parseFloat(e.target.value)
            })}
          />
          {/* ... 11 signal scores */}
        </Section>
      </div>
    )}
    
    {activeTab === 'risk' && (
      <div className="tab-content">
        {/* Risk Component Weights */}
        <Section title="Risk Component Weights">
          <Slider label="Volatility Weight" /* ... */ />
          <Slider label="Proximity Weight" /* ... */ />
          <Slider label="Trend Strength Weight" /* ... */ />
        </Section>
        
        {/* Stop Loss / Take Profit */}
        <Section title="Stop Loss / Take Profit">
          <Input label="S/R Buffer (ATR multiplier)" /* ... */ />
          <Input label="Stop Loss ATR Multiplier" /* ... */ />
          <Input label="Take Profit ATR Multiplier" /* ... */ />
        </Section>
        
        {/* S/R DBSCAN */}
        <Section title="Support/Resistance DBSCAN">
          <Input label="eps (%)" /* ... */ />
          <Input label="min_samples" /* ... */ />
          <Input label="order" /* ... */ />
          <Input label="lookback_days" /* ... */ />
        </Section>
      </div>
    )}
    
    {/* Save Button */}
    <button onClick={handleSaveAll} className="save-button">
      Save All Configurations
    </button>
  </div>
);
```

### Konfiguráció Összesítés

| Kategória | Paraméterek Száma | Endpoints |
|-----------|-------------------|-----------|
| Signal Config | 11 | `/api/v1/config/signal` |
| Indicator Params | 27 | `/api/v1/config/indicator-parameters` |
| Technical Component Weights | 6 | `/api/v1/config/technical-component-weights` |
| Technical Signal Weights | 11 | `/api/v1/config/technical-weights` |
| Risk Parameters | 10 | `/api/v1/config/risk-parameters` |
| **ÖSSZESEN** | **65 paraméter** | **5 endpoint** |

### Érintett Fájlok

**Backend:**
- `config.py` - ConfigManager class + 65 paraméter
- `config_api.py` - 5 endpoint + Pydantic models
- `signal_generator.py` - config.property használat
- `main.py` - Router registration

**Frontend:**
- `Configuration.tsx` - 3-tab UI + state management
- `api/config.ts` - API client (optional)

### Dokumentáció Fájlok
- `IMPLEMENTATION_GUIDE.md` - Teljes implementációs útmutató
- `Configuration_tsx_MODIFICATIONS.md` - Frontend módosítási guide

### Referencia
Chat: "Technical score calculation" (2026-02-02)
Chat: "113 KB-os TSX config fájl mérete" (2026-02-02)

---

## 10. Frontend-Backend Architektúra

### Technology Stack

**Frontend:**
- React 18 + TypeScript
- Vite build tool
- TailwindCSS for styling
- React Query for caching
- Axios for HTTP requests

**Backend:**
- Python 3.11+
- FastAPI framework
- SQLAlchemy ORM
- SQLite database
- Uvicorn ASGI server
- yfinance for market data

### Project Structure

```
trendsignal-mvp/
├── frontend/                 # React TypeScript app
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx      # Main signals view
│   │   │   ├── Configuration.tsx  # Config management
│   │   │   ├── SignalCard.tsx     # Individual signal display
│   │   │   └── ...
│   │   ├── api/
│   │   │   ├── signals.ts         # Signals API client
│   │   │   └── config.ts          # Config API client
│   │   ├── types/
│   │   │   └── signal.ts          # TypeScript interfaces
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                  # Python FastAPI app
│   ├── src/
│   │   ├── models.py              # SQLAlchemy models
│   │   ├── database.py            # DB engine & session
│   │   ├── config.py              # ConfigManager
│   │   ├── signal_generator.py   # Main orchestration
│   │   ├── sentiment_analyzer.py # Sentiment component
│   │   ├── technical_analysis.py # Technical component
│   │   ├── news_collector.py     # News fetching
│   │   ├── db_helpers.py          # CRUD operations
│   │   └── main.py                # FastAPI app entry
│   ├── config_api.py              # Config endpoints
│   ├── signals_api.py             # Signals endpoints
│   ├── requirements.txt
│   └── trendsignal.db             # SQLite database
│
├── docs/
│   ├── TrendSignal_MVP_Teljes_Specifikacio_UPDATED.md
│   ├── TrendSignal_Mukodesi_Dokumentacio.md
│   └── ...
│
└── README.md
```

### API Endpoints Architecture

**Base URL:** `http://localhost:8000`

#### 1. Signals API (`signals_api.py`)

```python
# GET /api/v1/signals
# Query params: status=active|archived, limit=50, offset=0
# Returns: List[SignalResponse]

# POST /api/v1/signals/refresh
# Triggers manual signal generation for all tickers
# Returns: List[SignalResponse]

# GET /api/v1/signals/{signal_id}
# Returns: SignalResponse (single signal detail)

# DELETE /api/v1/signals/{signal_id}
# Archives a signal (soft delete)

# GET /api/v1/signals/ticker/{ticker_symbol}
# Returns: List[SignalResponse] for specific ticker
```

#### 2. Configuration API (`config_api.py`)

```python
# GET /api/v1/config/signal
# Returns: Signal weights & thresholds

# PUT /api/v1/config/signal
# Body: SignalConfigUpdate
# Returns: {"status": "success"}

# GET /api/v1/config/indicator-parameters
# Returns: Indicator periods, timeframes, lookbacks

# PUT /api/v1/config/indicator-parameters
# Body: IndicatorParametersUpdate

# GET /api/v1/config/technical-component-weights
# Returns: MACD/Bollinger/etc. percentage weights

# PUT /api/v1/config/technical-component-weights
# Body: TechnicalComponentWeightsUpdate

# GET /api/v1/config/technical-weights
# Returns: Signal score impacts (SMA20 bullish = +25, etc.)

# PUT /api/v1/config/technical-weights
# Body: TechnicalWeightsUpdate

# GET /api/v1/config/risk-parameters
# Returns: Risk weights, S/L, T/P, DBSCAN params

# PUT /api/v1/config/risk-parameters
# Body: RiskParametersUpdate
```

#### 3. Tickers API (placeholder for future)

```python
# GET /api/v1/tickers
# Returns: List[Ticker] (all configured tickers)

# POST /api/v1/tickers
# Body: TickerCreate
# Returns: Ticker

# PUT /api/v1/tickers/{ticker_id}
# Body: TickerUpdate
# Returns: Ticker
```

### Frontend-Backend Communication Flow

**Signal Refresh Cycle:**

```
┌──────────────┐
│   Frontend   │
│  Dashboard   │
└──────┬───────┘
       │
       │ 1. User clicks "Refresh Signals"
       │
       ▼
┌──────────────────────┐
│ POST /api/v1/signals │
│      /refresh         │
└──────┬───────────────┘
       │
       │ 2. Backend triggers signal_generator.py
       │
       ▼
┌─────────────────────────────┐
│  SignalGenerator.generate() │
│  ├─ Fetch news              │
│  ├─ Calculate sentiment     │
│  ├─ Fetch price data        │
│  ├─ Calculate indicators    │
│  ├─ Generate signals        │
│  └─ Save to database        │
└──────┬──────────────────────┘
       │
       │ 3. Return signals JSON
       │
       ▼
┌──────────────┐
│   Frontend   │
│ Display Cards│
└──────────────┘
```

**Configuration Update Flow:**

```
┌──────────────┐
│   Frontend   │
│ Configuration│
└──────┬───────┘
       │
       │ 1. User modifies sliders/inputs
       │
       ▼
┌──────────────────────┐
│  PUT /api/v1/config/ │
│    indicator-params  │
└──────┬───────────────┘
       │
       │ 2. Backend validates & saves
       │
       ▼
┌─────────────────────┐
│  config.save_to_    │
│  file() → JSON      │
│  config.reload()    │
└──────┬──────────────┘
       │
       │ 3. Hot reload (no restart!)
       │
       ▼
┌─────────────────────────┐
│ Next signal generation  │
│ uses NEW parameters     │
└─────────────────────────┘
```

### Database Access Patterns

**Session Management:**
```python
# db_helpers.py
from database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# FastAPI dependency injection
@router.get("/api/v1/signals")
def get_signals(db: Session = Depends(get_db)):
    signals = db.query(Signal).filter_by(status='active').all()
    return signals
```

**Transaction Pattern:**
```python
def save_signal_to_db(signal_data: Dict, db: Session) -> Signal:
    """
    Atomic transaction for signal creation
    """
    try:
        # 1. Create signal object
        signal = Signal(**signal_data)
        
        # 2. Add to session
        db.add(signal)
        
        # 3. Commit
        db.commit()
        
        # 4. Refresh (get DB-generated ID)
        db.refresh(signal)
        
        return signal
    except Exception as e:
        db.rollback()
        raise e
```

### Error Handling

**Backend:**
```python
from fastapi import HTTPException

@router.get("/api/v1/signals/{signal_id}")
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    signal = db.query(Signal).filter_by(id=signal_id).first()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    return signal
```

**Frontend:**
```typescript
const fetchSignals = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/v1/signals');
    setSignals(response.data);
  } catch (error) {
    if (axios.isAxiosError(error)) {
      if (error.response?.status === 404) {
        toast.error('Signals not found');
      } else {
        toast.error('Failed to fetch signals');
      }
    }
    console.error('Error fetching signals:', error);
  }
};
```

### CORS Configuration

```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Development Workflow

**Backend Start:**
```bash
cd backend
pip install -r requirements.txt
python main.py  # or uvicorn main:app --reload
# Listening on http://localhost:8000
```

**Frontend Start:**
```bash
cd frontend
npm install
npm run dev
# Listening on http://localhost:5173
```

### Érintett Fájlok

**Backend:**
- `main.py` - FastAPI app + CORS
- `signals_api.py` - Signals endpoints
- `config_api.py` - Config endpoints
- `database.py` - Engine & SessionLocal

**Frontend:**
- `Dashboard.tsx` - Main signals view
- `Configuration.tsx` - Config management
- `api/signals.ts` - API client
- `vite.config.ts` - Proxy config (optional)

### Referencia
Chat: "Repo architektúra és technológiai stack áttekintése" (2026-01-30)
Chat: "Frontend indítási parancs" (2025-12-30)

---

## Összegzés

Ez a dokumentum 10 jelentős módosítást foglal össze a TrendSignal MVP fejlesztési története során:

1. ✅ **Sentiment Decay 24h** - Day trading overnight news support
2. ✅ **FinBERT Formula Fix** - Neutral probability normalization
3. ✅ **Manual Indicators** - Dependency-free technical analysis
4. ✅ **Database Persistence** - SQLite + SQLAlchemy architecture
5. ✅ **Signal Generation** - Component-based scoring system
6. ✅ **Enhanced Risk Score** - 3-component risk assessment
7. ✅ **Technical Time Series** - Historical indicator tracking
8. ✅ **Ticker Config DB** - Database-driven configuration
9. ✅ **UI Config Management** - 65 paraméter 5 endpoint-on
10. ✅ **Frontend-Backend Arch** - React + FastAPI + SQLite

---

**Készítette:** Claude (Anthropic)  
**Projekt:** TrendSignal MVP  
**Verzió:** 1.0  
**Dátum:** {{ DATE }}  
**Státusz:** Aktív fejlesztés
