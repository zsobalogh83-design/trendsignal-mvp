"""
TrendSignal – Trade Simulator Core

Egyetlen, kanonikus trade exit szimulációs logika.
Az archive_backtest_service és az optimizer is ezt hívja — soha nem divergálnak.

Ha a szimulációt változtatni kell, CSAK EZT a fájlt kell módosítani.

Exit prioritás (bar-onként):
  1. STAGNATION_EXIT       – STAGNATION_CONSECUTIVE_SLOTS egymást követő bar az entry ±sávon belül
                             (csak STAGNATION_GRACE_BARS kereskedési bar után aktivál)
  2. SL_HIT / TP_HIT       – stop/target elérése (ütközésnél nyitóárhoz közelebb lévő nyer)
  2b. TP tightening        – ár 50%+ úton TP felé → TP szűkítése (close + 15% × tp_range) [ELSŐ]
  2b. Intraday breakeven   – ár eléri entry + 1.0×initial_risk → SL = entry (egyszer) [MÁSODIK]
  2b. Kombinált re-check   – TP vs SL adjudikáció (nyitóárhoz közelebb lévő nyer)
  3. OPPOSING_SIGNAL       – ellentétes alert-szintű signal, +15 perces késéssel
  4. EOD_AUTO_LIQUIDATION  – SHORT trade-ek nap végén kötelezően zárnak
  5. MAX_HOLD_LIQUIDATION  – MAX_HOLD_BARS bar után kényszerzárás

SL dinamikusan frissülhet:
  - Azonos irányú alert-szintű signal → SL frissítés ha kedvezőbb (profit lock-in)
  - EOD trailing SL (csak LONG): nap végén day_close × (1 - sl_pct), csak felfelé;
    LONG_TRAILING_TIGHTEN_DAY-tól szűkebb szorzó

Version: 1.3 – breakeven SL = entry ± BREAKEVEN_FEE_PCT (jutalékot fedező breakeven)
Date: 2026-03-29
"""

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pytz

_ET_TZ = pytz.timezone('America/New_York')

# ── Konstansok ───────────────────────────────────────────────────────────────

ALERT_THRESHOLD              = 25           # Opposing / same-dir signal küszöb
MAX_HOLD_BARS                = 10 * 26      # 10 kereskedési nap × 26 bar/nap (15m, 09:30–16:00 ET)
# US_OPEN_UTC / US_CLOSE_UTC: csak EST referencia — DST-ben a tényleges UTC órák eltérnek.
# _is_trading_hours() DST-aware pytz konverzióval dolgozik, ezeket a konstansokat ne használd.
US_OPEN_UTC                  = (14, 30)     # 09:30 ET EST-ben (EDT-ben: 13:30 UTC!)
US_CLOSE_UTC                 = (21,  0)     # 16:00 ET EST-ben (EDT-ben: 20:00 UTC!)
STAGNATION_CONSECUTIVE_SLOTS = 10           # 10 × 15 min = 150 perc oldalazás → exit
STAGNATION_BAND_FACTOR       = 0.20         # sáv = 0.20 × initial_risk
STAGNATION_GRACE_BARS        = 16           # 4 kereskedési óra (4 × 4 bar/h) — előtte nem aktivál
LONG_TRAILING_TIGHTEN_DAY    = 3            # ettől a naptól szűkebb trailing SL
LONG_TRAILING_TIGHTEN_FACTOR = 0.6          # sl_pct szorzója a tighten naptól
BREAKEVEN_FEE_PCT            = 0.002        # Round-trip jutalék — breakeven SL ezt fedi be


# ── Adatmodell ───────────────────────────────────────────────────────────────

@dataclass
class Bar:
    """
    Egy OHLC bar (jellemzően 15m).
    Kompatibilis az optimizer PriceCandle dataclass-ával
    (timestamp, open, high, low, close mezők azonosak).
    """
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float


# ── Publikus API ─────────────────────────────────────────────────────────────

