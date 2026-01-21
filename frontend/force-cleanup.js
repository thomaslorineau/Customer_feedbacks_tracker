/**
 * Script de nettoyage forcé à exécuter dans la console du navigateur
 * Copiez-collez ce code dans la console (F12) pour nettoyer immédiatement
 */

(function forceCleanup() {
    console.log('🧹 Nettoyage forcé du localStorage...');
    
    // Nettoyer le localStorage
    const jobId = localStorage.getItem('ovh_last_job');
    if (jobId) {
        console.log('Job trouvé:', jobId);
    }
    
    localStorage.removeItem('ovh_last_job');
    localStorage.removeItem('ovh_last_job_source');
    
    // Arrêter TOUS les intervalles possibles
    let stopped = 0;
    for (let i = 1; i < 10000; i++) {
        try {
            clearInterval(i);
            stopped++;
        } catch (e) {
            // Ignore errors
        }
    }
    
    // Arrêter les intervalles spécifiques
    if (window.jobPollInterval) {
        clearInterval(window.jobPollInterval);
        window.jobPollInterval = null;
        stopped++;
    }
    if (window.jobStatusInterval) {
        clearInterval(window.jobStatusInterval);
        window.jobStatusInterval = null;
        stopped++;
    }
    
    // Arrêter les timeouts
    for (let i = 1; i < 10000; i++) {
        try {
            clearTimeout(i);
        } catch (e) {
            // Ignore errors
        }
    }
    
    console.log('✅ Nettoyage terminé !');
    console.log('   - LocalStorage nettoyé');
    console.log('   - Intervalles arrêtés');
    console.log('💡 Rechargez maintenant la page avec Ctrl+F5');
    
    // Afficher un message visuel
    const msg = document.createElement('div');
    msg.style.cssText = 'position:fixed;top:20px;right:20px;background:#34d399;color:white;padding:20px;border-radius:8px;z-index:99999;box-shadow:0 4px 12px rgba(0,0,0,0.3);';
    msg.innerHTML = '<strong>✅ Nettoyage terminé !</strong><br>Rechargez avec Ctrl+F5';
    document.body.appendChild(msg);
    
    setTimeout(() => {
        msg.remove();
    }, 5000);
})();

