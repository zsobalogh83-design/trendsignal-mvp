# Alignment Bonus - SZIMMETRIKUS Implementáció (v2)

## ⚠️ Kritikus Javítás: SELL Alignment Támogatás

Az eredeti implementáció **CSAK BUY irányba** adott bonus-t!  
**Most már SZIMMETRIKUS**: SELL signalok is kapnak (negatív) bonus-t.

---

## Hogyan Működik Most?

### 1. Abszolút Értékkel Ellenőrzi az Erősséget

```python
abs_sent = abs(sentiment_score)  # |-45| = 45
abs_tech = abs(technical_score)  # |-65| = 65
abs_risk = abs(risk_score)       # |-45| = 45

# Ellenőrzi hogy ERŐS-e (abszolút értékben)
tr_strong = abs_tech > 60 and abs_risk > 40  # 65 > 60 AND 45 > 40 → TRUE
```

### 2. Eldönti az Irányt (BUY/SELL/Mixed)

```python
if sentiment > 0 AND technical > 0 AND risk > 0:
    return +bonus_magnitude  # BUY alignment
elif sentiment < 0 AND technical < 0 AND risk < 0:
    return -bonus_magnitude  # SELL alignment
else:
    return 0  # Mixed signals (nincs alignment)
```

---

## Példák

### Példa 1: BUY Alignment (változatlan)

```
Komponensek:
  Sentiment: +45 (pozitív)
  Technical: +65 (pozitív)
  Risk:      +45 (pozitív)

Erősség ellenőrzés:
  TR: |65| > 60 ÉS |45| > 40 → TRUE
  ST: |45| > 40 ÉS |65| > 40 → TRUE
  SR: |45| > 40 ÉS |45| > 40 → TRUE
  → Mind a 3 pár erős!

Irány ellenőrzés:
  Mind > 0? IGEN → BUY alignment

Bonus: +8 (pozitív)

Base:  +52.0
Final: +60.0 (STRONG BUY)
```

### Példa 2: SELL Alignment (ÚJ!)

```
Komponensek:
  Sentiment: -45 (negatív hírek)
  Technical: -65 (bearish chart)
  Risk:      -45 (magas kockázat short-ra)

Erősség ellenőrzés:
  TR: |-65| > 60 ÉS |-45| > 40 → TRUE (65 > 60, 45 > 40)
  ST: |-45| > 40 ÉS |-65| > 40 → TRUE (45 > 40, 65 > 40)
  SR: |-45| > 40 ÉS |-45| > 40 → TRUE (45 > 40, 45 > 40)
  → Mind a 3 pár erős!

Irány ellenőrzés:
  Mind < 0? IGEN → SELL alignment

Bonus: -8 (NEGATÍV!)

Base:  -52.0
Final: -60.0 (STRONG SELL)
```

### Példa 3: Mixed Signals (nincs bonus)

```
Komponensek:
  Sentiment: +45 (pozitív hírek)
  Technical: -65 (bearish chart)
  Risk:      +45 (alacsony kockázat)

Erősség ellenőrzés:
  TR: |-65| > 60 ÉS |45| > 40 → TRUE
  ST: |45| > 40 ÉS |-65| > 40 → TRUE
  SR: |45| > 40 ÉS |45| > 40 → TRUE
  → Mind a 3 pár erős lenne...

Irány ellenőrzés:
  Mind > 0? NEM (technical < 0)
  Mind < 0? NEM (sentiment > 0, risk > 0)
  → VEGYES JELEK!

Bonus: 0 (nincs alignment!)

Base:  +12.0
Final: +12.0 (WEAK BUY, de ellentmondásos)
```

### Példa 4: Csak TR Alignment SELL-ben

```
Komponensek:
  Sentiment: -25 (gyengén negatív)
  Technical: -62 (bearish chart)
  Risk:      -45 (magas kockázat)

Erősség ellenőrzés:
  TR: |-62| > 60 ÉS |-45| > 40 → TRUE (62 > 60, 45 > 40)
  ST: |-25| > 40? NEM (25 < 40)
  SR: |-25| > 40? NEM
  → Csak TR erős

Irány ellenőrzés:
  Mind < 0? IGEN → SELL alignment

Bonus: -5 (TR bonus SELL irányban)

Base:  -35.0
Final: -40.0 (MODERATE SELL → STRONG SELL!)
```

---

## Console Log Példák

### BUY Alignment:
```
[MOL.BD] BASE SCORE: 40.79
[MOL.BD] ALIGNMENT BONUS: +5 (BUY components aligned)
[MOL.BD] FINAL COMBINED SCORE: 45.79
```

### SELL Alignment:
```
[NVDA] BASE SCORE: -42.30
[NVDA] ALIGNMENT BONUS: -8 (SELL components aligned)
[NVDA] FINAL COMBINED SCORE: -50.30
```

### Nincs Alignment:
```
[AAPL] BASE SCORE: 18.50
[AAPL] FINAL COMBINED SCORE: 18.50
```
(Nincs ALIGNMENT BONUS sor)

---

## Kritikus Ellenőrzés: Mixed Signals

**FONTOS:** Csak akkor kap bonus-t ha **MINDEN komponens ugyanabba az irányba mutat!**

### Miért Fontos Ez?

