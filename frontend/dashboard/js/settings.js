// Settings page - API Configuration
const API_BASE_URL = window.location.origin; // Use current server URL

// Debug: Log API base URL
console.log('API_BASE_URL:', API_BASE_URL);

// State
let configData = null;
let ovhModelsCache = null; // Cache for OVH models

// Load and display version
let versionData = null;
async function loadVersion() {
    try {
        console.log('[Version] Fetching from:', `${API_BASE_URL}/api/version`);
        const response = await fetch(`${API_BASE_URL}/api/version`);
        console.log('[Version] Response status:', response.status);
        if (response.ok) {
            versionData = await response.json();
            console.log('[Version] Data received:', JSON.stringify(versionData));
            const versionBadge = document.getElementById('versionBadge');
            if (versionBadge) {
                versionBadge.textContent = `v${versionData.version}`;
                versionBadge.title = `Version ${versionData.version} - Build: ${new Date(versionData.build_date).toLocaleDateString()}`;
                console.log('[Version] Badge updated to:', versionBadge.textContent);
            }
            // Also render in environment section (will be called after configData is loaded)
            if (configData) {
                renderEnvironmentInfo();
            }
        } else {
            console.error('[Version] Bad response:', response.status, await response.text());
        }
    } catch (error) {
        console.error('[Version] Failed to load:', error);
        // Still try to render with what we have
        if (configData) {
            renderEnvironmentInfo();
        }
    }
}

// Render Environment Info
function renderEnvironmentInfo() {
    const container = document.getElementById('environmentInfo');
    if (!container) {
        console.warn('[Environment] Container #environmentInfo not found');
        return;
    }
    
    console.log('[Environment] Rendering - configData:', !!configData, 'versionData:', !!versionData);
    if (!configData || !versionData) {
        console.warn('[Environment] Missing data - configData:', configData, 'versionData:', versionData);
        container.innerHTML = '<div class="skeleton-loader" style="height: 100px;"></div>';
        return;
    }
    console.log('[Environment] Data OK - version:', versionData.version, 'env:', configData.environment);
    
    const buildDate = versionData.build_date ? new Date(versionData.build_date).toLocaleDateString('fr-FR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }) : 'Unknown';
    
    container.innerHTML = `
        <div class="rate-limit-info" style="margin-bottom: 1.5rem;">
            <div class="info-card">
                <div class="info-card-label">Environment</div>
                <div class="info-card-value" style="font-size: 1.25rem; text-transform: capitalize;">
                    ${configData.environment || 'Unknown'}
                </div>
            </div>
            <div class="info-card">
                <div class="info-card-label">Version</div>
                <div class="info-card-value" style="font-size: 1.25rem;">
                    v${versionData.version || 'Unknown'}
                </div>
            </div>
            <div class="info-card">
                <div class="info-card-label">Build Date</div>
                <div class="info-card-value" style="font-size: 0.95rem; font-weight: 400;">
                    ${buildDate}
                </div>
            </div>
        </div>
        
        <div style="margin-top: 1.5rem;">
            <h3 style="font-size: 1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.75rem;">
                Version Notes
            </h3>
            <div style="background: var(--bg-secondary); border-radius: 8px; padding: 1rem; border-left: 3px solid var(--accent-primary);">
                <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6; margin: 0;">
                    <strong style="color: var(--text-primary);">v${versionData.version}</strong> - Build ${buildDate}
                </p>
                <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.6; margin: 0.5rem 0 0 0;">
                    This version includes improvements to the scraping system, enhanced error handling, and UI refinements.
                </p>
            </div>
        </div>
    `;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    initializeAccordion();
    loadVersion();
    loadConfiguration();
    loadBaseKeywords();
    loadPainPoints();
    loadAnalysisFocus();
    updateThemeToggle();
});

// Theme Management
function toggleTheme() {
    const body = document.body;
    const isDark = body.classList.contains('dark-mode');
    
    // Add transitioning class to prevent color transition artifacts
    body.classList.add('dark-mode-transitioning');
    
    if (isDark) {
        body.classList.remove('dark-mode');
        localStorage.setItem('theme', 'light');
    } else {
        body.classList.add('dark-mode');
        localStorage.setItem('theme', 'dark');
    }
    
    // Remove transitioning class after a short delay
    setTimeout(() => {
        body.classList.remove('dark-mode-transitioning');
    }, 200);
    
    // Dispatch event to notify other pages
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: isDark ? 'light' : 'dark' } }));
}

function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
    
    // Listen for theme changes from other pages
    window.addEventListener('themeChanged', (e) => {
        if (e.detail.theme === 'dark') {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
        updateThemeToggle();
    });
    
    // Setup theme toggle button
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Make toggleTheme available globally
    window.toggleTheme = toggleTheme;
}

// Load Configuration
async function loadConfiguration() {
    // Ensure renderEnvironmentInfo is called after both configData and versionData are loaded
    const checkAndRender = () => {
        if (configData && versionData) {
            renderEnvironmentInfo();
        }
    };
    
    // Check immediately if both are already loaded
    checkAndRender();
    try {
        // Add cache-busting timestamp to ensure fresh data
        const url = `${API_BASE_URL}/api/config?t=${Date.now()}`;
        console.log('Fetching configuration from:', url);
        const response = await fetch(url, {
            cache: 'no-store', // Prevent browser caching
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache'
            }
        });
        console.log('Response status:', response.status, response.statusText);
        if (!response.ok) {
            throw new Error(`Failed to load configuration: ${response.status} ${response.statusText}`);
        }
        
        configData = await response.json();
        console.log('Configuration loaded:', configData);
        
        // Load OVH models dynamically if OVH is configured
        await loadOVHModels();
        
        renderLLM();
        renderScrapersAPIKeys();
        renderRateLimiting();
        // Render environment info if version data is already loaded
        if (versionData) {
            renderEnvironmentInfo();
        }
    } catch (error) {
        console.error('Error loading configuration:', error);
        showError(`Failed to load configuration: ${error.message}`);
    }
}

// Accordion Management
function initializeAccordion() {
    // Load saved state from localStorage
    const savedState = localStorage.getItem('settingsAccordionState');
    if (savedState) {
        try {
            const state = JSON.parse(savedState);
            Object.keys(state).forEach(key => {
                const accordion = document.querySelector(`[data-accordion="${key}"]`);
                if (accordion) {
                    const header = accordion.querySelector('.accordion-header');
                    const content = accordion.querySelector('.accordion-content');
                    if (header && content) {
                        if (state[key]) {
                            header.classList.add('active');
                            content.classList.add('active');
                        } else {
                            header.classList.remove('active');
                            content.classList.remove('active');
                        }
                    }
                }
            });
        } catch (e) {
            console.warn('Failed to load accordion state:', e);
        }
    }
    // By default, all sections are closed (no active class in HTML)
}

function toggleAccordion(id) {
    const accordion = document.querySelector(`[data-accordion="${id}"]`);
    if (!accordion) return;
    
    const header = accordion.querySelector('.accordion-header');
    const content = accordion.querySelector('.accordion-content');
    
    if (!header || !content) return;
    
    const isActive = header.classList.contains('active');
    
    if (isActive) {
        header.classList.remove('active');
        content.classList.remove('active');
    } else {
        header.classList.add('active');
        content.classList.add('active');
    }
    
    // Save state to localStorage
    const state = {};
    document.querySelectorAll('.accordion').forEach(acc => {
        const accId = acc.getAttribute('data-accordion');
        const accHeader = acc.querySelector('.accordion-header');
        state[accId] = accHeader && accHeader.classList.contains('active');
    });
    localStorage.setItem('settingsAccordionState', JSON.stringify(state));
}

// Sub-accordion Management
function toggleSubAccordion(headerElement) {
    const content = headerElement.nextElementSibling;
    if (!content || !content.classList.contains('sub-accordion-content')) return;
    
    const isActive = headerElement.classList.contains('active');
    
    if (isActive) {
        headerElement.classList.remove('active');
        content.classList.remove('active');
    } else {
        headerElement.classList.add('active');
        content.classList.add('active');
    }
}

// Make functions available globally
window.toggleSubAccordion = toggleSubAccordion;

// Theme Toggle from Settings
function toggleThemeFromSettings() {
    toggleTheme();
    updateThemeToggle();
}

function updateThemeToggle() {
    const toggle = document.getElementById('themeToggle');
    if (toggle) {
        const isDark = document.body.classList.contains('dark-mode');
        if (isDark) {
            toggle.classList.add('active');
        } else {
            toggle.classList.remove('active');
        }
    }
}

