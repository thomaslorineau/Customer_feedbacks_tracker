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
            // Only update if less than 10 seconds ago (recent update) - force reload for recent updates
            if (now - updateTime < 10000) {
                updateLogoInNavigation(logoPath, true); // Force reload for recent uploads
            } else {
                // For older updates, still update but don't force reload
                updateLogoInNavigation(logoPath, false);
            }
        }
    }

    // Update logo in navigation menu
    function updateLogoInNavigation(logoPath, forceReload = false) {
        // Always hide SVG fallback first (no fake logo)
        const allSvgFallbacks = document.querySelectorAll('.nav-logo svg.ovh-logo');
        allSvgFallbacks.forEach(svg => {
            svg.style.display = 'none';
        });
        
        if (!logoPath) {
            // No logo path provided - hide all logos and ensure SVG fallback is hidden
            const navLogos = document.querySelectorAll('.nav-logo img.ovh-logo, .nav-logo img[alt="OVHcloud"]');
            navLogos.forEach(img => {
                if (img.tagName === 'IMG') {
                    img.style.display = 'none';
                }
            });
            return;
        }
        
        // Generate a fresh timestamp to force browser cache bypass
        const timestamp = Date.now();
        const logoUrl = logoPath + '?t=' + timestamp;
        
        // Update all logo images in navigation
        const navLogos = document.querySelectorAll('.nav-logo img.ovh-logo, .nav-logo img[alt="OVHcloud"]');
        navLogos.forEach(img => {
            if (img.tagName === 'IMG') {
                // Force reload by clearing src first, then setting new src with timestamp
                if (forceReload || img.src !== logoUrl) {
                    img.src = '';
                    // Use setTimeout to ensure browser clears cache
                    setTimeout(() => {
                        img.src = logoUrl;
                        img.style.display = 'block';
                        img.style.width = '40px';
                        img.style.height = '40px';
                        img.style.objectFit = 'contain';
                        img.style.filter = 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1))';
                    }, 10);
                } else {
                    img.src = logoUrl;
                    img.style.display = 'block';
                    img.style.width = '40px';
                    img.style.height = '40px';
                    img.style.objectFit = 'contain';
                    img.style.filter = 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1))';
                }
                
                img.onerror = function() {
                    // If logo fails to load, hide it (but never show SVG fallback)
                    this.style.display = 'none';
                };
                
                // Hide fallback SVG if exists (no fake logo)
                const fallbackSvg = img.nextElementSibling;
                if (fallbackSvg && fallbackSvg.classList.contains('ovh-logo')) {
                    fallbackSvg.style.display = 'none';
                }
            }
        });
    }

    // Check logo status on page load
    async function checkLogoStatus(forceReload = false) {
        try {
            // Check if there was a recent upload (less than 5 seconds ago)
            const logoUpdated = localStorage.getItem('logoUpdated');
            const isRecentUpload = logoUpdated && (Date.now() - parseInt(logoUpdated) < 5000);
            
            // If recent upload, skip API check to avoid overwriting
            if (isRecentUpload && !forceReload) {
                console.debug('Skipping logo status check - recent upload detected');
                return;
            }
            
            const response = await fetch(`${window.location.origin}/api/logo-status`);
            const data = await response.json();
            
            if (data.exists) {
                // Use fresh timestamp when loading from API
                // Force reload if explicitly requested or if it's a recent upload
                updateLogoInNavigation(data.path, forceReload || isRecentUpload);
                // Store in localStorage
                localStorage.setItem('logoPath', data.path);
            } else {
                // No logo exists - hide all logo images and ensure SVG fallback is hidden (no fake logo)
                const navLogos = document.querySelectorAll('.nav-logo img.ovh-logo, .nav-logo img[alt="OVHcloud"]');
                navLogos.forEach(img => {
                    if (img.tagName === 'IMG') {
                        img.style.display = 'none';
                    }
                });
                // Always hide SVG fallback (no fake logo)
                const allSvgFallbacks = document.querySelectorAll('.nav-logo svg.ovh-logo');
                allSvgFallbacks.forEach(svg => {
                    svg.style.display = 'none';
                });
                // Remove from localStorage if no logo
                localStorage.removeItem('logoPath');
            }
        } catch (error) {
            console.debug('Logo status check failed (this is OK if no logo uploaded):', error);
            // On error, hide logos to be safe and ensure SVG fallback is hidden (no fake logo)
            const navLogos = document.querySelectorAll('.nav-logo img.ovh-logo, .nav-logo img[alt="OVHcloud"]');
            navLogos.forEach(img => {
                if (img.tagName === 'IMG') {
                    img.style.display = 'none';
                }
            });
            // Always hide SVG fallback (no fake logo)
            const allSvgFallbacks = document.querySelectorAll('.nav-logo svg.ovh-logo');
            allSvgFallbacks.forEach(svg => {
                svg.style.display = 'none';
            });
        }
    }

    // Immediately hide SVG fallback on page load (no fake logo)
    function hideSvgFallback() {
        const allSvgFallbacks = document.querySelectorAll('.nav-logo svg.ovh-logo');
        allSvgFallbacks.forEach(svg => {
            svg.style.display = 'none';
        });
    }
    
    // Hide SVG fallback immediately (before DOM is ready)
    hideSvgFallback();
    
    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            hideSvgFallback(); // Hide again after DOM is ready
            checkLogoStatus();
            checkLogoUpdate();
            // Check for updates every 2 seconds
            setInterval(checkLogoUpdate, 2000);
        });
    } else {
        hideSvgFallback(); // Hide immediately if DOM is already ready
        checkLogoStatus();
        checkLogoUpdate();
        setInterval(checkLogoUpdate, 2000);
    }

    // Export function for manual updates (from settings page)
    window.updateLogoInNavigation = updateLogoInNavigation;
})();




