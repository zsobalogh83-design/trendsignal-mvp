# TrendSignal - Hiányzó Konfigurálható Paraméterek

**Dátum:** 2025-01-31  
**Cél:** Azonosítani, mely kalkulációs paraméterek NEM vezérelhetők a Configuration oldalról

---

## 📊 Jelenleg Vezérelhető Paraméterek (✅ MEGVAN)

### 1. Signal Component Weights (Signals Tab)
```typescript
componentWeights = {
  sentiment: 70,    // Sentiment súly (%)
  technical: 20,    // Technical súly (%)
  risk: 10          // Risk súly (%)
}
```
**Backend mapping:**
- `SENTIMENT_WEIGHT` (0.70)
- `TECHNICAL_WEIGHT` (0.20)
- `RISK_WEIGHT` (0.10)

**API:** `PUT /api/v1/config/signal`

---

### 2. Sentiment Decay Weights (Sentiment Tab)
```typescript
sentimentWeights = {
  fresh_0_2h: 100,         // 0-2 óra (%)
  strong_2_6h: 85,         // 2-6 óra (%)
  intraday_6_12h: 60,      // 6-12 óra (%)
  overnight_12_24h: 35     // 12-24 óra (%)
}
```
**Backend mapping:**
- `DECAY_WEIGHTS['0-2h']` (1.00)
- `DECAY_WEIGHTS['2-6h']` (0.85)
- `DECAY_WEIGHTS['6-12h']` (0.60)
- `DECAY_WEIGHTS['12-24h']` (0.35)

**API:** `PUT /api/v1/config/decay`

---

## ❌ HIÁNYZÓ Konfigurálható Paraméterek

### 3. Signal Decision Thresholds (❌ NEM VEZÉRELHETŐ)

**Jelenleg a Frontend-en:**
```typescript
// Configuration.tsx - SignalsTab
<div style={{ fontSize: '14px', color: '#cbd5e1', padding: '20px', textAlign: 'center' }}>
  Threshold configuration coming in Phase 2
</div>
```

**Backend paraméterek (config.py):**
```python
# Strong signals
STRONG_BUY_SCORE = 65              # Combined score threshold
STRONG_BUY_CONFIDENCE = 0.75       # Confidence threshold

STRONG_SELL_SCORE = -65
STRONG_SELL_CONFIDENCE = 0.75

# Moderate signals
MODERATE_BUY_SCORE = 50
MODERATE_BUY_CONFIDENCE = 0.65

MODERATE_SELL_SCORE = -50
MODERATE_SELL_CONFIDENCE = 0.65
```

**Javasolt UI (Configuration.tsx - Signals Tab):**
```typescript
// BUY Thresholds
<div className="threshold-group">
  <h3>🟢 BUY Signal Thresholds</h3>
  
  <div className="threshold-item">
    <label>Strong Buy Score: {strongBuyScore}</label>
    <input type="range" min="50" max="80" value={strongBuyScore} 
           onChange={(e) => setStrongBuyScore(parseInt(e.target.value))} />
    <span className="help-text">Combined score must be ≥ this value</span>
  </div>
  
  <div className="threshold-item">
    <label>Strong Buy Confidence: {(strongBuyConfidence * 100).toFixed(0)}%</label>
    <input type="range" min="60" max="90" value={strongBuyConfidence * 100} 
           onChange={(e) => setStrongBuyConfidence(parseInt(e.target.value) / 100)} />
    <span className="help-text">Overall confidence must be ≥ this value</span>
  </div>
  
  <div className="threshold-item">
    <label>Moderate Buy Score: {moderateBuyScore}</label>
    <input type="range" min="30" max="65" value={moderateBuyScore} 
           onChange={(e) => setModerateBuyScore(parseInt(e.target.value))} />
  </div>
  
  <div className="threshold-item">
    <label>Moderate Buy Confidence: {(moderateBuyConfidence * 100).toFixed(0)}%</label>
    <input type="range" min="50" max="75" value={moderateBuyConfidence * 100} 
           onChange={(e) => setModerateBuyConfidence(parseInt(e.target.value) / 100)} />
  </div>
</div>

// SELL Thresholds (hasonló struktúra)
```

