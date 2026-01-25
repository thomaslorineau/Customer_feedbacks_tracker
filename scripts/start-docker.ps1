# ============================================
# VibeCoding Docker Startup Script (Windows)
# ============================================
# This script starts the full Docker stack:
# - PostgreSQL database
# - Redis job queue
# - FastAPI API server
# - Worker service
# - Scheduler service
# ============================================

param(
    [switch]$Build,
    [switch]$Migrate,
    [switch]$Logs,
    [switch]$Stop,
    [switch]$Down,
    [switch]$Status
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VibeCoding Docker Manager" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "ERROR: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Change to project root
Set-Location $ProjectRoot

if ($Stop) {
    Write-Host "Stopping containers..." -ForegroundColor Yellow
    docker compose stop
    exit 0
}

if ($Down) {
    Write-Host "Stopping and removing containers..." -ForegroundColor Yellow
    docker compose down
    exit 0
}

if ($Status) {
    Write-Host "Container Status:" -ForegroundColor Green
    docker compose ps
    Write-Host ""
    Write-Host "Container Logs (last 10 lines each):" -ForegroundColor Green
    docker compose logs --tail=10
    exit 0
}

if ($Logs) {
    Write-Host "Following logs (Ctrl+C to stop)..." -ForegroundColor Yellow
    docker compose logs -f
    exit 0
}

# Build if requested or first time
if ($Build) {
    Write-Host "Building Docker images..." -ForegroundColor Yellow
    docker compose build --no-cache
}

# Start services
Write-Host "Starting Docker services..." -ForegroundColor Green
docker compose up -d

# Wait for PostgreSQL to be ready
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
do {
    Start-Sleep -Seconds 2
    $attempt++
    $result = docker compose exec -T postgres pg_isready -U ocft_user -d ocft_tracker 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "PostgreSQL is ready!" -ForegroundColor Green
        break
    }
    Write-Host "  Waiting... ($attempt/$maxAttempts)" -ForegroundColor Gray
} while ($attempt -lt $maxAttempts)

if ($attempt -ge $maxAttempts) {
    Write-Host "ERROR: PostgreSQL failed to start" -ForegroundColor Red
    docker compose logs postgres
    exit 1
}

# Wait for Redis to be ready
Write-Host "Waiting for Redis to be ready..." -ForegroundColor Yellow
$attempt = 0
do {
    Start-Sleep -Seconds 1
    $attempt++
    $result = docker compose exec -T redis redis-cli ping 2>$null
    if ($result -eq "PONG") {
        Write-Host "Redis is ready!" -ForegroundColor Green
        break
    }
    Write-Host "  Waiting... ($attempt/$maxAttempts)" -ForegroundColor Gray
} while ($attempt -lt $maxAttempts)

# Run migration if requested
if ($Migrate) {
    Write-Host "Running database migration..." -ForegroundColor Yellow
    
    # Check if DuckDB file exists
    if (Test-Path "$ProjectRoot\backend\data.duckdb") {
        Write-Host "Found DuckDB database, migrating data to PostgreSQL..." -ForegroundColor Cyan
        docker compose exec api python -m scripts.migrate_to_postgres --duckdb /app/data.duckdb
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Migration completed successfully!" -ForegroundColor Green
        } else {
            Write-Host "Migration had issues, check logs above" -ForegroundColor Yellow
        }
    } else {
        Write-Host "No DuckDB database found, starting fresh" -ForegroundColor Yellow
    }
}

# Show status
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Docker Stack Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
docker compose ps

Write-Host ""
Write-Host "Services:" -ForegroundColor Green
Write-Host "  - API:        http://localhost:8000" -ForegroundColor White
Write-Host "  - API Docs:   http://localhost:8000/api/docs" -ForegroundColor White
Write-Host "  - Dashboard:  http://localhost:8000/dashboard" -ForegroundColor White
Write-Host "  - PostgreSQL: localhost:5432" -ForegroundColor Gray
Write-Host "  - Redis:      localhost:6379" -ForegroundColor Gray

Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  .\start-docker.ps1 -Logs      # Follow all logs" -ForegroundColor Gray
Write-Host "  .\start-docker.ps1 -Stop      # Stop containers" -ForegroundColor Gray
Write-Host "  .\start-docker.ps1 -Down      # Stop and remove containers" -ForegroundColor Gray
Write-Host "  .\start-docker.ps1 -Status    # Show container status" -ForegroundColor Gray
Write-Host "  .\start-docker.ps1 -Build     # Rebuild images" -ForegroundColor Gray
Write-Host "  .\start-docker.ps1 -Migrate   # Migrate DuckDB to PostgreSQL" -ForegroundColor Gray
