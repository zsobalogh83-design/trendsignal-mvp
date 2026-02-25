# TrendSignal MVP – Rendszerleírás (Project Knowledge)

> **Generálva:** 2026-02-24 | **Verzió:** MVP v1.5
> **Cél:** Claude.ai project knowledge dokumentum fejlesztői munkához

---

## 1. Mi ez az alkalmazás?

A **TrendSignal MVP** egy önhangoló, AI-alapú tőzsdei kereskedési jelzésrendszer. Hírszemantika (NLP), technikai indikátorok és kockázatkezelés kombinálásával BUY / SELL / HOLD döntéseket generál részvényekre. Önhangolása genetikus algoritmus (DEAP) segítségével működik: a backtester visszateszteli a paramétereket, a GA evolúciósan optimalizálja azokat.

**Támogatott piacok:** US részvények (AAPL, TSLA, MSFT, NVDA) és magyar BÉT (OTP.BD, MOL.BD).
**Jelzésfrissítés:** 15 percenként, piaci nyitva tartás alatt.

---

## 2. Technológiai stack

### Backend
| Réteg | Technológia |
|-------|------------|
| Web framework | FastAPI 0.100+ (async, CORS) |
| Scheduler | APScheduler (AsyncIOScheduler) |
| ORM | SQLAlchemy 2.0+ |
| Adatbázis | SQLite (WAL mód, 30s timeout) |
| AI/NLP | HuggingFace Transformers – FinBERT (ProsusAI/finbert) |
| ML runtime | PyTorch |
| Genetikus algoritmus | DEAP 1.4.3 + ProcessPoolExecutor |
| Pénzügyi adatok | yfinance (ár), Finnhub, MarketAux, GNews API |
| Hírek | feedparser 6.0.10 (RSS) |
| Adatfeldolgozás | pandas 2.0+, numpy 1.24+ |
| Értesítés | Telegram Bot API |

### Frontend
| Réteg | Technológia |
|-------|------------|
| Framework | React 19.2 + TypeScript |
| Build | Vite 7.2 |
| State/Query | TanStack React Query v5 |
| Routing | React Router 7 |
| CSS | TailwindCSS 4.1 (PostCSS) |
| HTTP kliens | fetch-alapú custom hook |

---

## 3. Könyvtárszerkezet

```
trendsignal-mvp/
├── src/                         # Core Python modulok
│   ├── config.py                # Env vars, konstansok
│   ├── database.py              # SQLite session kezelés
│   ├── models.py                # SQLAlchemy ORM modellek
│   ├── signal_generator.py      # BUY/SELL/HOLD döntési logika
│   ├── technical_analyzer.py    # Technikai indikátorok (manuál impl.)
│   ├── sentiment_analyzer.py    # FinBERT + kulcsszavas fallback
│   ├── finbert_analyzer.py      # FinBERT wrapper
│   ├── news_collector.py        # Multi-source híraggregátor
│   ├── hungarian_news.py        # Magyar RSS parser
│   ├── yahoo_collector.py       # Yahoo Finance hírek
│   ├── finnhub_collector.py     # Finnhub API
│   ├── marketaux_collector.py   # MarketAux API
│   ├── gnews_collector.py       # GNews API
│   ├── price_service.py         # Árfolyam fetch + cache
│   ├── trade_manager.py         # Szimulált kereskedés (TZ-aware)
│   ├── scheduler.py             # Piaci idő + ütemező logika
│   ├── telegram_alerter.py      # Telegram értesítések
│   ├── ticker_config.py         # Ticker metaadat konfiguráció
│   ├── ticker_keywords.py       # Ticker-specifikus kulcsszavak
│   ├── backtest_service.py      # Visszatesztelési szolgáltatás
│   └── db_helpers.py            # DB segédfüggvények
│
├── optimizer/                   # Genetikus optimalizáló motor
│   ├── genetic.py               # DEAP GA (46-dimenziós tér)
│   ├── fitness.py               # Fitness kiértékelés
│   ├── backtester.py            # Jelzés visszajátszó szimulátor
│   ├── signal_data.py           # Adat betöltés optimalizáláshoz
│   ├── trade_simulator.py       # Kereskedési szimulátor
│   ├── parameter_space.py       # 46 paraméter definíciója
│   └── validation.py            # Optimalizálás validáció
│
├── frontend/                    # React TypeScript SPA
│   └── src/
│       ├── pages/               # Dashboard, SignalDetail, History,
│       │                        # NewsFeed, Configuration, OptimizerPage
│       ├── components/          # SignalCard, TickerManagement
│       ├── hooks/useApi.ts      # API kliens wrapper
│       └── api/client.ts        # HTTP kliens
│
├── main.py                      # Fő orchestrator
├── api.py                       # FastAPI belépési pont + APScheduler
├── signals_api.py               # Jelzés CRUD router
├── tickers_api.py               # Ticker kezelés router
├── simulated_trades_api.py      # Szimulált kereskedések router
├── optimizer_api.py             # Optimalizáló vezérlés router
├── config_api.py                # Konfiguráció router
├── config.json                  # Jelzéssúlyok és küszöbök (46+ param)
├── requirements.txt             # Python függőségek
└── trendsignal.db               # SQLite adatbázis (futásidejű)
```