**Szükséges Backend módosítás:**
```python
# config_api.py
@router.put("/config/thresholds")
async def update_thresholds(updates: Dict):
    """
    Update decision thresholds
    """
    config = get_config()
    
    if "STRONG_BUY_SCORE" in updates:
        config.strong_buy_score = updates["STRONG_BUY_SCORE"]
    if "STRONG_BUY_CONFIDENCE" in updates:
        config.strong_buy_confidence = updates["STRONG_BUY_CONFIDENCE"]
    # ... további thresholds
    
    save_config_to_file(config)
    return {"message": "Thresholds updated"}
```

---

### 4. Technical Indicator Parameters (❌ NEM VEZÉRELHETŐ)

**Jelenleg a Frontend-en:**
```typescript
// Configuration.tsx - TechnicalTab
<div style={{ fontSize: '14px', color: '#cbd5e1', padding: '40px', textAlign: 'center' }}>
  Technical parameter configuration coming in Phase 2
</div>
```

**Backend paraméterek (config.py):**
```python
# SMA periods
SMA_SHORT = 20
SMA_MEDIUM = 50
SMA_LONG = 200

# MACD parameters
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# RSI period
RSI_PERIOD = 14

# Bollinger Bands
BB_PERIOD = 20
BB_STD = 2  # Standard deviation multiplier

# ATR period
ATR_PERIOD = 14
```

**Javasolt UI (Configuration.tsx - Technical Tab):**
```typescript
// Moving Averages
<div className="indicator-group">
  <h3>📈 Moving Averages (SMA)</h3>
  
  <div className="indicator-item">
    <label>Short-term SMA: {smaShort} days</label>
    <input type="range" min="5" max="30" value={smaShort} 
           onChange={(e) => setSmaShort(parseInt(e.target.value))} />
    <span className="help-text">Default: 20 days</span>
  </div>
  
  <div className="indicator-item">
    <label>Medium-term SMA: {smaMedium} days</label>
    <input type="range" min="30" max="100" value={smaMedium} 
           onChange={(e) => setSmaMedium(parseInt(e.target.value))} />
    <span className="help-text">Default: 50 days</span>
  </div>
  
  <div className="indicator-item">
    <label>Long-term SMA: {smaLong} days</label>
    <input type="range" min="100" max="300" value={smaLong} 
           onChange={(e) => setSmaLong(parseInt(e.target.value))} />
    <span className="help-text">Default: 200 days (Golden Cross reference)</span>
  </div>
</div>

// MACD Parameters
<div className="indicator-group">
  <h3>📊 MACD Parameters</h3>
  
  <div className="indicator-item">
    <label>Fast EMA: {macdFast} days</label>
    <input type="range" min="8" max="20" value={macdFast} 
           onChange={(e) => setMacdFast(parseInt(e.target.value))} />
    <span className="help-text">Default: 12 days</span>
  </div>
  
  <div className="indicator-item">
    <label>Slow EMA: {macdSlow} days</label>
    <input type="range" min="20" max="40" value={macdSlow} 
           onChange={(e) => setMacdSlow(parseInt(e.target.value))} />
    <span className="help-text">Default: 26 days</span>
  </div>
  
  <div className="indicator-item">
    <label>Signal Line: {macdSignal} days</label>
    <input type="range" min="5" max="15" value={macdSignal} 
           onChange={(e) => setMacdSignal(parseInt(e.target.value))} />
    <span className="help-text">Default: 9 days</span>
  </div>
</div>

// RSI
<div className="indicator-group">
  <h3>⚡ RSI (Relative Strength Index)</h3>
  
  <div className="indicator-item">
    <label>RSI Period: {rsiPeriod} days</label>
    <input type="range" min="7" max="21" value={rsiPeriod} 
           onChange={(e) => setRsiPeriod(parseInt(e.target.value))} />
    <span className="help-text">Default: 14 days (Wilder's standard)</span>
  </div>
</div>

// Bollinger Bands
<div className="indicator-group">
  <h3>📉 Bollinger Bands</h3>
  
  <div className="indicator-item">
    <label>Period: {bbPeriod} days</label>
    <input type="range" min="10" max="30" value={bbPeriod} 
           onChange={(e) => setBbPeriod(parseInt(e.target.value))} />
    <span className="help-text">Default: 20 days</span>
  </div>
  
  <div className="indicator-item">
    <label>Standard Deviation: {bbStd}σ</label>
    <input type="range" min="1.5" max="3.0" step="0.1" value={bbStd} 
           onChange={(e) => setBbStd(parseFloat(e.target.value))} />
    <span className="help-text">Default: 2σ (95% confidence)</span>
  </div>
</div>

// ATR
<div className="indicator-group">
  <h3>📏 ATR (Average True Range)</h3>
  
  <div className="indicator-item">
    <label>ATR Period: {atrPeriod} days</label>
    <input type="range" min="7" max="21" value={atrPeriod} 
           onChange={(e) => setAtrPeriod(parseInt(e.target.value))} />
    <span className="help-text">Default: 14 days (Wilder's standard)</span>
  </div>
</div>
```

