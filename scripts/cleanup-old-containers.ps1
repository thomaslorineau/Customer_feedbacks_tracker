# ============================================
# Script de nettoyage des anciens containers vibe_* (PowerShell)
# ============================================

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Nettoyage des anciens containers vibe_*" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier que Docker est disponible
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Erreur: Docker n'est pas installé" -ForegroundColor Red
    exit 1
}

# Lister les anciens containers
$oldContainers = docker ps -a --format "{{.Names}}" | Select-String "^vibe_"

if (-not $oldContainers) {
    Write-Host "✓ Aucun ancien container détecté" -ForegroundColor Green
}
else {
    Write-Host "Anciens containers détectés:" -ForegroundColor Yellow
    $oldContainers | ForEach-Object { Write-Host "  - $_" }
    Write-Host ""
    
    $response = Read-Host "Voulez-vous arrêter et supprimer ces containers ? (o/N)"
    
    if ($response -match "^[Oo]$") {
        Write-Host ""
        Write-Host "Arrêt des anciens containers..." -ForegroundColor Cyan
        $oldContainers | ForEach-Object {
            $container = $_.ToString()
            docker stop $container 2>$null | Out-Null
            docker rm $container 2>$null | Out-Null
            Write-Host "  ✓ Supprimé: $container" -ForegroundColor Green
        }
        Write-Host "✓ Anciens containers supprimés" -ForegroundColor Green
    }
    else {
        Write-Host "Nettoyage annulé" -ForegroundColor Gray
    }
}

# Vérifier les anciens volumes
Write-Host ""
Write-Host "Vérification des volumes..." -ForegroundColor Yellow
$oldVolumes = docker volume ls --format "{{.Name}}" | Select-String "vibe|customer_feedbacks"

if (-not $oldVolumes) {
    Write-Host "✓ Aucun ancien volume détecté" -ForegroundColor Green
}
else {
    Write-Host "Anciens volumes détectés:" -ForegroundColor Yellow
    $oldVolumes | ForEach-Object { Write-Host "  - $_" }
    Write-Host ""
    Write-Host "⚠️  Les volumes contiennent les données PostgreSQL." -ForegroundColor Yellow
    Write-Host "   Ne les supprimez QUE si vous avez migré les données vers ocft_tracker" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Voulez-vous supprimer ces volumes ? (o/N)"
    
    if ($response -match "^[Oo]$") {
        Write-Host ""
        Write-Host "Suppression des anciens volumes..." -ForegroundColor Cyan
        $oldVolumes | ForEach-Object {
            $volume = $_.ToString()
            docker volume rm $volume 2>$null | Out-Null
            Write-Host "  ✓ Supprimé: $volume" -ForegroundColor Green
        }
        Write-Host "✓ Anciens volumes supprimés" -ForegroundColor Green
    }
    else {
        Write-Host "Suppression des volumes annulée" -ForegroundColor Gray
    }
}

# Vérifier les anciens réseaux
Write-Host ""
Write-Host "Vérification des réseaux..." -ForegroundColor Yellow
$oldNetworks = docker network ls --format "{{.Name}}" | Select-String "vibe|customer_feedbacks"

if (-not $oldNetworks) {
    Write-Host "✓ Aucun ancien réseau détecté" -ForegroundColor Green
}
else {
    Write-Host "Anciens réseaux détectés:" -ForegroundColor Yellow
    $oldNetworks | ForEach-Object { Write-Host "  - $_" }
    Write-Host ""
    $response = Read-Host "Voulez-vous supprimer ces réseaux ? (o/N)"
    
    if ($response -match "^[Oo]$") {
        Write-Host ""
        Write-Host "Suppression des anciens réseaux..." -ForegroundColor Cyan
        $oldNetworks | ForEach-Object {
            $network = $_.ToString()
            docker network rm $network 2>$null | Out-Null
            Write-Host "  ✓ Supprimé: $network" -ForegroundColor Green
        }
        Write-Host "✓ Anciens réseaux supprimés" -ForegroundColor Green
    }
    else {
        Write-Host "Suppression des réseaux annulée" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Nettoyage terminé" -ForegroundColor Green
Write-Host ""
Write-Host "Vous pouvez maintenant démarrer les nouveaux containers avec:" -ForegroundColor Cyan
Write-Host "  docker compose down"
Write-Host "  docker compose up -d"
