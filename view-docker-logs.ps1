# Script pour voir les logs Docker du serveur backend
# Usage: .\view-docker-logs.ps1 [--filter "Recommended Actions"] [--tail 100]

param(
    [string]$Filter = "",
    [int]$Tail = 100,
    [string]$Server = "gw2sdev-docker.ovh.net",
    [string]$Container = "ocft_api"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Logs Docker - Backend API" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Serveur: $Server" -ForegroundColor Gray
Write-Host "Container: $Container" -ForegroundColor Gray
Write-Host ""

if ($Filter) {
    Write-Host "Filtre: '$Filter'" -ForegroundColor Yellow
    Write-Host "Affichage des $Tail dernières lignes filtrées..." -ForegroundColor Yellow
    Write-Host ""
    
    $command = "docker logs --tail $Tail $Container 2>&1 | grep -i '$Filter'"
    Write-Host "Commande SSH:" -ForegroundColor Gray
    Write-Host "  ssh $Server '$command'" -ForegroundColor White
    Write-Host ""
    Write-Host "Exécution..." -ForegroundColor Cyan
    Write-Host ""
    
    ssh $Server $command
} else {
    Write-Host "Affichage des $Tail dernières lignes..." -ForegroundColor Yellow
    Write-Host ""
    
    $command = "docker logs --tail $Tail $Container"
    Write-Host "Commande SSH:" -ForegroundColor Gray
    Write-Host "  ssh $Server '$command'" -ForegroundColor White
    Write-Host ""
    Write-Host "Exécution..." -ForegroundColor Cyan
    Write-Host ""
    
    ssh $Server $command
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Pour voir les logs en temps réel:" -ForegroundColor Yellow
Write-Host "  ssh $Server 'docker logs -f $Container'" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