**Szükséges Backend módosítás:**
```python
# config_api.py
@router.put("/config/technical")
async def update_technical_params(updates: Dict):
    """
    Update technical indicator parameters
    """
    config = get_config()
    
    # SMA periods
    if "SMA_SHORT" in updates:
        config.sma_periods['short'] = updates["SMA_SHORT"]
    if "SMA_MEDIUM" in updates:
        config.sma_periods['medium'] = updates["SMA_MEDIUM"]
    if "SMA_LONG" in updates:
        config.sma_periods['long'] = updates["SMA_LONG"]
    
    # MACD params
    if "MACD_FAST" in updates:
        config.macd_params['fast'] = updates["MACD_FAST"]
    if "MACD_SLOW" in updates:
        config.macd_params['slow'] = updates["MACD_SLOW"]
    if "MACD_SIGNAL" in updates:
        config.macd_params['signal'] = updates["MACD_SIGNAL"]
    
    # RSI
    if "RSI_PERIOD" in updates:
        config.rsi_period = updates["RSI_PERIOD"]
    
    # Bollinger
    if "BB_PERIOD" in updates:
        config.bb_period = updates["BB_PERIOD"]
    if "BB_STD" in updates:
        config.bb_std = updates["BB_STD"]
    
    # ATR
    if "ATR_PERIOD" in updates:
        config.atr_period = updates["ATR_PERIOD"]
    
    save_config_to_file(config)
    return {"message": "Technical parameters updated"}
```

---

### 5. Technical Component Weights (❌ NEM VEZÉRELHETŐ)

**Jelenleg:** Hardcoded a `technical_analyzer.py`-ban

```python
# technical_analyzer.py - calculate_technical_score()
technical_score = (
    trend_score * 0.40 +        # 40% - HARDCODED
    momentum_score * 0.30 +     # 30% - HARDCODED
    volatility_score * 0.20 +   # 20% - HARDCODED
    volume_score * 0.10         # 10% - HARDCODED
)
```

**Javasolt UI (Configuration.tsx - Technical Tab):**
```typescript
<div className="sub-weights-group">
  <h3>⚖️ Technical Component Weights</h3>
  <p className="help-text">How each technical component contributes to the overall technical score</p>
  
  <div className="weight-item">
    <label>Trend (SMA, MACD): {technicalWeights.trend}%</label>
    <input type="range" min="0" max="100" value={technicalWeights.trend} 
           onChange={(e) => setTechnicalWeights({...technicalWeights, trend: parseInt(e.target.value)})} />
  </div>
  
  <div className="weight-item">
    <label>Momentum (RSI, Stochastic): {technicalWeights.momentum}%</label>
    <input type="range" min="0" max="100" value={technicalWeights.momentum} 
           onChange={(e) => setTechnicalWeights({...technicalWeights, momentum: parseInt(e.target.value)})} />
  </div>
  
  <div className="weight-item">
    <label>Volatility (Bollinger, ATR): {technicalWeights.volatility}%</label>
    <input type="range" min="0" max="100" value={technicalWeights.volatility} 
           onChange={(e) => setTechnicalWeights({...technicalWeights, volatility: parseInt(e.target.value)})} />
  </div>
  
  <div className="weight-item">
    <label>Volume Confirmation: {technicalWeights.volume}%</label>
    <input type="range" min="0" max="100" value={technicalWeights.volume} 
           onChange={(e) => setTechnicalWeights({...technicalWeights, volume: parseInt(e.target.value)})} />
  </div>
  
  <div className="total-indicator">
    Total: {technicalWeights.trend + technicalWeights.momentum + 
            technicalWeights.volatility + technicalWeights.volume}%
    {technicalWeights.trend + technicalWeights.momentum + 
     technicalWeights.volatility + technicalWeights.volume !== 100 && ' ⚠️ Must equal 100%'}
  </div>
</div>
```

