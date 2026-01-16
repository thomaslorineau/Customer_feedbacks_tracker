# Script pour configurer SSH Agent et ajouter la clé SSH
# Usage: .\scripts\utils\setup-ssh-agent.ps1

Write-Host "🔐 Configuration SSH Agent" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Gray

# Démarrer ssh-agent si pas déjà démarré
$sshAgent = Get-Process ssh-agent -ErrorAction SilentlyContinue
if (-not $sshAgent) {
    Write-Host "`nDémarrage de ssh-agent..." -ForegroundColor Yellow
    # Méthode sans droits admin
    $env:SSH_AUTH_SOCK = [System.IO.Path]::Combine($env:TEMP, "ssh-agent.sock")
    Start-Process ssh-agent -ArgumentList "-a", $env:SSH_AUTH_SOCK -NoNewWindow
    Start-Sleep -Seconds 2
    Write-Host "✅ ssh-agent démarré" -ForegroundColor Green
} else {
    Write-Host "✅ ssh-agent déjà actif" -ForegroundColor Green
}

# Ajouter la clé SSH
$sshKey = "$env:USERPROFILE\.ssh\id_rsa_windows"
if (Test-Path $sshKey) {
    Write-Host "`nAjout de la clé SSH: $sshKey" -ForegroundColor Yellow
    Write-Host "Entrez votre passphrase (elle sera mémorisée pour cette session):" -ForegroundColor White
    ssh-add $sshKey
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Clé SSH ajoutée avec succès!" -ForegroundColor Green
        Write-Host "`nVous pouvez maintenant faire git push sans retaper la passphrase" -ForegroundColor Cyan
    } else {
        Write-Host "❌ Erreur lors de l'ajout de la clé" -ForegroundColor Red
    }
} else {
    Write-Host "⚠️  Clé SSH non trouvée: $sshKey" -ForegroundColor Yellow
    Write-Host "Vérifiez le chemin de votre clé SSH" -ForegroundColor White
}

Write-Host "`n" + "=" * 50 -ForegroundColor Gray