def simulate_exit(
    bars: List,                                    # List[Bar] vagy List[PriceCandle] (duck-typed)
    direction: str,                                # "LONG" | "SHORT"
    entry_price: float,
    sl: float,
    tp: float,
    orig_sl_pct: float,                            # abs(entry_price - sl) / entry_price
    signal_ts: datetime,                           # Trade nyitásának timestampja
    opp_list: List[datetime],                      # Opposing signal timestampok (rendezve)
    same_dir_signals: List[Tuple[datetime, float]],# [(ts, sl_price)] azonos irányú alert-szintű
    symbol: str,                                   # Ticker (BÉT: .BD végű, US: egyéb)
) -> Dict:
    """
    Végigmegy a bar-okon és megkeresi az első exit triggert.

    Parameters
    ----------
    bars : List[Bar]
        Rendezett bar lista az entry bar-tól (inclusive). Duck-typed: Bar vagy PriceCandle
        egyaránt elfogadott, feltéve hogy timestamp/open/high/low/close attribútumai vannak.
    direction : "LONG" | "SHORT"
    entry_price : Belépési ár
    sl : Kezdeti stop-loss ár
    tp : Kezdeti take-profit ár
    orig_sl_pct : abs(entry_price - sl) / entry_price — EOD trailing SL alapja
    signal_ts : Trade nyitásának timestampja (opposing/same-dir szűrés kezdete)
    opp_list : Opposing signal timestampok (rendezve) — LONG-hoz SELL signalok, SHORT-hoz BUY-ok
    same_dir_signals : [(ts, sl_price)] — azonos irányú alert-szintű signalok SL frissítéshez
    symbol : Ticker symbol

    Returns
    -------
    Dict:
        exit_price    : float | None
        exit_time     : datetime | None
        exit_reason   : "SL_HIT" | "TP_HIT" | "STAGNATION_EXIT" | "OPPOSING_SIGNAL" |
                        "EOD_AUTO_LIQUIDATION" | "MAX_HOLD_LIQUIDATION" | "OPEN"
        duration_bars : int
    """
    initial_risk    = abs(entry_price - sl)
    stagnation_band = STAGNATION_BAND_FACTOR * initial_risk if initial_risk > 0 else 0.0
    stagnation_slots = 0

    current_sl = sl
    current_tp = tp
    initial_tp = tp
    be_applied = False          # intraday breakeven egyszer tüzel

    trading_days_held  = 0
    pending_opp_exit: Optional[datetime] = None
    bars_held = 0

    # Pointer az azonos irányú signalokban — signal_ts utáni első elemtől indulunk
    sd_idx = bisect_left([s[0] for s in same_dir_signals], signal_ts)

    for bar in bars:
        bar_ts = bar.timestamp

        # Kereskedési időn kívüli bar-okat kihagyjuk
        if _is_weekend(bar_ts) or not _is_trading_hours(bar_ts, symbol):
            continue

        bars_held += 1

        # ── Azonos irányú signal → SL frissítés ──────────────────────────
        while sd_idx < len(same_dir_signals):
            sig_ts, sig_sl = same_dir_signals[sd_idx]
            if sig_ts <= signal_ts:
                sd_idx += 1
                continue
            if sig_ts > bar_ts:
                break
            if direction == "LONG" and sig_sl > current_sl:
                current_sl = round(sig_sl, 4)
            elif direction == "SHORT" and sig_sl < current_sl:
                current_sl = round(sig_sl, 4)
            sd_idx += 1

        # ── 1. STAGNATION ─────────────────────────────────────────────────
        # Grace period: az első STAGNATION_GRACE_BARS kereskedési bar alatt
        # nem számolunk — a trade-nek időt adunk a kibontakozáshoz.
        if stagnation_band > 0 and bars_held > STAGNATION_GRACE_BARS:
            in_band = abs(bar.close - entry_price) <= stagnation_band
            stagnation_slots = stagnation_slots + 1 if in_band else 0
            if stagnation_slots >= STAGNATION_CONSECUTIVE_SLOTS:
                return {
                    "exit_price":    bar.close,
                    "exit_time":     bar_ts,
                    "exit_reason":   "STAGNATION_EXIT",
                    "duration_bars": bars_held,
                }
        elif bars_held <= STAGNATION_GRACE_BARS:
            stagnation_slots = 0  # grace period alatt a számláló nullán marad

        # ── 2. SL / TP ────────────────────────────────────────────────────
        h, l, o = bar.high, bar.low, bar.open

        if direction == "LONG":
            sl_hit = l <= current_sl
            tp_hit = h >= current_tp
        else:
            sl_hit = h >= current_sl
            tp_hit = l <= current_tp

        if sl_hit or tp_hit:
            if sl_hit and tp_hit:
                # Ütközés: amelyik közelebb volt a nyitóárhoz, az teljesül előbb
                if abs(o - current_sl) <= abs(o - current_tp):
                    return {"exit_price": current_sl, "exit_time": bar_ts,
                            "exit_reason": "SL_HIT", "duration_bars": bars_held}
                else:
                    return {"exit_price": current_tp, "exit_time": bar_ts,
                            "exit_reason": "TP_HIT", "duration_bars": bars_held}
            if sl_hit:
                return {"exit_price": current_sl, "exit_time": bar_ts,
                        "exit_reason": "SL_HIT", "duration_bars": bars_held}
            return {"exit_price": current_tp, "exit_time": bar_ts,
                    "exit_reason": "TP_HIT", "duration_bars": bars_held}

        # ── 2b. TP tightening (ELSŐ: current_tp frissítése mielőtt breakeven fut) ──
        # Ha az ár >= 50% úton a TP felé: TP = close + 15% × original_tp_range
        # Csak szűkíthet, soha nem tágíthat
        if direction == "LONG":
            tp_range_val = initial_tp - entry_price
            if tp_range_val > 0:
                tp_progress = (bar.close - entry_price) / tp_range_val
                if tp_progress >= 0.50:
                    new_tp = bar.close + 0.15 * tp_range_val
                    if new_tp < current_tp:
                        current_tp = round(new_tp, 4)
        elif direction == "SHORT":
            tp_range_val = entry_price - initial_tp
            if tp_range_val > 0:
                tp_progress = (entry_price - bar.close) / tp_range_val
                if tp_progress >= 0.50:
                    new_tp = bar.close - 0.15 * tp_range_val
                    if new_tp > current_tp:
                        current_tp = round(new_tp, 4)

        # ── 2b. Intraday breakeven (MÁSODIK: current_sl frissítése) ──────────
        # Ha az ár eléri entry + 1.0×initial_risk → SL = entry ± jutalék (csak egyszer)
        # LONG:  SL = entry × (1 + fee)  → exit esetén fedezi a round-trip jutalékot
        # SHORT: SL = entry × (1 - fee)  → ugyanígy
        if not be_applied and initial_risk > 0:
            if direction == "LONG" and current_sl < entry_price:
                if h >= entry_price + 1.0 * initial_risk:
                    current_sl = round(entry_price * (1.0 + BREAKEVEN_FEE_PCT), 4)
                    be_applied = True
            elif direction == "SHORT" and current_sl > entry_price:
                if l <= entry_price - 1.0 * initial_risk:
                    current_sl = round(entry_price * (1.0 - BREAKEVEN_FEE_PCT), 4)
                    be_applied = True

        # ── 2b. Kombinált re-check: TP vs SL adjudikáció ─────────────────
        # TP tightening és/vagy breakeven után újra ellenőrizzük — a nyitóárhoz
        # közelebb lévő szint teljesül előbb (azonos logika mint a step 2-ben)
        if direction == "LONG":
            tp_hit_2b = h >= current_tp
            sl_hit_2b = l <= current_sl
        else:
            tp_hit_2b = l <= current_tp
            sl_hit_2b = h >= current_sl

        if tp_hit_2b or sl_hit_2b:
            if tp_hit_2b and sl_hit_2b:
                if abs(o - current_sl) <= abs(o - current_tp):
                    return {"exit_price": current_sl, "exit_time": bar_ts,
                            "exit_reason": "SL_HIT", "duration_bars": bars_held}
                else:
                    return {"exit_price": current_tp, "exit_time": bar_ts,
                            "exit_reason": "TP_HIT", "duration_bars": bars_held}
            if sl_hit_2b:
                return {"exit_price": current_sl, "exit_time": bar_ts,
                        "exit_reason": "SL_HIT", "duration_bars": bars_held}
            return {"exit_price": current_tp, "exit_time": bar_ts,
                    "exit_reason": "TP_HIT", "duration_bars": bars_held}

        # ── 3. OPPOSING_SIGNAL – LETILTVA (elemzés: -1700pp kumulált veszteség, 46.4% dir_acc)
        # if pending_opp_exit is not None and bar_ts >= pending_opp_exit:
        #     return {"exit_price": bar.open, "exit_time": bar_ts,
        #             "exit_reason": "OPPOSING_SIGNAL", "duration_bars": bars_held}

        # ── 4. EOD kezelés (nap utolsó barján) ───────────────────────────
        bar_end = bar_ts + timedelta(minutes=15)
        is_last_bar_of_day = not _is_trading_hours(bar_end, symbol) and not _is_weekend(bar_end)

        if is_last_bar_of_day:
            if direction == "SHORT":
                # SHORT trade-ek intraday kötelezők – nap végén zárjuk
                return {
                    "exit_price":    bar.close,
                    "exit_time":     bar_ts,
                    "exit_reason":   "EOD_AUTO_LIQUIDATION",
                    "duration_bars": bars_held,
                }
            else:
                # LONG: EOD trailing SL (csak felfelé, profit lock-in)
                trading_days_held += 1
                if bar.close > entry_price:
                    eff_sl_pct = (orig_sl_pct * LONG_TRAILING_TIGHTEN_FACTOR
                                  if trading_days_held >= LONG_TRAILING_TIGHTEN_DAY
                                  else orig_sl_pct)
                    trailing_sl = round(bar.close * (1.0 - eff_sl_pct), 4)
                    if trailing_sl > current_sl:
                        current_sl = trailing_sl

        # ── 5. MAX HOLD ───────────────────────────────────────────────────
        if bars_held > MAX_HOLD_BARS:
            return {
                "exit_price":    bar.close,
                "exit_time":     bar_ts,
                "exit_reason":   "MAX_HOLD_LIQUIDATION",
                "duration_bars": bars_held,
            }

        # ── Opposing signal keresése – LETILTVA (lásd 3. blokk fentebb) ────
        # if pending_opp_exit is None:
        #     opp_ts = _find_opposing_signal(opp_list, signal_ts, bar_ts)
        #     if opp_ts is not None:
        #         pending_opp_exit = bar_ts + timedelta(minutes=15)

    # Nincs exit — OPEN marad
    return {
        "exit_price":    None,
        "exit_time":     None,
        "exit_reason":   "OPEN",
        "duration_bars": bars_held,
    }


