# TrendSignal Trackback System - Működési és Műszaki Terv

**Verzió:** 1.0  
**Dátum:** 2025-02-07  
**Szerző:** Zsolt & Claude  
**Cél:** Sentiment-alapú trading szignálok historikus teljesítményének szimulációja

---

## 1. Áttekintés

### 1.1 Rendszer célja
A Trackback System célja a TrendSignal által generált BUY/SELL szignálok utólagos szimulálása valós piaci körülmények között. A rendszer automatikusan nyit/zár pozíciókat a szignálok alapján, figyelembe véve a 15 perces reakcióidőt, stop-loss/take-profit szinteket, és ellentétes szignálokat.

### 1.2 Scope
- **Támogatott pozíciók**: Long (BUY szignálok), Short csak daytrade (auto-likvidálás EOD)
- **Támogatott tickerek**: MOL.BD, OTP.BD, AAPL, TSLA, MSFT, NVDA, AMZN, META, IBM
- **Szignál típusok**: Csak NON-NEUTRAL szignálok (BUY >= 25, SELL <= -25)
- **Position sizing**: ~700,000 HUF fix érték (min. trading fee limit elkerülése)
- **Végrehajtás**: 15 perces késleltetéssel (realisztikus reakcióidő)

### 1.3 Kizárások
- **Sentiment degradáció NEM exit reason** (nem likvidálási ok)
- **Multi-position**: 1 ticker = maximum 1 nyitott pozíció egyidejűleg
- **Leverage**: Nincs tőkeáttétel kalkuláció
- **Trading fees**: Jelenleg nem számoljuk (későbbi bővítési lehetőség)

---

## 2. Üzleti Szabályok

### 2.1 Pozíció Nyitás (Entry)

#### 2.1.1 Előfeltételek
1. **Új szignál generálódott** (NON-NEUTRAL: combined_score >= 25 vagy <= -25)
2. **Nincs nyitott pozíció** az adott tickerre
3. **Piaci órák**: Trading hours alatt generálódott szignál
4. **Adathozzáférés**: 5 perces gyertyák elérhetők az execution time-ra

#### 2.1.2 Végrehajtási időzítés
```
Szignál generálás:     T0 (pl. 2025-01-15 11:00:00)
Execution time:        T0 + 15 perc (11:15:00)
Entry price:           11:15:00-hoz legközelebbi 5min gyertya close ára
```

#### 2.1.3 Pozíció irány meghatározás
- **combined_score >= 25** → **LONG** pozíció (BUY)
- **combined_score <= -25** → **SHORT** pozíció (SELL)
  - ⚠️ SHORT csak daytrade: auto-likvidálás EOD 16:45-kor

#### 2.1.4 Position Sizing
```python
TARGET_POSITION_VALUE_HUF = 700_000

# USD ticker esetén (AAPL, TSLA, MSFT, etc.)
usd_huf_rate = get_current_exchange_rate()
target_value_usd = TARGET_POSITION_VALUE_HUF / usd_huf_rate
shares = floor(target_value_usd / entry_price)

# HUF ticker esetén (MOL.BD, OTP.BD)
shares = floor(TARGET_POSITION_VALUE_HUF / entry_price)
```

#### 2.1.5 Stop-Loss és Take-Profit rögzítés
**Belépéskor EGYSZER rögzítjük**, később nem változik:
```python
# Signal által számolt értékek
stop_loss_price = signal.stop_loss
take_profit_price = signal.take_profit

# LONG pozíció esetén
assert stop_loss_price < entry_price < take_profit_price

# SHORT pozíció esetén
assert take_profit_price < entry_price < stop_loss_price
```

---

### 2.2 Pozíció Zárás (Exit)

#### 2.2.1 Exit Triggerek (prioritási sorrendben)

##### **1. STOP-LOSS (legmagasabb prioritás)**
```python
# LONG
if current_price <= stop_loss_price:
    trigger_exit(reason="SL_HIT")

# SHORT
if current_price >= stop_loss_price:
    trigger_exit(reason="SL_HIT")
```

##### **2. TAKE-PROFIT**
```python
# LONG
if current_price >= take_profit_price:
    trigger_exit(reason="TP_HIT")

# SHORT
if current_price <= take_profit_price:
    trigger_exit(reason="TP_HIT")
```

