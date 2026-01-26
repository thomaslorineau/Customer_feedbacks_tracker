# ============================================
# Script de diagnostic Docker pour OCFT (Windows PowerShell)
# ============================================

param(
    [switch]$Help
)

$ErrorActionPreference = "Continue"

function Write-Header {
    param([string]$Text)
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Section {
    param([string]$Text)
    Write-Host $Text -ForegroundColor Blue
    Write-Host ""
}

function Write-Success {
    param([string]$Text)
    Write-Host "✓ $Text" -ForegroundColor Green
}

function Write-Error {
    param([string]$Text)
    Write-Host "✗ $Text" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Text)
    Write-Host "⚠️  $Text" -ForegroundColor Yellow
}

if ($Help) {
    Write-Host "Usage: .\scripts\diagnose-docker.ps1"
    Write-Host ""
    Write-Host "Ce script diagnostique les problèmes Docker et de connexion."
    exit 0
}

Write-Header "Diagnostic Docker - OCFT"

# 1. Vérifier que Docker est installé
Write-Section "1. Vérification de l'installation Docker"

$dockerInstalled = $false
$dockerPath = $null

# Vérifier dans le PATH
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker trouvé dans PATH: $dockerVersion"
        $dockerInstalled = $true
    }
} catch {
    # Docker pas dans PATH, chercher dans les emplacements communs
}

# Si pas trouvé, chercher Docker Desktop
if (-not $dockerInstalled) {
    $dockerDesktopPaths = @(
        "${env:ProgramFiles}\Docker\Docker\resources\bin\docker.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\resources\bin\docker.exe",
        "${env:LOCALAPPDATA}\Docker\Docker\resources\bin\docker.exe"
    )
    
    foreach ($path in $dockerDesktopPaths) {
        if (Test-Path $path) {
            $dockerPath = $path
            Write-Success "Docker Desktop trouvé: $path"
            Write-Warning "Docker n'est pas dans le PATH. Ajoutez-le ou utilisez le chemin complet."
            Write-Host "   Chemin complet: $path" -ForegroundColor Gray
            break
        }
    }
    
    if (-not $dockerPath) {
        Write-Error "Docker n'est pas installé ou introuvable"
        Write-Host ""
        Write-Host "Solutions:" -ForegroundColor Yellow
        Write-Host "  1. Installez Docker Desktop: https://www.docker.com/products/docker-desktop"
        Write-Host "  2. Ou exécutez: .\scripts\install-docker.ps1"
        Write-Host ""
        exit 1
    }
}

# 2. Vérifier que Docker Desktop est en cours d'exécution
Write-Section "2. Vérification du daemon Docker"

$dockerRunning = $false
try {
    if ($dockerPath) {
        & $dockerPath info 2>&1 | Out-Null
    } else {
        docker info 2>&1 | Out-Null
    }
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker daemon est actif"
        $dockerRunning = $true
    }
} catch {
    Write-Error "Docker daemon n'est pas en cours d'exécution"
}

if (-not $dockerRunning) {
    Write-Warning "Docker Desktop n'est probablement pas démarré"
    Write-Host ""
    Write-Host "Solutions:" -ForegroundColor Yellow
    Write-Host "  1. Démarrez Docker Desktop depuis le menu Démarrer"
    Write-Host "  2. Attendez que l'icône Docker apparaisse dans la barre des tâches"
    Write-Host "  3. Vérifiez que Docker Desktop est complètement démarré"
    Write-Host ""
    
    # Vérifier si le processus Docker Desktop existe
    $dockerProcess = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
    if ($dockerProcess) {
        Write-Host "  Processus Docker Desktop trouvé mais daemon non accessible" -ForegroundColor Yellow
        Write-Host "  Le daemon peut être en cours de démarrage..." -ForegroundColor Gray
    } else {
        Write-Host "  Docker Desktop n'est pas en cours d'exécution" -ForegroundColor Red
    }
    Write-Host ""
    exit 1
}

# 3. Vérifier l'état des containers
Write-Section "3. État des containers Docker"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

try {
    if ($dockerPath) {
        $containers = & $dockerPath compose ps -a 2>&1
    } else {
        $containers = docker compose ps -a 2>&1
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host $containers
    } else {
        Write-Warning "Impossible d'obtenir l'état des containers"
        Write-Host $containers -ForegroundColor Red
    }
} catch {
    Write-Error "Erreur lors de la vérification des containers: $_"
}

Write-Host ""

# 4. Vérifier les containers en cours d'exécution
Write-Section "4. Containers en cours d'exécution"

try {
    if ($dockerPath) {
        $running = & $dockerPath compose ps --format json 2>&1 | ConvertFrom-Json | Where-Object { $_.State -eq "running" }
    } else {
        $running = docker compose ps --format json 2>&1 | ConvertFrom-Json | Where-Object { $_.State -eq "running" }
    }
    
    if ($running) {
        Write-Success "Containers en cours d'exécution:"
        $running | ForEach-Object { Write-Host "  - $($_.Name) ($($_.Service))" -ForegroundColor Green }
    } else {
        Write-Error "Aucun container en cours d'exécution"
        Write-Host ""
        Write-Host "Pour démarrer les containers:" -ForegroundColor Yellow
        Write-Host "  .\scripts\start-docker.ps1" -ForegroundColor Gray
    }
} catch {
    Write-Warning "Impossible de vérifier les containers en cours d'exécution"
}

Write-Host ""

# 5. Vérifier les ports exposés
Write-Section "5. Ports exposés"

