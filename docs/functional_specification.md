# TrendSignal MVP – Funkcionális Specifikáció

> Verzió: 1.0 (reverse engineered, 2026-03-29)
> Státusz: Élő rendszer dokumentációja

---

## Tartalomjegyzék

1. [Rendszer áttekintése](#1-rendszer-áttekintése)
2. [Architektúra](#2-architektúra)
3. [Adatmodell](#3-adatmodell)
4. [Adatgyűjtés](#4-adatgyűjtés)
5. [Signal generálás](#5-signal-generálás)
6. [Trade szimuláció](#6-trade-szimuláció)
7. [Optimizer (Genetikai Algoritmus)](#7-optimizer-genetikai-algoritmus)
8. [API endpointok](#8-api-endpointok)
9. [Frontend](#9-frontend)
10. [Automatizálás és ütemezés](#10-automatizálás-és-ütemezés)
11. [Konfiguráció](#11-konfiguráció)

---

## 1. Rendszer áttekintése

A **TrendSignal MVP** egy AI-alapú kereskedési szignál generáló és backtesztelő rendszer, amely a következő feladatokat látja el:

- **Valós idejű szignálgenerálás**: 15 percenként BUY / SELL / HOLD döntések generálása aktív tickerekre, három komponens (szentiment, technikai, kockázat) kombinálásával.
- **Visszamenőleges kereskedés-szimuláció (backtest)**: Minden generált szignálhoz szimulált trade készül automatikusan, amelyen SL/TP, trailing stop, stagnation exit és ellentétes szignál alapú zárás fut.
- **Archive backtest**: Historikus szignálok (archive_signals) alapján teljes újraszimuláció, kizárólag memóriában, adatbázis-írás nélkül a futás közben.
- **Önhangoló optimizer**: Genetikai algoritmussal optimalizálja a 46 dimenziós konfigurációs teret (ATR szorzók, súlyok, küszöbök stb.), majd javasolja az elfogadott paraméterkészletet a felhasználónak.
- **Felhasználói felület**: React alapú dashboard szignálok, trade-ek, hírek, optimizátor-eredmények és konfiguráció megjelenítéséhez.

### Támogatott piacok

| Piac | Jelölés | Kereskedési idő (UTC) |
|------|---------|----------------------|
| Amerikai tőzsde (US) | (szuffixum nélkül) | 14:30–21:00, H–P |
| Budapesti Értéktőzsde (BÉT) | `.BD` szuffixum | 08:00–16:00, H–P |

---

## 2. Architektúra

### 2.1 Rétegek

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (React/TypeScript)                                 │
│  React Router · TanStack Query · Tailwind-style CSS          │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼───────────────────────────────────────┐
│  Backend API (Python/FastAPI)                                │
│  APScheduler · SQLAlchemy ORM · Pydantic validation          │
│                                                              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │ signals_api  │  │simulated_     │  │ optimizer_api    │  │
│  │ tickers_api  │  │trades_api     │  │ config_api       │  │
│  └──────────────┘  └───────────────┘  └──────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Core Services                                       │   │
│  │  signal_generator · backtest_service                 │   │
│  │  archive_backtest_service · trade_simulator_core     │   │
│  │  news_collector · price_service · scheduler          │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬───────────────────────────────────────┘
                       │ SQLAlchemy / sqlite3
┌──────────────────────▼───────────────────────────────────────┐
│  SQLite adatbázis (trendsignal.db)                          │
└──────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────┐
│  Optimizer (Python, külön processz)                         │
│  DEAP GA · multiprocessing.Pool · in-memory szimuláció      │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Technológiai stack

| Réteg | Technológia |
|-------|-------------|
| Backend framework | FastAPI (async) |
| Adatbázis | SQLite (`trendsignal.db`) |
| ORM | SQLAlchemy 1.4+ |
| Scheduler | APScheduler (AsyncIOScheduler) |
| Sentiment modell | FinBERT (transformers) |
| LLM elemzés | OpenRouter API (opcionális) |
| Ár-adatok (live) | yfinance |
| Ár-adatok (archive) | Alpaca API |
| Hírek | GNews, Finnhub, Marketaux, RSS |
| Optimizer GA | DEAP library |
| Párhuzamosítás | multiprocessing.Pool |
| Frontend | React 18 + TypeScript |
| Routing | React Router |
| Server state | TanStack React Query |

---

## 3. Adatmodell

### 3.1 Táblák áttekintése

| Tábla | Leírás |
|-------|--------|
| `tickers` | Követett instrumentumok |
| `news_items` | Összegyűjtött hírek szentiment-értékkel |
| `news_tickers` | Hírek és tickerek kapcsolótáblája |
| `price_data` | Technikai indiátor számításhoz (live, yfinance) |
| `price_data_alpaca` | Archive backtest ár-adatok (Alpaca, 15m) |
| `technical_indicators` | Kiszámított indikátorok tickerenként |
| `signals` | Generált szignálok (live) |
| `signal_calculations` | Audit trail: minden szignálhoz a számítási input/output |
| `archive_signals` | Historikus lezárt szignálok (optimizer input) |
| `simulated_trades` | Live szignálokhoz tartozó szimulált trade-ek |
| `archive_simulated_trades` | Archive szignálokhoz tartozó szimulált trade-ek |
| `api_quotas` | Hír-API rate limit nyilvántartás |
| `news_categories` | Hírkategória-cimkék |
| `optimizer_runs` | GA futtatások metaadatai |
| `optimizer_generations` | Generációnkénti fitness értékek |
| `config_proposals` | Jóváhagyásra váró konfigurációs javaslatok |

### 3.2 Tickers

| Mező | Típus | Leírás |
|------|-------|--------|
| `id` | PK | – |
| `symbol` | TEXT UNIQUE | Pl. `AAPL`, `OTP.BD` |
| `name` | TEXT | Teljes cégnév |
| `market` | TEXT | `US` / `BET` |
| `is_active` | BOOL | Aktív-e a szignálgenerálásban |
| `sector` | TEXT | Iparági szegmens |
| `relevance_keywords` | TEXT | Hírek szűréséhez kulcsszavak |

### 3.3 Signals

| Mező | Típus | Leírás |
|------|-------|--------|
| `id` | PK | – |
| `ticker_id` | FK | → tickers |
| `ticker_symbol` | TEXT | Denormalizált |
| `decision` | TEXT | `BUY` / `SELL` / `HOLD` |
| `strength` | TEXT | `STRONG` / `MODERATE` |
| `combined_score` | REAL | [-100, +100] |
| `overall_confidence` | REAL | [0.0, 1.0] |
| `entry_price` | REAL | Aktuális ár a szignál időpontjában |
| `stop_loss` | REAL | Javasolt SL ár |
| `take_profit` | REAL | Javasolt TP ár |
| `reasoning_json` | JSON | Kulcs hírek, indikátorok, score breakdown |
| `status` | TEXT | `active`, `closed`, `nogo`, `no_data` stb. |
| `calculated_at` | DATETIME | UTC |

### 3.4 SimulatedTrade / ArchiveSimulatedTrade

| Mező | Típus | Leírás |
|------|-------|--------|
| `id` | PK | – |
| `entry_signal_id` / `archive_signal_id` | FK | – |
| `ticker_symbol` | TEXT | – |
| `direction` | TEXT | `LONG` / `SHORT` |
| `status` | TEXT | `OPEN` / `CLOSED` |
| `entry_price` | REAL | Tényleges belépési ár |
| `entry_time` | DATETIME | Signal + 15 perc végrehajtási késés |
| `stop_loss_price` | REAL | Aktuális SL (dinamikusan frissülhet) |
| `take_profit_price` | REAL | Aktuális TP (szűkülhet) |
| `initial_stop_loss_price` | REAL | Eredeti SL (trailing SL számításhoz) |
| `initial_take_profit_price` | REAL | Eredeti TP |
| `exit_price` | REAL | Zárási ár |
| `exit_time` | DATETIME | – |
| `exit_reason` | TEXT | Ld. §6.3 |
| `pnl_percent` | REAL | Bruttó % P&L |
| `pnl_net_percent` | REAL | Nettó % P&L (0.2% round-trip fee levonva) |
| `duration_bars` | INT | 15m bar-ok száma |
| `combined_score` | REAL | Szignál score a trade nyitásakor |
| `overall_confidence` | REAL | – |
| `is_real_trade` | BOOL | `\|score\| >= 25` → valódi alert-szintű trade |
| `direction_2h_eligible` | BOOL | Volt-e értékelhető 2h-s ablak |
| `direction_2h_correct` | BOOL | Helyes irányba ment-e az ár 2 órán belül |
| `direction_2h_pct` | REAL | 2h-s ármozgás % |

### 3.5 SignalCalculations (audit trail)

Minden szignálhoz egy sor kerül mentésre az összes számítási paraméterrel, beleértve:
- Sentiment komponens bontás (raw score, decay, weighted)
- Technical komponens bontás (SMA, RSI, MACD, BB, Stoch, ADX, Volume)
- Risk komponens bontás
- Aktív konfigurációs értékek (46 paraméter)
- S/R szintek, ATR, SL/TP számítási módszer (`atr`, `sr`, `blended`, `capped`, `rr_target`)

---

## 4. Adatgyűjtés

### 4.1 Hírek gyűjtése

A `news_collector.py` az alábbi forrásokból gyűjt híreket tickerenként:

| Forrás | Típus | Prioritás |
|--------|-------|-----------|
| GNews API | REST, real-time | Elsődleges |
| Finnhub API | REST, tőzsdei fókusz | Elsődleges |
| Marketaux API | REST, fallback | Aktív ha friss < min küszöb |
| RSS feed | Szöveges, lassabb | Backup |

**Deduplikáció**: URL hash alapján, azonos hír több forrásból sem kerül kétszer tárolásra.

**Kategorizálás** (`news_categories`): earnings, macro, regulatory, product, analyst, other

### 4.2 Szentiment analízis

Két módszer, automatikus választással (`ScoreResolver`):

1. **FinBERT**: Transformer alapú pénzügyi szentiment modell → `[-1.0, +1.0]`
2. **LLM Context Checker** (opcionális, OpenRouter): Prompt-alapú elemzés → strukturált output:
   - `llm_score`: számszerű árhatás becslés `[-1.0, +1.0]`
   - `llm_price_impact`: `strong_up` / `up` / `neutral` / `down` / `strong_down`
   - `llm_impact_level`: 1–5 intenzitás
   - `llm_catalyst_type`: pl. `earnings`, `macro`, `regulatory`
   - `llm_priced_in`: már be van-e árazva

**Aktivált score** (`active_score`): ScoreResolver választja az elérhető módszerek közül.

### 4.3 Szentiment időbeli súlyozás (decay)

| Kor | Súly |
|-----|------|
| 0–2 óra | 1.00 |
| 2–6 óra | 0.85 |
| 6–12 óra | 0.60 |
| 12–24 óra | 0.35 |

24 óránál régebbi hírek nem számítanak bele a szignálba.

### 4.4 Ár-adatok

| Típus | Forrás | Granularitás | Felhasználás |
|-------|--------|-------------|--------------|
| Live | yfinance | 15m OHLCV | Szignálgenerálás, live backtest |
| Archive | Alpaca API | 15m OHLCV | Archive backtest, optimizer |

**Kereskedési idő ellenőrzés**:
- US: 14:30–21:00 UTC (hétfő–péntek)
- BÉT (`.BD`): 08:00–16:00 UTC (hétfő–péntek)

### 4.5 Technikai indikátorok

A `signal_generator.py` a következő indikátorokat számítja minden szignálhoz:

| Indikátor | Periódus | Felhasználás |
|-----------|---------|--------------|
| SMA | 20, 50, 200 | Trend irány |
| RSI | 14 | Túlvett/túladott |
| MACD | 12/26/9 | Momentum |
| Bollinger Bands | 20, 2σ | Volatilitás |
| ATR | 14 | SL/TP méretezés |
| Stochastic | %K, %D | Momentum |
| ADX | 14 | Trend erősség |
| Support/Resistance | DBSCAN | SL/TP blending |

---

## 5. Signal generálás

### 5.1 A folyamat

```
SignalGenerator.generate_signal(ticker, sentiment_data, technical_data, risk_data)
  │
  ├─ 1. Komponens score-ok normalizálása [-100, +100]
  ├─ 2. Dinamikus súlyozás (Config-ból)
  ├─ 3. Kombinált score számítás
  ├─ 4. Alignment bonus alkalmazás
  ├─ 5. R:R korrekció
  ├─ 6. Döntés és erősség meghatározás
  └─ 7. SL/TP szintek számítása
```

### 5.2 Score számítás

```
sentiment_contrib  = sentiment_score  × SENTIMENT_WEIGHT
technical_contrib  = technical_score  × TECHNICAL_WEIGHT
risk_contrib       = (risk_score - 50) × RISK_WEIGHT

base_combined = sentiment_contrib + technical_contrib + risk_contrib
```

**Alignment bonus** (±3 pont): Ha mindhárom komponens egyirányba mutat (mind BUY vagy mind SELL).

**R:R korrekció** (±1–±3 pont):
- Ha a TP az R:R minimum-kényszertől tolódott ki (`rr_target` módszer): −3 pont
- Ha természetes R:R ≥ 2.0: +1–+3 pont

### 5.3 Döntési küszöbök

| combined_score | Döntés | Strength |
|----------------|--------|---------|
| ≥ +50 | BUY | STRONG |
| +15 – +49 | BUY | MODERATE |
| −14 – +14 | HOLD | – |
| −49 – −15 | SELL | MODERATE |
| ≤ −50 | SELL | STRONG |

**HOLD zone határ**: `|score| < HOLD_ZONE_THRESHOLD` (alapértelmezett: 15)
**Alert küszöb**: `|score| >= 25` → valódi Telegram értesítés és `is_real_trade = True`

### 5.4 SL/TP számítás

#### Stop-Loss

**LONG (swing, több nap)**:
- ATR szorzó a konfidencia alapján:
  - Conf ≥ 0.75 → `atr_stop_high_conf` (alapért. 1.5×)
  - Conf 0.50–0.75 → `atr_stop_default` (alapért. 2.0×)
  - Conf < 0.50 → `atr_stop_low_conf` (alapért. 2.5×)
- Ha közel van support szint: blend az ATR SL és az S/R-alapú SL között

**SHORT (intraday)**:
- Szűkebb ATR szorzók (`short_atr_stop_*`, alapért. 0.5–1.0×)
- Max SL távolság: 1.5% (vs. LONG 5%)

**SL cap**: Max `entry × sl_max_pct` (LONG: 5%, SHORT: 1.5%)

#### Take-Profit

- ATR szorzó a volatilitás alapján:
  - Alacsony vol (ATR% < `vol_low_threshold`): `atr_tp_low_vol` (alapért. 2.5×)
  - Magas vol (ATR% > `vol_high_threshold`): `atr_tp_high_vol` (alapért. 4.0×)
  - Közte: lineáris interpoláció
- Ha közel van resistance szint: blend az ATR TP és az S/R-alapú TP között
- TP az S/R szint belső oldalán helyezkedik el (0.5% discount)

**Minimum R:R**: `MIN_RISK_REWARD = 1.5` – ha a természetes TP alatta marad, a TP kitolódik (de SL nem szűkül).

### 5.5 Szignál mentés

Minden szignálhoz két sor kerül mentésre:
1. `signals` tábla: az összesített döntés és szintek
2. `signal_calculations` tábla: teljes audit trail (46 konfigurációs paraméter, minden komponens részlete)

---

## 6. Trade szimuláció

### 6.1 Kanonikus exit logika (`trade_simulator_core.py`)

Minden exit szimuláció egyetlen kanonikus implementációra épül, amelyet az archive backtest, a live backtest és az optimizer egyaránt hív. Ha a szimulációs logikát módosítani kell, **kizárólag ezt a fájlt** kell szerkeszteni.

**Végrehajtási késleltetés**: Entry = signal timestamp utáni első kereskedési bar nyitóárán (+15 perc delay).

#### Exit prioritási sorrend (bar-onként)

| Prioritás | Típus | Feltétel |
|-----------|-------|---------|
| 1 | `STAGNATION_EXIT` | 10 egymást követő bar az entry ±(0.20 × initial_risk) sávban; csak 4 kereskedési óra (16 bar) grace period után aktivál |
| 2 | `SL_HIT` / `TP_HIT` | low ≤ SL (LONG) / high ≥ SL (SHORT); ütközésnél nyitóárhoz közelebb lévő nyer |
| 2b | TP tightening | Ár 50%+ úton TP felé: TP = close + 15% × initial_tp_range (csak szűkíthet) |
| 2b | Breakeven SL | Ár eléri entry + 1.0 × initial_risk: SL = entry × (1 ± round_trip_fee) [egyszer tüzel] |
| 2b | Kombinált re-check | TP tightening és/vagy breakeven után együttes SL/TP ellenőrzés adjudikációval |
| 3 | `OPPOSING_SIGNAL` | Ellentétes irányú alert-szintű szignál: +15 perces késleltetéssel zár |
| 4 | `EOD_AUTO_LIQUIDATION` | SHORT trade-ek kötelező nap végi zárása |
| 5 | `MAX_HOLD_LIQUIDATION` | 260 bar (10 kereskedési nap × 26 bar/nap) után kényszerzárás |

#### Dinamikus SL frissítés

- **Azonos irányú signal** (`|score| ≥ 25`): ha az új szignál SL kedvezőbb (LONG: magasabb, SHORT: alacsonyabb), az aktuális SL frissül → profit lock-in
- **EOD trailing SL** (csak LONG): nap végén `day_close × (1 − sl_pct)`, csak felfelé; a 3. naptól (`LONG_TRAILING_TIGHTEN_DAY`) szűkebb szorzóval

#### Breakeven SL részletei

- **Trigger**: ár eléri `entry + 1.0 × initial_risk` kedvező irányban
- **Új SL szint**:
  - LONG: `entry × (1 + 0.002)` → fedezi a 0.2% round-trip jutalékot
  - SHORT: `entry × (1 - 0.002)` → ugyanígy
- **Csak egyszer tüzel** (`be_applied` flag)

### 6.2 Live backtest (`backtest_service.py`)

Az aktív (live) szignálokhoz tartozó szimulált trade-eket kezeli a `simulated_trades` táblában.

```
BacktestService.run_backtest(date_from, date_to, symbols)
  │
  ├─ Query: NON-NEUTRAL signalok (|score| ≥ 15)
  ├─ Per signal:
  │   ├─ Ha CLOSED trade létezik: skip
  │   ├─ Ha OPEN trade: exit trigger ellenőrzés + SL/TP update
  │   └─ Ha nincs trade:
  │       ├─ is_real (|score| ≥ 25): TradeManager.open_position() [párhuzamos pozíció-ellenőrzéssel]
  │       └─ gyenge szignál (15–25): open_position_simulated() [ellenőrzés nélkül]
  └─ Commit
```

A live backtest **saját, párhuzamos implementációt** használ (nem delegál `trade_simulator_core`-ba), de azonos logikai szabályokat követ.

### 6.3 Archive backtest (`archive_backtest_service.py`)

A historikus `archive_signals` táblán futtatható teljes újraszimuláció.

```
ArchiveBacktestService.run(symbols, score_threshold=15.0)
  │
  ├─ Törli az előző futtatás eredményeit (archive_simulated_trades)
  ├─ Per ticker:
  │   ├─ Betölti az összes 15m bar-t memóriába
  │   ├─ Betölti az összes archive_signal-t
  │   ├─ Per signal:
  │   │   ├─ Entry: signal_ts utáni első kereskedési bar nyitóárán
  │   │   ├─ SL/TP: signal-ajánlott szintek arányosan igazítva az entry árhoz
  │   │   └─ Exit: trade_simulator_core.simulate_exit()
  │   └─ Bulk INSERT az eredmények
  └─ Összesített stats visszaadása
```

**Teljesítmény**: Tickerenkénti 1 DB lekérés, minden szimuláció memóriában fut.

### 6.4 Exit okok

| Kód | Leírás |
|-----|--------|
| `TP_HIT` | Take-profit elérve |
| `SL_HIT` | Stop-loss elérve (beleértve breakeven SL-t is) |
| `STAGNATION_EXIT` | Oldalazás 150 percen keresztül (4h grace után) |
| `OPPOSING_SIGNAL` | Ellentétes irányú alert érkezett |
| `EOD_AUTO_LIQUIDATION` | SHORT nap végi kötelező zárás |
| `MAX_HOLD_LIQUIDATION` | Maximális tartási idő elérve (10 kereskedési nap) |
| `OPEN` | Még nem zárt (nincs exit trigger) |

### 6.5 Teljesítmény-metrikák

Az API `/stats` végpontján elérhető összesítők:
- Win rate (TP / összes zárt trade)
- SL rate, stagnation rate, EOD rate
- Átlagos P&L%, legjobb/legrosszabb trade
- Profit factor (gross wins / gross losses)
- is_real vs. szimulált bontás
- 2H direction accuracy (volt-e helyes irányban a szignál 2 órán belül)

---

## 7. Optimizer (Genetikai Algoritmus)

### 7.1 Cél

Az optimizer megkeresi azt a 46 dimenziós konfigurációs vektort, amely maximalizálja a szimulált trade-ek fitness értékét az archivált szignálokon, anélkül hogy overfitting következne be.

### 7.2 Paramétertér (46 dimenzió)

| Csoport | Paraméterek | Db |
|---------|------------|-----|
| Szignál küszöb | HOLD_ZONE_THRESHOLD | 1 |
| LONG ATR SL szorzók | high_conf, default, low_conf | 3 |
| SHORT ATR SL szorzók | high_conf, default, low_conf | 3 |
| LONG ATR TP szorzók | low_vol, high_vol | 2 |
| SHORT ATR TP szorzók | low_vol, high_vol | 2 |
| Volatilitás küszöbök | vol_low, vol_high | 2 |
| S/R blending (SL) | support_soft_pct, support_hard_pct, buffer_atr_mult | 3 |
| S/R blending (TP) | resistance_soft_pct, resistance_hard_pct | 2 |
| LONG tartási paraméterek | max_hold_days, trailing_tighten_day, factor | 3 |
| Fő súlyok | SENTIMENT, TECHNICAL, RISK | 3 |
| Technikai sub-súlyok | SMA, RSI, MACD, BB, Stoch, Volume, ADX | 7 |
| Technikai detekció | RSI oversold/overbought, ADX strong, S/R paraméterek stb. | ~15 |

### 7.3 GA futtatás folyamata

```
genetic.py
  │
  ├─ 1. Adatbetöltés:
  │   ├─ signal_calculations (live szignálok, HOLD zone kizárva)
  │   ├─ archive_signals (max 4000 db)
  │   └─ price_data_alpaca: 45 nap lookahead per szignál
  │
  ├─ 2. Train/Val/Test split: 60% / 20% / 20%
  │
  ├─ 3. GA Loop (80 populáció × 100 generáció):
  │   ├─ Inicializálás: BASELINE_VECTOR körüli random vektorok
  │   ├─ Evaluáció (párhuzamos, CPU-onként):
  │   │   ├─ decode_vector() → config dict
  │   │   ├─ replay_and_simulate() → train + val fitness
  │   │   └─ fitness = min(train_fitness, val_fitness) [overfitting védelme]
  │   ├─ Szelekció: Tournament (k=3)
  │   ├─ Crossover: kétpontos (prob=0.70)
  │   ├─ Mutáció: Gauss (prob=0.20, σ=0.05 × tartomány)
  │   └─ Elitizmus: Top 2 megőrzése generációk között
  │
  └─ 4. Output:
      ├─ optimizer_generations: generációnkénti fitness
      ├─ optimizer_runs: futtatás metaadatai
      └─ config_proposals: rangsolt javaslatok review-ra
```

### 7.4 Fitness függvény

A fitness értékre épülő evaluáció a következő trade-szintű metrikákat kombinálja:
- Win rate súlyozva a P&L-lel
- Profit factor (gross gain / gross loss)
- Trade szám (min küszöb alatt penalizál)
- Drawndown elkerülés

### 7.5 Javaslat kapuk (Proposal Gates)

Egy `ConfigProposal` csak akkor kerülhet jóváhagyásra, ha minden kaput átmegy:

| Kapu | Feltétel |
|------|---------|
| `MIN_TRADES` | Test set ≥ 10 szimulált trade |
| `FITNESS_IMPROVEMENT` | test_fitness > baseline × 1.05 |
| `BOOTSTRAP_SIGNIFICANCE` | p-érték < 0.05 |
| `OVERFITTING` | train–val fitness gap < 30% |
| `PROFIT_FACTOR` | Test profit factor > 1.3 |
| `SIDEWAYS_REGIME` | Oldalazó piacon PF > 1.0 |
| `WALK_FORWARD` | 70%+ time window pozitív |

**Verdict értékek**: `PROPOSABLE` / `CONDITIONAL` / `REJECTED`

### 7.6 Jóváhagyási folyamat

1. Az optimizer `PROPOSABLE` verdiktű javaslatokat küld a frontend `/optimizer` oldalra
2. A felhasználó megtekinti a konfigurációs diff-et (baseline vs. javasolt)
3. `Approve` → az új config azonnal aktívvá válik (következő szignálgenerálástól él)
4. `Reject` → a javaslat elutasítva, a baseline config marad aktív

---

## 8. API Endpointok

### 8.1 Signals API (`/api/v1/signals`)

| Metódus | Útvonal | Leírás |
|---------|---------|--------|
| `POST` | `/generate` | Összes aktív ticker szignáljának generálása |
| `POST` | `/generate/{ticker}` | Egy ticker szignáljának generálása |
| `POST` | `/refresh` | Hírek + szignálok frissítése (background task) |
| `GET` | `/` | Aktív szignálok listája (status szűrővel) |
| `GET` | `/{signal_id}` | Egy szignál részletei |
| `GET` | `/history` | Szignál történet (dátum, döntés szűrőkkel) |
| `GET` | `/archive/history` | Archive szignálok (archive_signals tábla) |

### 8.2 Simulated Trades API (`/api/v1/simulated-trades`)

| Metódus | Útvonal | Leírás |
|---------|---------|--------|
| `POST` | `/backtest` | Live signal backtest futtatása |
| `POST` | `/archive-backtest` | Archive backtest futtatása (teljes újraszimuláció) |
| `GET` | `/` | Trade-ek listája (lapozással) |
| `GET` | `/{trade_id}` | Egy trade részletei |
| `GET` | `/stats` | Összesített performance metrikák |
| `GET` | `/open-pnl` | Nyitott pozíciók nem realizált P&L-je |

### 8.3 Configuration API (`/api/v1/config`)

| Metódus | Útvonal | Leírás |
|---------|---------|--------|
| `GET` | `/signal` | Aktív szignál konfiguráció |
| `POST` | `/signal` | Szignál konfiguráció módosítása |
| `GET` | `/technical` | Technikai indikátor paraméterek |
| `POST` | `/technical` | Technikai paraméterek módosítása |

### 8.4 Optimizer API (`/api/v1/optimizer`)

| Metódus | Útvonal | Leírás |
|---------|---------|--------|
| `GET` | `/status` | Futtatás státusza, legjobb fitness |
| `POST` | `/start` | GA futtatás indítása |
| `POST` | `/stop` | GA futtatás leállítása |
| `GET` | `/progress` | Generációnkénti progress, fitness görbe |
| `GET` | `/proposals` | Javaslatok listája (rang, verdict, review) |
| `GET` | `/proposals/{id}` | Javaslat részletei (config diff) |
| `POST` | `/proposals/{id}/approve` | Javaslat jóváhagyása → config aktiválás |
| `POST` | `/proposals/{id}/reject` | Javaslat elutasítása |

### 8.5 Tickers API (`/api/v1/tickers`)

| Metódus | Útvonal | Leírás |
|---------|---------|--------|
| `GET` | `/` | Tickerek listája |
| `POST` | `/` | Új ticker hozzáadása |
| `GET` | `/{id}` | Ticker részletei |
| `PUT` | `/{id}` | Ticker módosítása (keywords, sources) |
| `DELETE` | `/{id}` | Ticker deaktiválása |

---

## 9. Frontend

### 9.1 Oldalak

| Oldal | Útvonal | Funkció |
|-------|---------|---------|
| **Dashboard** | `/` | Aktív szignálok kártya-nézetben; döntés/erősség szűrők; frissítés gomb |
| **Signal History** | `/history` | Szignál- és trade-történet táblázatban; archive + live váltás; P&L összesítők; backtest trigger |
| **Signal Detail** | `/signal/:id` | Teljes szignál info: reasoning breakdown, komponens score-ok, simulated trade státusz és P&L |
| **News Feed** | `/news` | Feldolgozott hírek szentimental és relevancia értékkel; forrás és kategória szűrők |
| **Optimizer** | `/optimizer` | GA futtatás indítás/leállítás; fitness görbe (generációnként); proposals lista; approval UI |
| **Configuration** | `/settings` | Konfigurációs értékek szerkesztése: súlyok, küszöbök, hírforrások |

### 9.2 Adatlekérési réteg

A frontend TanStack React Query-vel kéri az adatokat:
- `useSignals()` — aktív szignálok, auto-refresh
- `useSignalHistory()` — szignál/trade történet
- `useSimulatedTrades()` — trade lista és stats
- `useOptimizerStatus()` — GA státusz polling

### 9.3 Főbb TypeScript típusok

```typescript
// Core
Ticker, NewsItem, Signal, TechnicalIndicators, SentimentSnapshot

// Trade szimuláció
SimulatedTrade, TradeExit, PerformanceMetrics, PerformanceByTicker

// Optimizer
OptimizerRun, ConfigProposal, OptimizerProgress,
GenerationRow, RegimeStats, WalkForwardWindow
```

---

## 10. Automatizálás és ütemezés

### 10.1 Scheduler (APScheduler)

Az alkalmazás indításakor (`api.py` lifespan hook) az `AsyncIOScheduler` elindul és registrálja a következő trigger-t:

| Trigger | Cron | Funkció |
|---------|------|---------|
| Szignálgenerálás | `0 14-20 * * 1-5` (UTC) | `generate_signals_for_active_markets()` |

**Eredmény**: 14:00–20:59 UTC között minden egész percen (percenként egyszer) fut a szignálgeneráló, de a belső logika (`is_us_market_open()`, `is_bet_open()`) szűri, hogy tényleg kereskedési időben van-e.

### 10.2 Szignálgenerálás folyamata (automatikus)

```
[APScheduler tüzel]
  ↓
generate_signals_for_active_markets()
  ├─ is_bet_open() → BÉT tickerek
  ├─ is_us_market_open() → US tickerek
  └─ run_batch_analysis(active_tickers)
      ├─ news_collector.collect_news(ticker)
      ├─ sentiment_analyzer.analyze(news)
      ├─ price_service.get_ohlcv(ticker)
      ├─ signal_generator.generate_signal(ticker, ...)
      └─ save_signal_to_db() + BacktestService.create_trade()
```

### 10.3 Manuális triggerek

- `POST /api/v1/signals/refresh` — Azonnali frissítés a frontend-ről
- `POST /api/v1/simulated-trades/backtest` — Live backtest manuális futtatása
- `POST /api/v1/simulated-trades/archive-backtest` — Archive backtest futtatása
- `POST /api/v1/optimizer/start` — GA futtatás indítása

---

## 11. Konfiguráció

### 11.1 Konfigurációs rétegek

A rendszer konfigurálható paramétereit két szinten tárolja:

1. **Adatbázis-szintű konfiguráció** (`signal_config` tábla): futásidőben módosítható súlyok, küszöbök — az optimizer által javasolt és jóváhagyott értékek ide kerülnek.
2. **Kód-szintű konstansok** (`trade_simulator_core.py`, `backtest_service.py`): szimulációs konstansok, amelyek módosítása mindkét rendszerben egyszerre érvényesül.

### 11.2 Szimulációs konstansok

| Konstans | Érték | Leírás |
|----------|-------|--------|
| `ALERT_THRESHOLD` | 25 | Valódi alert és is_real_trade küszöb |
| `SIGNAL_THRESHOLD` | 15 | HOLD zone határa |
| `MAX_HOLD_BARS` | 260 | 10 kereskedési nap (10 × 26 bar) |
| `STAGNATION_CONSECUTIVE_SLOTS` | 10 | 150 perc oldalazás → exit |
| `STAGNATION_BAND_FACTOR` | 0.20 | Sáv = 20% × initial_risk |
| `STAGNATION_GRACE_BARS` | 16 | 4 kereskedési óra grace period |
| `BREAKEVEN_FEE_PCT` | 0.002 | Round-trip jutalék a breakeven SL-hez |
| `SL_MAX_PCT` | 0.05 | Max SL távolság LONG-nál (5%) |
| `SHORT_SL_MAX_PCT` | 0.015 | Max SL távolság SHORT-nál (1.5%) |
| `MIN_RISK_REWARD` | 1.5 | Minimum R:R kényszer |
| `TRADE_FEE_PCT` | 0.002 | Round-trip díj (P&L számításban) |

### 11.3 Konfigurációs szinkronizáció

**Fontos**: A `trade_simulator_core.py` az egyetlen kanonikus szimulációs implementáció. Az `archive_backtest_service.py` és az `optimizer/trade_simulator.py` ezt hívja. A `backtest_service.py` (live szimuláció) párhuzamos, de azonos logikát alkalmaz. Szimulációs logika módosításakor **mindkét helyen** kell frissíteni.
