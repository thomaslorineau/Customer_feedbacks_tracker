# Script pour créer le fichier .env
$envContent = @"
# ============================================
# Configuration OVH Customer Feedbacks Tracker
# ============================================

# ============================================
# BASE DE DONNÉES (OBLIGATOIRE)
# ============================================
# PostgreSQL est requis pour ce projet.
# 
# Option 1: Service cloud gratuit (RECOMMANDÉ pour tester)
#   - Supabase: https://supabase.com (gratuit jusqu'à 500MB)
#   - Neon: https://neon.tech (gratuit jusqu'à 3GB)
#   - Créez un projet et récupérez la connection string
#
# Option 2: PostgreSQL local
#   - Installez PostgreSQL depuis https://www.postgresql.org/download/windows/
#   - Créez une base de données: CREATE DATABASE ocft_tracker;
#   - Créez un utilisateur: CREATE USER ocft_user WITH PASSWORD 'votre_mot_de_passe';
#   - Donnez les permissions: GRANT ALL PRIVILEGES ON DATABASE ocft_tracker TO ocft_user;
#
# Format: postgresql://user:password@host:port/database
# Exemple cloud: postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
# Exemple local: postgresql://ocft_user:password@localhost:5432/ocft_tracker
DATABASE_URL=postgresql://ocft_user:ocft_secure_password_2026@localhost:5432/ocft_tracker
USE_POSTGRES=true

# ============================================
# ENVIRONNEMENT
# ============================================
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# ============================================
# REDIS (OPTIONNEL - pour les jobs asynchrones)
# ============================================
# Si Redis n'est pas installé, le système utilisera une file d'attente en mémoire
REDIS_URL=redis://localhost:6379/0

# ============================================
# CLÉS API (OPTIONNEL)
# ============================================
LLM_PROVIDER=openai
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GITHUB_TOKEN=
TRUSTPILOT_API_KEY=

# ============================================
# NOTIFICATIONS EMAIL (OPTIONNEL)
# ============================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_FROM_NAME=OVH Feedbacks Tracker

# ============================================
# CORS (pour le développement)
# ============================================
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080
"@

$envPath = Join-Path $PSScriptRoot ".env"
if (Test-Path $envPath) {
    Write-Host "⚠️  Le fichier .env existe déjà" -ForegroundColor Yellow
    $overwrite = Read-Host "Voulez-vous le remplacer? (o/N)"
    if ($overwrite -ne "o" -and $overwrite -ne "O") {
        Write-Host "Annulé." -ForegroundColor Yellow
        exit 0
    }
}

$envContent | Out-File -FilePath $envPath -Encoding utf8
Write-Host "✅ Fichier .env créé avec succès!" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  IMPORTANT: Configurez DATABASE_URL dans backend/.env" -ForegroundColor Yellow
Write-Host "   Voir backend/SETUP_POSTGRES.md pour les instructions" -ForegroundColor Yellow


