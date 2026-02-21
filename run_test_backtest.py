"""
Run backtest using BacktestService (production logic)
Optionally pass a date range as arguments, defaults to today.

Usage:
    python run_test_backtest.py                         # today
    python run_test_backtest.py 2026-02-17              # specific day
    python run_test_backtest.py 2026-02-10 2026-02-21   # date range
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Force UTF-8 stdout/stderr on Windows (needed for emoji in config.py prints)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add project root AND src/ to path
# (src/ modules use bare imports like "from config import ..." internally)
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)

from database import SessionLocal
from backtest_service import BacktestService


def main():
    # Parse optional date args
    args = sys.argv[1:]

    if len(args) == 0:
        # Default: today
        date_from = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        date_to = date_from + timedelta(days=1)
    elif len(args) == 1:
        date_from = datetime.strptime(args[0], "%Y-%m-%d")
        date_to = date_from + timedelta(days=1)
    elif len(args) == 2:
        date_from = datetime.strptime(args[0], "%Y-%m-%d")
        date_to = datetime.strptime(args[1], "%Y-%m-%d") + timedelta(days=1)
    else:
        print("Usage: python run_test_backtest.py [date_from] [date_to]")
        print("  date_from / date_to format: YYYY-MM-DD")
        sys.exit(1)

    print(f"\nBacktest időszak: {date_from.date()} → {(date_to - timedelta(days=1)).date()}")

    db = SessionLocal()
    try:
        service = BacktestService(db)
        result = service.run_backtest(
            date_from=date_from,
            date_to=date_to,
        )

        stats = result['stats']
        print("\n" + "=" * 70)
        print("ÖSSZEFOGLALÓ")
        print("=" * 70)
        print(f"Futási idő:       {result['execution_time_seconds']}s")
        print(f"Összes signal:    {stats['total_signals']}")
        print(f"├─ Most nyitott:  {stats['newly_opened']}")
        print(f"├─ Most lezárt:   {stats['newly_closed']}")
        print(f"├─ Már lezárt:    {stats['already_closed']}")
        print(f"├─ Még nyitott:   {stats['still_open']}")
        print(f"├─ Skip (no adat):{stats['skipped_no_data']}")
        print(f"└─ Skip (invalid):{stats['skipped_invalid']}")
        if stats['errors']:
            print(f"\n⚠️  Hibák: {len(stats['errors'])}")
            for err in stats['errors'][:5]:
                print(f"   {err['symbol']} signal#{err['signal_id']}: {err['error']}")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()
