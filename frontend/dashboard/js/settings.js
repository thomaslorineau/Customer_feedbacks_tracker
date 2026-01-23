// Settings page - API Configuration
const API_BASE_URL = window.location.origin; // Use current server URL

// Debug: Log API base URL
console.log('API_BASE_URL:', API_BASE_URL);

// State
let configData = null;

// Load and display version
let versionData = null;
async function loadVersion() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/version`);
        if (response.ok) {
            versionData = await response.json();
            const versionBadge = document.getElementById('versionBadge');
            if (versionBadge) {
                versionBadge.textContent = `v${versionData.version}`;
                versionBadge.title = `Version ${versionData.version} - Build: ${new Date(versionData.build_date).toLocaleDateString()}`;
            }
            // Also render in environment section (will be called after configData is loaded)
            if (configData) {
                renderEnvironmentInfo();
            }
        }
    } catch (error) {
        console.warn('Failed to load version:', error);
        // Still try to render with what we have
        if (configData) {
            renderEnvironmentInfo();
        }
    }
}

// Render Environment Info
function renderEnvironmentInfo() {
    const container = document.getElementById('environmentInfo');
    if (!container) return;
    
    if (!configData || !versionData) {
        container.innerHTML = '<div class="skeleton-loader" style="height: 100px;"></div>';
        return;
    }
    
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
        const url = `${API_BASE_URL}/api/config`;
        console.log('Fetching configuration from:', url);
        const response = await fetch(url);
        console.log('Response status:', response.status, response.statusText);
        if (!response.ok) {
            throw new Error(`Failed to load configuration: ${response.status} ${response.statusText}`);
        }
        
        configData = await response.json();
        console.log('Configuration loaded:', configData);
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
    
    const llmProviders = [
        { 
            id: 'openai', 
            name: 'OpenAI', 
            icon: '🤖',
            description: 'GPT models for sentiment analysis and text processing',
            docsUrl: 'https://platform.openai.com/api-keys'
        },
        { 
            id: 'anthropic', 
            name: 'Anthropic', 
            icon: '🧠',
            description: 'Claude models for advanced text understanding',
            docsUrl: 'https://console.anthropic.com/'
        },
        { 
            id: 'mistral', 
            name: 'Mistral AI', 
            icon: '🌊',
            description: 'Mistral models for advanced AI capabilities',
            docsUrl: 'https://console.mistral.ai/api-keys/'
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
        },
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
}

function renderProviderCard(provider) {
    const keyData = configData.api_keys[provider.id];
    if (!keyData) {
        console.warn(`No key data for provider: ${provider.id}`);
        return '';
    }
    const isConfigured = keyData.configured || false;
    const maskedKey = keyData.masked || 'Not configured';
    
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
                    </div>
                </div>
                
                <div class="api-key-info">
                    <div class="info-item">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 14px; height: 14px;">
                            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
                        </svg>
                        Length: ${keyData.length} chars
                    </div>
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
                            // Single field (default)
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
                            `
                        }
                        <div class="form-actions">
                            <button type="submit" class="btn-save-key" id="save-btn-${provider.id}">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                                    <polyline points="17 21 17 13 7 13 7 21"/>
                                    <polyline points="7 3 7 8 15 8"/>
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
        { id: 'openai', name: 'OpenAI', icon: '🤖', docsUrl: 'https://platform.openai.com/api-keys' },
        { id: 'anthropic', name: 'Anthropic', icon: '🧠', docsUrl: 'https://console.anthropic.com/' },
        { id: 'mistral', name: 'Mistral AI', icon: '🌊', docsUrl: 'https://console.mistral.ai/api-keys/' }
    ];
    
    const scraperProviders = [
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
    
    // Determine field name
    const fieldMap = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'mistral': 'MISTRAL_API_KEY',
        'github': 'GITHUB_TOKEN',
        'trustpilot': 'TRUSTPILOT_API_KEY',
        'linkedin': 'LINKEDIN_CLIENT_ID',
        'twitter': 'TWITTER_BEARER_TOKEN'
    };
    
    const fieldName = fieldMap[provider];
    if (!fieldName) {
        console.error(`Field name not found for provider: ${provider}`);
        return;
    }
    
    // Don't reveal the key for security - leave input empty
    // User must enter the full key when editing
    let currentKey = '';
    
    // Replace the configured view with edit form
    const apiKeyValue = card.querySelector('.api-key-value');
    const apiKeyInfo = card.querySelector('.api-key-info');
    
    if (apiKeyValue && apiKeyInfo) {
        const editFormHtml = `
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
                                value="${currentKey}"
                                autocomplete="off"
                            />
                            <button type="button" class="btn-toggle-visibility" onclick="toggleInputVisibility('key-input-${provider}')">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                    <circle cx="12" cy="12" r="3"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-save-key" id="save-btn-${provider}">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                                <polyline points="17 21 17 13 7 13 7 21"/>
                                <polyline points="7 3 7 8 15 8"/>
                            </svg>
                            Save API Key
                        </button>
                        <button type="button" class="btn-get-key" onclick="exitEditMode('${provider}')" style="background: var(--text-secondary);">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"/>
                                <line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                            Cancel
                        </button>
                    </div>
                </form>
            </div>
        `;
        
        apiKeyValue.outerHTML = editFormHtml;
        
        // Focus on input after a short delay
        setTimeout(() => {
            const input = document.getElementById(`key-input-${provider}`);
            if (input) {
                input.focus();
                input.select();
            }
        }, 100);
    }
}