// Load OVH Models Dynamically
async function loadOVHModels(forceApiKey = null, forceEndpoint = null) {
    // If forceApiKey is provided, use it instead of checking configData
    // This allows loading models even when OVH is not yet saved/configured
    if (forceApiKey) {
        console.log('[loadOVHModels] Loading models with provided API key (force mode)');
        try {
            const endpoint = forceEndpoint || 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1';
            const response = await fetch(`${API_BASE_URL}/api/ovh/models?t=${Date.now()}`, {
                cache: 'no-store',
                headers: {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache'
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to fetch OVH models: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                console.warn('[loadOVHModels] Error fetching OVH models:', data.error);
                ovhModelsCache = [];
                return;
            }
            
            if (data.models && data.models.length > 0) {
                ovhModelsCache = data.models;
                console.log(`[loadOVHModels] Successfully loaded ${data.models.length} models from OVH endpoint (force mode)`);
                return;
            } else {
                console.warn('[loadOVHModels] No models found in response');
                ovhModelsCache = [];
                return;
            }
        } catch (error) {
            console.error('[loadOVHModels] Error loading OVH models (force mode):', error);
            ovhModelsCache = [];
            return;
        }
    }
    
    // Check if OVH is configured
    const ovhKeyData = configData?.api_keys?.ovh;
    if (!ovhKeyData || !ovhKeyData.configured) {
        console.log('[loadOVHModels] OVH not configured, skipping model fetch');
        ovhModelsCache = null;
        return;
    }
    
    try {
        console.log('[loadOVHModels] Fetching available models from OVH endpoint...');
        const response = await fetch(`${API_BASE_URL}/api/ovh/models?t=${Date.now()}`, {
            cache: 'no-store',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to fetch OVH models: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            console.warn('[loadOVHModels] Error fetching OVH models:', data.error);
            ovhModelsCache = [];
            // Show error in UI if possible
            return;
        }
        
        if (data.models && data.models.length > 0) {
            ovhModelsCache = data.models;
            console.log(`[loadOVHModels] Successfully loaded ${data.models.length} models from OVH endpoint`);
            // Re-render LLM section to update the select dropdown
            renderLLM();
        } else {
            console.warn('[loadOVHModels] No models found in response');
            ovhModelsCache = [];
        }
    } catch (error) {
        console.error('[loadOVHModels] Error loading OVH models:', error);
        ovhModelsCache = [];
        // Re-render to show error state
        renderLLM();
    }
}

// Render LLM Section
function renderLLM() {
    const container = document.getElementById('llmContainer');
    const statusContainer = document.getElementById('llmStatusContainer');
    
    if (!container || !statusContainer) {
        console.error('LLM containers not found');
        return;
    }
    
    if (!configData || !configData.api_keys) {
        console.error('configData or api_keys missing', configData);
        return;
    }
    
    // Use dynamic OVH models if available, otherwise empty array (will be loaded dynamically)
    const ovhModels = ovhModelsCache && ovhModelsCache.length > 0 
        ? ovhModelsCache 
        : []; // Empty list - models will be loaded dynamically from endpoint
    
    const llmProviders = [
        { 
            id: 'ovh', 
            name: 'OVH AI Endpoints', 
            icon: '☁️',
            description: ovhModelsCache && ovhModelsCache.length > 0 
                ? `OVH AI Endpoints - ${ovhModelsCache.length} models available`
                : 'OVH AI Endpoints - OpenAI-compatible API (DeepSeek, Llama, Qwen, Mistral)',
            docsUrl: 'https://endpoints.ai.cloud.ovh.net/',
            hasModelSelect: true,
            models: ovhModels // Use dynamic models (empty array if not loaded yet)
        }
    ];
    
    // Check which LLMs are configured
    let configuredLLMs = [];
    let configuredCount = 0;
    
    llmProviders.forEach(provider => {
        const keyData = configData.api_keys[provider.id];
        if (keyData && keyData.configured) {
            configuredCount++;
            configuredLLMs.push(provider);
        }
    });
    
    // Determine active LLM provider (the one selected in config, or first configured)
    const activeLLM = configData.llm_provider && 
                      configData.api_keys[configData.llm_provider]?.configured 
                      ? configData.llm_provider 
                      : (configuredLLMs.length > 0 ? configuredLLMs[0].id : null);
    
    // Get active provider name
    const activeProviderName = activeLLM ? llmProviders.find(p => p.id === activeLLM)?.name || activeLLM : null;
    
    // Render status
    statusContainer.innerHTML = `
        <div class="rate-limit-info" style="margin-bottom: 1.5rem; max-width: 600px;">
            ${configuredLLMs.length > 0 ? `
                <div class="info-card">
                    <div class="info-card-label">Active Provider</div>
                    ${configuredLLMs.length > 1 ? `
                        <select 
                            id="llmProviderSelect" 
                            class="filter-select" 
                            style="width: 100%; margin-top: 0.5rem; padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; font-size: 1rem; background: var(--bg-primary); color: var(--text-primary);"
                            onchange="updateActiveLLMProvider(this.value)"
                        >
                            ${configuredLLMs.map(p => `
                                <option value="${p.id}" ${p.id === activeLLM ? 'selected' : ''}>
                                    ${p.icon} ${p.name}
                                </option>
                            `).join('')}
                        </select>
                        <p style="margin-top: 0.5rem; color: var(--text-secondary); font-size: 0.85em; line-height: 1.5;">
                            Select which LLM provider to use for AI analysis features.
                        </p>
                    ` : `
                        <div class="info-card-value" style="font-size: 1.25rem; text-transform: capitalize; margin-top: 0.5rem;">
                            ${activeProviderName}
                        </div>
                    `}
                </div>
                ${configuredLLMs.length > 1 ? `
                    <div class="info-card" style="margin-top: 0.75rem;">
                        <div class="info-card-label">Configured Providers</div>
                        <div class="info-card-value" style="font-size: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem;">
                            ${configuredLLMs.map(p => `<span style="padding: 0.25rem 0.75rem; background: var(--bg-secondary, #f3f4f6); border-radius: 4px; font-weight: 500;">${p.name}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
            ` : `
                <div class="info-card" style="border-left: 3px solid var(--warning, #f59e0b);">
                    <div class="info-card-label">Warning</div>
                    <div class="info-card-value" style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 400;">
                        No LLM provider configured. AI features will be disabled.
                    </div>
                </div>
            `}
        </div>
    `;
    
    // Update badge
    const badge = document.getElementById('llmBadge');
    if (badge) {
        badge.textContent = `${configuredCount}/${llmProviders.length}`;
    }
    
    // Render LLM providers
    container.innerHTML = `
        <div class="api-keys-groups">
            <div class="api-keys-group api-keys-group-llm">
                ${llmProviders.map(provider => renderProviderCard(provider)).join('')}
            </div>
        </div>
    `;
    
    // Attach event listeners to buttons after rendering
    llmProviders.forEach(provider => {
        attachButtonListeners(provider.id);
    });
}

// Render Scrapers API Keys Section
function renderScrapersAPIKeys() {
    const container = document.getElementById('scrapersApiKeysContainer');
    if (!container) {
        console.error('scrapersApiKeysContainer not found');
        return;
    }
    
    if (!configData || !configData.api_keys) {
        console.error('configData or api_keys missing', configData);
        return;
    }
    
    const scraperProviders = [
        { 
            id: 'discord', 
            name: 'Discord', 
            icon: '💬',
            description: 'Scrape Discord messages from OVH server (requires bot token and guild ID)',
            docsUrl: 'https://discord.com/developers/docs/getting-started',
            requiresAuth: true,
            fields: [
                { name: 'DISCORD_BOT_TOKEN', label: 'Bot Token' },
                { name: 'DISCORD_GUILD_ID', label: 'Guild (Server) ID' }
            ]
        },
        { 
            id: 'github', 
            name: 'GitHub', 
            icon: '🐙',
            description: 'Personal access token for enhanced rate limits',
            docsUrl: 'https://github.com/settings/tokens',
            group: 'scraper'
        },
        { 
            id: 'trustpilot', 
            name: 'Trustpilot', 
            icon: '⭐',
            description: 'API access for Trustpilot review scraping',
            docsUrl: 'https://developers.trustpilot.com/',
            group: 'scraper'
        },
        { 
            id: 'linkedin', 
            name: 'LinkedIn', 
            icon: '💼',
            description: 'Scrape LinkedIn posts (requires your own API credentials)',
            docsUrl: 'https://www.linkedin.com/developers/apps',
            requiresAuth: true,
            fields: [
                { name: 'LINKEDIN_CLIENT_ID', label: 'Client ID' },
                { name: 'LINKEDIN_CLIENT_SECRET', label: 'Client Secret' }
            ]
        },
        { 
            id: 'twitter', 
            name: 'Twitter/X API', 
            icon: '🐦',
            description: 'Official Twitter API (requires your own Bearer Token)',
            docsUrl: 'https://developer.twitter.com/en/portal/dashboard',
            requiresAuth: true,
            fields: [
                { name: 'TWITTER_BEARER_TOKEN', label: 'Bearer Token' }
            ]
        }
    ];
    
    // Count configured keys
    let configuredCount = 0;
    scraperProviders.forEach(provider => {
        const keyData = configData.api_keys[provider.id];
        if (keyData && keyData.configured) {
            configuredCount++;
        }
    });
    
    // Update badge
    const badge = document.getElementById('scrapersApiKeysBadge');
    if (badge) {
        badge.textContent = `${configuredCount}/${scraperProviders.length}`;
    }
    
    // Render scraper providers
    container.innerHTML = `
        <div class="api-keys-groups">
            <div class="api-keys-group">
                ${scraperProviders.map(provider => renderProviderCard(provider)).join('')}
            </div>
        </div>
    `;
    
    // Attach event listeners to buttons after rendering
    scraperProviders.forEach(provider => {
        attachButtonListeners(provider.id);
    });
}

// Attach event listeners to provider buttons
function attachButtonListeners(providerId) {
    const editBtn = document.getElementById(`edit-btn-${providerId}`);
    const deleteBtn = document.getElementById(`delete-btn-${providerId}`);
    
    if (editBtn) {
        editBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Edit button clicked for:', providerId);
            if (window.enableEditMode) {
                window.enableEditMode(providerId);
            } else {
                console.error('enableEditMode function not available');
            }
        });
    }
    
    if (deleteBtn) {
        deleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log('Delete button clicked for:', providerId);
            if (window.deleteAPIKey) {
                window.deleteAPIKey(providerId);
            } else {
                console.error('deleteAPIKey function not available');
            }
        });
    }
}

