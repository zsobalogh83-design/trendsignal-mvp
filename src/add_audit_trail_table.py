"""
Database Migration: Add signal_calculations table for audit trail
Run this script to add the new audit trail table to existing database

Usage:
    python add_audit_trail_table.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from database import Base, engine
from models import SignalCalculation  # Import to register the model

def migrate():
    """Add signal_calculations table to database"""
    print("=" * 70)
    print("🔧 TrendSignal Database Migration: Add Audit Trail Table")
    print("=" * 70)
    print()
    
    try:
        # Create only the new table (won't affect existing tables)
        print("📊 Creating signal_calculations table...")
        SignalCalculation.__table__.create(bind=engine, checkfirst=True)
        print("✅ Table created successfully!")
        print()
        
        print("💾 Database schema updated:")
        print("   - signal_calculations (NEW) - stores detailed audit trail")
        print("   - Linked to signals table via signal_id foreign key")
        print()
        
        print("=" * 70)
        print("✅ Migration completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    migrate()
