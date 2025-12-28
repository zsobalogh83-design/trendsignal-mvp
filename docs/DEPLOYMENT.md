# TrendSignal MVP - Deployment Guide

## 🎯 Workflow Overview

```
Claude (outputs) 
    ↓ (download)
SharePoint/Local folder
    ↓ (GitHub Desktop)
GitHub Repository
    ↓ (git clone/pull)
Google Colab
    ↓ (development & testing)
Production Ready! ✅
```

---

## 📋 One-Time Setup (Already Done!)

✅ GitHub repository created  
✅ GitHub Desktop installed  
✅ Repository cloned locally  
✅ SharePoint folder ready  

---

## 🔄 Daily Development Workflow

### 1. Claude Készít Új Modult/Frissítést

```
Claude creates → outputs folder → download link
```

### 2. Te Letöltöd és Bemásolod

```
1. Download from Claude outputs
2. Copy to: C:\Users\...\trendsignal-mvp\src\
   (or wherever your local clone is)
```

### 3. GitHub Desktop Sync

```
1. Open GitHub Desktop
2. See changes listed automatically
3. Write commit message: "Added sentiment_analyzer module"
4. Click: "Commit to main"
5. Click: "Push origin"
```

### 4. Colab Pull & Test

```python
# In Colab
%cd /content/trendsignal-mvp
!git pull origin main

# Test new module
from src.sentiment_analyzer import SentimentAnalyzer
analyzer = SentimentAnalyzer()
# ... test code ...
```

### 5. Feedback to Claude

```
"Claude, a sentiment analyzer működik, de add hozzá XYZ funkciót"
→ Claude updates module
→ Repeat from step 1
```

---

## ⚡ Quick Commands Reference

### Colab - First Time Setup
```python
!git clone https://github.com/zsobalogh83-design/trendsignal-mvp.git
%cd trendsignal-mvp
!pip install -r requirements.txt --quiet
```

### Colab - Daily Pull
```python
%cd /content/trendsignal-mvp
!git pull origin main
```

### Colab - Import Modules
```python
import sys
sys.path.insert(0, '/content/trendsignal-mvp/src')

from config import get_config
from signal_generator import SignalGenerator
# ... etc
```

### GitHub Desktop
```
1. See changes
2. Commit message
3. Commit to main
4. Push origin
```

---

## 🐛 Troubleshooting

### "Module not found" in Colab
```python
import sys
sys.path.insert(0, '/content/trendsignal-mvp/src')
```

### GitHub Desktop doesn't show changes
```
1. Check file is in correct folder
2. Refresh GitHub Desktop (View → Refresh)
3. Check .gitignore isn't blocking file
```

### Colab git pull fails
```python
# Reset to clean state
!git reset --hard origin/main
!git pull origin main
```

### API keys not working
```python
# Set explicitly in Colab
import os
os.environ['NEWSAPI_KEY'] = 'your_key_here'
os.environ['ALPHAVANTAGE_KEY'] = 'your_key_here'
```

---

## 📊 Expected Development Speed

| Task | Time |
|------|------|
| Claude creates module | 5-10 min |
| Download from outputs | 10 sec |
| Copy to local folder | 10 sec |
| GitHub Desktop commit/push | 30 sec |
| Colab git pull | 10 sec |
| Test new module | 2-5 min |
| **Total per update** | **~10 min** |

---

## 🎯 Optimization Tips

1. **Batch updates** - Claude creates multiple modules at once
2. **Test locally first** - Before GitHub push
3. **Clear commit messages** - Easy to track changes
4. **Use Development.ipynb** - Clean testing environment
5. **Save work frequently** - Colab can disconnect

---

## 📈 Progress Tracking

### Phase 1: Core Modules ✅
- [x] config.py
- [x] news_collector.py  
- [x] sentiment_analyzer.py
- [x] technical_analyzer.py
- [x] signal_generator.py
- [x] utils.py
- [x] main.py

### Phase 2: Enhancements (TODO)
- [ ] Real FinBERT integration
- [ ] Database persistence
- [ ] FastAPI REST API
- [ ] React dashboard
- [ ] Backtesting engine

---

**Last Updated:** 2024-12-27  
**Status:** Ready for development! 🚀