function renderProviderCard(provider) {
    const keyData = configData?.api_keys?.[provider.id];
    // For Discord, check if it exists even if not configured (it needs to be shown)
    if (!keyData && provider.id !== 'discord' && provider.id !== 'ovh') {
        console.warn(`No key data for provider: ${provider.id}`);
        return '';
    }
    // For Discord and OVH, create default keyData if missing
    const actualKeyData = keyData || { configured: false, masked: null, length: 0 };
    // Explicitly check configured status - ensure it's a boolean
    const isConfigured = actualKeyData.configured === true;
    const maskedKey = actualKeyData.masked || 'Not configured';
    
    // Debug log for LLM providers
    if (['openai', 'anthropic', 'mistral', 'ovh'].includes(provider.id)) {
        console.log(`[renderProviderCard] ${provider.id}: configured=${actualKeyData.configured}, isConfigured=${isConfigured}, keyData:`, actualKeyData);
    }
    
    return `
        <div class="api-key-card" data-provider="${provider.id}">
            <div class="api-key-header">
                <div class="api-key-title">
                    <span style="font-size: 1.5rem;">${provider.icon}</span>
                    <div>
                        <h3>${provider.name}</h3>
                        <p style="margin: 0.25rem 0 0 0; font-size: 0.875rem; color: var(--text-secondary);">
                            ${provider.description}
                        </p>
                    </div>
                </div>
                <span class="status-badge ${isConfigured ? 'configured' : 'not-configured'}">
                    ${isConfigured ? '✓ Configured' : '✗ Not Configured'}
                </span>
            </div>
            
            ${isConfigured ? `
                <div class="api-key-value">
                    <div class="key-display" 
                         id="key-${provider.id}">
                        ${maskedKey}
                    </div>
                    <div class="key-actions">
                        <button class="btn-icon" 
                                id="edit-btn-${provider.id}"
                                title="Edit API key"
                                type="button"
                                data-provider="${provider.id}"
                                data-action="edit">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                            </svg>
                            Edit
                        </button>
                        <button class="btn-icon btn-danger" 
                                id="delete-btn-${provider.id}"
                                title="Delete API key"
                                type="button"
                                data-provider="${provider.id}"
                                data-action="delete"
                                style="color: var(--error-color);">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                            </svg>
                            Delete
                        </button>
                    </div>
                </div>
                
                <div class="api-key-info">
                    <div class="info-item">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 14px; height: 14px;">
                            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
                        </svg>
                        Length: ${keyData.length} chars
                    </div>
                    ${provider.id === 'ovh' && keyData.model ? `
                    <div class="info-item">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 14px; height: 14px;">
                            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                            <path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>
                        </svg>
                        Model: <a href="https://endpoints.ai.cloud.ovh.net/" target="_blank" style="color: #6366f1; text-decoration: underline; font-weight: 500; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 4px;" onmouseover="this.style.color='#4f46e5'; this.style.textDecoration='underline'; this.style.opacity='0.8'" onmouseout="this.style.color='#6366f1'; this.style.textDecoration='underline'; this.style.opacity='1'" title="Voir la documentation OVH AI Endpoints pour ${keyData.model}">
                            <span>${keyData.model}</span>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 12px; height: 12px; flex-shrink: 0;">
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                                <polyline points="15 3 21 3 21 9"/>
                                <line x1="10" y1="14" x2="21" y2="3"/>
                            </svg>
                        </a>
                    </div>
                    ` : ''}
                    <div class="info-item">
                        <a href="${provider.docsUrl}" target="_blank" style="color: var(--accent-color); text-decoration: none;">
                            📄 Get API Key
                        </a>
                    </div>
                </div>
            ` : `
                <div class="api-key-form-container">
                    <form class="api-key-form" onsubmit="event.preventDefault(); saveAPIKey('${provider.id}');">
                        ${provider.fields && provider.fields.length > 1 ? 
                            // Multiple fields (e.g., LinkedIn)
                            provider.fields.map(field => `
                                <div class="form-group">
                                    <label for="key-input-${provider.id}-${field.name}">${field.label}</label>
                                    <div class="input-with-button">
                                        <input 
                                            type="password" 
                                            id="key-input-${provider.id}-${field.name}"
                                            class="api-key-input"
                                            placeholder="Enter your ${field.label}"
                                            autocomplete="off"
                                        />
                                        <button type="button" class="btn-toggle-visibility" onclick="toggleInputVisibility('key-input-${provider.id}-${field.name}')">
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                                <circle cx="12" cy="12" r="3"/>
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            `).join('') :
                            // Single field (default) or OVH with model selector
                            `
                                <div class="form-group">
                                    <label for="key-input-${provider.id}">API Key</label>
                                    <div class="input-with-button">
                                        <input 
                                            type="password" 
                                            id="key-input-${provider.id}"
                                            class="api-key-input"
                                            placeholder="Enter your ${provider.name} API key"
                                            autocomplete="off"
                                        />
                                        <button type="button" class="btn-toggle-visibility" onclick="toggleInputVisibility('key-input-${provider.id}')">
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                                <circle cx="12" cy="12" r="3"/>
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                                ${provider.hasModelSelect && provider.models ? `
                                    <div class="form-group">
                                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                                            <label for="model-select-${provider.id}" style="margin: 0;">Model</label>
                                            ${provider.id === 'ovh' ? `
                                                <button 
                                                    type="button" 
                                                    onclick="loadOVHModels().then(() => renderLLM());" 
                                                    style="background: #6366f1; color: white; border: none; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: 500; transition: background 0.2s;"
                                                    onmouseover="this.style.background='#4f46e5'" 
                                                    onmouseout="this.style.background='#6366f1'"
                                                    title="Refresh available models from OVH endpoint"
                                                >
                                                    🔄 Refresh Models
                                                </button>
                                            ` : ''}
                                        </div>
                                        <select 
                                            id="model-select-${provider.id}"
                                            class="api-key-input"
                                            style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 0.95rem;"
                                            ${provider.id === 'ovh' && (!provider.models || provider.models.length === 0) ? 'disabled' : ''}
                                        >
                                            ${provider.models && provider.models.length > 0 ? provider.models.map(model => `
                                                <option value="${model}" ${model === (provider.defaultModel || provider.models[0]) ? 'selected' : ''}>${model}</option>
                                            `).join('') : `
                                                <option value="">Loading models...</option>
                                            `}
                                        </select>
                                        <p style="margin-top: 0.5rem; color: var(--text-secondary); font-size: 0.85em;">
                                            ${provider.id === 'ovh' && ovhModelsCache && ovhModelsCache.length > 0 
                                                ? `${ovhModelsCache.length} models loaded from your OVH endpoint`
                                                : provider.id === 'ovh'
                                                    ? 'Select the model to use with OVH AI Endpoints (click Refresh to load available models)'
                                                    : 'Select the model to use with OVH AI Endpoints'}
                                        </p>
                                    </div>
                                ` : ''}
                            `
                        }
                        <div class="form-actions">
                            <button type="submit" class="btn-save-key" id="save-btn-${provider.id}">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M20 6L9 17l-5-5"/>
                                </svg>
                                Save API Key
                            </button>
                            <a href="${provider.docsUrl}" target="_blank" class="btn-get-key">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                                    <polyline points="15 3 21 3 21 9"/>
                                    <line x1="10" y1="14" x2="21" y2="3"/>
                                </svg>
                                Get API Key
                            </a>
                        </div>
                    </form>
                </div>
            `}
        </div>
    `;
}

// Render Rate Limiting Info
function renderRateLimiting() {
    const container = document.getElementById('rateLimitInfo');
    const rateLimiting = configData.rate_limiting;
    
    container.innerHTML = `
        <div class="info-card">
            <div class="info-card-label">Requests per Window</div>
            <div class="info-card-value">${rateLimiting.requests_per_window}</div>
        </div>
        <div class="info-card">
            <div class="info-card-label">Window Duration</div>
            <div class="info-card-value">${rateLimiting.window_seconds}s</div>
        </div>
    `;
}


