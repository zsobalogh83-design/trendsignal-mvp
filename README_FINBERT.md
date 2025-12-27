# TrendSignal MVP - Sentiment-Driven Trading Signals

**Version:** 1.5 (FinBERT Integration)  
**Status:** ✅ Production Ready  
**Date:** 2024-12-27

---

## 🎯 Overview

**TrendSignal** is an automated decision support system for day traders that:
- 🧠 Uses **FinBERT AI** for financial sentiment analysis
- 📰 Collects news from **Alpha Vantage + Portfolio.hu** (7 RSS feeds)
- 📊 Performs **technical analysis** (7 indicators)
- 🎯 Generates **BUY/SELL/HOLD signals** with confidence scores
- 🇭🇺 Supports **Hungarian BÉT** + 🇺🇸 **US blue-chips**

---

## ✨ Key Features

✅ **FinBERT-powered sentiment** (92-96% confidence)  
✅ **Ticker-aware keywords** (100+ per ticker)  
✅ **24h decay model** (0-2h, 2-6h, 6-12h, 12-24h)  
✅ **Sentiment-driven strategy** (70% weight)  
✅ **Technical confirmation** (20% weight)  
✅ **Auto entry/stop/target** calculation  
✅ **Batch processing** (multiple tickers)

---

## 🚀 Quick Start (Google Colab)

```python
# 1. Clone repository
!git clone https://github.com/zsobalogh83-design/trendsignal-mvp.git
%cd trendsignal-mvp

# 2. Install dependencies
!pip install -r requirements.txt --quiet

# 3. Set API keys
import os
os.environ['ALPHAVANTAGE_KEY'] = 'your_key_here'

# 4. Run analysis
from main import run_analysis

signal = run_analysis('AAPL', 'Apple Inc.')
signal.display()
```

---

## 📊 Supported Tickers

### 🇺🇸 US Blue-Chips:
- **AAPL** - Apple Inc.
- **TSLA** - Tesla Inc.
- **MSFT** - Microsoft
- **NVDA** - NVIDIA

### 🇭🇺 Hungarian BÉT:
- **OTP.BD** - OTP Bank
- **MOL.BD** - MOL Nyrt

*Easily extendable in `ticker_keywords.py`*

---

## 🧠 Sentiment Analysis

### English News (FinBERT):
```python
from finbert_analyzer import FinBERTAnalyzer

analyzer = FinBERTAnalyzer()
result = analyzer.analyze("Apple beats earnings expectations")

# Output: {score: +0.91, confidence: 0.94, label: 'positive'}
```

### Hungarian News (Enhanced Keywords):
```python
from hungarian_news import HungarianNewsCollector

collector = HungarianNewsCollector()
news = collector.collect_news('OTP.BD', 'OTP Bank')

# 7 Hungarian RSS sources (Portfolio.hu, Telex, HVG, Index)
```

---

## 📈 Signal Example

```
AAPL - WEAK BUY
Score: +41.2 (65% confidence)

Sentiment: +45.1 (21 news, FinBERT analyzed)
Technical: +23.3 (RSI oversold, mixed MACD)
Risk: +50.0 (low volatility)

Entry: $273.25
Stop-Loss: $267.78 (-2.0%)
Take-Profit: $284.18 (+4.0%)
R:R Ratio: 1:2
```

---

## 🔧 Configuration

Toggle FinBERT in `src/config.py`:

```python
USE_FINBERT = True   # Real FinBERT (recommended)
USE_FINBERT = False  # Keyword-based (fallback)
```

---

## 📚 Documentation

- [MVP Complete Documentation](MVP_COMPLETE_DOCUMENTATION.md)
- [FinBERT Integration Guide](docs/FINBERT_INTEGRATION.md)
- [Hungarian News Guide](docs/HUNGARIAN_NEWS.md)
- [Deployment Guide](DEPLOYMENT.md)

---

## 🔄 Update & Pull

```python
# In Colab, get latest version:
%cd /content/trendsignal-mvp
!git pull origin main
```

---

## 🐛 Common Issues

**Q: NewsAPI returns 0 results?**  
A: Free tier limitation. Alpha Vantage works great!

**Q: FinBERT too slow?**  
A: First load downloads model (~1-2 min). Cached after.

**Q: Hungarian sentiment = 0.00?**  
A: FinBERT is English-only. Use keyword-based or Phase 2 translation.

---

## 🎊 Status

**MVP Backend: ✅ COMPLETE**

- ✅ FinBERT integration
- ✅ 6 tickers supported
- ✅ Hungarian + English sources
- ✅ Working SDLC workflow
- ✅ Tested and validated

**Phase 2:** Dashboard UI, Database, Real-time monitoring

---

**Repository:** https://github.com/zsobalogh83-design/trendsignal-mvp  
**Author:** Claude (Anthropic) + Zsolt Balogh  
**License:** Private (MVP)

**Last Updated:** 2024-12-27
