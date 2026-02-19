"""
Database Migration: Create simulated_trades table
TrendSignal Trackback System - Phase 1

Run this script to create the simulated_trades table in trendsignal.db

Usage:
    python migrate_create_simulated_trades.py

Version: 1.0
Date: 2026-02-17
"""

import sqlite3
from pathlib import Path
import sys

# Database path (same as in database.py)
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "trendsignal.db"

def migrate():
    """Create simulated_trades table with indexes and triggers"""
    
    print("=" * 60)
    print("📊 TrendSignal - Simulated Trades Migration")
    print("=" * 60)
    print(f"Database: {DATABASE_PATH}")
    
    if not DATABASE_PATH.exists():
        print("❌ Error: trendsignal.db not found!")
        print(f"   Expected location: {DATABASE_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(DATABASE_PATH))
    cursor = conn.cursor()
    
    try:
        # ===== 1. CREATE TABLE =====
        print("\n1️⃣  Creating simulated_trades table...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulated_trades (
                -- Primary Key
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Position identifiers
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('LONG', 'SHORT')),
                status TEXT NOT NULL CHECK(status IN ('OPEN', 'CLOSED')),
                
                -- Entry information
                entry_signal_id INTEGER NOT NULL,
                entry_signal_generated_at TIMESTAMP NOT NULL,
                entry_execution_time TIMESTAMP NOT NULL,
                entry_price REAL NOT NULL,
                entry_score REAL NOT NULL,
                entry_confidence REAL NOT NULL,
                
                -- Stop-Loss and Take-Profit (fixed at entry)
                stop_loss_price REAL NOT NULL,
                take_profit_price REAL NOT NULL,
                
                -- Position size
                position_size_shares INTEGER NOT NULL,
                position_value_huf REAL NOT NULL,
                usd_huf_rate REAL,
                
                -- Exit information (NULL if status='OPEN')
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
                
                -- P&L calculation
                pnl_percent REAL,
                pnl_amount_huf REAL,
                
                -- Duration
                duration_minutes INTEGER,
                
                -- Audit fields
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Foreign Keys
                FOREIGN KEY (entry_signal_id) REFERENCES signals(id) ON DELETE CASCADE,
                FOREIGN KEY (exit_signal_id) REFERENCES signals(id) ON DELETE SET NULL
            )
        """)
        
        print("   ✅ Table created successfully")
        
        # ===== 2. CREATE INDEXES =====
        print("\n2️⃣  Creating indexes...")
        
        indexes = [
            ("idx_simtrades_symbol", "symbol"),
            ("idx_simtrades_status", "status"),
            ("idx_simtrades_direction", "direction"),
            ("idx_simtrades_entry_exec", "entry_execution_time"),
            ("idx_simtrades_exit_exec", "exit_execution_time"),
            ("idx_simtrades_exit_reason", "exit_reason"),
            ("idx_simtrades_created_at", "created_at"),
            ("idx_simtrades_entry_signal", "entry_signal_id"),
            ("idx_simtrades_exit_trigger", "exit_trigger_time"),
            ("idx_simtrades_pnl_pct", "pnl_percent"),
            ("idx_simtrades_pnl_huf", "pnl_amount_huf"),
        ]
        
        for idx_name, column in indexes:
            try:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {idx_name} 
                    ON simulated_trades({column})
                """)
                print(f"   ✅ {idx_name}")
            except sqlite3.OperationalError as e:
                print(f"   ⚠️  {idx_name} (already exists or error: {e})")
        
        # Composite index for common queries
        print("\n   Creating composite indexes...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_simtrades_symbol_status 
                ON simulated_trades(symbol, status)
            """)
            print("   ✅ idx_simtrades_symbol_status")
        except sqlite3.OperationalError:
            print("   ⚠️  idx_simtrades_symbol_status (already exists)")
        
        # ===== 3. CREATE TRIGGER =====
        print("\n3️⃣  Creating auto-update trigger...")
        
        try:
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_simtrades_timestamp 
                AFTER UPDATE ON simulated_trades
                FOR EACH ROW
                BEGIN
                    UPDATE simulated_trades 
                    SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END
            """)
            print("   ✅ Trigger created successfully")
        except sqlite3.OperationalError as e:
            print(f"   ⚠️  Trigger (already exists or error: {e})")
        
        # ===== 4. VERIFY =====
        print("\n4️⃣  Verifying table structure...")
        
        cursor.execute("PRAGMA table_info(simulated_trades)")
        columns = cursor.fetchall()
        
        print(f"   ✅ Table has {len(columns)} columns:")
        for col in columns[:5]:  # Show first 5 columns
            print(f"      - {col[1]} ({col[2]})")
        print(f"      ... and {len(columns) - 5} more columns")
        
        # Check row count
        cursor.execute("SELECT COUNT(*) FROM simulated_trades")
        count = cursor.fetchone()[0]
        print(f"\n   📊 Current row count: {count}")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