try {
    if ($dockerPath) {
        $ports = & $dockerPath compose ps --format "table {{.Name}}\t{{.Ports}}" 2>&1
    } else {
        $ports = docker compose ps --format "table {{.Name}}\t{{.Ports}}" 2>&1
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host $ports
    } else {
        Write-Warning "Impossible d'obtenir les ports"
    }
} catch {
    Write-Warning "Erreur lors de la vérification des ports"
}

Write-Host ""

# 6. Vérifier les logs de l'API
Write-Section "6. Dernières lignes des logs API (50 lignes)"

try {
    if ($dockerPath) {
        $logs = & $dockerPath compose logs api --tail=50 2>&1
    } else {
        $logs = docker compose logs api --tail=50 2>&1
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host $logs
    } else {
        Write-Warning "Impossible de récupérer les logs (le container API n'existe peut-être pas)"
    }
} catch {
    Write-Warning "Erreur lors de la récupération des logs"
}

Write-Host ""

# 7. Vérifier les ports en écoute sur le système
Write-Section "7. Ports en écoute sur le système"

$portsToCheck = @(11840, 5432, 6379)
foreach ($port in $portsToCheck) {
    $listening = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($listening) {
        Write-Success "Port $port est en écoute"
    } else {
        Write-Warning "Port $port n'est pas en écoute"
    }
}

Write-Host ""

# 8. Tester la connexion HTTP locale
Write-Section "8. Test de connexion HTTP locale"

try {
    $response = Invoke-WebRequest -Uri "http://localhost:11840/" -TimeoutSec 5 -ErrorAction Stop
    Write-Success "Le serveur répond sur localhost:11840 (Code: $($response.StatusCode))"
} catch {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11840/health" -TimeoutSec 5 -ErrorAction Stop
        Write-Success "Le serveur répond sur localhost:11840/health (Code: $($response.StatusCode))"
    } catch {
        Write-Error "Le serveur ne répond pas sur localhost:11840"
        Write-Host "  Erreur: $($_.Exception.Message)" -ForegroundColor Red
        
        # Vérifier si le port est utilisé par autre chose
        $portInUse = Get-NetTCPConnection -LocalPort 11840 -ErrorAction SilentlyContinue
        if ($portInUse) {
            Write-Warning "Le port 11840 est utilisé par un autre processus"
            $portInUse | ForEach-Object {
                $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
                if ($process) {
                    Write-Host "  Processus: $($process.Name) (PID: $($process.Id))" -ForegroundColor Yellow
                }
            }
        }
    }
}

Write-Host ""

# 9. Vérifier la configuration docker-compose
Write-Section "9. Configuration des ports dans docker-compose.yml"

if (Test-Path "docker-compose.yml") {
    $portConfig = Select-String -Path "docker-compose.yml" -Pattern "ports:" -Context 0,5
    if ($portConfig) {
        Write-Host $portConfig
    } else {
        Write-Warning "Configuration des ports non trouvée"
    }
} else {
    Write-Error "docker-compose.yml introuvable"
}

Write-Host ""

# 10. Vérifier les variables d'environnement
Write-Section "10. Variables d'environnement importantes"

if (Test-Path ".env") {
    $envVars = Get-Content ".env" | Select-String -Pattern "POSTGRES_|DATABASE_URL|CORS_ORIGINS"
    if ($envVars) {
        $envVars | ForEach-Object {
            $line = $_.Line
            # Masquer les mots de passe
            $line = $line -replace '(PASSWORD|SECRET)=.*', '$1=***'
            Write-Host $line -ForegroundColor Gray
        }
    } else {
        Write-Host "Variables non trouvées" -ForegroundColor Gray
    }
} else {
    Write-Host "Fichier .env non trouvé (utilise les valeurs par défaut)" -ForegroundColor Gray
}

Write-Host ""

# Résumé et recommandations
Write-Header "Résumé et recommandations"

# Vérifier si les containers sont démarrés
try {
    if ($dockerPath) {
        $psOutput = & $dockerPath compose ps 2>&1
    } else {
        $psOutput = docker compose ps 2>&1
    }
    
    if ($psOutput -notmatch "Up") {
        Write-Warning "Les containers ne sont pas démarrés"
        Write-Host "   Commande: .\scripts\start-docker.ps1" -ForegroundColor Gray
        Write-Host ""
    }
    
    if ($psOutput -notmatch "11840") {
        Write-Warning "Le port 11840 n'est pas exposé"
        Write-Host "   Vérifiez docker-compose.yml" -ForegroundColor Gray
        Write-Host ""
    }
    
    if ($psOutput -match "api.*unhealthy") {
        Write-Error "Le container API est unhealthy"
        Write-Host "   Consultez les logs: docker compose logs api" -ForegroundColor Gray
        Write-Host ""
    }
} catch {
    Write-Warning "Impossible de vérifier l'état des containers"
}

Write-Success "Diagnostic terminé"
Write-Host ""
Write-Host "Commandes utiles:" -ForegroundColor Yellow
Write-Host "  .\scripts\start-docker.ps1 -Status    # Voir l'état des containers" -ForegroundColor Gray
Write-Host "  .\scripts\start-docker.ps1 -Logs      # Suivre les logs de l'API" -ForegroundColor Gray
Write-Host "  .\scripts\start-docker.ps1            # Démarrer les containers" -ForegroundColor Gray
Write-Host "  .\scripts\start-docker.ps1 -Build     # Reconstruire et démarrer" -ForegroundColor Gray
Write-Host ""