##### **3. ELLENTÉTES SZIGNÁL**
```python
# LONG pozícióban vagyunk
if new_signal.direction == "SELL" and new_signal.combined_score <= -25:
    trigger_exit(reason="OPPOSING_SIGNAL")

# SHORT pozícióban vagyunk
if new_signal.direction == "BUY" and new_signal.combined_score >= 25:
    trigger_exit(reason="OPPOSING_SIGNAL")
```

##### **4. EOD AUTO-LIKVIDÁLÁS (csak SHORT)**
```python
# Minden nap 16:45-kor (US market close előtt 15 perccel)
if position.direction == "SHORT" and current_time >= "16:45:00":
    trigger_exit(reason="EOD_AUTO_LIQUIDATION")
```

#### 2.2.2 Végrehajtási időzítés
```
Trigger detektálás:    T1 (pl. 2025-01-16 14:30:00)
Execution time:        T1 + 15 perc (14:45:00)
Exit price:            14:45:00-hoz legközelebbi 5min gyertya close ára
```

#### 2.2.3 Ha több trigger egyszerre
Ha ugyanabban a 15 perces időablakban több trigger is teljesül:
1. **SL_HIT** (legfontosabb - veszteségvédelem)
2. **TP_HIT** (nyereség realizálás)
3. **OPPOSING_SIGNAL** (stratégiai váltás)
4. **EOD_AUTO_LIQUIDATION** (kényszerítés)

---

### 2.3 P&L Számítás

```python
# LONG pozíció
pnl_percent = ((exit_price - entry_price) / entry_price) * 100
pnl_amount_huf = (exit_price - entry_price) * shares * (usd_huf_rate if USD else 1)

# SHORT pozíció
pnl_percent = ((entry_price - exit_price) / entry_price) * 100
pnl_amount_huf = (entry_price - exit_price) * shares * (usd_huf_rate if USD else 1)

# Duration
duration_minutes = (exit_execution_time - entry_execution_time).total_seconds() / 60
```

---

## 3. Adatbázis Séma

### 3.1 Új tábla: `simulated_trades`

```sql
CREATE TABLE simulated_trades (
    -- Primary Key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Pozíció azonosítók
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
    status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED')),
    
    -- Belépés információk
    entry_signal_id INTEGER NOT NULL,
    entry_signal_generated_at TIMESTAMP NOT NULL,
    entry_execution_time TIMESTAMP NOT NULL,
    entry_price REAL NOT NULL,
    entry_score REAL NOT NULL,
    entry_confidence REAL NOT NULL,
    
    -- Stop-Loss és Take-Profit (fix, belépéskor rögzített)
    stop_loss_price REAL NOT NULL,
    take_profit_price REAL NOT NULL,
    
    -- Pozíció méret
    position_size_shares INTEGER NOT NULL,
    position_value_huf REAL NOT NULL,
    usd_huf_rate REAL,  -- NULL if HUF ticker
    
    -- Kilépés információk (NULL ha status='OPEN')
    exit_trigger_time TIMESTAMP,
    exit_execution_time TIMESTAMP,
    exit_price REAL,
    exit_reason TEXT CHECK(exit_reason IN (
        'SL_HIT', 
        'TP_HIT', 
        'OPPOSING_SIGNAL', 
        'EOD_AUTO_LIQUIDATION',
        NULL
    )),
    exit_signal_id INTEGER,
    exit_score REAL,
    exit_confidence REAL,
    
    -- P&L kalkuláció
    pnl_percent REAL,
    pnl_amount_huf REAL,
    
    -- Időtartam
    duration_minutes INTEGER,
    
    -- Audit mezők
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (entry_signal_id) REFERENCES signals(id) ON DELETE CASCADE,
    FOREIGN KEY (exit_signal_id) REFERENCES signals(id) ON DELETE SET NULL
);

-- Indexek a gyors querying-hez
CREATE INDEX idx_simtrades_symbol ON simulated_trades(symbol);
CREATE INDEX idx_simtrades_status ON simulated_trades(status);
CREATE INDEX idx_simtrades_direction ON simulated_trades(direction);
CREATE INDEX idx_simtrades_entry_exec ON simulated_trades(entry_execution_time);
CREATE INDEX idx_simtrades_exit_exec ON simulated_trades(exit_execution_time);
CREATE INDEX idx_simtrades_exit_reason ON simulated_trades(exit_reason);
CREATE INDEX idx_simtrades_created_at ON simulated_trades(created_at);

-- Composite index a gyakori filterekhez
CREATE INDEX idx_simtrades_symbol_status ON simulated_trades(symbol, status);
```