**Szükséges Backend módosítás:**
```python
# config.py
TECHNICAL_TREND_WEIGHT = 0.40
TECHNICAL_MOMENTUM_WEIGHT = 0.30
TECHNICAL_VOLATILITY_WEIGHT = 0.20
TECHNICAL_VOLUME_WEIGHT = 0.10

@dataclass
class TrendSignalConfig:
    # ... existing fields
    
    # Technical component weights
    technical_trend_weight: float = TECHNICAL_TREND_WEIGHT
    technical_momentum_weight: float = TECHNICAL_MOMENTUM_WEIGHT
    technical_volatility_weight: float = TECHNICAL_VOLATILITY_WEIGHT
    technical_volume_weight: float = TECHNICAL_VOLUME_WEIGHT

# technical_analyzer.py
def calculate_technical_score(...):
    config = get_config()
    config.reload()
    
    technical_score = (
        trend_score * config.technical_trend_weight +
        momentum_score * config.technical_momentum_weight +
        volatility_score * config.technical_volatility_weight +
        volume_score * config.technical_volume_weight
    )
```

---

### 6. Risk Component Weights (❌ NEM VEZÉRELHETŐ)

**Jelenleg:** Hardcoded a `signal_generator.py`-ban

```python
# signal_generator.py - calculate_risk_score()
risk_score = (
    volatility_risk * 0.40 +      # 40% - HARDCODED
    proximity_risk * 0.35 +        # 35% - HARDCODED
    trend_strength_risk * 0.25     # 25% - HARDCODED
)
```

**Javasolt UI (Configuration.tsx - új "Risk" Tab):**
```typescript
<div className="risk-tab">
  <h2>🛡️ Risk Management Configuration</h2>
  
  <div className="risk-weights-group">
    <h3>⚖️ Risk Component Weights</h3>
    <p className="help-text">How each risk factor contributes to the overall risk score</p>
    
    <div className="weight-item">
      <label>Volatility (ATR %): {riskWeights.volatility}%</label>
      <input type="range" min="0" max="100" value={riskWeights.volatility} 
             onChange={(e) => setRiskWeights({...riskWeights, volatility: parseInt(e.target.value)})} />
      <span className="help-text">Measures price volatility via ATR</span>
    </div>
    
    <div className="weight-item">
      <label>Proximity (S/R Distance): {riskWeights.proximity}%</label>
      <input type="range" min="0" max="100" value={riskWeights.proximity} 
             onChange={(e) => setRiskWeights({...riskWeights, proximity: parseInt(e.target.value)})} />
      <span className="help-text">Distance to support/resistance levels</span>
    </div>
    
    <div className="weight-item">
      <label>Trend Strength (ADX): {riskWeights.trendStrength}%</label>
      <input type="range" min="0" max="100" value={riskWeights.trendStrength} 
             onChange={(e) => setRiskWeights({...riskWeights, trendStrength: parseInt(e.target.value)})} />
      <span className="help-text">Trend reliability via ADX indicator</span>
    </div>
    
    <div className="total-indicator">
      Total: {riskWeights.volatility + riskWeights.proximity + riskWeights.trendStrength}%
      {riskWeights.volatility + riskWeights.proximity + riskWeights.trendStrength !== 100 && 
       ' ⚠️ Must equal 100%'}
    </div>
  </div>
</div>
```

**Szükséges Backend módosítás:**
```python
# config.py
RISK_VOLATILITY_WEIGHT = 0.40
RISK_PROXIMITY_WEIGHT = 0.35
RISK_TREND_STRENGTH_WEIGHT = 0.25

@dataclass
class TrendSignalConfig:
    # ... existing fields
    
    # Risk component weights
    risk_volatility_weight: float = RISK_VOLATILITY_WEIGHT
    risk_proximity_weight: float = RISK_PROXIMITY_WEIGHT
    risk_trend_strength_weight: float = RISK_TREND_STRENGTH_WEIGHT

# signal_generator.py
def calculate_risk_score(...):
    config = get_config()
    config.reload()
    
    risk_score = (
        volatility_risk * config.risk_volatility_weight +
        proximity_risk * config.risk_proximity_weight +
        trend_strength_risk * config.risk_trend_strength_weight
    )
```

---

### 7. Stop Loss / Take Profit Multipliers (❌ NEM VEZÉRELHETŐ)

**Jelenleg:** Hardcoded