---

## 4. Adatbázis séma (SQLite – trendsignal.db)

| Tábla | Cél | Kulcs mezők |
|-------|-----|-------------|
| `tickers` | Részvény metaadat | symbol, name, market, industry, priority, language, keywords (JSON) |
| `news_items` | Összegyűjtött hírek | url, title, sentiment_score, language, cluster_id, published_at |
| `news_sources` | Hírforrás definíciók | name, type (RSS/API), credibility_weight |
| `news_tickers` | Hír↔ticker M2M | news_id, ticker_id, relevance_score |
| `price_data` | OHLCV gyertyák | ticker_symbol, timestamp, interval, open/high/low/close, volume |
| `technical_indicators` | Számított indikátorok | sma_20/50/200, macd, rsi, bb_upper/lower, atr, adx, stoch_k/d |
| `signals` | Generált jelzések | ticker_symbol, decision, combined_score, sentiment/technical/risk scores, entry_price, stop_loss, take_profit, reasoning_json |
| `signal_calculations` | Audit trail | signal_id, összes input érték, score breakdown, config snapshot |
| `simulated_trades` | Szimulált pozíciók | entry_signal_id, entry_price, stop_loss, take_profit, position_size, pnl_percent, exit_trigger |
| `optimization_runs` | GA futások | run_id, status, generations, fitness, proposals |

---

## 5. Jelzésgenerálási pipeline

```
News APIs / RSS feeds
        ↓
  NewsCollector (aggregátor)
        ↓
  SentimentAnalyzer (FinBERT EN / kulcsszavas HU)
        ↓                              ↓
  sentiment_score              price_service (yfinance)
                                       ↓
                              TechnicalAnalyzer (RSI, MACD, BB, SMA, ATR, ADX, Stoch)
                                       ↓
                               technical_score
                                       ↓
  sentiment_score + technical_score + risk_score → combined_score
                                       ↓
                              SignalGenerator → BUY / SELL / HOLD
                                       ↓
                              TradeManager (entry, SL, TP, pozícióméret)
                                       ↓
                          simulated_trades tábla + Telegram alert
```

---

## 6. Jelzéspontozási logika

### Összetett pontszám képlete
```
combined_score =
  (sentiment_score × SENTIMENT_WEIGHT) +   # 0.50
  (technical_score × TECHNICAL_WEIGHT) +   # 0.35
  (risk_score × RISK_WEIGHT) +             # 0.15
  alignment_bonus
```

### Döntési küszöbök (config.json)
| Döntés | Feltétel |
|--------|---------|
| **STRONG BUY** | score ≥ 55, confidence ≥ 0.75 |
| **MODERATE BUY** | score ≥ 35, confidence ≥ 0.65 |
| **HOLD** | -15 < score < 15 |
| **MODERATE SELL** | score ≤ -35, confidence ≥ 0.65 |
| **STRONG SELL** | score ≤ -65, confidence ≥ 0.75 |

### Alignment bónuszok
| Feltétel | Bónusz |
|----------|--------|
| Mindhárom komponens egyirányú | +8 pont |
| Tech + Risk VAGY Sentiment + Tech egyirányú | +5 pont |
| Sentiment + Risk egyirányú | +3 pont |

### Szentiment súly-bomlás (24 óra)
| Hír kora | Súly |
|----------|------|
| 0–2 óra | 100% |
| 2–6 óra | 85% |
| 6–12 óra | 60% |
| 12–24 óra | 35% |

