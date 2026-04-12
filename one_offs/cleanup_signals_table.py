"""
one_offs/cleanup_signals_table.py

Retroaktív migráció: a signals táblában felgyülemlett, archívba sosem kerülő
státuszú signalok áthelyezése az archive_signals táblába.

Érintett státuszok:
  - nogo          : trade_manager elutasította (ATR filter, HOLD döntés stb.)
  - macd_filtered : MACD entry gate blokkolta
  - rsi_filtered  : RSI entry gate blokkolta
  - migrated      : már az archive-ban kell legyen, de 194 db kimaradt

A migrátor idempotens (INSERT OR IGNORE + már-migrált ellenőrzés),
ezért biztonságosan futtatható többször.

Futtatás:
    python one_offs/cleanup_signals_table.py
"""
import sys
import logging
from pathlib import Path

# Projekt gyökér hozzáadása a Python path-hoz
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.live_to_archive_migrator import migrate_signal_without_trade, DATABASE_PATH
import sqlite3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)


def get_signal_ids(statuses: list[str]) -> list[int]:
    conn = sqlite3.connect(str(DATABASE_PATH))
    placeholders = ','.join('?' * len(statuses))
    rows = conn.execute(
        f"SELECT id, ticker_symbol, status, decision FROM signals WHERE status IN ({placeholders}) ORDER BY id",
        statuses,
    ).fetchall()
    conn.close()
    return rows


def run():
    target_statuses = ['nogo', 'macd_filtered', 'rsi_filtered', 'migrated']
    rows = get_signal_ids(target_statuses)

    counts = {s: 0 for s in target_statuses}
    for r in rows:
        counts[r[2]] += 1

    print(f"\nMigrálásra váró signalok:")
    for status, cnt in counts.items():
        print(f"  {status}: {cnt} db")
    print(f"  ÖSSZESEN: {len(rows)} db\n")

    ok = skipped = errors = 0
    for signal_id, ticker, status, decision in rows:
        try:
            result = migrate_signal_without_trade(signal_id)
            if result:
                ok += 1
            else:
                skipped += 1
                logger.debug(f"  Skip {signal_id} ({ticker} {status} {decision})")
        except Exception as e:
            errors += 1
            logger.warning(f"  Hiba {signal_id} ({ticker} {status}): {e}")

        if (ok + skipped + errors) % 200 == 0:
            logger.info(f"  Haladás: {ok+skipped+errors}/{len(rows)} — ok={ok} skip={skipped} err={errors}")

    print(f"\nEredmeny:")
    print(f"  Migralt:  {ok}")
    print(f"  Kihagyva: {skipped}  (pl. nincs signal_calculations, vagy mar archive-ban)")
    print(f"  Hiba:     {errors}")

    # Ellenorzes: mennyi maradt a signals tablaban nem-migrated allapotban
    conn = sqlite3.connect(str(DATABASE_PATH))
    remaining = conn.execute(
        "SELECT status, COUNT(*) FROM signals WHERE status IN ('nogo','macd_filtered','rsi_filtered') GROUP BY status"
    ).fetchall()
    conn.close()

    if remaining:
        print(f"\nFigyelmeztes: alábbi signalok maradtak a signals táblában (nincs signal_calculations):")
        for status, cnt in remaining:
            print(f"  {status}: {cnt} db")
    else:
        print(f"\nMinden nogo/macd_filtered/rsi_filtered signal migrálva vagy status=migrated.")


if __name__ == '__main__':
    run()
