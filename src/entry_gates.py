"""
Entry gate szűrők — közös implementáció.

Mindkét helyen ugyanaz a logika fut:
  - trade_manager.open_position()   (live szimuláció)
  - archive_backtest_service._run_ticker()  (archive backtest)

Visszatérési érték: (blocked, filter_name, reason_msg)
  blocked=False  → a signal átment minden szűrőn
  blocked=True   → filter_name és reason_msg adja meg az okot
"""

from __future__ import annotations
from typing import Optional, Tuple


def check_entry_gates(
    direction: str,
    rsi: Optional[float],
    macd_hist: Optional[float],
    sma_200: Optional[float],
    sma_50: Optional[float],
    close_price: Optional[float],
    nearest_resistance: Optional[float],
    cfg,
) -> Tuple[bool, str, str]:
    """
    Ellenőrzi az összes entry gate feltételt.

    Returns:
        (False, '', '')                         — átment
        (True, 'rsi_filtered',    reason_msg)   — RSI gate blokkolta
        (True, 'macd_filtered',   reason_msg)   — MACD gate blokkolta
        (True, 'sma200_filtered', reason_msg)   — SMA200 gate blokkolta
        (True, 'sma50_filtered',  reason_msg)   — SMA50 gate blokkolta
        (True, 'resist_filtered', reason_msg)   — Resistance distance gate blokkolta
    """
    p = close_price

    if direction == "LONG":
        if rsi is not None and rsi >= cfg.entry_gate_rsi_buy_max:
            return True, 'rsi_filtered', (
                f"Entry filter [RSI]: RSI={rsi:.1f} >= {cfg.entry_gate_rsi_buy_max} for BUY — overbought, skip"
            )
        if macd_hist is not None and macd_hist <= cfg.entry_gate_macd_hist_buy_min:
            return True, 'macd_filtered', (
                f"Entry filter [MACD]: hist={macd_hist:.4f} <= {cfg.entry_gate_macd_hist_buy_min} for BUY — bearish momentum, skip"
            )
        if sma_200 and sma_200 > 0 and p and p > 0:
            pct = (p - sma_200) / sma_200 * 100
            if pct > cfg.entry_gate_sma200_buy_max_pct:
                return True, 'sma200_filtered', (
                    f"Entry filter [SMA200]: price {pct:+.1f}% vs SMA200 > {cfg.entry_gate_sma200_buy_max_pct}% for BUY — too extended, skip"
                )
        if nearest_resistance and p and p > 0:
            dist_r = (nearest_resistance - p) / p * 100
            if dist_r > cfg.entry_gate_dist_resist_buy_max_pct:
                return True, 'resist_filtered', (
                    f"Entry filter [Resistance]: dist={dist_r:.1f}% > {cfg.entry_gate_dist_resist_buy_max_pct}% for BUY — no room to run, skip"
                )

    else:  # SHORT
        if rsi is not None and rsi <= cfg.entry_gate_rsi_sell_min:
            return True, 'rsi_filtered', (
                f"Entry filter [RSI]: RSI={rsi:.1f} <= {cfg.entry_gate_rsi_sell_min} for SELL — oversold, skip"
            )
        if macd_hist is not None and macd_hist >= cfg.entry_gate_macd_hist_sell_max:
            return True, 'macd_filtered', (
                f"Entry filter [MACD]: hist={macd_hist:.4f} >= {cfg.entry_gate_macd_hist_sell_max} for SELL — bullish momentum, skip"
            )
        if sma_200 and sma_200 > 0 and p and p > 0:
            pct = (p - sma_200) / sma_200 * 100
            if pct < cfg.entry_gate_sma200_sell_min_pct:
                return True, 'sma200_filtered', (
                    f"Entry filter [SMA200]: price {pct:+.1f}% vs SMA200 < {cfg.entry_gate_sma200_sell_min_pct}% for SELL — too oversold, skip"
                )
        if sma_50 and sma_50 > 0 and p and p > 0:
            pct = (p - sma_50) / sma_50 * 100
            if pct < cfg.entry_gate_sma50_sell_min_pct:
                return True, 'sma50_filtered', (
                    f"Entry filter [SMA50]: price {pct:+.1f}% vs SMA50 < {cfg.entry_gate_sma50_sell_min_pct}% for SELL — not extended enough, skip"
                )

    return False, '', ''