---

## 7. Technikai indikátorok

Minden indikátor **manuálisan implementált** (nem TA-Lib függőség).

| Indikátor | Timeframe | Lookback |
|-----------|-----------|---------|
| RSI (14) | 5m | 2 nap |
| SMA 20 | 5m | 2 nap |
| SMA 50 | 1h | 30 nap |
| SMA 200 | 1d | 180 nap |
| MACD (12/26/9) | 15m | 3 nap |
| Bollinger Bands (20, 2σ) | 1h | 7 nap |
| ATR (14) | 1d | 180 nap |
| Stochastic (14) | 15m | 3 nap |
| ADX (14) | 1h | 30 nap |

**Support/Resistance:** DBSCAN clustering (eps=4, min_samples=3, lookback=180 nap)

---

## 8. Kockázatkezelés és kereskedési paraméterek

| Paraméter | Érték |
|-----------|-------|
| Stop Loss | Legközelebbi support ± 0.3% buffer VAGY ATR × 1.2 |
| Take Profit | ATR × 2.5 |
| Pozícióméret | 700 000 HUF célérték (dinamikus HUF/USD konverzió) |
| Min. SL távolság | 2.0% |
| Max. SL távolság | 8.0% |
| Min. TP távolság | 2.0% |

**Kereskedési életciklus:**
1. Jelzés generálódik (UTC timestamp)
2. 15 perc késleltetés (végrehajtás)
3. Entry következő elérhető áron (yfinance)
4. Pozícióméret: 700k HUF
5. SL/TP frissítés azonos irányú jelzésnél
6. Kilépési triggerek: SL elérve | TP elérve | Ellentétes jelzés | EOD zárás (16:45)
7. P&L számítás HUF-ban

---

## 9. Genetikus optimalizáló motor

**Cél:** A 46-dimenziós paramétertér automatikus finomhangolása backtester-alapú fitness funkcióval.

| Paraméter | Érték |
|-----------|-------|
| Populáció | 80 egyed |
| Generációk | 100 |
| Szelekció | Tournament (k=3) |
| Crossover | Two-point, 70% valószínűség |
| Mutáció | Gaussi, 20% valószínűség |
| Fitness | Sharpe-ráta + win rate (backtester) |
| Validáció | Külön validációs halmaz, 5 generációnként |

**Optimalizáló API-n keresztül indítható, javaslatok approve-olhatók a frontendről.**

---

## 10. Hírforrások és sentiment analízis

### Angol forrás
| Forrás | Limit | Megjegyzés |
|--------|-------|-----------|
| Finnhub | 60 req/perc | Pénzügyi hírek |
| MarketAux | 100 req/nap | Átfogó hírek |
| GNews | Nincs limit | Valós idejű |
| Yahoo Finance | Nincs limit | yfinance-en át |

### Magyar forrás (RSS)
- Portfolio.hu (3 feed: Befektetés, Bankolás, Gazdaság)
- Telex.hu
- HVG.hu
- Index.hu

### Sentiment motorok
- **FinBERT** (ProsusAI/finbert): English szövegekre, 92–96% konfidencia
- **Kulcsszavas fallback**: Magyar szövegekre, 37+ HU kulcsszó + ticker-specifikus szótár

---

## 11. REST API végpontok

**Base URL:** `http://localhost:8000/api/v1/`

### Jelzések
| Végpont | Metódus | Leírás |
|---------|---------|--------|
| `/signals` | GET | Jelzések listája (lapozva, szűrhető) |
| `/signals/{id}` | GET | Jelzés részletei komponensekkel |
| `/signals/generate` | POST | Jelzés generálás tickerekre |
| `/signals/history` | GET | Jelzéstörténet dátumszűrővel |
| `/signals/{id}/reason` | GET | Reasoning JSON lekérés |

### Tickerek
| Végpont | Metódus | Leírás |
|---------|---------|--------|
| `/tickers` | GET, POST | Ticker lista / létrehozás |
| `/tickers/{id}` | GET, PUT, DELETE | Ticker CRUD |

### Szimulált kereskedések
| Végpont | Metódus | Leírás |
|---------|---------|--------|
| `/simulated_trades` | GET | Nyitott/zárt pozíciók |
| `/simulated_trades/{id}` | GET | Pozíció részletei, P&L |
| `/simulated_trades/stats` | GET | Összesített statisztika |

