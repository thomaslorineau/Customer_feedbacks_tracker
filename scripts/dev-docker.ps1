# ============================================
# VibeCoding Development with Docker (Windows)
# Starts PostgreSQL + Redis, then API locally
# ============================================

param(
    [switch]$Stop,
    [switch]$Postgres,
    [switch]$Worker
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot | Split-Path -Parent

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VibeCoding Development Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check Docker
try {
    docker info | Out-Null
} catch {
    Write-Host "ERROR: Docker is not running" -ForegroundColor Red
    exit 1
}

Set-Location $ProjectRoot

if ($Stop) {
    Write-Host "Stopping development containers..." -ForegroundColor Yellow
    docker compose -f docker-compose.dev.yml down
    exit 0
}

# Start PostgreSQL and Redis
Write-Host "Starting PostgreSQL and Redis..." -ForegroundColor Green
docker compose -f docker-compose.dev.yml up -d

# Wait for services
Write-Host "Waiting for services..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check services
$pgReady = docker compose -f docker-compose.dev.yml exec -T postgres pg_isready -U vibe_user 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Waiting for PostgreSQL..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
}

$redisReady = docker compose -f docker-compose.dev.yml exec -T redis redis-cli ping 2>$null
if ($redisReady -ne "PONG") {
    Write-Host "Waiting for Redis..." -ForegroundColor Gray
    Start-Sleep -Seconds 3
}

Write-Host "Services ready!" -ForegroundColor Green

# Activate venv
$VenvPath = "$ProjectRoot\.venv\Scripts\Activate.ps1"
if (Test-Path $VenvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Gray
    & $VenvPath
}

# Set environment variables for local development with Docker services
$env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:USE_POSTGRES = "true"
$env:ENVIRONMENT = "development"

Set-Location "$ProjectRoot\backend"

if ($Postgres) {
    Write-Host ""
    Write-Host "Environment configured for PostgreSQL mode:" -ForegroundColor Green
    Write-Host "  DATABASE_URL: $env:DATABASE_URL" -ForegroundColor Gray
    Write-Host "  REDIS_URL: $env:REDIS_URL" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Run the API manually:" -ForegroundColor Yellow
    Write-Host "  uvicorn app.main:app --reload --host 127.0.0.1 --port 8000" -ForegroundColor White
    Write-Host ""
    Write-Host "Run the worker (optional):" -ForegroundColor Yellow
    Write-Host "  python worker.py" -ForegroundColor White
    exit 0
}

if ($Worker) {
    Write-Host "Starting worker..." -ForegroundColor Green
    python worker.py
    exit 0
}

# Start API with hot reload
Write-Host ""
Write-Host "Starting API server with hot reload..." -ForegroundColor Green
Write-Host "  API:  http://localhost:8000" -ForegroundColor White
Write-Host "  Docs: http://localhost:8000/api/docs" -ForegroundColor White
Write-Host ""

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
