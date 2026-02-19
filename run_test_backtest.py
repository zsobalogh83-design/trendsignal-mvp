"""
Run test backtest on today's signals only
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.database import SessionLocal
from test_backtest import TestBacktest

def main():
    db = SessionLocal()
    try:
        service = TestBacktest(db)
        stats = service.run_test(date="2026-02-17")
        
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Expected: {stats['total']} signals")
        print(f"Opened:   {stats['opened']} trades")
        print(f"Skip:     {stats['skip_no_data'] + stats['skip_invalid'] + stats['skip_duplicate']}")
        print("=" * 70)
        
    finally:
        db.close()

if __name__ == "__main__":
    main()
