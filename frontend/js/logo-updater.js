/**
 * Logo Updater - Updates logo in navigation across all pages
 * Automatically checks for logo updates and refreshes navigation
 */

(function() {
    'use strict';

    // Check for logo updates from localStorage
    function checkLogoUpdate() {
        const logoPath = localStorage.getItem('logoPath');
        const logoUpdated = localStorage.getItem('logoUpdated');
        
        if (logoPath && logoUpdated) {
            const updateTime = parseInt(logoUpdated);
            const now = Date.now();
            // Only update if less than 10 seconds ago (recent update)
            if (now - updateTime < 10000) {
                updateLogoInNavigation(logoPath);
            }
        }
    }

    // Update logo in navigation menu
    function updateLogoInNavigation(logoPath) {
        if (!logoPath) {
            // No logo path provided - hide all logos
            const navLogos = document.querySelectorAll('.nav-logo img.ovh-logo, .nav-logo img[alt="OVHcloud"]');
            navLogos.forEach(img => {
                if (img.tagName === 'IMG') {
                    img.style.display = 'none';
                }
            });
            return;
        }
        
        // Update all logo images in navigation
        const navLogos = document.querySelectorAll('.nav-logo img.ovh-logo, .nav-logo img[alt="OVHcloud"]');
        navLogos.forEach(img => {
            if (img.tagName === 'IMG') {
                img.src = logoPath + '?t=' + Date.now();
                img.style.display = 'block';
                img.style.width = '40px';
                img.style.height = '40px';
                img.style.objectFit = 'contain';
                img.style.filter = 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1))';
                img.onerror = function() {
                    // If logo fails to load, hide it
                    this.style.display = 'none';
                };
                
                // Hide fallback SVG if exists
                const fallbackSvg = img.nextElementSibling;
                if (fallbackSvg && fallbackSvg.classList.contains('ovh-logo')) {
                    fallbackSvg.style.display = 'none';
                }
            }
        });
    }

    // Check logo status on page load
    async function checkLogoStatus() {
        try {
            const response = await fetch(`${window.location.origin}/api/logo-status`);
            const data = await response.json();
            
            if (data.exists) {
                updateLogoInNavigation(data.path);
                // Store in localStorage
                localStorage.setItem('logoPath', data.path);
            } else {
                // No logo exists - hide all logo images and show placeholder
                const navLogos = document.querySelectorAll('.nav-logo img.ovh-logo, .nav-logo img[alt="OVHcloud"]');
                navLogos.forEach(img => {
                    if (img.tagName === 'IMG') {
                        img.style.display = 'none';
                    }
                });
                // Remove from localStorage if no logo
                localStorage.removeItem('logoPath');
            }
        } catch (error) {
            console.debug('Logo status check failed (this is OK if no logo uploaded):', error);
            // On error, hide logos to be safe
            const navLogos = document.querySelectorAll('.nav-logo img.ovh-logo, .nav-logo img[alt="OVHcloud"]');
            navLogos.forEach(img => {
                if (img.tagName === 'IMG') {
                    img.style.display = 'none';
                }
            });
        }
    }

    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            checkLogoStatus();
            checkLogoUpdate();
            // Check for updates every 2 seconds
            setInterval(checkLogoUpdate, 2000);
        });
    } else {
        checkLogoStatus();
        checkLogoUpdate();
        setInterval(checkLogoUpdate, 2000);
    }

    // Export function for manual updates (from settings page)
    window.updateLogoInNavigation = updateLogoInNavigation;
})();



