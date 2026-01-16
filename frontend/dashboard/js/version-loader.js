// Shared version loader for all pages
// Try to import API, but handle case where it's not available
let API = null;
let api = null;

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
                getVersion: async () => {
                    try {
                        const baseURL = window.location.protocol + '//' + window.location.hostname + (window.location.port ? ':' + window.location.port : ':8000');
                        const response = await fetch(`${baseURL}/api/version`);
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

// Load and display version
export async function loadVersion() {
    try {
        await initAPI();
        const response = await api.getVersion();
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
        }
    } catch (error) {
        console.warn('Failed to load version:', error);
        // Keep default version if API fails
    }
}

// Make loadVersion available globally
window.loadVersion = loadVersion;

// Auto-load version when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadVersion);
} else {
    loadVersion();
}

