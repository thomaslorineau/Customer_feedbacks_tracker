# Script pour créer une clé SSH dédiée pour ce projet
# Usage: .\scripts\utils\create-project-ssh-key.ps1

Write-Host "🔐 Création d'une clé SSH dédiée pour ce projet" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Gray

$projectKey = "$env:USERPROFILE\.ssh\id_rsa_vibecoding"
$projectKeyPub = "$projectKey.pub"

if (Test-Path $projectKey) {
    Write-Host "`n⚠️  La clé existe déjà: $projectKey" -ForegroundColor Yellow
    $overwrite = Read-Host "Voulez-vous la recréer ? (o/N)"
    if ($overwrite -ne "o" -and $overwrite -ne "O") {
        Write-Host "Annulé" -ForegroundColor Gray
        exit 0
    }
    Remove-Item $projectKey -ErrorAction SilentlyContinue
    Remove-Item $projectKeyPub -ErrorAction SilentlyContinue
}

Write-Host "`n📝 Création de la clé SSH (sans passphrase)..." -ForegroundColor Yellow
Write-Host "   Fichier: $projectKey" -ForegroundColor Gray

# Créer la clé SSH sans passphrase
ssh-keygen -t rsa -b 4096 -f $projectKey -N '""' -C "vibecoding-project-key"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Clé SSH créée avec succès!" -ForegroundColor Green
    
    # Afficher la clé publique
    Write-Host "`n📋 Clé publique à ajouter dans Stash:" -ForegroundColor Yellow
    Write-Host "=" * 60 -ForegroundColor Gray
    Get-Content $projectKeyPub
    Write-Host "=" * 60 -ForegroundColor Gray
    
    Write-Host "`n📝 Instructions:" -ForegroundColor Cyan
    Write-Host "   1. Copiez la clé publique ci-dessus" -ForegroundColor White
    Write-Host "   2. Allez sur Stash → Settings → SSH keys" -ForegroundColor White
    Write-Host "   3. Ajoutez cette clé" -ForegroundColor White
    Write-Host "   4. Exécutez ensuite: .\scripts\utils\configure-git-ssh-key.ps1" -ForegroundColor White
    
} else {
    Write-Host "❌ Erreur lors de la création de la clé" -ForegroundColor Red
    exit 1
}



