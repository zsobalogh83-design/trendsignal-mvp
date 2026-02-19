"""
TrendSignal - Reset & Debug Backtest
Clears simulated_trades table and runs backtest with detailed logging

Usage:
    python reset_and_test.py
"""

import requests
import sqlite3
import sys
from datetime import datetime

# Database path
DB_PATH = "trendsignal.db"

# Colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.OKCYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'=' * 70}{Colors.ENDC}\n")


def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_info(text, indent=0):
    prefix = "  " * indent
    print(f"{prefix}{text}")


def reset_simulated_trades():
    """Drop and recreate simulated_trades table"""
    print_header("Simulated Trades Reset")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check current count
        cursor.execute("SELECT COUNT(*) FROM simulated_trades")
        before_count = cursor.fetchone()[0]
        print_info(f"Jelenlegi trade-ek: {before_count}")
        
        if before_count > 0:
            # Drop table
            print_info("Tábla törlése...")
            cursor.execute("DROP TABLE IF EXISTS simulated_trades")
            
            # Recreate table (you'll need to run the migration script after this)
            print_warning("Futtasd újra: python migrate_create_simulated_trades.py")
            
            conn.commit()
            print_success("Tábla törölve!")
        else:
            print_info("Tábla már üres")
        
        conn.close()
        return True
        
    except Exception as e:
        print_error(f"Hiba: {e}")
        return False


def get_signal_stats():
    """Get signal statistics from database"""
    print_header("Signal Statisztikák")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Total signals
        cursor.execute("SELECT COUNT(*) FROM signals")
        total = cursor.fetchone()[0]
        print_info(f"Összes signal: {total}")
        
        # Non-neutral signals
        cursor.execute("""
            SELECT COUNT(*) FROM signals 
            WHERE combined_score >= 25 OR combined_score <= -25
        """)
        non_neutral = cursor.fetchone()[0]
        print_info(f"NON-NEUTRAL signalok (|score| >= 25): {non_neutral}")
        
        # Signal breakdown by score
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN combined_score >= 65 THEN 'STRONG BUY (>=65)'
                    WHEN combined_score >= 25 THEN 'MODERATE BUY (25-64)'
                    WHEN combined_score <= -65 THEN 'STRONG SELL (<=-65)'
                    WHEN combined_score <= -25 THEN 'MODERATE SELL (-64 to -25)'
                    ELSE 'NEUTRAL/HOLD (-24 to +24)'
                END as category,
                COUNT(*) as count
            FROM signals
            GROUP BY category
            ORDER BY 
                CASE 
                    WHEN combined_score >= 65 THEN 1
                    WHEN combined_score >= 25 THEN 2
                    WHEN combined_score <= -65 THEN 3
                    WHEN combined_score <= -25 THEN 4
                    ELSE 5
                END
        """)
        
        print_info("\nScore eloszlás:")
        for row in cursor.fetchall():
            print_info(f"  {row[0]}: {row[1]}", indent=1)
        
        # Date range
        cursor.execute("""
            SELECT 
                MIN(created_at) as oldest,
                MAX(created_at) as newest
            FROM signals
            WHERE combined_score >= 25 OR combined_score <= -25
        """)
        oldest, newest = cursor.fetchone()
        print_info(f"\nSignal időszak:")
        print_info(f"  Legrégebbi: {oldest}", indent=1)
        print_info(f"  Legújabb: {newest}", indent=1)
        
        # Missing stop_loss or take_profit
        cursor.execute("""
            SELECT COUNT(*) FROM signals
            WHERE (combined_score >= 25 OR combined_score <= -25)
            AND (stop_loss IS NULL OR take_profit IS NULL)
        """)
        missing_sl_tp = cursor.fetchone()[0]
        if missing_sl_tp > 0:
            print_warning(f"\nHiányzó SL/TP: {missing_sl_tp} signal!")
        
        # Price data coverage
        cursor.execute("""
            SELECT 
                MIN(timestamp) as oldest,
                MAX(timestamp) as newest,
                COUNT(DISTINCT DATE(timestamp)) as days,
                COUNT(*) as candles
            FROM price_data
            WHERE interval = '5m'
        """)
        price_oldest, price_newest, price_days, price_candles = cursor.fetchone()
        print_info(f"\n5 perces árfolyam adat:")
        print_info(f"  Időszak: {price_oldest} → {price_newest}", indent=1)
        print_info(f"  Napok: {price_days}", indent=1)
        print_info(f"  Gyertyák: {price_candles:,}", indent=1)
        
        conn.close()
        return non_neutral
        
    except Exception as e:
        print_error(f"Hiba: {e}")
        return 0


def run_backtest():
    """Run backtest via API"""
    print_header("Backtest Futtatása")
    
    try:
        print_info("🚀 POST /api/v1/simulated-trades/backtest")
        print_info("   (Ez eltarthat 1-5 percig...)\n")
        
        response = requests.post(
            "http://localhost:8000/api/v1/simulated-trades/backtest",
            json={},
            timeout=600  # 10 minute timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            stats = data['stats']
            
            print_success(f"Backtest kész! ({data['execution_time_seconds']}s)")
            
            print_info(f"\n📊 Eredmények:")
            print_info(f"Összes signal: {stats['total_signals']}", indent=1)
            print_info(f"├─ Már lezárt: {stats['already_closed']}", indent=1)
            print_info(f"├─ Most lezárt: {stats['newly_closed']}", indent=1)
            print_info(f"├─ Még nyitott: {stats['still_open']}", indent=1)
            print_info(f"├─ Most nyitott: {stats['newly_opened']}", indent=1)
            print_info(f"├─ Skip (nincs adat): {stats['skipped_no_data']}", indent=1)
            print_info(f"└─ Skip (invalid): {stats['skipped_invalid']}", indent=1)
            
            if stats.get('errors'):
                print_warning(f"\n⚠️  Hibák: {len(stats['errors'])}")
                for err in stats['errors'][:3]:
                    print_info(f"{err['symbol']}: {err['error']}", indent=1)
            
            return stats
        else:
            print_error(f"HTTP {response.status_code}")
            print_info(response.text, indent=1)
            return None
            
    except Exception as e:
        print_error(f"Hiba: {e}")
        return None


def verify_results():
    """Verify created trades in database"""
    print_header("Eredmények Ellenőrzése")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Total trades
        cursor.execute("SELECT COUNT(*) FROM simulated_trades")
        total = cursor.fetchone()[0]
        print_info(f"Létrehozott trade-ek: {total}")
        
        if total == 0:
            print_error("HIBA: Egy trade sem lett létrehozva!")
            return False
        
        # Status breakdown
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM simulated_trades 
            GROUP BY status
        """)
        print_info("\nStatus eloszlás:")
        for status, count in cursor.fetchall():
            print_info(f"  {status}: {count}", indent=1)
        
        # Direction breakdown
        cursor.execute("""
            SELECT direction, COUNT(*) 
            FROM simulated_trades 
            GROUP BY direction
        """)
        print_info("\nIrány eloszlás:")
        for direction, count in cursor.fetchall():
            print_info(f"  {direction}: {count}", indent=1)
        
        # Exit reasons (for closed)
        cursor.execute("""
            SELECT exit_reason, COUNT(*) 
            FROM simulated_trades 
            WHERE status = 'CLOSED'
            GROUP BY exit_reason
        """)
        closed_reasons = cursor.fetchall()
        if closed_reasons:
            print_info("\nKilépési okok:")
            for reason, count in closed_reasons:
                print_info(f"  {reason}: {count}", indent=1)
        
        # Sample trades
        cursor.execute("""
            SELECT id, symbol, direction, status, entry_price, exit_price, pnl_percent
            FROM simulated_trades
            LIMIT 5
        """)
        print_info("\nPélda trade-ek:")
        for row in cursor.fetchall():
            tid, symbol, direction, status, entry, exit_p, pnl = row
            if status == 'CLOSED':
                print_info(f"  #{tid} {symbol} {direction} @ ${entry:.2f} → ${exit_p:.2f} ({pnl:+.2f}%)", indent=1)
            else:
                print_info(f"  #{tid} {symbol} {direction} @ ${entry:.2f} (OPEN)", indent=1)
        
        conn.close()
        return total > 0
        
    except Exception as e:
        print_error(f"Hiba: {e}")
        return False