### 3.2 Új tábla trigger: Auto-update timestamp

```sql
CREATE TRIGGER update_simtrades_timestamp 
AFTER UPDATE ON simulated_trades
FOR EACH ROW
BEGIN
    UPDATE simulated_trades 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;
```

---

## 4. Backend Architektúra

### 4.1 Új modulok

#### 4.1.1 `app/models/simulated_trade.py`
```python
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class SimulatedTrade(Base):
    __tablename__ = "simulated_trades"
    
    # Fields as per DB schema above
    
    # Relationships
    entry_signal = relationship("Signal", foreign_keys=[entry_signal_id])
    exit_signal = relationship("Signal", foreign_keys=[exit_signal_id])
    
    # Computed properties
    @property
    def is_open(self):
        return self.status == "OPEN"
    
    @property
    def is_profitable(self):
        return self.pnl_percent and self.pnl_percent > 0
    
    @property
    def unrealized_pnl(self):
        """Számolás OPEN pozíciókhoz current price alapján"""
        if self.status == "CLOSED":
            return None
        # Logic to fetch current price and calculate
```

#### 4.1.2 `app/services/trade_manager.py`
```python
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.simulated_trade import SimulatedTrade
from app.models.signal import Signal
from app.services.price_service import get_5min_candle_at_time

class TradeManager:
    """
    Központi osztály a trade lifecycle kezelésére
    """
    
    def open_position(self, db: Session, signal: Signal) -> SimulatedTrade:
        """
        Új pozíció nyitása signal alapján
        
        Args:
            db: Database session
            signal: Signal object (non-neutral, >= 25 or <= -25)
        
        Returns:
            SimulatedTrade object
        
        Raises:
            PositionAlreadyExistsError: Ha már van open pozíció erre a tickerre
            InsufficientDataError: Ha nincs 5min candle az execution time-ra
        """
        # 1. Check if position already exists
        existing = db.query(SimulatedTrade).filter(
            SimulatedTrade.symbol == signal.symbol,
            SimulatedTrade.status == "OPEN"
        ).first()
        
        if existing:
            raise PositionAlreadyExistsError(f"Open position exists for {signal.symbol}")
        
        # 2. Calculate execution time
        execution_time = signal.generated_at + timedelta(minutes=15)
        
        # 3. Get entry price from 5min candle
        candle = get_5min_candle_at_time(signal.symbol, execution_time)
        if not candle:
            raise InsufficientDataError(f"No 5min candle for {signal.symbol} at {execution_time}")
        
        entry_price = candle.close
        
        # 4. Determine direction
        direction = "LONG" if signal.combined_score >= 25 else "SHORT"
        
        # 5. Calculate position size
        position_size, position_value, usd_huf = self._calculate_position_size(
            signal.symbol, entry_price
        )
        
        # 6. Create trade record
        trade = SimulatedTrade(
            symbol=signal.symbol,
            direction=direction,
            status="OPEN",
            entry_signal_id=signal.id,
            entry_signal_generated_at=signal.generated_at,
            entry_execution_time=execution_time,
            entry_price=entry_price,
            entry_score=signal.combined_score,
            entry_confidence=signal.confidence,
            stop_loss_price=signal.stop_loss,
            take_profit_price=signal.take_profit,
            position_size_shares=position_size,
            position_value_huf=position_value,
            usd_huf_rate=usd_huf
        )
        
        db.add(trade)
        db.commit()
        db.refresh(trade)
        
        return trade
    
    def check_exit_triggers(self, db: Session, trade: SimulatedTrade) -> dict:
        """
        Ellenőrzi az exit triggereket egy open pozícióra
        
        Returns:
            {
                "should_exit": bool,
                "reason": str,  # "SL_HIT", "TP_HIT", "OPPOSING_SIGNAL", "EOD_AUTO_LIQUIDATION"
                "exit_signal_id": int or None
            }
        """
        current_time = datetime.now()
        current_price = self._get_current_price(trade.symbol)
        
        # 1. Check STOP-LOSS (highest priority)
        if trade.direction == "LONG" and current_price <= trade.stop_loss_price:
            return {"should_exit": True, "reason": "SL_HIT", "exit_signal_id": None}
        
        if trade.direction == "SHORT" and current_price >= trade.stop_loss_price:
            return {"should_exit": True, "reason": "SL_HIT", "exit_signal_id": None}
        
        # 2. Check TAKE-PROFIT
        if trade.direction == "LONG" and current_price >= trade.take_profit_price:
            return {"should_exit": True, "reason": "TP_HIT", "exit_signal_id": None}
        
        if trade.direction == "SHORT" and current_price <= trade.take_profit_price:
            return {"should_exit": True, "reason": "TP_HIT", "exit_signal_id": None}
        
        # 3. Check OPPOSING SIGNAL
        opposing_signal = self._get_latest_opposing_signal(db, trade)
        if opposing_signal:
            return {
                "should_exit": True, 
                "reason": "OPPOSING_SIGNAL", 
                "exit_signal_id": opposing_signal.id
            }
        
        # 4. Check EOD AUTO-LIQUIDATION (SHORT only)
        if trade.direction == "SHORT" and current_time.time() >= time(16, 45):
            return {"should_exit": True, "reason": "EOD_AUTO_LIQUIDATION", "exit_signal_id": None}
        
        return {"should_exit": False, "reason": None, "exit_signal_id": None}
    
    def close_position(self, db: Session, trade: SimulatedTrade, exit_info: dict) -> SimulatedTrade:
        """
        Pozíció zárása
        
        Args:
            trade: Open SimulatedTrade object
            exit_info: Dict from check_exit_triggers()
        """
        exit_trigger_time = datetime.now()
        exit_execution_time = exit_trigger_time + timedelta(minutes=15)
        
        # Get exit price
        candle = get_5min_candle_at_time(trade.symbol, exit_execution_time)
        exit_price = candle.close
        
        # Calculate P&L
        if trade.direction == "LONG":
            pnl_percent = ((exit_price - trade.entry_price) / trade.entry_price) * 100
            pnl_amount = (exit_price - trade.entry_price) * trade.position_size_shares
        else:  # SHORT
            pnl_percent = ((trade.entry_price - exit_price) / trade.entry_price) * 100
            pnl_amount = (trade.entry_price - exit_price) * trade.position_size_shares
        
        # Convert to HUF if USD ticker
        if trade.usd_huf_rate:
            pnl_amount_huf = pnl_amount * trade.usd_huf_rate
        else:
            pnl_amount_huf = pnl_amount
        
        # Duration
        duration_minutes = (exit_execution_time - trade.entry_execution_time).total_seconds() / 60
        
        # Update trade
        trade.status = "CLOSED"
        trade.exit_trigger_time = exit_trigger_time
        trade.exit_execution_time = exit_execution_time
        trade.exit_price = exit_price
        trade.exit_reason = exit_info["reason"]
        trade.exit_signal_id = exit_info["exit_signal_id"]
        trade.pnl_percent = pnl_percent
        trade.pnl_amount_huf = pnl_amount_huf
        trade.duration_minutes = int(duration_minutes)
        
        # Get exit signal details if available
        if trade.exit_signal_id:
            exit_signal = db.query(Signal).get(trade.exit_signal_id)
            trade.exit_score = exit_signal.combined_score
            trade.exit_confidence = exit_signal.confidence
        
        db.commit()
        db.refresh(trade)
        
        return trade
    
    def _calculate_position_size(self, symbol: str, entry_price: float) -> tuple:
        """
        Position sizing calculation
        
        Returns:
            (shares, position_value_huf, usd_huf_rate)
        """
        TARGET_VALUE_HUF = 700_000
        
        if symbol.endswith(".BD"):  # HUF ticker
            shares = int(TARGET_VALUE_HUF / entry_price)
            return shares, shares * entry_price, None
        else:  # USD ticker
            usd_huf_rate = self._get_usd_huf_rate()
            target_value_usd = TARGET_VALUE_HUF / usd_huf_rate
            shares = int(target_value_usd / entry_price)
            position_value_huf = shares * entry_price * usd_huf_rate
            return shares, position_value_huf, usd_huf_rate
    
    def _get_usd_huf_rate(self) -> float:
        """Get current USD/HUF exchange rate"""
        # Implementation: yfinance or other source
        pass
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current market price"""
        # Implementation: latest 5min candle close
        pass
    
    def _get_latest_opposing_signal(self, db: Session, trade: SimulatedTrade) -> Signal:
        """
        Check if there's a recent opposing signal
        
        Returns Signal object or None
        """
        if trade.direction == "LONG":
            # Looking for SELL signal with score <= -25
            signal = db.query(Signal).filter(
                Signal.symbol == trade.symbol,
                Signal.combined_score <= -25,
                Signal.generated_at > trade.entry_execution_time
            ).order_by(Signal.generated_at.desc()).first()
        else:  # SHORT
            # Looking for BUY signal with score >= 25
            signal = db.query(Signal).filter(
                Signal.symbol == trade.symbol,
                Signal.combined_score >= 25,
                Signal.generated_at > trade.entry_execution_time
            ).order_by(Signal.generated_at.desc()).first()
        
        return signal
```

