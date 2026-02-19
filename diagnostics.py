"""
TrendSignal - Diagnostic SQL Queries
Debug why trades are not being created properly

Usage:
    python diagnostics.py
"""

import sqlite3
from datetime import datetime

DB_PATH = "trendsignal.db"


def run_query(cursor, title, query):
    """Run a query and print results"""
    print(f"\n{'=' * 70}")
    print(f"📊 {title}")
    print('=' * 70)
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("  (Nincs adat)")
            return
        
        # Print column headers
        col_names = [description[0] for description in cursor.description]
        header = " | ".join(f"{name:15s}" for name in col_names)
        print(header)
        print("-" * len(header))
        
        # Print rows
        for row in results[:20]:  # Limit to 20 rows
            formatted = " | ".join(f"{str(val)[:15]:15s}" for val in row)
            print(formatted)
        
        if len(results) > 20:
            print(f"... és még {len(results) - 20} sor")
        
    except Exception as e:
        print(f"❌ Hiba: {e}")


def main():
    """Run all diagnostic queries"""
    
    print("\n" + "=" * 70)
    print("  TrendSignal - Diagnostic Report")
    print("=" * 70)
    print(f"  Időpont: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Total counts
    run_query(cursor, "Tábla méretetek", """
        SELECT 
            'signals' as tabla, COUNT(*) as count FROM signals
        UNION ALL
        SELECT 'simulated_trades', COUNT(*) FROM simulated_trades
        UNION ALL
        SELECT 'price_data (5m)', COUNT(*) FROM price_data WHERE interval = '5m'
        UNION ALL
        SELECT 'tickers', COUNT(*) FROM tickers
    """)
    
    # 2. Signal score distribution
    run_query(cursor, "Signal Score Eloszlás", """
        SELECT 
            CASE 
                WHEN combined_score >= 65 THEN 'STRONG BUY (>=65)'
                WHEN combined_score >= 25 THEN 'MODERATE BUY (25-64)'
                WHEN combined_score <= -65 THEN 'STRONG SELL (<=-65)'
                WHEN combined_score <= -25 THEN 'MODERATE SELL (-64 to -25)'
                ELSE 'NEUTRAL (-24 to +24)'
            END as category,
            COUNT(*) as count,
            ROUND(AVG(combined_score), 2) as avg_score
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
    
    # 3. Signals missing SL/TP
    run_query(cursor, "Signalok Hiányzó SL/TP-vel", """
        SELECT 
            id,
            ticker_symbol,
            combined_score,
            stop_loss,
            take_profit,
            created_at
        FROM signals
        WHERE (combined_score >= 25 OR combined_score <= -25)
        AND (stop_loss IS NULL OR take_profit IS NULL)
        LIMIT 10
    """)
    
    # 4. Signal date distribution
    run_query(cursor, "Signal Dátum Eloszlás (utolsó 14 nap)", """
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as total_signals,
            SUM(CASE WHEN ABS(combined_score) >= 25 THEN 1 ELSE 0 END) as non_neutral
        FROM signals
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 14
    """)
    
    # 5. Price data coverage by ticker
    run_query(cursor, "5 Perces Árfolyam Lefedettség", """
        SELECT 
            ticker_symbol,
            MIN(timestamp) as oldest,
            MAX(timestamp) as newest,
            COUNT(DISTINCT DATE(timestamp)) as days,
            COUNT(*) as candles
        FROM price_data
        WHERE interval = '5m'
        GROUP BY ticker_symbol
        ORDER BY ticker_symbol
    """)
    
    # 6. Simulated trades summary
    run_query(cursor, "Simulated Trades Állapot", """
        SELECT 
            symbol,
            status,
            direction,
            COUNT(*) as count,
            ROUND(AVG(pnl_percent), 2) as avg_pnl_pct
        FROM simulated_trades
        GROUP BY symbol, status, direction
        ORDER BY symbol, status
    """)
    
    # 7. Sample signals without trades
    run_query(cursor, "Példa Signalok Trade Nélkül", """
        SELECT 
            s.id,
            s.ticker_symbol,
            s.combined_score,
            s.stop_loss,
            s.take_profit,
            s.created_at,
            CASE WHEN st.id IS NOT NULL THEN 'VAN' ELSE 'NINCS' END as has_trade
        FROM signals s
        LEFT JOIN simulated_trades st ON s.id = st.entry_signal_id
        WHERE ABS(s.combined_score) >= 25
        AND st.id IS NULL
        LIMIT 10
    """)
    
    # 8. Date overlap check
    run_query(cursor, "Signal vs Price Data Overlap Check", """
        SELECT 
            s.ticker_symbol,
            MIN(DATE(s.created_at)) as signal_from,
            MAX(DATE(s.created_at)) as signal_to,
            MIN(DATE(p.timestamp)) as price_from,
            MAX(DATE(p.timestamp)) as price_to,
            CASE 
                WHEN MIN(DATE(s.created_at)) >= MIN(DATE(p.timestamp)) 
                 AND MAX(DATE(s.created_at)) <= MAX(DATE(p.timestamp))
                THEN 'COVERED'
                ELSE 'GAP!'
            END as coverage
        FROM signals s
        LEFT JOIN price_data p ON s.ticker_symbol = p.ticker_symbol AND p.interval = '5m'
        WHERE ABS(s.combined_score) >= 25
        GROUP BY s.ticker_symbol
    """)
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ Diagnostic Complete")
    print("=" * 70)
    print("\n💡 Következő lépések:")
    print("   1. Ellenőrizd a 'GAP!' tickereket")
    print("   2. Nézd meg a hiányzó SL/TP signalokat")
    print("   3. Ellenőrizd hogy van-e overlap a signal és price data között")
    print()


if __name__ == "__main__":
    main()
