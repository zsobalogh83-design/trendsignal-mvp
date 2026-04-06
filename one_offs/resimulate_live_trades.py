"""
TrendSignal - Live Trade Tábla Törlése

Törli az összes simulated_trades rekordot.
A trade újraszimulációt a frontendről kell elindítani (Backtest gomb).

Usage:
    python one_offs/resimulate_live_trades.py           # interaktív megerősítés
    python one_offs/resimulate_live_trades.py --confirm  # prompt nélkül
"""

import sys
import os
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import SessionLocal
from src.models import SimulatedTrade


def main():
    auto_confirm = "--confirm" in sys.argv[1:]

    db = SessionLocal()
    try:
        count = db.query(SimulatedTrade).count()

        print(f"\n{'='*60}")
        print(f"  SIMULATED_TRADES TÖRLÉSE")
        print(f"{'='*60}")
        print(f"  Törölendő rekord: {count}")
        print(f"  A backtest újrafuttatása a frontendről történik.")
        print(f"{'='*60}\n")

        if not auto_confirm:
            confirm = input("Folytatod? [igen/nem]: ").strip().lower()
            if confirm != "igen":
                print("Megszakítva.")
                return

        deleted = db.query(SimulatedTrade).delete()
        db.commit()
        print(f"  ✅ Törölve: {deleted} rekord\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