// Enable Edit Mode
async function enableEditMode(provider) {
    console.log('enableEditMode called for provider:', provider);
    const card = document.querySelector(`[data-provider="${provider}"]`);
    if (!card) {
        console.error(`Card not found for provider: ${provider}`);
        return;
    }
    
    const keyData = configData.api_keys[provider];
    if (!keyData || !keyData.configured) {
        console.warn(`Provider ${provider} is not configured, cannot edit`);
        return;
    }
    
    // Get provider info
    const llmProviders = [
        { id: 'ovh', name: 'OVH AI Endpoints', icon: '☁️', docsUrl: 'https://endpoints.ai.cloud.ovh.net/' },
        { id: 'openai', name: 'OpenAI', icon: '🤖', docsUrl: 'https://platform.openai.com/api-keys' },
        { id: 'anthropic', name: 'Anthropic', icon: '🧠', docsUrl: 'https://console.anthropic.com/' },
        { id: 'mistral', name: 'Mistral AI', icon: '🌊', docsUrl: 'https://console.mistral.ai/api-keys/' }
    ];
    
    const scraperProviders = [
        { id: 'discord', name: 'Discord', icon: '💬', docsUrl: 'https://discord.com/developers/docs/getting-started' },
        { id: 'github', name: 'GitHub', icon: '🐙', docsUrl: 'https://github.com/settings/tokens' },
        { id: 'trustpilot', name: 'Trustpilot', icon: '⭐', docsUrl: 'https://developers.trustpilot.com/' },
        { id: 'linkedin', name: 'LinkedIn', icon: '💼', docsUrl: 'https://www.linkedin.com/developers/apps' },
        { id: 'twitter', name: 'Twitter/X API', icon: '🐦', docsUrl: 'https://developer.twitter.com/en/portal/dashboard' }
    ];
    
    const providerInfo = [...llmProviders, ...scraperProviders].find(p => p.id === provider);
    if (!providerInfo) {
        console.error(`Provider info not found for: ${provider}`);
        return;
    }
    
    // Check if provider requires multiple fields (like LinkedIn, Discord)
    const multiFieldProviders = {
        'linkedin': [
            { name: 'LINKEDIN_CLIENT_ID', label: 'Client ID' },
            { name: 'LINKEDIN_CLIENT_SECRET', label: 'Client Secret' }
        ],
        'discord': [
            { name: 'DISCORD_BOT_TOKEN', label: 'Bot Token' },
            { name: 'DISCORD_GUILD_ID', label: 'Guild (Server) ID' }
        ]
    };
    
    // Determine field name for single-field providers
    const fieldMap = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'mistral': 'MISTRAL_API_KEY',
        'ovh': 'OVH_API_KEY',
        'github': 'GITHUB_TOKEN',
        'trustpilot': 'TRUSTPILOT_API_KEY',
        'twitter': 'TWITTER_BEARER_TOKEN'
    };
    
    // Replace the configured view with edit form
    const apiKeyValue = card.querySelector('.api-key-value');
    const apiKeyInfo = card.querySelector('.api-key-info');
    
    if (apiKeyValue && apiKeyInfo) {
        // For single-field providers (including OVH), fetch the real API key from the server
        let realApiKey = '';
        if (!multiFieldProviders[provider]) {
            try {
                const revealResponse = await fetch(`${API_BASE_URL}/api/config/reveal-key?provider=${provider}&t=${Date.now()}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                if (revealResponse.ok) {
                    const revealData = await revealResponse.json();
                    realApiKey = revealData.key || '';
                    if (realApiKey) {
                        console.log(`[enableEditMode] Revealed API key for ${provider}, length: ${realApiKey.length}`);
                    } else {
                        console.warn(`[enableEditMode] No key found for ${provider}`);
                    }
                } else {
                    const errorText = await revealResponse.text();
                    console.warn(`[enableEditMode] Failed to reveal key for ${provider}: ${revealResponse.status} - ${errorText}`);
                }
            } catch (error) {
                console.error(`[enableEditMode] Error revealing key for ${provider}:`, error);
                // Continue with empty value - user can enter it manually
            }
        }
        
        let editFormHtml = '';
        
        // Handle multi-field providers (LinkedIn, Discord)
        if (multiFieldProviders[provider]) {
            const fields = multiFieldProviders[provider];
            // Get existing values from configData
            const existingValues = {};
            if (provider === 'discord') {
                // Discord values are stored separately in configData.api_keys
                const discordBotToken = configData.api_keys?.discord_bot_token?.masked || '';
                const discordGuildId = configData.api_keys?.discord_guild_id?.masked || '';
                // Try to get from the main discord key if available
                const discordKey = configData.api_keys?.discord;
                if (discordKey && discordKey.configured) {
                    // Values might be in a nested structure
                    existingValues['DISCORD_BOT_TOKEN'] = '';
                    existingValues['DISCORD_GUILD_ID'] = '';
                }
            } else if (provider === 'linkedin') {
                const linkedinKey = configData.api_keys?.linkedin;
                if (linkedinKey && linkedinKey.configured) {
                    existingValues['LINKEDIN_CLIENT_ID'] = '';
                    existingValues['LINKEDIN_CLIENT_SECRET'] = '';
                }
            }
            
            editFormHtml = `
                <div class="api-key-form-container">
                    <form class="api-key-form" onsubmit="event.preventDefault(); saveAPIKey('${provider}');">
                        ${fields.map(field => `
                            <div class="form-group">
                                <label for="key-input-${provider}-${field.name}">${field.label}</label>
                                <div class="input-with-button">
                                    <input 
                                        type="password" 
                                        id="key-input-${provider}-${field.name}"
                                        class="api-key-input"
                                        placeholder="Enter your ${field.label}"
                                        autocomplete="off"
                                        value="${existingValues[field.name] || ''}"
                                    />
                                    <button type="button" class="btn-toggle-visibility" onclick="toggleInputVisibility('key-input-${provider}-${field.name}')">
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                            <circle cx="12" cy="12" r="3"/>
                                    </svg>
                                </button>
                            </div>
                        </div>
                    `).join('')}
                        <div class="form-actions">
                            <button type="submit" class="btn-primary" id="save-btn-${provider}">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M20 6L9 17l-5-5"/>
                                </svg>
                                Save API Key
                            </button>
                            <button type="button" class="btn-cancel" onclick="exitEditMode('${provider}')" style="background: #ef4444; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 6px; font-size: 0.9rem; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; transition: all 0.2s ease;" onmouseover="this.style.background='#dc2626'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#ef4444'; this.style.transform='translateY(0)'">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width: 16px; height: 16px;">
                                    <line x1="18" y1="6" x2="6" y2="18"/>
                                    <line x1="6" y1="6" x2="18" y2="18"/>
                                </svg>
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            `;
        } else {
            // Single field provider or OVH (special case with model selector)
            const fieldName = fieldMap[provider];
            if (!fieldName && provider !== 'ovh') {
                console.error(`Field name not found for provider: ${provider}`);
                return;
            }
            
            // Check if OVH (needs model selector)
            const isOVH = provider === 'ovh';
            const ovhKeyData = isOVH ? configData.api_keys?.ovh : null;
            const currentModel = isOVH ? (ovhKeyData?.model || 'Llama-3.1-70B-Instruct') : null;
            const currentEndpoint = isOVH ? (ovhKeyData?.endpoint || 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1') : null;
            
            // Use dynamic OVH models if available, otherwise show empty list
            // Models will be loaded automatically when OVH is configured
            const ovhModelsForSelect = isOVH && ovhModelsCache && ovhModelsCache.length > 0 
                ? ovhModelsCache 
                : []; // Empty list - models loaded dynamically
            
            editFormHtml = `
                <div class="api-key-form-container">
                    <form class="api-key-form" onsubmit="event.preventDefault(); saveAPIKey('${provider}');">
                        <div class="form-group">
                            <label for="key-input-${provider}">API Key</label>
                            <div class="input-with-button">
                                <input 
                                    type="password" 
                                    id="key-input-${provider}"
                                    class="api-key-input"
                                    placeholder="Enter your ${providerInfo.name} API key"
                                    autocomplete="off"
                                    value="${realApiKey || ''}"
                                />
                                <button type="button" class="btn-toggle-visibility" onclick="toggleInputVisibility('key-input-${provider}')">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                        <circle cx="12" cy="12" r="3"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    ${isOVH ? `
                        <div class="form-group">
                            <label for="endpoint-input-${provider}">Endpoint URL</label>
                            <input 
                                type="text" 
                                id="endpoint-input-${provider}"
                                class="api-key-input"
                                placeholder="https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
                                value="${currentEndpoint || ''}"
                                autocomplete="off"
                            />
                        </div>
                        <div class="form-group">
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                                <label for="model-select-${provider}" style="margin: 0;">Model</label>
                                <button 
                                    type="button" 
                                    id="refresh-models-btn-${provider}"
                                    style="background: #6366f1; color: white; border: none; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: 500; transition: background 0.2s;"
                                    onmouseover="this.style.background='#4f46e5'" 
                                    onmouseout="this.style.background='#6366f1'"
                                    title="Refresh available models from OVH endpoint"
                                >
                                    🔄 Refresh
                                </button>
                            </div>
                            <select 
                                id="model-select-${provider}"
                                class="api-key-input"
                                style="padding: 0.75rem; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-primary); color: var(--text-primary); font-size: 0.95rem;"
                                ${ovhModelsForSelect.length === 0 ? 'disabled' : ''}
                            >
                                ${ovhModelsForSelect.length > 0 ? ovhModelsForSelect.map(model => `
                                    <option value="${model}" ${currentModel === model ? 'selected' : ''}>${model}</option>
                                `).join('') : `
                                    <option value="">Loading models from endpoint...</option>
                                `}
                            </select>
                            <p style="margin-top: 0.5rem; color: var(--text-secondary); font-size: 0.85em;">
                                ${ovhModelsCache && ovhModelsCache.length > 0 
                                    ? `${ovhModelsCache.length} models loaded from your OVH endpoint`
                                    : 'Click Refresh to load available models from your OVH endpoint'}
                            </p>
                        </div>
                    ` : ''}
                    <div class="form-actions">
                        <button type="submit" class="btn-save-key" id="save-btn-${provider}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M20 6L9 17l-5-5"/>
                            </svg>
                            Save API Key
                        </button>
                        <button type="button" class="btn-cancel" onclick="exitEditMode('${provider}')" style="background: #ef4444; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 6px; font-size: 0.9rem; font-weight: 500; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; transition: all 0.2s ease;" onmouseover="this.style.background='#dc2626'; this.style.transform='translateY(-1px)'" onmouseout="this.style.background='#ef4444'; this.style.transform='translateY(0)'">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="width: 16px; height: 16px;">
                                <line x1="18" y1="6" x2="6" y2="18"/>
                                <line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        `;
        }
        
        apiKeyValue.outerHTML = editFormHtml;
        
        // Focus on first input after a short delay
        setTimeout(() => {
            // For multi-field providers, focus on first field
            if (multiFieldProviders[provider]) {
                const firstField = multiFieldProviders[provider][0];
                const input = document.getElementById(`key-input-${provider}-${firstField.name}`);
                if (input) {
                    input.focus();
                }
            } else {
                // Single field provider
                const input = document.getElementById(`key-input-${provider}`);
                if (input) {
                    // For OVH, verify that the key was properly loaded
                    if (provider === 'ovh' && realApiKey && input.value !== realApiKey) {
                        console.warn(`[enableEditMode] OVH key mismatch: input has ${input.value.length} chars, realApiKey has ${realApiKey.length} chars. Updating input...`);
                        input.value = realApiKey;
                    }
                    
                    // For OVH, add event listener to auto-load models when a valid key is entered
                    if (provider === 'ovh') {
                        const modelSelect = document.getElementById(`model-select-${provider}`);
                        let debounceTimer = null;
                        
                        const checkAndLoadModels = async () => {
                            const currentKey = input.value.trim();
                            const endpointInput = document.getElementById(`endpoint-input-${provider}`);
                            const currentEndpoint = endpointInput ? endpointInput.value.trim() : 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1';
                            
                            // Check if key looks valid (length >= 50 for OVH JWT tokens)
                            if (currentKey.length >= 50 && currentKey.length <= 500) {
                                console.log(`[enableEditMode] Valid OVH key detected (${currentKey.length} chars), loading models...`);
                                // Disable select while loading
                                if (modelSelect) {
                                    modelSelect.disabled = true;
                                    modelSelect.innerHTML = '<option value="">Loading models...</option>';
                                }
                                
                                try {
                                    // Temporarily save the key to test loading models
                                    // First, save the key temporarily, then load models, then restore if needed
                                    const tempSaveResponse = await fetch(`${API_BASE_URL}/api/llm-config`, {
                                        method: 'POST',
                                        headers: {
                                            'Content-Type': 'application/json'
                                        },
                                        body: JSON.stringify({
                                            ovh_api_key: currentKey,
                                            ovh_endpoint_url: currentEndpoint || 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1'
                                        })
                                    });
                                    
                                    if (!tempSaveResponse.ok) {
                                        throw new Error('Failed to save key temporarily');
                                    }
                                    
                                    // Now load models using the regular endpoint
                                    const testResponse = await fetch(`${API_BASE_URL}/api/ovh/models?t=${Date.now()}`);
                                    
                                    if (testResponse.ok) {
                                        const testData = await testResponse.json();
                                        if (testData.models && testData.models.length > 0) {
                                            // Update cache and select
                                            ovhModelsCache = testData.models;
                                            if (modelSelect) {
                                                modelSelect.disabled = false;
                                                const currentValue = modelSelect.value || '';
                                                modelSelect.innerHTML = testData.models.map(model => 
                                                    `<option value="${model}" ${model === currentValue ? 'selected' : ''}>${model}</option>`
                                                ).join('');
                                                console.log(`[enableEditMode] Models loaded and select updated (${testData.models.length} models)`);
                                            }
                                        } else if (modelSelect) {
                                            modelSelect.disabled = false;
                                            modelSelect.innerHTML = `<option value="">${testData.error || 'No models found'}</option>`;
                                        }
                                    } else {
                                        const errorData = await testResponse.json().catch(() => ({ error: 'Failed to load models' }));
                                        if (modelSelect) {
                                            modelSelect.disabled = false;
                                            modelSelect.innerHTML = `<option value="">Error: ${errorData.error || 'Failed to load models'}</option>`;
                                        }
                                    }
                                } catch (error) {
                                    console.error('[enableEditMode] Error loading models:', error);
                                    if (modelSelect) {
                                        modelSelect.disabled = false;
                                        modelSelect.innerHTML = '<option value="">Error loading models - check your API key</option>';
                                    }
                                }
                            } else if (currentKey.length > 0 && currentKey.length < 50) {
                                // Key is too short, might be masked or invalid
                                if (modelSelect && (!ovhModelsCache || ovhModelsCache.length === 0)) {
                                    modelSelect.disabled = true;
                                    modelSelect.innerHTML = '<option value="">Enter a valid API key (282 chars) to load models</option>';
                                }
                            }
                        };
                        
                        // Listen for input changes with debounce (reduced to 800ms for faster response)
                        input.addEventListener('input', () => {
                            clearTimeout(debounceTimer);
                            debounceTimer = setTimeout(checkAndLoadModels, 800); // Wait 0.8 seconds after user stops typing
                        });
                        
                        // Also check immediately if key is already present
                        if (input.value && input.value.length >= 50) {
                            checkAndLoadModels();
                        }
                        
                        // Add click handler for Refresh button
                        const refreshBtn = document.getElementById(`refresh-models-btn-${provider}`);
                        if (refreshBtn) {
                            refreshBtn.addEventListener('click', async () => {
                                console.log('[enableEditMode] Refresh button clicked');
                                await checkAndLoadModels();
                            });
                        }
                    }
                    
                    input.focus();
                    input.select();
                }
            }
        }, 100);
    }
}

// Exit Edit Mode
function exitEditMode(provider) {
    // Reload configuration to restore the original view
    loadConfiguration().then(async () => {
        // Reload OVH models if OVH provider
        if (provider === 'ovh') {
            await loadOVHModels();
        }
        // Re-render the specific provider card
        const llmProviders = ['openai', 'anthropic', 'mistral', 'ovh'];
        if (llmProviders.includes(provider)) {
            renderLLM();
        } else {
            renderScrapersAPIKeys();
        }
    });
}

// Make functions globally available
window.enableEditMode = enableEditMode;
window.exitEditMode = exitEditMode;

// Debug: Verify functions are available
console.log('Settings functions exported:', {
    enableEditMode: typeof window.enableEditMode
});

// Toggle Input Visibility
function toggleInputVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
    } else {
        input.type = 'password';
    }
}

// Save API Key
async function saveAPIKey(provider) {
    const saveBtn = document.getElementById(`save-btn-${provider}`);
    
    // Find provider config
    const providers = [
        { id: 'openai', fields: [{ name: 'OPENAI_API_KEY' }] },
        { id: 'anthropic', fields: [{ name: 'ANTHROPIC_API_KEY' }] },
        { id: 'mistral', fields: [{ name: 'MISTRAL_API_KEY' }] },
        { id: 'ovh', fields: [{ name: 'OVH_API_KEY' }, { name: 'OVH_ENDPOINT_URL' }, { name: 'OVH_MODEL' }] },
        { id: 'github', fields: [{ name: 'GITHUB_TOKEN' }] },
        { id: 'trustpilot', fields: [{ name: 'TRUSTPILOT_API_KEY' }] },
        { id: 'linkedin', fields: [{ name: 'LINKEDIN_CLIENT_ID' }, { name: 'LINKEDIN_CLIENT_SECRET' }] },
        { id: 'twitter', fields: [{ name: 'TWITTER_BEARER_TOKEN' }] },
        { id: 'discord', fields: [{ name: 'DISCORD_BOT_TOKEN' }, { name: 'DISCORD_GUILD_ID' }] }
    ];
    
    const providerConfig = providers.find(p => p.id === provider);
    if (!providerConfig) {
        showError('Unknown provider');
        return;
    }
    
    // Collect values from all fields
    const values = {};
    let hasEmptyField = false;
    
    for (const field of providerConfig.fields) {
        let inputId;
        if (provider === 'ovh') {
            // OVH has special input IDs
            if (field.name === 'OVH_API_KEY') {
                inputId = `key-input-${provider}`;
            } else if (field.name === 'OVH_ENDPOINT_URL') {
                inputId = `endpoint-input-${provider}`;
            } else if (field.name === 'OVH_MODEL') {
                // Model comes from select, handled separately
                continue;
            } else {
                inputId = `key-input-${provider}-${field.name}`;
            }
        } else if (providerConfig.fields.length > 1) {
            inputId = `key-input-${provider}-${field.name}`;
        } else {
            inputId = `key-input-${provider}`;
        }
        
        const input = document.getElementById(inputId);
        if (!input && field.name !== 'OVH_MODEL') {
            // For OVH_ENDPOINT_URL, it's optional (has default), so don't error
            if (provider === 'ovh' && field.name === 'OVH_ENDPOINT_URL') {
                console.log(`[saveAPIKey] OVH endpoint field not found, will use default`);
                continue;
            }
            console.error(`[saveAPIKey] Input field not found: ${inputId} for field ${field.name}`);
            showError(`Input field not found for ${field.name}`);
            return;
        }
        if (input) {
            const value = input.value.trim();
            console.log(`[saveAPIKey] Field ${field.name}: value length = ${value.length}, value = ${value.substring(0, 10)}...`);
            if (!value && field.name !== 'OVH_ENDPOINT_URL') {
                hasEmptyField = true;
            }
            values[field.name] = value;
        }
    }
    
    // For OVH, also get model from select and set default endpoint if not provided
    if (provider === 'ovh') {
        const modelSelect = document.getElementById(`model-select-${provider}`);
        if (modelSelect) {
            values.OVH_MODEL = modelSelect.value;
        } else {
            values.OVH_MODEL = 'Llama-3.1-70B-Instruct'; // Default
        }
        
        // Set default endpoint if not provided
        if (!values.OVH_ENDPOINT_URL || values.OVH_ENDPOINT_URL.trim() === '') {
            values.OVH_ENDPOINT_URL = 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1';
            console.log(`[saveAPIKey] Using default OVH endpoint: ${values.OVH_ENDPOINT_URL}`);
        }
        
        // CRITICAL: Check if API key field contains a masked value (short length)
        // If the key is too short (< 50 chars), it's likely a masked value
        // In this case, fetch the real key from the server before saving
        const apiKeyInput = document.getElementById(`key-input-${provider}`);
        if (apiKeyInput && values.OVH_API_KEY) {
            const keyLength = values.OVH_API_KEY.length;
            // OVH JWT tokens are typically 200+ characters, so if we have < 50, it's likely masked
            if (keyLength < 50) {
                console.log(`[saveAPIKey] OVH API key appears to be masked (${keyLength} chars), fetching real key from server...`);
                try {
                    const revealResponse = await fetch(`${API_BASE_URL}/api/config/reveal-key?provider=${provider}&t=${Date.now()}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    if (revealResponse.ok) {
                        const revealData = await revealResponse.json();
                        if (revealData.key && revealData.key.length >= 50) {
                            console.log(`[saveAPIKey] Retrieved real OVH API key from server (${revealData.key.length} chars)`);
                            values.OVH_API_KEY = revealData.key;
                        } else {
                            // If revealed key is also too short, it means it's corrupted in DB
                            // Don't save the masked value - keep existing key or show error
                            console.error(`[saveAPIKey] Revealed key is also too short (${revealData.key?.length || 0} chars). Key may be corrupted in database.`);
                            showError('OVH API key appears to be corrupted. Please re-enter your full API key.');
                            saveBtn.disabled = false;
                            saveBtn.innerHTML = `
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M20 6L9 17l-5-5"/>
                                </svg>
                                Save API Key
                            `;
                            return;
                        }
                    } else {
                        // If reveal fails, don't save masked value
                        console.error(`[saveAPIKey] Failed to reveal key. Not saving masked value.`);
                        showError('Could not retrieve API key. Please re-enter your full API key.');
                        saveBtn.disabled = false;
                        saveBtn.innerHTML = `
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M20 6L9 17l-5-5"/>
                            </svg>
                            Save API Key
                        `;
                        return;
                    }
                } catch (error) {
                    console.error(`[saveAPIKey] Error revealing key:`, error);
                    // Don't save masked value - show error
                    showError('Error retrieving API key. Please re-enter your full API key.');
                    saveBtn.disabled = false;
                    saveBtn.innerHTML = `
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M20 6L9 17l-5-5"/>
                        </svg>
                        Save API Key
                    `;
                    return;
                }
            } else {
                // Key is long enough (>= 50 chars), it's likely the real key
                // Ensure it's not empty and has reasonable length
                if (keyLength >= 50 && keyLength <= 500) {
                    console.log(`[saveAPIKey] OVH API key from input field is valid (${keyLength} chars), will be saved`);
                }
            }
        } else if (apiKeyInput) {
            // Field exists - check if it's empty or has a valid key
            const currentValue = apiKeyInput.value || '';
            if (!currentValue || currentValue.trim() === '') {
                // Field is empty - try to get existing key to preserve it
                console.log(`[saveAPIKey] OVH API key field is empty, fetching existing key to preserve it...`);
                try {
                    const revealResponse = await fetch(`${API_BASE_URL}/api/config/reveal-key?provider=${provider}&t=${Date.now()}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    if (revealResponse.ok) {
                        const revealData = await revealResponse.json();
                        if (revealData.key && revealData.key.length >= 50) {
                            console.log(`[saveAPIKey] Preserving existing OVH API key (${revealData.key.length} chars)`);
                            values.OVH_API_KEY = revealData.key;
                        } else {
                            console.warn(`[saveAPIKey] Existing key is too short or missing (${revealData.key?.length || 0} chars)`);
                        }
                    } else {
                        console.warn(`[saveAPIKey] Could not fetch existing key (status ${revealResponse.status})`);
                    }
                } catch (error) {
                    console.warn(`[saveAPIKey] Could not fetch existing key to preserve:`, error);
                    // Continue - user might want to clear the key
                }
            } else if (currentValue.length >= 50) {
                // Field has a valid key - use it
                console.log(`[saveAPIKey] Using OVH API key from input field (${currentValue.length} chars)`);
                values.OVH_API_KEY = currentValue;
            } else {
                // Field has a short value - might be masked, fetch real key
                console.log(`[saveAPIKey] OVH API key field has short value (${currentValue.length} chars), fetching real key...`);
                try {
                    const revealResponse = await fetch(`${API_BASE_URL}/api/config/reveal-key?provider=${provider}&t=${Date.now()}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    if (revealResponse.ok) {
                        const revealData = await revealResponse.json();
                        if (revealData.key && revealData.key.length >= 50) {
                            console.log(`[saveAPIKey] Retrieved real OVH API key from server (${revealData.key.length} chars)`);
                            values.OVH_API_KEY = revealData.key;
                        } else {
                            console.warn(`[saveAPIKey] Revealed key is also too short (${revealData.key?.length || 0} chars)`);
                        }
                    }
                } catch (error) {
                    console.warn(`[saveAPIKey] Could not fetch real key:`, error);
                }
            }
        }
    }
    
    console.log(`[saveAPIKey] Collected values for ${provider}:`, Object.keys(values));
    
    // Allow empty values for LLM providers (to clear existing keys)
    // For Discord, both fields are required if one is filled
    const llmProviders = ['openai', 'anthropic', 'mistral', 'ovh'];
    if (hasEmptyField && !llmProviders.includes(provider)) {
        // For Discord, check if at least one field is filled - if so, both are required
        if (provider === 'discord') {
            const hasBotToken = values['DISCORD_BOT_TOKEN'] && values['DISCORD_BOT_TOKEN'].trim();
            const hasGuildId = values['DISCORD_GUILD_ID'] && values['DISCORD_GUILD_ID'].trim();
            // Check if Discord is already configured (if so, allow empty fields to keep existing values)
            const discordKey = configData?.api_keys?.discord;
            const isAlreadyConfigured = discordKey && discordKey.configured;
            
            if (hasBotToken || hasGuildId) {
                // At least one is filled, both are required
                if (!hasBotToken || !hasGuildId) {
                    showError('Both Bot Token and Guild ID are required for Discord');
                    return;
                }
            } else if (!isAlreadyConfigured) {
                // Both are empty and Discord is not configured - require at least one
                showError('Please fill in at least one Discord field (Bot Token or Guild ID)');
                return;
            }
            // If both are empty but Discord is already configured, allow saving (will keep existing values)
        } else {
            showError('Please fill in all required fields');
            return;
        }
    }
    
    // Disable button and show loading
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="loading-spinner"></span> Saving...';
    
    try {
        // Prepare payload based on provider
        let payload = {};
        if (provider === 'openai') {
            payload = { openai_api_key: values.OPENAI_API_KEY };
        } else if (provider === 'anthropic') {
            payload = { anthropic_api_key: values.ANTHROPIC_API_KEY };
        } else if (provider === 'mistral') {
            payload = { mistral_api_key: values.MISTRAL_API_KEY };
        } else if (provider === 'ovh') {
            // OVH needs API key, endpoint URL, and model
            // Use values already collected (including defaults)
            payload = { 
                ovh_api_key: values.OVH_API_KEY || '',
                ovh_endpoint_url: values.OVH_ENDPOINT_URL || 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1',
                ovh_model: values.OVH_MODEL || 'Llama-3.1-70B-Instruct'
            };
            console.log(`[saveAPIKey] OVH payload:`, { 
                api_key_length: payload.ovh_api_key?.length || 0,
                endpoint: payload.ovh_endpoint_url,
                model: payload.ovh_model
            });
        } else {
            // For other providers, use a generic endpoint
            // Send all fields as a single request
            console.log(`[saveAPIKey] Sending request for ${provider} with keys:`, Object.keys(values));
            const response = await fetch(`${API_BASE_URL}/api/config/set-key`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider: provider, keys: values })
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`[saveAPIKey] Error response for ${provider}:`, errorText);
                throw new Error(`Failed to save API key: ${errorText}`);
            }
            
            // Reload configuration to refresh display
            await loadConfiguration();
            
            // Re-render the specific section
            if (provider === 'discord' || provider === 'linkedin' || provider === 'twitter') {
                renderScrapersAPIKeys();
            }
            
            showSuccess(`${provider.toUpperCase()} API key(s) saved successfully!`);
            return;
        }
        
        // For OpenAI, Anthropic, Mistral, and OVH, use existing endpoint
        const response = await fetch(`${API_BASE_URL}/api/llm-config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            let errorMessage = 'Failed to save API key';
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorData.message || errorMessage;
            } catch (e) {
                const errorText = await response.text();
                errorMessage = errorText || errorMessage;
            }
            
            // For OVH, provide more specific error message
            if (provider === 'ovh' && errorMessage.includes('masked') || errorMessage.includes('corrupted') || errorMessage.includes('too short')) {
                errorMessage = 'La clé API OVH semble être masquée ou corrompue. Veuillez ré-entrer votre clé API complète (282 caractères).';
            }
            
            throw new Error(errorMessage);
        }
        
        // CRITICAL: For OVH, verify the saved key length after save
        if (provider === 'ovh' && payload.ovh_api_key) {
            // Reload configuration to verify
            await loadConfiguration();
            const savedOvhKey = configData?.api_keys?.ovh;
            if (savedOvhKey && savedOvhKey.configured) {
                const savedLength = savedOvhKey.length || 0;
                const expectedLength = payload.ovh_api_key.length;
                
                if (savedLength < 50) {
                    throw new Error(`La clé API sauvegardée est corrompue (${savedLength} caractères au lieu de ${expectedLength}). Veuillez ré-entrer votre clé API complète.`);
                }
                
                if (Math.abs(savedLength - expectedLength) > 10) {
                    console.warn(`[saveAPIKey] Saved key length mismatch: expected ~${expectedLength}, got ${savedLength}`);
                }
            }
        }
        
        // Reload configuration with cache-busting to ensure fresh data
        await loadConfiguration();
        
        // Small delay to ensure backend has processed the update
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Reload again to get the latest data
        await loadConfiguration();
        
        // Reload OVH models if OVH was updated
        if (provider === 'ovh') {
            await loadOVHModels();
        }
        
        showSuccess(`${provider.toUpperCase()} API key saved successfully!`);
        
        // Update badges and re-render sections
        if (configData && configData.api_keys) {
            // Check if it's an LLM provider
            const llmProviders = ['openai', 'anthropic', 'mistral', 'ovh'];
            if (llmProviders.includes(provider)) {
                renderLLM();
            } else {
                renderScrapersAPIKeys();
            }
        }
        
    } catch (error) {
        console.error('Error saving API key:', error);
        showError(`Failed to save ${provider.toUpperCase()} API key: ${error.message}`);
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 6L9 17l-5-5"/>
            </svg>
            Save API Key
        `;
    }
}

