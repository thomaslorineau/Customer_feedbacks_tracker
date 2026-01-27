// Shared version loader for all pages
// Try to import API, but handle case where it's not available
let API = null;
let api = null;

// Initialize version check variables before they're used
let lastVersionCheck = 0;
const VERSION_CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

async function initAPI() {
    if (!api) {
        try {
            // Try to import API from dashboard/js
            const apiModule = await import('/dashboard/js/api.js');
            API = apiModule.API;
            api = new API();
        } catch (error) {
            console.warn('Could not import API module, using fetch directly:', error);
            // Fallback: use fetch directly
            api = {
                getVersion: async (timestamp = null) => {
                    try {
                        const baseURL = window.location.protocol + '//' + window.location.hostname + (window.location.port ? ':' + window.location.port : ':8000');
                        let url = `${baseURL}/api/version`;
                        if (timestamp) {
                            url += `?t=${timestamp}`;
                        }
                        const response = await fetch(url);
                        if (!response.ok) {
                            throw new Error(`Failed to get version: ${response.statusText}`);
                        }
                        return response.json();
                    } catch (error) {
                        console.warn('Failed to fetch version from API:', error);
                        return { version: '1.0.1' };
                    }
                }
            };
        }
    }
}

// Load and display version with cache-busting (but only if cache expired)
export async function loadVersion(force = false) {
    try {
        const now = Date.now();
        // Check cache first (unless forced)
        if (!force && now - lastVersionCheck < VERSION_CACHE_DURATION) {
            return; // Use cached version
        }
        
        await initAPI();
        // Add cache-busting timestamp to request only if forced or cache expired
        const timestamp = force ? new Date().getTime() : null;
        const response = await api.getVersion(timestamp);
        if (response && response.version) {
            const versionBadge = document.getElementById('versionBadge');
            if (versionBadge) {
                versionBadge.textContent = `v${response.version}`;
                if (response.build_date) {
                    versionBadge.title = `Version ${response.version} - Build: ${new Date(response.build_date).toLocaleDateString()}`;
                } else {
                    versionBadge.title = `Version ${response.version}`;
                }
            }
            lastVersionCheck = now;
        }
    } catch (error) {
        console.warn('Failed to load version:', error);
        // Keep default version if API fails
    }
}

// Make loadVersion available globally
window.loadVersion = loadVersion;

// Auto-load version when DOM is ready (use setTimeout to ensure all declarations are processed)
function initVersionLoader() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', loadVersion);
    } else {
        // Use setTimeout to ensure all module code is fully evaluated
        setTimeout(loadVersion, 0);
    }
}

// Initialize after module is fully loaded
initVersionLoader();

// Auto-refresh version every 5 minutes (instead of 30 seconds to reduce log noise)
let versionRefreshInterval = null;

function startVersionAutoRefresh() {
    // Clear existing interval if any
    if (versionRefreshInterval) {
        clearInterval(versionRefreshInterval);
    }
    // Refresh every 5 minutes (300000 ms) instead of 30 seconds
    versionRefreshInterval = setInterval(() => {
        const now = Date.now();
        // Only refresh if cache expired
        if (now - lastVersionCheck > VERSION_CACHE_DURATION) {
            loadVersion();
            lastVersionCheck = now;
        }
    }, 300000); // 5 minutes
}

// Start auto-refresh when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startVersionAutoRefresh);
} else {
    startVersionAutoRefresh();
}

// Cleanup interval on page unload
window.addEventListener('beforeunload', () => {
    if (versionRefreshInterval) {
        clearInterval(versionRefreshInterval);
    }
});

