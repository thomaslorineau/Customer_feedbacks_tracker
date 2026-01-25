# ============================================
# Installation Automatique PostgreSQL
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Essayer d'installer via Scoop (version normale, nécessite admin mais peut fonctionner)
$scoopCmd = "$env:USERPROFILE\scoop\shims\scoop.cmd"

if (Test-Path $scoopCmd) {
    Write-Host "Tentative d'installation via Scoop..." -ForegroundColor Yellow
    & $scoopCmd install postgresql 2>&1 | Tee-Object -Variable output
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ PostgreSQL installé via Scoop!" -ForegroundColor Green
        
        # Trouver le chemin
        $pgPath = "$env:USERPROFILE\scoop\apps\postgresql\current"
        if (Test-Path "$pgPath\bin\initdb.exe") {
            Write-Host "PostgreSQL trouvé dans: $pgPath" -ForegroundColor Gray
            
            # Créer un lien vers l'emplacement attendu
            $targetPath = "$env:USERPROFILE\postgresql-portable"
            if (-not (Test-Path $targetPath)) {
                try {
                    New-Item -ItemType SymbolicLink -Path $targetPath -Target $pgPath -Force | Out-Null
                    Write-Host "✅ Lien créé" -ForegroundColor Green
                } catch {
                    # Copier seulement bin
                    New-Item -ItemType Directory -Path "$targetPath\bin" -Force | Out-Null
                    Copy-Item -Path "$pgPath\bin\*" -Destination "$targetPath\bin" -Recurse -Force
                }
            }
            
            Write-Host ""
            Write-Host "Configuration et test..." -ForegroundColor Cyan
            & "$ProjectRoot\scripts\quick-setup-postgres.ps1"
            exit 0
        }
    } else {
        Write-Host "⚠️ Installation Scoop échouée (peut nécessiter droits admin)" -ForegroundColor Yellow
    }
}

# Si Scoop échoue, vérifier si PostgreSQL portable existe déjà
$pgPortablePath = "$env:USERPROFILE\postgresql-portable\bin\initdb.exe"
if (Test-Path $pgPortablePath) {
    Write-Host "✅ PostgreSQL portable trouvé!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Configuration et test..." -ForegroundColor Cyan
    & "$ProjectRoot\scripts\quick-setup-postgres.ps1"
    exit 0
}

# Sinon, donner les instructions
Write-Host ""
Write-Host "❌ PostgreSQL non trouvé" -ForegroundColor Red
Write-Host ""
Write-Host "OPTIONS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Télécharger PostgreSQL portable manuellement:" -ForegroundColor Cyan
Write-Host "   https://github.com/garethflowers/postgresql-portable/releases" -ForegroundColor White
Write-Host "   Extraire dans: $env:USERPROFILE\postgresql-portable" -ForegroundColor White
Write-Host "   Puis relancer: .\scripts\auto-install-postgres.ps1" -ForegroundColor White
Write-Host ""
Write-Host "2. Utiliser un service cloud (RECOMMANDÉ):" -ForegroundColor Cyan
Write-Host "   - Supabase: https://supabase.com" -ForegroundColor White
Write-Host "   - Neon: https://neon.tech" -ForegroundColor White
Write-Host "   Puis configurer DATABASE_URL et lancer:" -ForegroundColor White
Write-Host "   python scripts/init-db-python.py" -ForegroundColor White
Write-Host ""
exit 1