// Delete API Key
async function deleteAPIKey(provider) {
    if (!confirm(`Are you sure you want to delete the ${provider.toUpperCase()} API key? This action cannot be undone.`)) {
        return;
    }
    
    // Find provider config
    const providers = [
        { id: 'openai', fields: [{ name: 'OPENAI_API_KEY' }] },
        { id: 'anthropic', fields: [{ name: 'ANTHROPIC_API_KEY' }] },
        { id: 'mistral', fields: [{ name: 'MISTRAL_API_KEY' }] },
        { id: 'ovh', fields: [{ name: 'OVH_API_KEY' }, { name: 'OVH_ENDPOINT_URL' }, { name: 'OVH_MODEL' }] },
        { id: 'github', fields: [{ name: 'GITHUB_TOKEN' }] },
        { id: 'trustpilot', fields: [{ name: 'TRUSTPILOT_API_KEY' }] },
        { id: 'linkedin', fields: [{ name: 'LINKEDIN_CLIENT_ID' }, { name: 'LINKEDIN_CLIENT_SECRET' }] },
        { id: 'twitter', fields: [{ name: 'TWITTER_BEARER_TOKEN' }] },
        { id: 'discord', fields: [{ name: 'DISCORD_BOT_TOKEN' }, { name: 'DISCORD_GUILD_ID' }] }
    ];
    
    const providerConfig = providers.find(p => p.id === provider);
    if (!providerConfig) {
        showError('Unknown provider');
        return;
    }
    
    try {
        // Prepare payload with empty values to delete the keys
        let payload = {};
        if (provider === 'openai') {
            payload = { openai_api_key: '' };
        } else if (provider === 'anthropic') {
            payload = { anthropic_api_key: '' };
        } else if (provider === 'mistral') {
            payload = { mistral_api_key: '' };
        } else if (provider === 'ovh') {
            payload = { ovh_api_key: '', ovh_endpoint_url: '', ovh_model: '' };
        } else {
            // For other providers, send empty values for all fields
            const emptyValues = {};
            providerConfig.fields.forEach(field => {
                emptyValues[field.name] = '';
            });
            const response = await fetch(`${API_BASE_URL}/api/config/set-key`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider: provider, keys: emptyValues })
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to delete API key: ${errorText}`);
            }
            
        // Reload configuration to refresh display
        await loadConfiguration();
        
        // Small delay to ensure backend has processed the update
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Reload again to get the latest data
        await loadConfiguration();
        
        // Re-render the specific section
        const llmProviders = ['openai', 'anthropic', 'mistral', 'ovh'];
        if (llmProviders.includes(provider)) {
            renderLLM();
        } else if (provider === 'discord' || provider === 'linkedin' || provider === 'twitter') {
            renderScrapersAPIKeys();
        }
        
        showSuccess(`${provider.toUpperCase()} API key(s) deleted successfully!`);
        return;
        }
        
        // For OpenAI, Anthropic, Mistral, and OVH, use existing endpoint with empty string
        const response = await fetch(`${API_BASE_URL}/api/llm-config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            let errorMessage = 'Failed to delete API key';
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorData.message || errorMessage;
            } catch (e) {
                const errorText = await response.text();
                errorMessage = errorText || errorMessage;
            }
            throw new Error(errorMessage);
        }
        
        // Reload configuration with cache-busting to ensure fresh data
        await loadConfiguration();
        
        // Small delay to ensure backend has processed the update
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Reload again to get the latest data
        await loadConfiguration();
        
        // Reload OVH models if OVH was deleted
        if (provider === 'ovh') {
            await loadOVHModels();
        }
        
        // Force re-render sections to update badges
        const llmProviders = ['openai', 'anthropic', 'mistral', 'ovh'];
        if (llmProviders.includes(provider)) {
            renderLLM();
        } else {
            renderScrapersAPIKeys();
        }
        
        showSuccess(`${provider.toUpperCase()} API key deleted successfully!`);
        
    } catch (error) {
        console.error('Error deleting API key:', error);
        showError(`Failed to delete ${provider.toUpperCase()} API key: ${error.message}`);
    }
}

