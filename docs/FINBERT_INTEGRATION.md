# FinBERT Integration Guide

## 🧠 Mock → FinBERT Migration

### Előtte (Mock Keyword-Based):
```python
from sentiment_analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer(config)
result = analyzer.analyze_text("Apple beats earnings")
# Mock sentiment based on keywords
```

### Utána (Real FinBERT):
```python
from finbert_analyzer import SentimentAnalyzerFinBERT

analyzer = SentimentAnalyzerFinBERT(config)
result = analyzer.analyze_text("Apple beats earnings")
# Real BERT-based sentiment! ✅
```

---

## 🚀 Javasolt Megoldás: Config Flag

**Készítek egy kapcsolót** hogy könnyen válthass mock és FinBERT között!

**Előny:** 
- ✅ Biztonságos (rollback 1 flag-gel)
- ✅ A/B tesztelés
- ✅ Nem breaking change

---

## 📋 Implementation Plan

1. FinBERT modul (finbert_analyzer.py) ✅ Kész
2. Config flag (USE_FINBERT = True/False)
3. Conditional import minden news collector-ban
4. Test standalone
5. Full integration test

---

**Folytatjuk?** Készítem a config flag integrációt! 🔧