// Exit Edit Mode
function exitEditMode(provider) {
    // Reload configuration to restore the original view
    loadConfiguration().then(() => {
        // Re-render the specific provider card
        const llmProviders = ['openai', 'anthropic', 'mistral'];
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
        { id: 'github', fields: [{ name: 'GITHUB_TOKEN' }] },
        { id: 'trustpilot', fields: [{ name: 'TRUSTPILOT_API_KEY' }] },
        { id: 'linkedin', fields: [{ name: 'LINKEDIN_CLIENT_ID' }, { name: 'LINKEDIN_CLIENT_SECRET' }] },
        { id: 'twitter', fields: [{ name: 'TWITTER_BEARER_TOKEN' }] }
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
        const inputId = providerConfig.fields.length > 1 
            ? `key-input-${provider}-${field.name}`
            : `key-input-${provider}`;
        const input = document.getElementById(inputId);
        if (!input) {
            showError(`Input field not found for ${field.name}`);
            return;
        }
        const value = input.value.trim();
        if (!value) {
            hasEmptyField = true;
        }
        values[field.name] = value;
    }
    
    // Allow empty values for LLM providers (to clear existing keys)
    const llmProviders = ['openai', 'anthropic', 'mistral'];
    if (hasEmptyField && !llmProviders.includes(provider)) {
        showError('Please fill in all required fields');
        return;
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
        } else {
            // For other providers, use a generic endpoint
            // Send all fields as a single request
            const response = await fetch(`${API_BASE_URL}/api/config/set-key`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider: provider, keys: values })
            });
            
            if (!response.ok) throw new Error('Failed to save API key');
            
            // Reload configuration
            await loadConfiguration();
            showSuccess(`${provider.toUpperCase()} API key(s) saved successfully!`);
            return;
        }
        
        // For OpenAI, Anthropic, and Mistral, use existing endpoint
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
            throw new Error(errorMessage);
        }
        
        // Reload configuration
        await loadConfiguration();
        showSuccess(`${provider.toUpperCase()} API key saved successfully!`);
        
        // Update badges and re-render sections
        if (configData && configData.api_keys) {
            // Check if it's an LLM provider
            const llmProviders = ['openai', 'anthropic', 'mistral'];
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
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                <polyline points="17 21 17 13 7 13 7 21"/>
                <polyline points="7 3 7 8 15 8"/>
            </svg>
            Save API Key
        `;
    }
}

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
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                        <polyline points="17 21 17 13 7 13 7 21"/>
                        <polyline points="7 3 7 8 15 8"/>
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
