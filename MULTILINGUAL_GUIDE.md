# Magyar Nyelv Támogatás - Használati Útmutató

## 🌐 Automatikus Nyelv Detektálás

A rendszer **automatikusan felismeri** a hír nyelvét és a megfelelő sentiment analyzer-t használja!

---

## 🔄 Hogyan Működik

```
Hír bejön
    ↓
Nyelv detektálás (magyar vs angol)
    ↓
┌─────────────────┐  ┌─────────────────┐
│ Magyar (hu)     │  │ Angol (en)      │
│ 🇭🇺 🔤          │  │ 🇬🇧 🧠          │
│                 │  │                 │
│ Enhanced        │  │ FinBERT         │
│ Keywords        │  │ AI Model        │
│                 │  │                 │
│ +37 pos kw      │  │ 92-96% conf     │
│ +37 neg kw      │  │ Contextual      │
│ +ticker kw      │  │ understanding   │
└─────────────────┘  └─────────────────┘
    ↓                    ↓
Sentiment Score (-1.0 to +1.0)
```

---

## 🧪 Tesztelés

### Nyelv Detektálás:

```python
from multilingual_sentiment import detect_language

texts = [
    "Apple reports strong earnings",
    "Az OTP Bank növelte nyereségét",
]

for text in texts:
    lang = detect_language(text)
    flag = "🇬🇧" if lang == 'en' else "🇭🇺"
    print(f"{flag} {lang.upper()}: {text}")

# Output:
# 🇬🇧 EN: Apple reports strong earnings
# 🇭🇺 HU: Az OTP Bank növelte nyereségét
```

### Multilingual Sentiment:

```python
from multilingual_sentiment import MultilingualSentimentAnalyzer

analyzer = MultilingualSentimentAnalyzer()

# Angol hír → FinBERT
result_en = analyzer.analyze_text("Apple beats earnings", 'AAPL')
print(f"EN: {result_en['score']:+.3f} via {result_en['method']}")

# Magyar hír → Keywords
result_hu = analyzer.analyze_text("Az OTP erős eredményt ért el", 'OTP.BD')
print(f"HU: {result_hu['score']:+.3f} via {result_hu['method']}")

# Output:
# EN: +0.912 via finbert
# HU: +0.500 via keywords
```

---

## 🎯 Automatikus Használat

**A news collector-ok automatikusan használják!**

```python
from hungarian_news import EnhancedNewsCollector

collector = EnhancedNewsCollector(config)

# Vegyes angol+magyar hírek gyűjtése
news = collector.collect_all_news('OTP.BD', 'OTP Bank', lookback_hours=24)

# Minden hír automatikusan:
# - Nyelv detektálva
# - Megfelelő analyzer használva
# - Sentiment kiszámolva

for item in news:
    # item.sentiment_score már készen van!
    print(f"{item.sentiment_score:+.2f} | {item.title}")
```

**Nincs extra kód! Minden automatikus!** ✅

---

## 📊 Nyelvenkénti Teljesítmény

### Angol (FinBERT):
```
Pontosság: 92-96%
Confidence: 0.85-0.95
Range: -0.95 to +0.95 (teljes spektrum)
Kontextus: ✅ Érti a nuance-okat

Példa:
  "Position decreased" → -0.94 (pénzügyileg negatív!)
  "Steady performance" → +0.85 (pozitív kontextus!)
```

### Magyar (Enhanced Keywords):
```
Pontosság: ~70-80% (keyword-based)
Confidence: 0.60-0.80
Range: -1.0 to +1.0
Kontextus: ⚠️ Limited (csak keywords)

Példa:
  "növekedés" → pozitív
  "csökkenés" → negatív
  "csapda" → negatív ✅
```

---

## 🔍 Nyelv Detektálás Logika

### Magyar Jellemzők:
```
1. Speciális karakterek: á, é, í, ó, ö, ő, ú, ü, ű
2. Magyar szavak: hogy, és, van, lesz, nak, nek, ról, ben
3. Pénzügyi: forint, milliárd, nyrt, zrt, bank
```

### Döntés:
```
Ha ≥2 magyar karakter VAGY több magyar szó
  → 🇭🇺 Magyar
Különben
  → 🇬🇧 Angol
```

---

## 🚀 Production Usage

### OTP.BD (Vegyes Hírek):

```python
collector = EnhancedNewsCollector(config)

news = collector.collect_all_news('OTP.BD', 'OTP Bank', lookback_hours=48)

# Várható:
# - Portfolio.hu magyar hírek → 🇭🇺 Keywords
# - Alpha Vantage angol hírek → 🇬🇧 FinBERT (ha van)
# - Mindkettő aggregálva egy listában!

print(f"Total: {len(news)} news")

hu_news = [n for n in news if detect_language(n.title) == 'hu']
en_news = [n for n in news if detect_language(n.title) == 'en']

print(f"  Magyar: {len(hu_news)} (keywords)")
print(f"  Angol: {len(en_news)} (FinBERT)")
```

---

## 📈 Batch Processing

```python
# Automatikus nyelv detektálás batch módban is!
texts = [
    "Apple strong quarter",
    "OTP nyereség emelkedés",
    "Tesla delivery record",
    "MOL olajár hatás",
]

results = analyzer.analyze_batch(texts)

# Angol hírek → FinBERT batch (gyors!)
# Magyar hírek → Keywords egyenként
# Eredmények eredeti sorrendben visszaadva
```

---

## ⚙️ Konfiguráció

### FinBERT ki/be kapcsolás:

```python
# config.py
USE_FINBERT = True   # Angol → FinBERT, Magyar → Keywords
USE_FINBERT = False  # Minden → Keywords
```

### Nyelv detektálás finomhangolás:

```python
# multilingual_sentiment.py
# Bővíthető magyar/angol szavak listája
hungarian_words = [...]  # Add több magyar szót
english_words = [...]    # Add több angol szót
```

---

## 🎯 Várható Eredmények

### OTP.BD Signal (Magyar hírek):

```
Előtte (csak keywords):
  Sentiment: 0.00 (nincs magyar kw)
  Confidence: 17%

Utána (multilingual):
  Sentiment: ±0.3 to ±0.5 (magyar kw működik!)
  Confidence: 40-60%
  
Ha angol OTP hír is van:
  Sentiment: +0.7 (FinBERT angol hírre!)
  Confidence: 65-75% ✅
```

---

## 🐛 Troubleshooting

### "Language always 'en'"
```python
# Check magyar karakterek
text = "Az OTP növekedése"
print([c for c in text if c in 'áéíóöőúüű'])
# Ha üres → nincs magyar char → 'en' lesz
```

### "FinBERT not used for English"
```python
from config import USE_FINBERT
print(f"USE_FINBERT = {USE_FINBERT}")
# Ha False → minden keywords
```

---

## 📝 Phase 2 Improvements

- [ ] **Google Translate API** → magyar → angol → FinBERT
- [ ] **Multilingual BERT** (xlm-roberta) magyar support
- [ ] **Language confidence score** (mennyire biztos a detektálás)
- [ ] **Mixed language handling** (angol+magyar egy szövegben)

---

**Last Updated:** 2024-12-27  
**Status:** ✅ Ready for testing