```python
# signal_generator.py - _calculate_levels()

# Stop Loss
sr_stop = support - (0.5 * atr)      # 0.5x ATR - HARDCODED
atr_stop = entry - (2 * atr)         # 2x ATR - HARDCODED

# Take Profit
atr_target = entry + (3 * atr)       # 3x ATR - HARDCODED
```

**Javasolt UI (Configuration.tsx - Risk Tab):**
```typescript
<div className="stop-loss-config">
  <h3>🛑 Stop Loss Configuration</h3>
  
  <div className="multiplier-item">
    <label>S/R Buffer (ATR multiplier): {slSrBuffer}×</label>
    <input type="range" min="0" max="1.5" step="0.1" value={slSrBuffer} 
           onChange={(e) => setSlSrBuffer(parseFloat(e.target.value))} />
    <span className="help-text">Default: 0.5× (support - 0.5×ATR)</span>
  </div>
  
  <div className="multiplier-item">
    <label>ATR-based Stop (ATR multiplier): {slAtrMult}×</label>
    <input type="range" min="1" max="4" step="0.5" value={slAtrMult} 
           onChange={(e) => setSlAtrMult(parseFloat(e.target.value))} />
    <span className="help-text">Default: 2× (entry - 2×ATR)</span>
  </div>
</div>

<div className="take-profit-config">
  <h3>🎯 Take Profit Configuration</h3>
  
  <div className="multiplier-item">
    <label>ATR-based Target (ATR multiplier): {tpAtrMult}×</label>
    <input type="range" min="2" max="5" step="0.5" value={tpAtrMult} 
           onChange={(e) => setTpAtrMult(parseFloat(e.target.value))} />
    <span className="help-text">Default: 3× (entry + 3×ATR)</span>
  </div>
  
  <div className="info-box">
    <p>💡 Current R:R target: 1:{(tpAtrMult / slAtrMult).toFixed(1)}</p>
    <p className="help-text">
      With SL={slAtrMult}× and TP={tpAtrMult}×, 
      your theoretical R:R ratio is 1:{(tpAtrMult / slAtrMult).toFixed(1)}
    </p>
  </div>
</div>
```

**Szükséges Backend módosítás:**
```python
# config.py
STOP_LOSS_SR_BUFFER = 0.5   # S/R buffer multiplier
STOP_LOSS_ATR_MULT = 2.0    # ATR-based stop multiplier
TAKE_PROFIT_ATR_MULT = 3.0  # ATR-based target multiplier

@dataclass
class TrendSignalConfig:
    # ... existing fields
    
    # Stop Loss / Take Profit
    stop_loss_sr_buffer: float = STOP_LOSS_SR_BUFFER
    stop_loss_atr_mult: float = STOP_LOSS_ATR_MULT
    take_profit_atr_mult: float = TAKE_PROFIT_ATR_MULT

# signal_generator.py
def _calculate_levels(...):
    config = get_config()
    config.reload()
    
    # Stop Loss
    sr_stop = support - (config.stop_loss_sr_buffer * atr)
    atr_stop = entry - (config.stop_loss_atr_mult * atr)
    
    # Take Profit
    atr_target = entry + (config.take_profit_atr_mult * atr)
```

---

### 8. Support/Resistance DBSCAN Parameters (❌ NEM VEZÉRELHETŐ)

**Jelenleg:** Hardcoded

```python
# technical_analyzer.py - detect_support_resistance()

eps = 0.04 * current_price  # 4% - HARDCODED
min_samples = 3              # HARDCODED
order = 7                    # 7-day window - HARDCODED
lookback = 180               # 180 days - HARDCODED
```

