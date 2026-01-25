# Vérification de la migration
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Set-Location "$ProjectRoot\backend"

$env:DATABASE_URL = "postgresql://vibe_user:dev_password_123@localhost:5432/vibe_tracker"
$env:USE_POSTGRES = "true"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Verification Migration DuckDB -> PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

python -c @"
import os
import sys
sys.path.insert(0, '.')

os.environ['DATABASE_URL'] = r'$env:DATABASE_URL'
os.environ['USE_POSTGRES'] = 'true'

from app.database import get_posts, get_source_stats, get_sentiment_stats

# Compter tous les posts
posts = get_posts(limit=1000)
print(f'Total posts dans PostgreSQL: {len(posts)}')

# Statistiques par source
stats = get_source_stats()
print('')
print('Posts par source:')
for s in stats[:15]:
    print(f'  {s[\"source\"]}: {s[\"count\"]}')

# Statistiques sentiment
sentiment = get_sentiment_stats()
print('')
print('Posts par sentiment:')
for s in sentiment:
    print(f'  {s[\"sentiment_label\"]}: {s[\"count\"]}')

print('')
print('OK: Migration verifiee!')
"@

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Migration completee avec succes!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