#### 4.1.3 `app/services/price_service.py`
```python
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.price_data import PriceData

def get_5min_candle_at_time(symbol: str, target_time: datetime) -> PriceData:
    """
    Get the closest 5min candle at or before target_time
    
    Args:
        symbol: Ticker symbol
        target_time: Target datetime
    
    Returns:
        PriceData object or None
    """
    # Query 5min candles
    candle = db.query(PriceData).filter(
        PriceData.symbol == symbol,
        PriceData.interval == "5m",
        PriceData.timestamp <= target_time
    ).order_by(PriceData.timestamp.desc()).first()
    
    return candle

def get_current_price(symbol: str) -> float:
    """
    Get current market price (latest 5min candle close)
    """
    latest = db.query(PriceData).filter(
        PriceData.symbol == symbol,
        PriceData.interval == "5m"
    ).order_by(PriceData.timestamp.desc()).first()
    
    return latest.close if latest else None
```

#### 4.1.4 `app/scheduler/trade_executor.py`
```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.trade_manager import TradeManager
from app.database import SessionLocal

def check_and_execute_trades():
    """
    15 percenként futó job:
    1. Ellenőrzi az open pozíciókat (exit triggerek)
    2. Zár pozíciókat ha kell
    """
    db = SessionLocal()
    trade_manager = TradeManager()
    
    try:
        # Get all open positions
        open_trades = db.query(SimulatedTrade).filter(
            SimulatedTrade.status == "OPEN"
        ).all()
        
        for trade in open_trades:
            # Check exit triggers
            exit_info = trade_manager.check_exit_triggers(db, trade)
            
            if exit_info["should_exit"]:
                # Close position
                trade_manager.close_position(db, trade, exit_info)
                print(f"Closed {trade.symbol} {trade.direction} - {exit_info['reason']}")
    
    finally:
        db.close()

def on_signal_generated(signal: Signal):
    """
    Signal generálás után hívódik meg
    Automatikusan nyit pozíciót, ha feltételek teljesülnek
    """
    db = SessionLocal()
    trade_manager = TradeManager()
    
    try:
        # Only non-neutral signals
        if abs(signal.combined_score) >= 25:
            # Try to open position
            trade = trade_manager.open_position(db, signal)
            print(f"Opened {trade.symbol} {trade.direction} @ {trade.entry_price}")
    
    except PositionAlreadyExistsError:
        print(f"Position already exists for {signal.symbol}")
    
    finally:
        db.close()

# Scheduler setup
scheduler = BackgroundScheduler()
scheduler.add_job(
    check_and_execute_trades,
    'cron',
    minute='*/15',  # Every 15 minutes
    id='trade_executor'
)
```