**Javasolt UI (Configuration.tsx - Technical Tab):**
```typescript
<div className="sr-config">
  <h3>📍 Support/Resistance Detection (DBSCAN)</h3>
  
  <div className="dbscan-param">
    <label>Clustering Distance (eps): {dbscanEps}%</label>
    <input type="range" min="1" max="8" step="0.5" value={dbscanEps} 
           onChange={(e) => setDbscanEps(parseFloat(e.target.value))} />
    <span className="help-text">Default: 4% (pivot points within 4% clustered together)</span>
  </div>
  
  <div className="dbscan-param">
    <label>Min Cluster Size: {dbscanMinSamples}</label>
    <input type="range" min="2" max="5" value={dbscanMinSamples} 
           onChange={(e) => setDbscanMinSamples(parseInt(e.target.value))} />
    <span className="help-text">Default: 3 (minimum 3 pivots to form S/R level)</span>
  </div>
  
  <div className="dbscan-param">
    <label>Pivot Order (days): {pivotOrder}</label>
    <input type="range" min="3" max="14" value={pivotOrder} 
           onChange={(e) => setPivotOrder(parseInt(e.target.value))} />
    <span className="help-text">Default: 7 (7-day window for local min/max detection)</span>
  </div>
  
  <div className="dbscan-param">
    <label>Lookback Period (days): {srLookback}</label>
    <input type="range" min="90" max="365" step="30" value={srLookback} 
           onChange={(e) => setSrLookback(parseInt(e.target.value))} />
    <span className="help-text">Default: 180 days (6 months historical data)</span>
  </div>
  
  <div className="info-box">
    <p>💡 Higher eps = Fewer, broader S/R levels</p>
    <p>💡 Higher min_samples = Stronger, more tested levels</p>
    <p>💡 Higher order = Smoother, more significant pivots</p>
  </div>
</div>
```

**Szükséges Backend módosítás:**
```python
# config.py
DBSCAN_EPS_PCT = 0.04      # 4%
DBSCAN_MIN_SAMPLES = 3
PIVOT_ORDER = 7
SR_LOOKBACK_DAYS = 180

@dataclass
class TrendSignalConfig:
    # ... existing fields
    
    # S/R Detection
    dbscan_eps_pct: float = DBSCAN_EPS_PCT
    dbscan_min_samples: int = DBSCAN_MIN_SAMPLES
    pivot_order: int = PIVOT_ORDER
    sr_lookback_days: int = SR_LOOKBACK_DAYS

# technical_analyzer.py
def detect_support_resistance(...):
    config = get_config()
    config.reload()
    
    eps = config.dbscan_eps_pct * current_price
    min_samples = config.dbscan_min_samples
    order = config.pivot_order
    lookback = config.sr_lookback_days
```

---

### 9. Confidence Calculation Weights (❌ NEM VEZÉRELHETŐ)

**Jelenleg:** Hardcoded

```python
# signal_generator.py - calculate_overall_confidence()

overall_conf = (
    sent_conf * 0.40 +         # 40% - HARDCODED
    tech_conf * 0.30 +         # 30% - HARDCODED
    volume_factor * 0.20 +     # 20% - HARDCODED
    rr_bonus * 0.10            # 10% - HARDCODED
)
```

**Javasolt UI (Configuration.tsx - Signals Tab):**
```typescript
<div className="confidence-config">
  <h3>🎯 Overall Confidence Calculation</h3>
  <p className="help-text">How different factors contribute to signal confidence</p>
  
  <div className="weight-item">
    <label>Sentiment Confidence: {confidenceWeights.sentiment}%</label>
    <input type="range" min="0" max="100" value={confidenceWeights.sentiment} 
           onChange={(e) => setConfidenceWeights({...confidenceWeights, sentiment: parseInt(e.target.value)})} />
    <span className="help-text">FinBERT model certainty</span>
  </div>
  
  <div className="weight-item">
    <label>Technical Confidence: {confidenceWeights.technical}%</label>
    <input type="range" min="0" max="100" value={confidenceWeights.technical} 
           onChange={(e) => setConfidenceWeights({...confidenceWeights, technical: parseInt(e.target.value)})} />
    <span className="help-text">Indicator alignment</span>
  </div>
  
  <div className="weight-item">
    <label>News Volume Factor: {confidenceWeights.volume}%</label>
    <input type="range" min="0" max="100" value={confidenceWeights.volume} 
           onChange={(e) => setConfidenceWeights({...confidenceWeights, volume: parseInt(e.target.value)})} />
    <span className="help-text">Number of news articles (10+ = 100%)</span>
  </div>
  
  <div className="weight-item">
    <label>Risk:Reward Bonus: {confidenceWeights.rrBonus}%</label>
    <input type="range" min="0" max="100" value={confidenceWeights.rrBonus} 
           onChange={(e) => setConfidenceWeights({...confidenceWeights, rrBonus: parseInt(e.target.value)})} />
    <span className="help-text">Setup quality bonus (R:R ≥ 2:1)</span>
  </div>
  
  <div className="total-indicator">
    Total: {confidenceWeights.sentiment + confidenceWeights.technical + 
            confidenceWeights.volume + confidenceWeights.rrBonus}%
    {confidenceWeights.sentiment + confidenceWeights.technical + 
     confidenceWeights.volume + confidenceWeights.rrBonus !== 100 && 
     ' ⚠️ Must equal 100%'}
  </div>
</div>
```

