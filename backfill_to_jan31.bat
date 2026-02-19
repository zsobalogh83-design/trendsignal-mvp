@echo off
REM ============================================================
REM TrendSignal - Smart Backfill to Earliest Signal
REM Fills price data from earliest signal (2026-01-31) to today
REM Only adds missing candles, keeps existing data
REM ============================================================

echo.
echo ============================================================
echo   TrendSignal - Smart Price Data Backfill
echo ============================================================
echo.

REM Step 1: Find earliest signal
echo [1/3] Legkorabbi signal keresese...
echo.

python -c "import sqlite3; conn = sqlite3.connect('trendsignal.db'); cursor = conn.cursor(); cursor.execute('SELECT MIN(DATE(created_at)) FROM signals WHERE ABS(combined_score) >= 25'); oldest = cursor.fetchone()[0]; conn.close(); print(f'Legkorabbi NON-NEUTRAL signal: {oldest}')"

echo.
echo.

REM Step 2: Show current coverage
echo [2/3] Jelenlegi arfolyam lefedetts^eg...
echo.

python -c "import sqlite3; conn = sqlite3.connect('trendsignal.db'); cursor = conn.cursor(); cursor.execute('SELECT ticker_symbol, MIN(DATE(timestamp)), MAX(DATE(timestamp)), COUNT(*) FROM price_data WHERE interval = \"5m\" GROUP BY ticker_symbol ORDER BY ticker_symbol'); rows = cursor.fetchall(); conn.close(); print('Ticker     | Legkorabbi  | Legujabb    | Gyertya'); print('-' * 60); [print(f'{r[0]:10s} | {r[1]} | {r[2]} | {r[3]:,}') for r in rows] if rows else print('(Nincs 5m adat meg)')"

echo.
echo.

REM Step 3: Backfill from 2026-01-31
echo [3/3] Backfill futtatasa...
echo    Idoszak: 2026-01-31 - 2026-02-17
echo    Mod: Csak hianyzo gyertya hozzaadasza
echo.
echo    Inditas? (Ctrl+C = megszakitas)
pause

echo.
echo Backfill futtatasa...
echo (Ez eltarthat 2-3 percig)
echo.

python backfill_price_data.py --from 2026-01-31 --to 2026-02-17

echo.
echo.

REM Verify results
echo ============================================================
echo   Ellenorzes
echo ============================================================
echo.

python -c "import sqlite3; conn = sqlite3.connect('trendsignal.db'); cursor = conn.cursor(); cursor.execute('SELECT ticker_symbol, MIN(DATE(timestamp)), MAX(DATE(timestamp)), COUNT(*) FROM price_data WHERE interval = \"5m\" GROUP BY ticker_symbol ORDER BY ticker_symbol'); rows = cursor.fetchall(); total = sum(r[3] for r in rows); conn.close(); print('Frissitett 5m adatok:'); print('Ticker     | Legkorabbi  | Legujabb    | Gyertya'); print('-' * 60); [print(f'{r[0]:10s} | {r[1]} | {r[2]} | {r[3]:,}') for r in rows]; print('-' * 60); print(f'OSSZESEN: {total:,} gyertya')"

echo.
echo.
echo ============================================================
echo ✅ Kesz!
echo ============================================================
echo.
echo 💡 Kovetkezo lepesek:
echo    1. Ellenorizd hogy minden ticker 2026-01-31-tol kezdodik
echo    2. Ha OK, futtasd: python reset_and_test.py
echo.
pause