---

### 4.2 API Endpoints

#### 4.2.1 `GET /api/simulated-trades`
**Lista simulated trades-ekről szűrési lehetőségekkel**

**Query Parameters:**
- `symbol` (optional): Filter by ticker
- `status` (optional): "OPEN" | "CLOSED" | "ALL"
- `direction` (optional): "LONG" | "SHORT" | "ALL"
- `profitable` (optional): true | false (csak CLOSED trades-re)
- `exit_reason` (optional): "SL_HIT" | "TP_HIT" | "OPPOSING_SIGNAL" | "EOD_AUTO_LIQUIDATION"
- `date_from` (optional): ISO date (entry_execution_time >= date_from)
- `date_to` (optional): ISO date (entry_execution_time <= date_to)
- `limit` (optional, default=50): Max results
- `offset` (optional, default=0): Pagination offset

**Response:**
```json
{
  "total": 38,
  "trades": [
    {
      "id": 1,
      "symbol": "TSLA",
      "direction": "LONG",
      "status": "OPEN",
      "entry": {
        "signal_id": 123,
        "generated_at": "2025-02-01T11:00:00Z",
        "execution_time": "2025-02-01T11:15:00Z",
        "price": 195.50,
        "score": 72.5,
        "confidence": 0.71
      },
      "stop_loss": 191.20,
      "take_profit": 201.80,
      "position_size_shares": 500,
      "position_value_huf": 690500,
      "current_price": 197.84,
      "unrealized_pnl_percent": 1.2,
      "unrealized_pnl_huf": 8280,
      "duration_minutes": 7200
    },
    {
      "id": 2,
      "symbol": "AAPL",
      "direction": "LONG",
      "status": "CLOSED",
      "entry": {
        "signal_id": 98,
        "generated_at": "2025-01-28T10:00:00Z",
        "execution_time": "2025-01-28T10:15:00Z",
        "price": 182.30,
        "score": 68.2,
        "confidence": 0.65
      },
      "exit": {
        "trigger_time": "2025-01-30T14:30:00Z",
        "execution_time": "2025-01-30T14:45:00Z",
        "price": 178.90,
        "reason": "SL_HIT",
        "signal_id": null,
        "score": null,
        "confidence": null
      },
      "stop_loss": 179.00,
      "take_profit": 188.50,
      "pnl_percent": -1.9,
      "pnl_huf": -12300,
      "duration_minutes": 2850
    }
  ],
  "stats": {
    "total_trades": 38,
    "open_positions": 3,
    "closed_trades": 35,
    "win_rate": 62.5,
    "wins": 24,
    "losses": 14,
    "total_pnl_percent": 12.4,
    "avg_hold_duration_days": 2.3
  }
}
```