**Szükséges Backend módosítás:**
```python
# config.py
CONFIDENCE_SENTIMENT_WEIGHT = 0.40
CONFIDENCE_TECHNICAL_WEIGHT = 0.30
CONFIDENCE_VOLUME_WEIGHT = 0.20
CONFIDENCE_RR_WEIGHT = 0.10

@dataclass
class TrendSignalConfig:
    # ... existing fields
    
    # Confidence weights
    confidence_sentiment_weight: float = CONFIDENCE_SENTIMENT_WEIGHT
    confidence_technical_weight: float = CONFIDENCE_TECHNICAL_WEIGHT
    confidence_volume_weight: float = CONFIDENCE_VOLUME_WEIGHT
    confidence_rr_weight: float = CONFIDENCE_RR_WEIGHT

# signal_generator.py
def calculate_overall_confidence(...):
    config = get_config()
    config.reload()
    
    overall_conf = (
        sent_conf * config.confidence_sentiment_weight +
        tech_conf * config.confidence_technical_weight +
        volume_factor * config.confidence_volume_weight +
        rr_bonus * config.confidence_rr_weight
    )
```

---

## 📊 Összefoglaló Táblázat

| # | Paraméter Kategória | Jelenleg Vezérelhető? | Prioritás | Implementáció Nehézsége |
|---|---------------------|------------------------|-----------|-------------------------|
| 1 | Signal Component Weights | ✅ IGEN | - | - |
| 2 | Sentiment Decay Weights | ✅ IGEN | - | - |
| 3 | Signal Decision Thresholds | ❌ NEM | 🔥 MAGAS | KÖNNYŰ |
| 4 | Technical Indicator Parameters | ❌ NEM | 🔥 MAGAS | KÖZEPES |
| 5 | Technical Component Weights | ❌ NEM | 🔥 MAGAS | KÖNNYŰ |
| 6 | Risk Component Weights | ❌ NEM | 🔶 KÖZEPES | KÖNNYŰ |
| 7 | Stop Loss / Take Profit Mult | ❌ NEM | 🔶 KÖZEPES | KÖNNYŰ |
| 8 | S/R DBSCAN Parameters | ❌ NEM | 🔶 KÖZEPES | KÖZEPES |
| 9 | Confidence Calculation Weights | ❌ NEM | 🔷 ALACSONY | KÖNNYŰ |

---

## 🎯 Javasolt Implementációs Sorrend

### Phase 2A (Gyors Win-ek - 1-2 nap):
1. ✅ **Signal Decision Thresholds** - Leggyakrabban módosított, egyszerű UI
2. ✅ **Technical Component Weights** - Fontos fine-tuning lehetőség
3. ✅ **Risk Component Weights** - Risk management optimalizálás

### Phase 2B (Haladó Paraméterek - 2-3 nap):
4. ✅ **Technical Indicator Parameters** - Több slider, validációval
5. ✅ **Stop Loss / Take Profit Multipliers** - Trade management
6. ✅ **S/R DBSCAN Parameters** - Haladó felhasználóknak

### Phase 2C (Nice-to-Have - 1 nap):
7. ✅ **Confidence Calculation Weights** - Fine-tuning

---

## 🛠️ Technikai Követelmények

### Backend Módosítások:
1. **config.py** - Új paraméterek hozzáadása a `TrendSignalConfig` dataclass-hoz
2. **config_api.py** - Új PUT endpointok (pl. `/config/thresholds`, `/config/technical`, `/config/risk`)
3. **signal_generator.py** - Hardcoded értékek lecserélése `config.xxx` referenciákra
4. **technical_analyzer.py** - Hardcoded értékek lecserélése
5. **config.json** - Új mezők perzisztálása

### Frontend Módosítások:
1. **Configuration.tsx** - Új UI szekcióok és sliderek
2. **useApi.ts** - Új API hook-ok (pl. `useUpdateThresholds`, `useUpdateTechnicalParams`)
3. **State management** - Új React state változók minden új paraméterhez

### Validáció:
- Súlyok összege = 100% (ahol releváns)
- Min/max értékek ellenőrzése
- Reasonable defaults
- Backend-Frontend szinkronizáció

---

**Készítette:** Claude + Zsolt  
**Dátum:** 2025-01-31  
**Verzió:** 1.0
