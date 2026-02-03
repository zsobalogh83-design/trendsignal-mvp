"""
Recreate signal_calculations table with optimized structure
Run this after updating models.py

Usage:
    python recreate_audit_table.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from database import engine, Base
from models import SignalCalculation
from sqlalchemy import inspect

def recreate_table():
    """Drop old table and create new optimized structure"""
    print("=" * 70)
    print("🔧 Recreating signal_calculations with optimized structure")
    print("=" * 70)
    print()
    
    try:
        # Check if table exists
        inspector = inspect(engine)
        table_exists = 'signal_calculations' in inspector.get_table_names()
        
        if table_exists:
            print("📋 Old table found - dropping...")
            SignalCalculation.__table__.drop(engine)
            print("✅ Old table dropped")
        else:
            print("ℹ️  No existing table found")
        
        print()
        print("📊 Creating new optimized table...")
        SignalCalculation.__table__.create(engine)
        print("✅ New table created!")
        
        print()
        print("=" * 70)
        print("✅ SUCCESS!")
        print("=" * 70)
        print()
        print("New structure:")
        print("  - ~66 indexed columns for fast queries")
        print("  - 6 JSON fields for detailed audit data")
        print("  - All config parameters as columns for ML tuning")
        print()
        print("Next: Generate new signals to populate the table!")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    recreate_table()