#### 4.2.2 `GET /api/simulated-trades/{trade_id}`
**Részletes információ egy trade-ről**

**Response:**
```json
{
  "id": 2,
  "symbol": "AAPL",
  "direction": "LONG",
  "status": "CLOSED",
  "entry": {
    "signal_id": 98,
    "signal_details": {
      "combined_score": 68.2,
      "sentiment_score": 78,
      "technical_score": 55,
      "risk_score": 72,
      "confidence": 0.65,
      "news_count": 8,
      "avg_sentiment": 0.42
    },
    "generated_at": "2025-01-28T10:00:00Z",
    "execution_time": "2025-01-28T10:15:00Z",
    "price": 182.30
  },
  "exit": {
    "trigger_time": "2025-01-30T14:30:00Z",
    "execution_time": "2025-01-30T14:45:00Z",
    "price": 178.90,
    "reason": "SL_HIT",
    "signal_id": null
  },
  "risk_management": {
    "stop_loss": 179.00,
    "take_profit": 188.50,
    "risk_reward_ratio": 1.83
  },
  "position": {
    "size_shares": 540,
    "value_huf": 692400,
    "usd_huf_rate": 385.5
  },
  "pnl": {
    "percent": -1.9,
    "amount_huf": -12300,
    "duration_minutes": 2850,
    "duration_formatted": "2d 0h 30m"
  }
}
```

#### 4.2.3 `POST /api/simulated-trades/backtest`
**Historikus backtest futtatása megadott időszakra**

**Request Body:**
```json
{
  "symbols": ["AAPL", "TSLA", "MSFT"],
  "date_from": "2025-01-01",
  "date_to": "2025-02-01",
  "clear_existing": false
}
```

**Response:**
```json
{
  "status": "completed",
  "processed_signals": 142,
  "opened_trades": 38,
  "skipped_signals": 104,
  "skip_reasons": {
    "position_already_open": 67,
    "insufficient_data": 23,
    "neutral_signal": 14
  },
  "execution_time_seconds": 4.2
}
```

#### 4.2.4 `DELETE /api/simulated-trades/clear`
**Összes simulated trade törlése (reset)**

**Query Parameters:**
- `confirm` (required): "yes" (safety check)

**Response:**
```json
{
  "status": "success",
  "deleted_trades": 38
}
```

---

## 5. Frontend Komponensek

### 5.1 Új route: `/simulated-trades`

#### 5.1.1 `SimulatedTradesPage.tsx`
**Főoldal a mockup alapján**

**Funkciók:**
- Stats Cards (Total Trades, Win Rate, Total P&L, Avg Hold)
- Filter bar (Symbol, Status, Date Range)
- Trade lista tábla
- Expandable details minden trade-hez
- Pagination
- Legend

