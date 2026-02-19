# ============================================================
# TrendSignal - Backtest Runner (PowerShell)
# Runs simulated trade backtest via API with detailed output
# ============================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  TrendSignal - Backtest Szimuláció" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Function to make API calls
function Invoke-ApiCall {
    param(
        [string]$Url,
        [string]$Method = "GET",
        [string]$Body = $null
    )
    
    try {
        if ($Body) {
            $response = Invoke-RestMethod -Uri $Url -Method $Method -ContentType "application/json" -Body $Body -ErrorAction Stop
        } else {
            $response = Invoke-RestMethod -Uri $Url -Method $Method -ErrorAction Stop
        }
        return $response
    }
    catch {
        Write-Host "❌ API hiba: $_" -ForegroundColor Red
        return $null
    }
}

# Step 1: Check backend
Write-Host "[1/4] Backend ellenőrzése..." -ForegroundColor Yellow
try {
    $health = Invoke-ApiCall -Url "http://localhost:8000/"
    if ($health) {
        Write-Host "✅ Backend fut (v$($health.version))" -ForegroundColor Green
        Write-Host "    Database: $($health.database)" -ForegroundColor Gray
        Write-Host "    Scheduler: $($health.scheduler_status)" -ForegroundColor Gray
    }
}
catch {
    Write-Host "❌ HIBA: Backend nem fut!" -ForegroundColor Red
    Write-Host "   Indítsd el: python api.py" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Step 2: Show current database stats
Write-Host "[2/4] Jelenlegi állapot..." -ForegroundColor Yellow
$dbStatus = Invoke-ApiCall -Url "http://localhost:8000/api/v1/database/status"
if ($dbStatus) {
    Write-Host "    Tickers: $($dbStatus.statistics.tickers)" -ForegroundColor Gray
    Write-Host "    Signals: $($dbStatus.statistics.signals) (Active: $($dbStatus.statistics.active_signals))" -ForegroundColor Gray
    Write-Host "    Simulated Trades: $($dbStatus.statistics.simulated_trades.total)" -ForegroundColor Gray
    Write-Host "      - Open: $($dbStatus.statistics.simulated_trades.open)" -ForegroundColor Gray
    Write-Host "      - Closed: $($dbStatus.statistics.simulated_trades.closed)" -ForegroundColor Gray
}

Write-Host ""

# Step 3: Run backtest
Write-Host "[3/4] Backtest indítása..." -ForegroundColor Yellow
Write-Host "    - Minden signal feldolgozása" -ForegroundColor Gray
Write-Host "    - Lezárt trade-ek skip-elve" -ForegroundColor Gray
Write-Host "    - Új pozíciók nyitása + exit triggerek" -ForegroundColor Gray
Write-Host ""

$startTime = Get-Date
$backtest = Invoke-ApiCall -Url "http://localhost:8000/api/v1/simulated-trades/backtest" -Method "POST" -Body "{}"

if ($backtest) {
    Write-Host "✅ Backtest befejezve!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Eredmények:" -ForegroundColor Cyan
    Write-Host "    Futási idő: $($backtest.execution_time_seconds) másodperc" -ForegroundColor White
    Write-Host ""
    Write-Host "    Összes signal: $($backtest.stats.total_signals)" -ForegroundColor White
    Write-Host "    ├─ Már lezárt: $($backtest.stats.already_closed)" -ForegroundColor Gray
    Write-Host "    ├─ Most lezárt: $($backtest.stats.newly_closed)" -ForegroundColor Green
    Write-Host "    ├─ Még nyitott: $($backtest.stats.still_open)" -ForegroundColor Yellow
    Write-Host "    ├─ Most nyitott: $($backtest.stats.newly_opened)" -ForegroundColor Cyan
    Write-Host "    ├─ Skip (nincs adat): $($backtest.stats.skipped_no_data)" -ForegroundColor DarkGray
    Write-Host "    └─ Skip (invalid): $($backtest.stats.skipped_invalid)" -ForegroundColor DarkGray
    
    if ($backtest.stats.errors.Count -gt 0) {
        Write-Host ""
        Write-Host "⚠️  Hibák ($($backtest.stats.errors.Count)):" -ForegroundColor Yellow
        foreach ($error in $backtest.stats.errors) {
            Write-Host "    - Signal $($error.signal_id) ($($error.symbol)): $($error.error)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "❌ Backtest sikertelen!" -ForegroundColor Red
}

Write-Host ""

# Step 4: Get summary statistics
Write-Host "[4/4] Teljes statisztikák..." -ForegroundColor Yellow
$stats = Invoke-ApiCall -Url "http://localhost:8000/api/v1/simulated-trades/stats/summary"

if ($stats) {
    Write-Host ""
    Write-Host "💰 Összesített eredmények:" -ForegroundColor Cyan
    Write-Host "    Összes trade: $($stats.total_trades)" -ForegroundColor White
    Write-Host "    ├─ Nyitott: $($stats.open_trades)" -ForegroundColor Yellow
    Write-Host "    └─ Lezárt: $($stats.closed_trades)" -ForegroundColor White
    
    if ($stats.closed_trades -gt 0) {
        Write-Host ""
        Write-Host "    Profitable: $($stats.profitable_trades)" -ForegroundColor Green
        Write-Host "    Veszteséges: $($stats.loss_trades)" -ForegroundColor Red
        Write-Host "    Win Rate: $($stats.win_rate)%" -ForegroundColor $(if ($stats.win_rate -gt 50) { "Green" } else { "Red" })
        Write-Host ""
        Write-Host "    Total P&L: $([math]::Round($stats.total_pnl_huf, 0).ToString('N0')) HUF" -ForegroundColor $(if ($stats.total_pnl_huf -gt 0) { "Green" } else { "Red" })
        Write-Host "    Átlag P&L: $([math]::Round($stats.avg_pnl_percent, 2))%" -ForegroundColor $(if ($stats.avg_pnl_percent -gt 0) { "Green" } else { "Red" })
        Write-Host "    Átlag tartás: $([math]::Round($stats.avg_duration_minutes / 60, 1)) óra" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✅ Kész!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 További lekérdezések:" -ForegroundColor Yellow
Write-Host "   Összes trade:" -ForegroundColor Gray
Write-Host "   curl http://localhost:8000/api/v1/simulated-trades/" -ForegroundColor White
Write-Host ""
Write-Host "   Nyitott pozíciók:" -ForegroundColor Gray
Write-Host "   curl 'http://localhost:8000/api/v1/simulated-trades/?status=OPEN'" -ForegroundColor White
Write-Host ""
Write-Host "   AAPL trade-ek:" -ForegroundColor Gray
Write-Host "   curl 'http://localhost:8000/api/v1/simulated-trades/?symbol=AAPL'" -ForegroundColor White
Write-Host ""
Write-Host "📖 API dokumentáció: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to exit"