def main():
    """Main execution"""
    print_header("TrendSignal - Reset & Debug Backtest")
    
    # Step 1: Reset table
    print_info("Szeretnéd törölni a simulated_trades táblát? (y/n): ", end="")
    choice = input().strip().lower()
    
    if choice == 'y':
        if not reset_simulated_trades():
            print_error("Reset sikertelen!")
            sys.exit(1)
        
        print_info("\n⚠️  FONTOS: Futtasd most:")
        print_info("   python migrate_create_simulated_trades.py\n")
        print_info("Megtetted? (y/n): ", end="")
        if input().strip().lower() != 'y':
            print_warning("Futtasd a migrációt és indítsd újra ezt a scriptet!")
            sys.exit(0)
    
    # Step 2: Analyze signals
    non_neutral_count = get_signal_stats()
    
    if non_neutral_count == 0:
        print_error("Nincs feldolgozható signal!")
        sys.exit(1)
    
    # Step 3: Run backtest
    print_info("\nIndítod a backtest-et? (y/n): ", end="")
    if input().strip().lower() != 'y':
        print_info("Megszakítva.")
        sys.exit(0)
    
    stats = run_backtest()
    
    if not stats:
        print_error("Backtest sikertelen!")
        sys.exit(1)
    
    # Step 4: Verify results
    if not verify_results():
        print_error("HIBA: A backtest nem hozott létre trade-eket megfelelően!")
        sys.exit(1)
    
    # Final summary
    print_header("Összefoglaló")
    print_success("Backtest sikeresen lefutott!")
    print_info(f"\n📊 Várható vs Valós:")
    print_info(f"  Várható trade-ek: {non_neutral_count} (NON-NEUTRAL signalok)", indent=1)
    print_info(f"  Létrehozott trade-ek: {stats['newly_opened'] + stats['already_closed'] + stats['newly_closed'] + stats['still_open']}", indent=1)
    print_info(f"  Skip (nincs adat): {stats['skipped_no_data']}", indent=1)
    print_info(f"  Skip (invalid): {stats['skipped_invalid']}", indent=1)
    
    if stats['skipped_no_data'] + stats['skipped_invalid'] > non_neutral_count * 0.5:
        print_warning("\n⚠️  Túl sok signal lett skip-elve (>50%)!")
        print_info("Ellenőrizd:", indent=1)
        print_info("- Van-e elég 5 perces árfolyam adat?", indent=2)
        print_info("- A signaloknak van-e SL/TP értéke?", indent=2)
        print_info("- A signal dátumok belül vannak az árfolyam adat időszakában?", indent=2)


if __name__ == "__main__":
    main()