```
Rossz példa (ha nem lenne irány ellenőrzés):
  Sentiment: +50 (jó hírek)
  Technical: -70 (rossz chart)
  Risk:      +48 (alacsony kockázat)

Ha CSAK az erősségre néznénk:
  TR: |70| > 60 ÉS |48| > 40 → TRUE
  ST: |50| > 40 ÉS |70| > 40 → TRUE
  SR: |50| > 40 ÉS |48| > 40 → TRUE
  → Mind a 3 pár "erős"? Bonus +8?

DE: Technical ELLENTMOND a többinek!
  → Ez NEM alignment!
  → Helyes bonus: 0
```

Az új logika ezt helyesen kezeli:
```python
if sentiment > 0 and technical > 0 and risk > 0:
    # Csak ha MINDHÁROM pozitív
elif sentiment < 0 and technical < 0 and risk < 0:
    # Csak ha MINDHÁROM negatív
else:
    return 0  # Vegyes → nincs bonus
```

---

## Threshold-ok (változatlan)

| Pár | Threshold | Bonus Magnitude |
|-----|-----------|-----------------|
| TR | \|tech\| > 60 AND \|risk\| > 40 | 5 |
| ST | \|sent\| > 40 AND \|tech\| > 40 | 5 |
| SR | \|sent\| > 40 AND \|risk\| > 40 | 3 |
| ALL | Mind a 3 pár erős | 8 (cap) |

**Alkalmazás:**
- BUY (mind >0): +magnitude
- SELL (mind <0): -magnitude
- Mixed: 0

---

## Tesztelési Szcenáriók

### Teszt 1: Perfect SELL Signal

```python
test_sell = generator.generate_signal(
    sentiment_data={"weighted_avg": -0.45, "confidence": 0.8},  # -45
    technical_data={"score": -65, "confidence": 0.9},           # -65
    risk_data={"score": -45},                                    # -45
)
```

**Elvárt:**
```
[TEST] BASE SCORE: -52.0
[TEST] ALIGNMENT BONUS: -8 (SELL components aligned)
[TEST] FINAL COMBINED SCORE: -60.0
Decision: STRONG SELL
```

### Teszt 2: Mixed Signal (no bonus)

```python
test_mixed = generator.generate_signal(
    sentiment_data={"weighted_avg": 0.45},   # +45
    technical_data={"score": -65},           # -65 (ellentmond!)
    risk_data={"score": 45},                 # +45
)
```

**Elvárt:**
```
[TEST] BASE SCORE: 12.0
[TEST] FINAL COMBINED SCORE: 12.0
(Nincs ALIGNMENT BONUS sor)
```

### Teszt 3: Weak Components (no bonus)

```python
test_weak = generator.generate_signal(
    sentiment_data={"weighted_avg": -0.35},  # -35 (<40)
    technical_data={"score": -55},           # -55 (<60)
    risk_data={"score": -35},                # -35 (<40)
)
```

**Elvárt:**
```
[TEST] BASE SCORE: -38.5
[TEST] FINAL COMBINED SCORE: -38.5
(Nincs ALIGNMENT BONUS sor - egyik pár sem elég erős)
```

---

## JSON Output Példák

### SELL Signal Reasoning:

```json
{
  "combined_score": -50.30,
  "decision": "SELL",
  "strength": "STRONG",
  "reasoning": {...},
  "alignment_bonus": -8
}
```

### BUY Signal Reasoning:

```json
{
  "combined_score": 45.79,
  "decision": "BUY",
  "strength": "STRONG",
  "reasoning": {...},
  "alignment_bonus": 5
}
```

### No Alignment:

```json
{
  "combined_score": 18.50,
  "decision": "BUY",
  "strength": "WEAK",
  "reasoning": {...},
  "alignment_bonus": null
}
```

---

## SQL Lekérdezések

### SELL Alignment Signalok:

```sql
SELECT 
  ticker_symbol,
  combined_score,
  decision,
  JSON_EXTRACT(reasoning, '$.alignment_bonus') as bonus
FROM signals 
WHERE JSON_EXTRACT(reasoning, '$.alignment_bonus') < 0
ORDER BY combined_score ASC;
```

### BUY ÉS SELL Alignment Együtt:

```sql
SELECT 
  ticker_symbol,
  combined_score,
  decision,
  JSON_EXTRACT(reasoning, '$.alignment_bonus') as bonus,
  CASE 
    WHEN JSON_EXTRACT(reasoning, '$.alignment_bonus') > 0 THEN 'BUY Aligned'
    WHEN JSON_EXTRACT(reasoning, '$.alignment_bonus') < 0 THEN 'SELL Aligned'
    ELSE 'No Alignment'
  END as alignment_type
FROM signals 
WHERE calculated_at > datetime('now', '-1 hour')
ORDER BY ABS(combined_score) DESC;
```

---

## Változások az Eredeti Verzióhoz Képest

| Verzió | BUY Bonus | SELL Bonus | Mixed Signal |
|--------|-----------|------------|--------------|
| v1 | ✅ Működik | ❌ Mindig 0 | ❌ Kap bonus-t |
| v2 | ✅ Működik | ✅ Működik | ✅ Nincs bonus |

**v2 Javítások:**
1. SELL alignment támogatás (negatív bonus)
2. Mixed signal detektálás (irány ellenőrzés)
3. Frissített logging (BUY/SELL jelzés)
4. Frissített reasoning (null vagy ±érték)

---

## Deployment

1. Cseréld le a `signal_generator.py` fájlt
2. Indítsd újra a backendet
3. Teszteld SELL signalokkal
4. Ellenőrizd a console log-ot
5. Nézd meg az adatbázist

**Filename:** `signal_generator_v2.py` (szimmetrikus verzió)
