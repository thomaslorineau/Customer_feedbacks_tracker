/**
 * Logo Updater - Updates logo in navigation across all pages
 * Automatically checks for logo updates and refreshes navigation
 */

(function() {
    'use strict';

    // Check for logo updates from localStorage (only for recent uploads)
    function checkLogoUpdate() {
        const logoPath = localStorage.getItem('logoPath');
        const logoUpdated = localStorage.getItem('logoUpdated');
        
        // Only update if it's a very recent upload (< 10 seconds) to handle immediate updates
        if (logoPath && logoUpdated) {
            const updateTime = parseInt(logoUpdated);
            const now = Date.now();
            const timeSinceUpdate = now - updateTime;
            
            // Only force reload for very recent uploads (< 10 seconds)
            if (timeSinceUpdate < 10000) {
                updateLogoInNavigation(logoPath, true);
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

    // Check logo status on page load (ONLY ONCE - no periodic checks)
    async function checkLogoStatus(forceReload = false) {
        try {
            // First, check localStorage - if we have a logo path, use it directly
            const storedLogoPath = localStorage.getItem('logoPath');
            if (storedLogoPath && !forceReload) {
                // Use stored logo path - no API call needed
                updateLogoInNavigation(storedLogoPath, false);
                return;
            }
            
            // Only check API if no stored path or if forceReload is explicitly requested
            // This happens only once on initial page load
            const response = await fetch(`${window.location.origin}/api/logo-status`);
            const data = await response.json();
            
            if (data.exists) {
                updateLogoInNavigation(data.path, forceReload);
                // Store in localStorage for future use
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
            // Check logo status ONCE on page load (checks API only if no localStorage)
            checkLogoStatus(false);
            // Check for very recent uploads (< 10 seconds) - only runs once, no interval
            checkLogoUpdate();
        });
    } else {
        hideSvgFallback(); // Hide immediately if DOM is already ready
        // Check logo status ONCE on page load (checks API only if no localStorage)
        checkLogoStatus(false);
        // Check for very recent uploads (< 10 seconds) - only runs once, no interval
        checkLogoUpdate();
    }

    // Export function for manual updates (from settings page)
    window.updateLogoInNavigation = updateLogoInNavigation;
})();




