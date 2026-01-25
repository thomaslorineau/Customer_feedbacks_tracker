# ============================================
# Téléchargement et Installation PostgreSQL Portable
# ============================================

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Installation PostgreSQL Portable" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$PostgresPath = "$env:USERPROFILE\postgresql-portable"
$DataDir = "$env:USERPROFILE\postgresql-data"
$BinPath = Join-Path $PostgresPath "bin"

# Vérifier si déjà installé
if (Test-Path (Join-Path $BinPath "initdb.exe")) {
    Write-Host "✅ PostgreSQL portable déjà installé" -ForegroundColor Green
    Write-Host "Chemin: $PostgresPath" -ForegroundColor Gray
} else {
    Write-Host "Téléchargement de PostgreSQL portable..." -ForegroundColor Yellow
    
    # Créer le dossier de destination
    New-Item -ItemType Directory -Path $PostgresPath -Force | Out-Null
    
    # Essayer de récupérer l'URL depuis GitHub API
    try {
        Write-Host "Récupération de l'URL de téléchargement..." -ForegroundColor Gray
        $releases = Invoke-RestMethod -Uri "https://api.github.com/repos/garethflowers/postgresql-portable/releases/latest" -ErrorAction Stop
        $asset = $releases.assets | Where-Object { $_.name -like "*win-x64.zip" } | Select-Object -First 1
        
        if ($asset) {
            $downloadUrl = $asset.browser_download_url
            Write-Host "URL trouvée: $downloadUrl" -ForegroundColor Gray
        } else {
            throw "Aucun asset win-x64.zip trouvé"
        }
    } catch {
        Write-Host "⚠️ Impossible de récupérer l'URL automatiquement" -ForegroundColor Yellow
        Write-Host "Utilisation d'une URL alternative..." -ForegroundColor Gray
        
        # URLs alternatives à essayer
        $downloadUrls = @(
            "https://github.com/garethflowers/postgresql-portable/releases/download/v15.5.0/postgresql-portable-15.5.0-win-x64.zip",
            "https://github.com/garethflowers/postgresql-portable/releases/download/v15.4.0/postgresql-portable-15.4.0-win-x64.zip",
            "https://github.com/garethflowers/postgresql-portable/releases/download/v15.3.0/postgresql-portable-15.3.0-win-x64.zip"
        )
        
        $downloadUrl = $null
        foreach ($url in $downloadUrls) {
            try {
                Write-Host "Test: $url" -ForegroundColor Gray
                $response = Invoke-WebRequest -Uri $url -Method Head -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
                if ($response.StatusCode -eq 200) {
                    $downloadUrl = $url
                    break
                }
            } catch {
                continue
            }
        }
        
        if (-not $downloadUrl) {
            Write-Host "❌ Impossible de trouver une URL de téléchargement valide" -ForegroundColor Red
            Write-Host ""
            Write-Host "Veuillez télécharger manuellement depuis:" -ForegroundColor Yellow
            Write-Host "  https://github.com/garethflowers/postgresql-portable/releases" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Et extraire dans: $PostgresPath" -ForegroundColor Yellow
            exit 1
        }
    }
    
    # Télécharger
    $zipPath = "$env:TEMP\postgresql-portable.zip"
    Write-Host "Téléchargement depuis: $downloadUrl" -ForegroundColor Green
    Write-Host "Cela peut prendre quelques minutes..." -ForegroundColor Gray
    
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing -TimeoutSec 300
        Write-Host "✅ Téléchargement terminé" -ForegroundColor Green
    } catch {
        Write-Host "❌ Erreur lors du téléchargement: $_" -ForegroundColor Red
        exit 1
    }
    
    # Extraire
    Write-Host "Extraction..." -ForegroundColor Yellow
    try {
        Expand-Archive -Path $zipPath -DestinationPath $PostgresPath -Force
        Remove-Item $zipPath -Force
        Write-Host "✅ Extraction terminée" -ForegroundColor Green
    } catch {
        Write-Host "❌ Erreur lors de l'extraction: $_" -ForegroundColor Red
        exit 1
    }
    
    # Vérifier que les binaires existent
    if (-not (Test-Path (Join-Path $BinPath "initdb.exe"))) {
        Write-Host "❌ Les binaires ne sont pas au bon endroit" -ForegroundColor Red
        Write-Host "Structure attendue: $BinPath\initdb.exe" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Vérifiez que l'archive a été correctement extraite" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "✅ PostgreSQL portable installé!" -ForegroundColor Green
Write-Host ""

# Maintenant configurer et tester
Write-Host "Configuration et test..." -ForegroundColor Cyan
& "$ProjectRoot\scripts\quick-setup-postgres.ps1"