#### 5.1.2 `TradeDetailModal.tsx`
**Kattintható modal a teljes trade részletekkel**

**Tartalom:**
- Entry Signal Details (score breakdown, news summary)
- Exit Signal Details (if applicable)
- Risk Management (SL/TP, R:R ratio)
- Position Info (shares, value)
- P&L breakdown

#### 5.1.3 `TradeStatsCard.tsx`
**Statisztika kártyák a header-ben**

#### 5.1.4 `TradeTable.tsx`
**Trade lista reusable komponens**

---

## 6. Implementációs Ütemterv

### Phase 1: Database & Models (1-2 óra)
1. ✅ DB migráció: `simulated_trades` tábla létrehozása
2. ✅ SQLAlchemy model: `SimulatedTrade`
3. ✅ Trigger setup: auto-update timestamp

### Phase 2: Core Backend Services (3-4 óra)
1. ✅ `trade_manager.py`: Teljes TradeManager osztály
2. ✅ `price_service.py`: Price fetch utilities
3. ✅ Unit tesztek: TradeManager metódusok

### Phase 3: Scheduler Integration (2-3 óra)
1. ✅ `trade_executor.py`: 15 perces job setup
2. ✅ Signal generálás hook: automatikus pozíció nyitás
3. ✅ Logging és error handling

### Phase 4: API Endpoints (2-3 óra)
1. ✅ `GET /api/simulated-trades` + filtering
2. ✅ `GET /api/simulated-trades/{id}` + details
3. ✅ `POST /api/simulated-trades/backtest`
4. ✅ `DELETE /api/simulated-trades/clear`

### Phase 5: Frontend UI (4-5 óra)
1. ✅ `SimulatedTradesPage.tsx` + routing
2. ✅ `TradeTable.tsx` komponens
3. ✅ `TradeDetailModal.tsx` komponens
4. ✅ Filter bar + stats cards
5. ✅ Pagination logic

### Phase 6: Testing & Refinement (2-3 óra)
1. ✅ End-to-end test: signal → trade open → trade close
2. ✅ Edge case testing (multi-trigger, data gaps)
3. ✅ Performance optimization (DB query tuning)
4. ✅ UI polish (loading states, error messages)

**Teljes becsült idő: 14-20 óra**

---

## 7. Tesztelési Forgatókönyvek

### 7.1 Happy Path Tests

#### Test 1: BUY → TP Hit
```
1. BUY signal generálódik (score=72, conf=0.71)
2. 15 perc múlva position nyílik @ $100
3. SL=$95, TP=$108
4. 2 nap múlva ár eléri $108
5. 15 perc delay után pozíció zárul @ $108.20
6. P&L: +8.2%
```

#### Test 2: BUY → SL Hit
```
1. BUY signal (score=65)
2. Position open @ $100
3. SL=$95, TP=$107
4. Rossz hírek, ár esik $94.80-ra
5. SL trigger → 15 perc delay → exit @ $94.50
6. P&L: -5.5%
```

#### Test 3: BUY → Opposing SELL Signal
```
1. BUY signal (score=68)
2. Position open @ $100
3. 3 nap múlva SELL signal (score=-72)
4. Opposing trigger → 15 perc delay → exit @ $102.30
5. P&L: +2.3%
```

#### Test 4: SHORT → EOD Auto-Liquidation
```
1. SELL signal @ 14:30 (score=-78)
2. Position open @ 14:45, SHORT @ $100
3. 16:45-kor auto-liquidation trigger
4. Exit @ 17:00 (15 min delay) @ $98.50
5. P&L: +1.5%
```

### 7.2 Edge Case Tests

#### Edge 1: Position Already Exists
```
1. BUY signal @ 10:00 for AAPL
2. Position opens @ 10:15
3. Újabb BUY signal @ 11:00 for AAPL
4. Expecting: PositionAlreadyExistsError
5. Új pozíció NEM nyílik
```

#### Edge 2: Multiple Triggers Same Time
```
1. Position open @ $100, SL=$95, TP=$108
2. @ 14:30 ár = $108.50 (TP hit) ÉS új SELL signal (opposing)
3. Exit reason priority: TP_HIT (magasabb prioritás)
```

