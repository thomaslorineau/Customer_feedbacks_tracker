# ============================================
# Script d'arrêt localhost
# ============================================

Write-Host "Arrêt du serveur localhost..." -ForegroundColor Yellow

# Trouver et arrêter les processus Python sur le port 8000
$connections = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($connections) {
    foreach ($conn in $connections) {
        $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($process -and $process.ProcessName -eq "python") {
            Write-Host "Arrêt du processus Python (PID: $($process.Id))..." -ForegroundColor Yellow
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "✅ Serveur arrêté" -ForegroundColor Green
} else {
    Write-Host "ℹ️  Aucun serveur trouvé sur le port 8000" -ForegroundColor Cyan
}

# Optionnel: arrêter PostgreSQL aussi
Write-Host ""
Write-Host "Voulez-vous arrêter PostgreSQL aussi ? (O/N)" -ForegroundColor Yellow
$response = Read-Host
if ($response -eq "O" -or $response -eq "o") {
    $pgBin = "C:\Users\tlorinea\scoop\apps\postgresql\current\bin"
    $pgCtl = Join-Path $pgBin "pg_ctl.exe"
    $dataDir = "C:\Users\tlorinea\scoop\apps\postgresql\current\data"
    
    if (Test-Path $pgCtl) {
        Write-Host "Arrêt de PostgreSQL..." -ForegroundColor Yellow
        & $pgCtl stop -D $dataDir 2>&1 | Out-Null
        Write-Host "   ✅ PostgreSQL arrêté" -ForegroundColor Green
    }
}