### Konfiguráció & optimalizáló
| Végpont | Metódus | Leírás |
|---------|---------|--------|
| `/config` | GET, PUT | Konfig olvasás/írás |
| `/optimizer/run` | POST | GA indítása |
| `/optimizer/runs` | GET | Futások listája |
| `/optimizer/runs/{id}/progress` | GET | Live progress |
| `/optimizer/proposals` | GET | Javasolt paraméterhalmazok |
| `/optimizer/proposals/{id}/approve` | POST | Paraméter alkalmazása |

**CORS:** `localhost:5173` (Vite dev), `localhost:3000`, wildcard (dev)

---

## 12. Értesítési rendszer

**Telegram Bot:**
- Küszöb: combined_score ≥ 30
- Max. 10 értesítés/óra
- Tartalom: jelzés, news excerpts, link (konfigurálható)
- `telegram_watermarks.json`: duplikáció-elkerülés

---

## 13. Ütemezés és piaci idők

| Piac | Nyitvatartás | Timezone |
|------|-------------|---------|
| BÉT (Budapest) | 09:00–17:00 | CET/CEST |
| US tőzsde | 09:30–16:00 | US/Eastern |

- Jelzésfrissítés: **15 percenként** piaci nyitvatartás alatt
- EOD kereskedési zárás: **16:45**
- APScheduler beépítve a FastAPI lifespan-ba

---

## 14. Környezeti változók (kötelező)

```env
FINNHUB_API_KEY=...
MARKETAUX_API_KEY=...
GNEWS_API_KEY=...
NEWSAPI_KEY=...
ALPHAVANTAGE_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

**Feature flagek (config.py):**
- `USE_FINBERT = True` – FinBERT bekapcsolva (vs kulcsszavas)
- `USE_MULTILINGUAL = True` – Többnyelvű BERT
- `TELEGRAM_ALERTS_ENABLED = True` – Telegram értesítések

---

## 15. Frontend oldalak

| Oldal | Fájl | Leírás |
|-------|------|--------|
| Dashboard | `Dashboard.tsx` | Aktuális jelzések összefoglalója |
| Signal Detail | `SignalDetail.tsx` | Részletes jelzéselemzés, komponensek |
| Signal History | `SignalHistory.tsx` | Jelzéstörténet, szűrők |
| News Feed | `NewsFeed.tsx` | Hírcikkek megjelenítése |
| Configuration | `Configuration.tsx` | Paraméter hangolás UI |
| Optimizer | `OptimizerPage.tsx` | GA indítás, javaslatok kezelése |

---

## 16. Fejlesztési konvenciók

- **Python:** SQLAlchemy 2.0 deklaratív stílus, nincs relationship() ORM join (registry conflict elkerülés), manuális join query-k
- **Async:** FastAPI async endpointok, `asyncio.run()` a schedulerben
- **DB:** WAL mód, 30s busy timeout, 64MB cache; minden ír/olvas context manageren belül
- **Konfiguráció:** `config.json` fut-idejű; `config.py` env-alapú; `ticker_config.py` per-ticker metaadat
- **Timezone:** pytz, minden timestamp UTC-ben tárolva, helyi idő csak megjelenítésnél
- **Tesztek:** `tests/` + `optimizer/test_*.py` lépésenkénti tesztek

---

## 17. Legfontosabb fájlok fejlesztői referencia

| Fájl | Mikor releváns |
|------|---------------|
| `src/signal_generator.py` | Jelzés logika módosításakor |
| `src/technical_analyzer.py` | Indikátor számítás módosításakor |
| `src/sentiment_analyzer.py` | Sentiment pipeline változtatáskor |
| `src/trade_manager.py` | SL/TP/pozícióméret logikánál |
| `optimizer/genetic.py` | GA paraméter tér bővítésekor |
| `optimizer/parameter_space.py` | Új optimalizálható paraméter felvételekor |
| `config.json` | Küszöbök, súlyok, indikátor paraméterek |
| `src/models.py` | DB séma változtatáskor |
| `api.py` | FastAPI startup, lifespan, scheduler |
| `signals_api.py` | Jelzés API endpointok |

---

*Ez a dokumentum a Claude.ai project knowledge számára készült. Frissíteni kell, ha az architektúra lényegesen megváltozik.*