// Make functions available globally
window.deleteAPIKey = deleteAPIKey;
window.loadOVHModels = loadOVHModels;

// Show Success
function showSuccess(message) {
    const feedback = document.getElementById('copyFeedback');
    feedback.style.background = '#28a745';
    feedback.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"/>
        </svg>
        <span>${message}</span>
    `;
    feedback.classList.add('show');
    
    setTimeout(() => {
        feedback.classList.remove('show');
    }, 3000);
}

// Show Error
function showError(message) {
    const feedback = document.getElementById('copyFeedback');
    feedback.style.background = '#dc3545';
    feedback.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
        <span>${message}</span>
    `;
    feedback.classList.add('show');
    
    setTimeout(() => {
        feedback.classList.remove('show');
        feedback.style.background = '#28a745';
    }, 3000);
}

// Base Keywords Management
async function loadBaseKeywords() {
    const container = document.getElementById('baseKeywordsContainer');
    if (!container) return;
    
    try {
        container.innerHTML = '<div class="skeleton-loader"></div>';
        
        const response = await fetch(`${API_BASE_URL}/settings/base-keywords`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        container.innerHTML = `
            <div class="base-keywords-form">
                <div class="keywords-field-group">
                    <label class="keywords-field-label">
                        <span class="keywords-field-label-icon">🏢</span>
                        <span>Brands <span style="color: var(--text-secondary); font-weight: 400;">(Marques OVH)</span></span>
                    </label>
                    <textarea id="baseKeywordsBrands" class="keywords-textarea" placeholder="OVH, OVHCloud, Kimsufi...">${(data.brands || []).join(', ')}</textarea>
                </div>
                <div class="keywords-field-group">
                    <label class="keywords-field-label">
                        <span class="keywords-field-label-icon">📦</span>
                        <span>Products <span style="color: var(--text-secondary); font-weight: 400;">(Produits OVH)</span></span>
                    </label>
                    <textarea id="baseKeywordsProducts" class="keywords-textarea" placeholder="OVH domain, OVH hosting, OVH VPS...">${(data.products || []).join(', ')}</textarea>
                </div>
                <div class="keywords-field-group">
                    <label class="keywords-field-label">
                        <span class="keywords-field-label-icon">⚠️</span>
                        <span>Problems <span style="color: var(--text-secondary); font-weight: 400;">(Problèmes/Complaints)</span></span>
                    </label>
                    <textarea id="baseKeywordsProblems" class="keywords-textarea" placeholder="OVH complaint, OVH support, OVH billing...">${(data.problems || []).join(', ')}</textarea>
                </div>
                <div class="keywords-field-group">
                    <label class="keywords-field-label">
                        <span class="keywords-field-label-icon">👔</span>
                        <span>Leadership <span style="color: var(--text-secondary); font-weight: 400;">(Direction OVH)</span></span>
                    </label>
                    <textarea id="baseKeywordsLeadership" class="keywords-textarea" placeholder="Michel Paulin, Octave Klaba, OVH CEO...">${(data.leadership || []).join(', ')}</textarea>
                </div>
            </div>
            <div class="form-actions" style="margin-top: 1.5rem; max-width: 900px;">
                <button class="btn-save-key" onclick="saveBaseKeywords()">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M20 6L9 17l-5-5"/>
                    </svg>
                    Save Base Keywords
                </button>
            </div>
        `;
    } catch (error) {
        console.error('Error loading base keywords:', error);
        container.innerHTML = `<div style="color: var(--error, #dc3545); padding: 1rem;">Error loading base keywords: ${error.message}</div>`;
    }
}

async function saveBaseKeywords() {
    try {
        const brands = document.getElementById('baseKeywordsBrands').value.split(',').map(k => k.trim()).filter(k => k);
        const products = document.getElementById('baseKeywordsProducts').value.split(',').map(k => k.trim()).filter(k => k);
        const problems = document.getElementById('baseKeywordsProblems').value.split(',').map(k => k.trim()).filter(k => k);
        const leadership = document.getElementById('baseKeywordsLeadership').value.split(',').map(k => k.trim()).filter(k => k);
        
        const response = await fetch(`${API_BASE_URL}/settings/base-keywords`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ brands, products, problems, leadership })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        showSuccess('Base keywords saved successfully!');
    } catch (error) {
        console.error('Error saving base keywords:', error);
        showError(`Failed to save base keywords: ${error.message}`);
    }
}

