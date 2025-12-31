# Support/Resistance Fix - FINAL SUMMARY

**Date:** 2024-12-30
**Issue:** S/R levels too close to current price (0.3%-0.5% distance)
**Solution:** Better parameters based on blue chip swing trading best practices

---

## Design Decisions

### ✅ **Decision #1: Show ALL S/R levels with distance info**

**Why:**
- Don't hide information from user
- User decides if 0.3% S/R is tradeable
- 2.5% is a guideline, not a filter rule
- Market structure is what it is

**Implementation:**
```python
# Return format with distance info:
{
    'support': [
        {'price': 2935, 'distance_pct': 0.03},  # Very close
        {'price': 2850, 'distance_pct': 2.93}   # Reasonable
    ]
}
```

---

### ✅ **Decision #2: Small stop-loss buffer (0.5× ATR)**

**Original question:** "Why put stop-loss BELOW support?"

**Answer:**
- **Support = Buyers step in at this level**
- **Stop AT support** → spike-out risk (temporary dip triggers stop)
- **Stop BELOW support** → only triggers if support TRULY breaks
- **0.5× ATR buffer** (not 1.5×) → tight but safe

**Example:**
```
Support: 2935 HUF
ATR: 12 HUF
Stop-Loss: 2935 - (0.5 × 12) = 2929 HUF

If price dips to 2936 → stop NOT triggered (bounce expected)
If price breaks to 2928 → stop triggered (support broken)
```

---

### ✅ **Decision #3: Two different S/R calculations**

**Codebase has TWO S/R systems:**

#### 1. **`technical_analyzer.py` → detect_support_resistance()**
**Purpose:** Swing trading S/R (long-term significant levels)
- **Lookback:** 180 days (6 months)
- **Method:** Pivot detection, order=7
- **Clustering:** 4% tolerance
- **Returns:** Dict with price + distance_pct
- **Used for:** TechnicalAnalyzer.analyze() result

#### 2. **`signal_generator.py` → calculate_technical_score()**
**Purpose:** Intraday S/R (short-term levels)
- **Lookback:** Last 100 candles of 15m data (~25 hours)
- **Method:** Simple min/max
- **Returns:** nearest_support, nearest_resistance (floats)
- **Used for:** Quick intraday reference

**Both are valid** - different use cases!

---

## Code Changes

### `technical_analyzer.py`

**Function:** `detect_support_resistance()`

**Changes:**
1. ✅ `lookback_days`: 90 → **180**
2. ✅ `order`: 2 → **7**
3. ✅ `proximity_pct`: 0.02 → **0.04**
4. ✅ Return format: Simple list → **Dict with distance info**
5. ✅ Sort by proximity (nearest first)

```python
return {
    'support': [
        {'price': s, 'distance_pct': (price - s) / price * 100}
        for s in supports if s < price
    ],
    'resistance': [
        {'price': r, 'distance_pct': (r - price) / price * 100}
        for r in resistances if r > price
    ]
}
```

---

### `signal_generator.py`

**Function:** `_calculate_levels()`

**Changes:**
1. ✅ Handle new S/R dict format
2. ✅ Stop-loss buffer: **1.5× → 0.5× ATR**
3. ✅ Take-profit: Use resistance directly (no buffer)

```python
# Parse new format
support_levels = risk_data.get("support", [])
nearest_support = support_levels[0]['price'] if support_levels else None

if "BUY" in decision:
    if nearest_support:
        stop_loss = nearest_support - (atr * 0.5)  # Small buffer
    ...
```

**Function:** `calculate_technical_score()`

**Added comment:**
```python
# NOTE: This is INTRADAY S/R (15m min/max)
# Different from detect_support_resistance() (180d swing S/R)
```

---

## Expected Behavior After Fix

### Current Issue:
```
OTP.BD: Support 2935 (-0.03%), Resistance 2945 (+0.31%)
→ order=2 on 90 days → too many micro-pivots
```

### After Fix:
```
OTP.BD: 
  Support levels:
    - 2850 HUF (-2.93%) ← Nearest meaningful level
    - 2780 HUF (-5.31%)
  
  Resistance levels:
    - 3020 HUF (+2.86%) ← Nearest meaningful level
    - 3150 HUF (+7.29%)
  
  → order=7 on 180 days → only significant swings
```

**OR** (if market is in tight consolidation):
```
GOOGL:
  Support levels: [] (no significant pivots in 6 months)
  Resistance levels: [] (no significant pivots in 6 months)
  
  → Fallback to ATR-based stop/target
```

---

## Why This Approach is Correct

### ✅ Respects Market Reality
- Shows actual S/R structure
- Doesn't force arbitrary distances
- Preserves trading information

### ✅ User-Informed Decisions
- User sees: "S/R at 0.3% distance"
- User decides: "Too tight, skip trade" OR "Tight range breakout play"
- System doesn't hide this choice

### ✅ Proper Stop-Loss Logic
- 0.5× ATR buffer (not 1.5×)
- Protects from spikes
- Confirms true support break

### ✅ Variable R:R Ratios
- Good setups: 1:2 or 1:3
- Tight setups: 1:0.5 (user sees this and skips)
- Real market structure, not forced ratios

---

## Testing Plan

1. Run signal generation with new parameters
2. Check S/R distances for all tickers:
   - **If <1%:** Expect tight consolidation
   - **If 2-5%:** Normal swing trading ranges
   - **If >5%:** Wide ranges or breakout scenarios
3. Verify stop-loss uses 0.5× ATR buffer
4. Confirm frontend shows distance warnings for close S/R

---

## UI Recommendation (Future)

Add visual indicators on signal cards:

```
Entry & Exit Levels:
  Entry:       2936 HUF
  Stop-Loss:   2929 HUF (-0.24%)
    ├─ Based on support: 2935 HUF (-0.03%) ⚠️ VERY CLOSE
    └─ Buffer: 0.5× ATR (6 HUF)
  
  Take-Profit: 2945 HUF (+0.31%)
    └─ Based on resistance: 2945 HUF (+0.31%) ⚠️ CLOSE
  
  ⚠️ WARNING: Tight S/R range - Low profit potential
  💡 Recommendation: Consider skipping or wait for breakout
```

---

**Status:** ✅ **COMPLETE**
**Philosophy:** Respect market structure, inform user, don't force parameters
