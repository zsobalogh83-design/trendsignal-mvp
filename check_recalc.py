import sqlite3

conn = sqlite3.connect('trendsignal.db')
trades = conn.execute('SELECT COUNT(*) FROM archive_simulated_trades').fetchone()[0]
print(f'archive_simulated_trades: {trades}')
try:
    conn.execute('BEGIN IMMEDIATE')
    conn.execute('ROLLBACK')
    print('DB: SZABAD - a folyamat befejezodott')
except Exception as e:
    print('DB: BLOKKOLT - meg fut...')
conn.close()