// ============================================================================
// PAIN POINTS MANAGEMENT
// ============================================================================

async function loadPainPoints() {
    const container = document.getElementById('painPointsContainer');
    if (!container) return;
    
    container.innerHTML = '<div class="skeleton-loader" style="height: 200px;"></div>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/settings/pain-points`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        const painPoints = data.pain_points || [];
        
        container.innerHTML = `
            <div class="pain-points-form">
                <div id="painPointsList" style="margin-bottom: 1.5rem;">
                    ${painPoints.map((pp, index) => renderPainPointItem(pp, index)).join('')}
                </div>
                <button class="btn-primary" onclick="addPainPoint()" style="margin-bottom: 1rem;">
                    + Add Pain Point
                </button>
                <button class="btn-primary" onclick="savePainPoints()" style="margin-left: 0.5rem;">
                    💾 Save Pain Points
                </button>
            </div>
        `;
        
        // Store data globally for updates
        window.painPointsData = painPoints;
    } catch (error) {
        console.error('Error loading pain points:', error);
        container.innerHTML = `
            <div class="error-message">
                <p>❌ Failed to load pain points: ${error.message}</p>
                <button class="btn-secondary" onclick="loadPainPoints()">Retry</button>
            </div>
        `;
    }
}

function renderPainPointItem(pp, index) {
    const keywordsStr = Array.isArray(pp.keywords) ? pp.keywords.join(', ') : (pp.keywords || '');
    return `
        <div class="pain-point-item" data-index="${index}" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
            <div style="display: flex; gap: 1rem; align-items: start;">
                <div style="flex: 1;">
                    <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.5rem;">
                        <input type="text" 
                               class="pain-point-icon" 
                               value="${pp.icon || '📊'}" 
                               placeholder="📊"
                               style="width: 60px; font-size: 1.5rem; text-align: center; border: 1px solid var(--border-color); border-radius: 4px; padding: 0.25rem;"
                               onchange="updatePainPointIcon(${index}, this.value)">
                        <input type="text" 
                               class="pain-point-title" 
                               value="${pp.title || ''}" 
                               placeholder="Pain Point Title"
                               style="flex: 1; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 4px;"
                               onchange="updatePainPointTitle(${index}, this.value)">
                        <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                            <input type="checkbox" 
                                   class="pain-point-enabled" 
                                   ${pp.enabled !== false ? 'checked' : ''}
                                   onchange="updatePainPointEnabled(${index}, this.checked)">
                            <span>Enabled</span>
                        </label>
                        <button class="btn-danger" onclick="removePainPoint(${index})" style="padding: 0.5rem 1rem;">
                            🗑️ Delete
                        </button>
                    </div>
                    <textarea class="pain-point-keywords" 
                              placeholder="Enter keywords separated by commas (e.g., slow, performance, lag)"
                              style="width: 100%; min-height: 60px; padding: 0.5rem; border: 1px solid var(--border-color); border-radius: 4px; font-family: inherit;"
                              onchange="updatePainPointKeywords(${index}, this.value)">${keywordsStr}</textarea>
                </div>
            </div>
        </div>
    `;
}

