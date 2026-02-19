@echo off
REM ============================================================
REM TrendSignal - Complete Reset & Backtest
REM Clean slate: DROP table + Recreate + Run backtest
REM ============================================================

echo.
echo ============================================================
echo   TrendSignal - Clean Backtest (Development Mode)
echo ============================================================
echo.

REM Step 1: Drop simulated_trades table
echo [1/4] Simulated trades tabla torlese...
echo.

python -c "import sqlite3; conn = sqlite3.connect('trendsignal.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM simulated_trades'); before = cursor.fetchone()[0]; cursor.execute('DROP TABLE IF EXISTS simulated_trades'); conn.commit(); conn.close(); print(f'Torolve: {before} trade')"

if errorlevel 1 (
    echo ❌ Hiba a torlesnel!
    pause
    exit /b 1
)

echo ✅ Tabla torolve
echo.

REM Step 2: Recreate table
echo [2/4] Tabla ujrakezelese...
echo.

python migrate_create_simulated_trades.py

if errorlevel 1 (
    echo ❌ Hiba a tabla letrehozasanal!
    pause
    exit /b 1
)

echo.
echo.

REM Step 3: Show signal stats
echo [3/4] Signal statisztikak...
echo.

python -c "import sqlite3; conn = sqlite3.connect('trendsignal.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM signals WHERE ABS(combined_score) >= 25'); count = cursor.fetchone()[0]; cursor.execute('SELECT MIN(DATE(created_at)), MAX(DATE(created_at)) FROM signals WHERE ABS(combined_score) >= 25'); date_min, date_max = cursor.fetchone(); conn.close(); print(f'NON-NEUTRAL signalok: {count}'); print(f'Idoszak: {date_min} - {date_max}')"

echo.
echo.

REM Step 4: Run backtest
echo [4/4] Backtest futtatasa (CSAK AHOL VAN ARFOLYAM ADAT)...
echo    Idoszak: 2026-02-02 - 2026-02-17
echo.
echo    Inditas? (Ctrl+C = megszakitas)
pause

echo.
echo Backtest futtatasa...
echo (Ez eltarthat 1-2 percig)
echo.

curl -X POST "http://localhost:8000/api/v1/simulated-trades/backtest" ^
  -H "Content-Type: application/json" ^
  -d "{\"date_from\": \"2026-02-02\", \"date_to\": \"2026-02-17\"}" ^
  -s | python -m json.tool

echo.
echo.

REM Verify
echo ============================================================
echo   Ellenorzes
echo ============================================================
echo.

python -c "import sqlite3; conn = sqlite3.connect('trendsignal.db'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM signals WHERE ABS(combined_score) >= 25 AND DATE(created_at) BETWEEN \"2026-02-02\" AND \"2026-02-17\"'); expected = cursor.fetchone()[0]; cursor.execute('SELECT COUNT(*) FROM simulated_trades'); actual = cursor.fetchone()[0]; cursor.execute('SELECT status, COUNT(*) FROM simulated_trades GROUP BY status'); status_rows = cursor.fetchall(); conn.close(); print(f'Vart trade-ek: {expected} (febr 2-17 signalok)'); print(f'Letrehozott trade-ek: {actual}'); print(f'\nAllapot bontasban:'); [print(f'  {r[0]}: {r[1]}') for r in status_rows] if status_rows else print('  (nincs trade)')"

echo.
echo.
echo ============================================================
echo ✅ Kesz!
echo ============================================================
echo.
echo 💡 Mit varunk:
echo    - Vart trade-ek ≈ Letrehozott trade-ek
echo    - Minden signal kap egy trade-et (OPEN vagy CLOSED)
echo.
echo 📊 Statisztikak: curl http://localhost:8000/api/v1/simulated-trades/stats/summary
echo.
pause