#### Edge 3: Insufficient 5min Data
```
1. BUY signal generálódik @ 09:00
2. Execution time: 09:15
3. Nincs 5min candle 09:15-re (piaci szünet/gap)
4. Expecting: InsufficientDataError
5. Pozíció NEM nyílik
```

---

## 8. Monitoring & Observability

### 8.1 Logging Strategy
```python
import logging

logger = logging.getLogger("trade_manager")

# Log minden trade event
logger.info(f"OPEN: {symbol} {direction} @ {price} | Score: {score} | Conf: {conf}")
logger.info(f"CLOSE: {symbol} {direction} @ {price} | Reason: {reason} | P&L: {pnl}%")
logger.warning(f"SKIP: {symbol} - {skip_reason}")
logger.error(f"ERROR: {symbol} - {error_message}")
```

### 8.2 Metrics to Track
- **Trade frequency**: Trades/day per ticker
- **Win rate**: % profitable trades
- **Avg P&L**: Mean P&L across all closed trades
- **Avg holding time**: Duration per trade
- **Exit reason distribution**: SL/TP/Opposing/EOD breakdown
- **Signal→Trade conversion**: % signals that opened positions

---

## 9. Jövőbeli Bővítési Lehetőségek

### 9.1 Trading Fees Integration
```python
# Per-trade commission
COMMISSION_PERCENT = 0.15  # 0.15% per trade
MIN_COMMISSION_HUF = 500   # Min 500 HUF per trade

pnl_after_fees = pnl_gross - (2 * commission)  # Entry + Exit
```

### 9.2 Slippage Modeling
```python
# Random slippage between -0.1% and +0.1%
slippage = random.uniform(-0.001, 0.001)
actual_entry_price = theoretical_price * (1 + slippage)
```

### 9.3 Portfolio-Level Management
- Max portfolio exposure (pl. max 3 open positions)
- Sector diversification rules
- Daily loss limits

### 9.4 ML Optimization
- Signal threshold tuning (jelenleg: 25/-25)
- Dynamic position sizing based on confidence
- Stop-loss/take-profit optimization

### 9.5 Broker API Integration
- Real trading végrehajtás (Alpaca, Interactive Brokers)
- Live trade monitoring
- Order status tracking

---

## 10. Kritikus Figyelmeztető Pontok

### ⚠️ 1. Historikus Backtest Bias
A rendszer **NEM tartalmaz look-ahead bias védelmet**. A backtesting során használt szignálok és árak valós időben generálódtak, tehát nincs "jövőbe látás".

### ⚠️ 2. Slippage Hiánya
Jelenleg **nincs slippage modelezés**, tehát a szimulált P&L optimistább lehet mint a valós trading.

### ⚠️ 3. Trading Fees Hiánya
**Nincs kereskedési díj** kalkulálva, ami 0.15-0.3% per trade lehet (entry + exit = ~0.5% összesen).

### ⚠️ 4. Dividend/Split Handling
A rendszer **NEM kezeli osztalékokat és stock split-eket**. Long pozíciók esetén ez torzíthatja a P&L-t.

### ⚠️ 5. Gap Risk
**Overnight gap-ek** nem garantálják, hogy a stop-loss a beállított áron teljesül. Short pozíciók esetén különösen veszélyes.

### ⚠️ 6. Liquidity Assumptions
A rendszer feltételezi, hogy mindig van elegendő likviditás a végrehajtáshoz. **Small-cap tickereknél** ez nem biztos.

---

## 11. Adatvédelmi és Compliance Megjegyzések

- A rendszer **NEM tárol érzékeny pénzügyi információkat** (pl. számlaszámok, hitelkártya adatok)
- **NEM végez valós kereskedést**, csak szimulációt
- **NEM ad befektetési tanácsot**, csak historikus teljesítményt mutat
- Fontos: Disclaimer a UI-ban: *"Ez a rendszer szimulációs célokat szolgál. Múltbeli teljesítmény nem garancia a jövőbeli eredményekre."*

---

## 12. Kapcsolódó Dokumentumok

- `TrendSignal_Architecture_Overview.md`
- `Signal_Generation_Logic.md`
- `Database_Schema_v2.md`
- `API_Documentation.md`

---

## Verziókezelés

| Verzió | Dátum | Módosítások | Szerző |
|--------|-------|-------------|--------|
| 1.0 | 2025-02-07 | Kezdeti terv | Zsolt & Claude |

---

**🎯 Következő lépés: Implementáció Phase 1 - Database & Models**