# ── Belső segédfüggvények ────────────────────────────────────────────────────

def _is_trading_hours(dt: datetime, symbol: str) -> bool:
    """DST-aware kereskedési idő ellenőrzés.

    US piacok: 9:30–16:00 ET (pytz DST-konverzióval).
      - EST (téli): 14:30–21:00 UTC
      - EDT (nyári, ~márc.–nov.): 13:30–20:00 UTC
    BÉT: 8:00–16:00 UTC (CET/CEST egyforma UTC-offszet a .BD tickereknél).

    dt: naive UTC datetime (ahogy az adatbázisban tárolva van).
    """
    if symbol.endswith(".BD"):
        td = dt.hour + dt.minute / 60.0
        return 8.0 <= td < 16.0
    # US: DST-aware konverzió
    et_time = pytz.utc.localize(dt).astimezone(_ET_TZ)
    td = et_time.hour + et_time.minute / 60.0
    return 9.5 <= td < 16.0  # 9:30–16:00 ET


def _is_weekend(dt: datetime) -> bool:
    return dt.weekday() >= 5


def _find_opposing_signal(
    opp_list: List[datetime],
    signal_ts: datetime,
    bar_ts: datetime,
) -> Optional[datetime]:
    """
    Visszaadja az első opposing signal timestampját signal_ts < ts <= bar_ts tartományban.
    """
    idx = bisect_left(opp_list, signal_ts)
    for i in range(idx, len(opp_list)):
        ts = opp_list[i]
        if ts <= signal_ts:
            continue
        if ts <= bar_ts:
            return ts
        break
    return None
