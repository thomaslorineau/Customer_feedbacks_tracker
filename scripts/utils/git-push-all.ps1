# Script pour push develop et master avec SSH Agent
# Usage: .\scripts\utils\git-push-all.ps1

Write-Host "📤 Push Git avec SSH Agent" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Gray

# Vérifier si la clé est déjà dans ssh-agent
$keys = ssh-add -l 2>&1
if ($LASTEXITCODE -ne 0 -or $keys -match "The agent has no identities") {
    Write-Host "`n⚠️  Aucune clé SSH dans l'agent" -ForegroundColor Yellow
    Write-Host "Exécutez d'abord: .\scripts\utils\setup-ssh-agent.ps1" -ForegroundColor White
    Write-Host "OU ajoutez manuellement: ssh-add ~/.ssh/id_rsa_windows" -ForegroundColor White
    exit 1
}

Write-Host "✅ Clé SSH détectée dans l'agent" -ForegroundColor Green

# Push develop
Write-Host "`n📤 Push develop..." -ForegroundColor Yellow
git checkout develop
git push origin develop

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ develop pushé" -ForegroundColor Green
} else {
    Write-Host "❌ Erreur lors du push develop" -ForegroundColor Red
    exit 1
}

# Push master
Write-Host "`n📤 Push master..." -ForegroundColor Yellow
git checkout master
git push origin master

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ master pushé" -ForegroundColor Green
} else {
    Write-Host "❌ Erreur lors du push master" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Tous les pushs réussis!" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Gray


