/**
 * Script utilitaire pour nettoyer les jobs obsolètes du localStorage
 * À exécuter dans la console du navigateur (F12) si des erreurs 404 persistent
 */

(function clearStaleJobs() {
    console.log('🧹 Nettoyage des jobs obsolètes...');
    
    // Nettoyer le localStorage
    const lastJobId = localStorage.getItem('ovh_last_job');
    if (lastJobId) {
        console.log(`Job trouvé dans localStorage: ${lastJobId.substring(0, 8)}...`);
        
        // Vérifier si le job existe encore
        fetch(`/api/scrape/jobs/${lastJobId}`)
            .then(resp => {
                if (resp.status === 404) {
                    console.log('✅ Job obsolète détecté, nettoyage du localStorage...');
                    localStorage.removeItem('ovh_last_job');
                    localStorage.removeItem('ovh_last_job_source');
                    console.log('✅ LocalStorage nettoyé !');
                    
                    // Arrêter tous les intervalles de polling
                    if (window.jobPollInterval) {
                        clearInterval(window.jobPollInterval);
                        window.jobPollInterval = null;
                    }
                    if (window.jobStatusInterval) {
                        clearInterval(window.jobStatusInterval);
                        window.jobStatusInterval = null;
                    }
                    
                    // Masquer les éléments UI
                    const progressContainer = document.getElementById('scrapingProgressContainer');
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                    const jobPanel = document.getElementById('jobPanel');
                    if (jobPanel) {
                        jobPanel.style.display = 'none';
                    }
                    
                    console.log('✅ Nettoyage terminé ! Rechargez la page.');
                } else {
                    console.log('ℹ️ Le job existe encore, pas de nettoyage nécessaire.');
                }
            })
            .catch(err => {
                console.log('⚠️ Erreur lors de la vérification, nettoyage préventif...');
                localStorage.removeItem('ovh_last_job');
                localStorage.removeItem('ovh_last_job_source');
                console.log('✅ LocalStorage nettoyé !');
            });
    } else {
        console.log('ℹ️ Aucun job trouvé dans localStorage.');
    }
})();

