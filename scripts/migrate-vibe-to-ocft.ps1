# ============================================
# Script de migration vibe -> ocft (PowerShell)
# Migre les données de vibe_tracker vers ocft_tracker
# ============================================

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Migration vibe -> ocft" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier que Docker est disponible
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Erreur: Docker n'est pas installé" -ForegroundColor Red
    exit 1
}

# Vérifier que les containers existent
$postgresContainer = docker ps -a --format "{{.Names}}" | Select-String "^ocft_postgres$"
if (-not $postgresContainer) {
    Write-Host "Erreur: Container ocft_postgres introuvable" -ForegroundColor Red
    Write-Host "   Assurez-vous que docker-compose.yml a été mis à jour et que les containers sont créés" -ForegroundColor Yellow
    exit 1
}

# Vérifier que PostgreSQL est prêt
Write-Host "Vérification de PostgreSQL..." -ForegroundColor Yellow
$pgReady = docker compose exec -T postgres pg_isready -U ocft_user -d ocft_tracker 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erreur: PostgreSQL n'est pas prêt" -ForegroundColor Red
    Write-Host "   Démarrez les containers avec: docker compose up -d postgres" -ForegroundColor Yellow
    exit 1
}

# Vérifier si vibe_tracker existe encore (ancienne base)
$oldDbExists = docker compose exec -T postgres psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='vibe_tracker'" 2>$null
$oldDbExists = $oldDbExists.Trim()

if ($oldDbExists -eq "1") {
    Write-Host "Ancienne base de données 'vibe_tracker' détectée" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Voulez-vous migrer les données de vibe_tracker vers ocft_tracker ? (o/N)"
    
    if ($response -match "^[Oo]$") {
        Write-Host ""
        Write-Host "Migration des données..." -ForegroundColor Cyan
        
        # Compter les posts dans l'ancienne base
        $oldCount = docker compose exec -T postgres psql -U vibe_user -d vibe_tracker -tAc "SELECT COUNT(*) FROM posts" 2>$null
        $oldCount = if ($oldCount) { [int]$oldCount.Trim() } else { 0 }
        Write-Host "  Posts dans vibe_tracker: $oldCount"
        
        # Compter les posts dans la nouvelle base
        $newCount = docker compose exec -T postgres psql -U ocft_user -d ocft_tracker -tAc "SELECT COUNT(*) FROM posts" 2>$null
        $newCount = if ($newCount) { [int]$newCount.Trim() } else { 0 }
        Write-Host "  Posts dans ocft_tracker: $newCount"
        
        if ($oldCount -gt 0 -and $newCount -eq 0) {
            Write-Host ""
            Write-Host "Export des données depuis vibe_tracker..." -ForegroundColor Yellow
            $exportFile = "$env:TEMP\vibe_posts_export.sql"
            docker compose exec -T postgres pg_dump -U vibe_user -d vibe_tracker --data-only --table=posts > $exportFile 2>$null
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Erreur lors de l'export" -ForegroundColor Red
                exit 1
            }
            
            Write-Host "Import des données dans ocft_tracker..." -ForegroundColor Yellow
            Get-Content $exportFile | docker compose exec -T postgres psql -U ocft_user -d ocft_tracker 2>$null
            
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Erreur lors de l'import" -ForegroundColor Red
                Remove-Item $exportFile -ErrorAction SilentlyContinue
                exit 1
            }
            
            # Vérifier le résultat
            $finalCount = docker compose exec -T postgres psql -U ocft_user -d ocft_tracker -tAc "SELECT COUNT(*) FROM posts" 2>$null
            $finalCount = if ($finalCount) { [int]$finalCount.Trim() } else { 0 }
            Write-Host ""
            Write-Host "✓ Migration terminée: $finalCount posts dans ocft_tracker" -ForegroundColor Green
            
            # Nettoyer
            Remove-Item $exportFile -ErrorAction SilentlyContinue
            
            Write-Host ""
            $deleteResponse = Read-Host "Voulez-vous supprimer l'ancienne base de données 'vibe_tracker' ? (o/N)"
            if ($deleteResponse -match "^[Oo]$") {
                Write-Host "Suppression de vibe_tracker..." -ForegroundColor Yellow
                docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS vibe_tracker;" 2>$null | Out-Null
                Write-Host "✓ Ancienne base supprimée" -ForegroundColor Green
            }
        }
        elseif ($newCount -gt 0) {
            Write-Host "⚠ La nouvelle base contient déjà des données ($newCount posts)" -ForegroundColor Yellow
            Write-Host "   Migration ignorée pour éviter les doublons" -ForegroundColor Yellow
        }
        else {
            Write-Host "⚠ Aucune donnée à migrer" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "Migration annulée" -ForegroundColor Gray
    }
}
else {
    Write-Host "✓ Aucune ancienne base de données détectée" -ForegroundColor Green
}

Write-Host ""
Write-Host "Migration terminée" -ForegroundColor Green
Write-Host ""
Write-Host "Pour vérifier:" -ForegroundColor Cyan
Write-Host "  docker compose exec postgres psql -U ocft_user -d ocft_tracker -c 'SELECT COUNT(*) FROM posts;'"