function addPainPoint() {
    const container = document.getElementById('painPointsList');
    if (!container) return;
    
    if (!window.painPointsData) {
        window.painPointsData = [];
    }
    
    const newIndex = window.painPointsData.length;
    window.painPointsData.push({
        title: '',
        icon: '📊',
        keywords: [],
        enabled: true
    });
    
    container.innerHTML += renderPainPointItem(window.painPointsData[newIndex], newIndex);
}

function removePainPoint(index) {
    if (confirm('Are you sure you want to delete this pain point?')) {
        if (window.painPointsData && window.painPointsData[index]) {
            window.painPointsData.splice(index, 1);
            loadPainPoints();
        }
    }
}

function updatePainPointIcon(index, icon) {
    if (window.painPointsData && window.painPointsData[index]) {
        window.painPointsData[index].icon = icon;
    }
}

function updatePainPointTitle(index, title) {
    if (window.painPointsData && window.painPointsData[index]) {
        window.painPointsData[index].title = title;
    }
}

function updatePainPointKeywords(index, keywordsStr) {
    if (window.painPointsData && window.painPointsData[index]) {
        window.painPointsData[index].keywords = keywordsStr.split(',').map(k => k.trim()).filter(k => k);
    }
}

function updatePainPointEnabled(index, enabled) {
    if (window.painPointsData && window.painPointsData[index]) {
        window.painPointsData[index].enabled = enabled;
    }
}

async function savePainPoints() {
    const container = document.getElementById('painPointsContainer');
    if (!container) return;
    
    // Collect current data from DOM
    const painPoints = [];
    const items = container.querySelectorAll('.pain-point-item');
    
    items.forEach((item) => {
        const titleInput = item.querySelector('.pain-point-title');
        const iconInput = item.querySelector('.pain-point-icon');
        const keywordsTextarea = item.querySelector('.pain-point-keywords');
        const enabledCheckbox = item.querySelector('.pain-point-enabled');
        
        if (titleInput && iconInput && keywordsTextarea) {
            const title = titleInput.value.trim();
            if (title) {
                painPoints.push({
                    title: title,
                    icon: iconInput.value.trim() || '📊',
                    keywords: keywordsTextarea.value.split(',').map(k => k.trim()).filter(k => k),
                    enabled: enabledCheckbox ? enabledCheckbox.checked : true
                });
            }
        }
    });
    
    if (painPoints.length === 0) {
        showError('Please add at least one pain point before saving.');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/settings/pain-points`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ pain_points: painPoints })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        const result = await response.json();
        showSuccess(`Successfully saved ${result.count} pain point(s)!`);
        loadPainPoints(); // Reload to refresh display
    } catch (error) {
        console.error('Error saving pain points:', error);
        showError(`Failed to save pain points: ${error.message}`);
    }
}

// Make functions available globally
window.loadPainPoints = loadPainPoints;
window.addPainPoint = addPainPoint;
window.removePainPoint = removePainPoint;
window.updatePainPointIcon = updatePainPointIcon;
window.updatePainPointTitle = updatePainPointTitle;
window.updatePainPointKeywords = updatePainPointKeywords;
window.updatePainPointEnabled = updatePainPointEnabled;
window.savePainPoints = savePainPoints;

// LLM Prompts for Custom Analysis Management
function loadAnalysisFocus() {
    const input = document.getElementById('analysisFocusInput');
    if (!input) return;
    
    const savedFocus = localStorage.getItem('analysisFocus') || '';
    input.value = savedFocus;
}

function saveAnalysisFocus() {
    const input = document.getElementById('analysisFocusInput');
    if (!input) return;
    
    const focus = input.value.trim();
    localStorage.setItem('analysisFocus', focus);
    
    if (focus) {
        showSuccess(`LLM prompts saved: "${focus}"`);
    } else {
        showSuccess('LLM prompts cleared - using general analysis');
    }
}

// Jira Configuration Management
async function loadJiraConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/jira/config`);
        if (!response.ok) throw new Error('Failed to load Jira config');
        
        const config = await response.json();
        
        // Update form fields
        const serverUrlInput = document.getElementById('jiraServerUrl');
        const usernameInput = document.getElementById('jiraUsername');
        const apiTokenInput = document.getElementById('jiraApiToken');
        const projectKeyInput = document.getElementById('jiraProjectKey');
        
        if (serverUrlInput) serverUrlInput.value = config.server_url || '';
        if (usernameInput) usernameInput.value = config.username || '';
        if (apiTokenInput) apiTokenInput.value = ''; // Never show token for security
        if (projectKeyInput) projectKeyInput.value = config.project_key || '';
        
        // Update badge
        const badge = document.getElementById('jiraBadge');
        if (badge) {
            badge.textContent = config.configured ? '✓ Configured' : 'Not configured';
            badge.style.color = config.configured ? '#34d399' : '#ef4444';
        }
        
        // Update status
        const statusDiv = document.getElementById('jiraConfigStatus');
        if (statusDiv) {
            if (config.configured) {
                statusDiv.innerHTML = `
                    <div style="background: rgba(52, 211, 153, 0.1); border: 1px solid rgba(52, 211, 153, 0.3); border-radius: 6px; padding: 0.75rem; color: #34d399;">
                        ✓ Jira is configured and ready to use
                    </div>
                `;
            } else {
                statusDiv.innerHTML = `
                    <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; padding: 0.75rem; color: #ef4444;">
                        ⚠ Jira is not configured. Please fill all required fields.
                    </div>
                `;
            }
        }
    } catch (error) {
        console.error('Error loading Jira config:', error);
        const statusDiv = document.getElementById('jiraConfigStatus');
        if (statusDiv) {
            statusDiv.innerHTML = `
                <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; padding: 0.75rem; color: #ef4444;">
                    Error loading Jira configuration
                </div>
            `;
        }
    }
}

async function saveJiraConfig() {
    const serverUrl = document.getElementById('jiraServerUrl')?.value.trim() || '';
    const username = document.getElementById('jiraUsername')?.value.trim() || '';
    const apiToken = document.getElementById('jiraApiToken')?.value.trim() || '';
    const projectKey = document.getElementById('jiraProjectKey')?.value.trim() || '';
    
    if (!serverUrl || !username || !apiToken || !projectKey) {
        showError('Please fill all required fields');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/jira/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                server_url: serverUrl,
                username: username,
                api_token: apiToken,
                project_key: projectKey
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save Jira config');
        }
        
        const result = await response.json();
        showSuccess('Jira configuration saved successfully!');
        
        // Clear API token field for security
        const apiTokenInput = document.getElementById('jiraApiToken');
        if (apiTokenInput) apiTokenInput.value = '';
        
        // Reload config to update badge
        await loadJiraConfig();
    } catch (error) {
        console.error('Error saving Jira config:', error);
        showError(`Failed to save Jira configuration: ${error.message}`);
    }
}

async function testJiraConnection() {
    const btn = event.target;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Testing...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/jira/test-connection`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(result.message || 'Connection successful!');
        } else {
            showError(result.error || 'Connection failed');
        }
    } catch (error) {
        console.error('Error testing Jira connection:', error);
        showError(`Failed to test connection: ${error.message}`);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Update Active LLM Provider
async function updateActiveLLMProvider(providerId) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/llm-config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                llm_provider: providerId,
                openai_api_key: null,
                anthropic_api_key: null,
                mistral_api_key: null
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Failed to update provider' }));
            throw new Error(errorData.detail || 'Failed to update provider');
        }
        
        // Reload configuration to get updated provider
        await loadConfiguration();
        
        // Re-render LLM section to show updated active provider
        renderLLM();
        
        showSuccess(`Active provider set to ${providerId.charAt(0).toUpperCase() + providerId.slice(1)}`);
    } catch (error) {
        console.error('Error updating LLM provider:', error);
        showError(`Failed to update provider: ${error.message}`);
        
        // Reload configuration to restore previous state
        await loadConfiguration();
        renderLLM();
    }
}

// Make functions available globally
window.saveJiraConfig = saveJiraConfig;
window.testJiraConnection = testJiraConnection;
window.updateActiveLLMProvider = updateActiveLLMProvider;

// Load Jira config on page load
document.addEventListener('DOMContentLoaded', () => {
    loadJiraConfig();
});
