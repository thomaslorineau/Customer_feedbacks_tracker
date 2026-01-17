// Settings page - API Configuration
const API_BASE_URL = window.location.origin; // Use current server URL

// Debug: Log API base URL
console.log('API_BASE_URL:', API_BASE_URL);

// State
let configData = null;
let revealedKeys = new Set();

// Load and display version
async function loadVersion() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/version`);
        if (response.ok) {
            const data = await response.json();
            const versionBadge = document.getElementById('versionBadge');
            if (versionBadge) {
                versionBadge.textContent = `v${data.version}`;
                versionBadge.title = `Version ${data.version} - Build: ${new Date(data.build_date).toLocaleDateString()}`;
            }
        }
    } catch (error) {
        console.warn('Failed to load version:', error);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    loadVersion();
    loadConfiguration();
    loadBaseKeywords();
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
        renderAPIKeys();
        renderRateLimiting();
    } catch (error) {
        console.error('Error loading configuration:', error);
        showError(`Failed to load configuration: ${error.message}`);
    }
}

// Render API Keys
function renderAPIKeys() {
    const container = document.getElementById('apiKeysContainer');
    if (!container) {
        console.error('apiKeysContainer not found');
        return;
    }
    
    if (!configData || !configData.api_keys) {
        console.error('configData or api_keys missing', configData);
        return;
    }
    
    const providers = [
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
            id: 'google', 
            name: 'Google AI', 
            icon: '🔍',
            description: 'Gemini models for multimodal AI capabilities',
            docsUrl: 'https://makersuite.google.com/app/apikey'
        },
        { 
            id: 'github', 
            name: 'GitHub', 
            icon: '🐙',
            description: 'Personal access token for enhanced rate limits',
            docsUrl: 'https://github.com/settings/tokens'
        },
        { 
            id: 'trustpilot', 
            name: 'Trustpilot', 
            icon: '⭐',
            description: 'API access for Trustpilot review scraping',
            docsUrl: 'https://developers.trustpilot.com/'
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
    
    container.innerHTML = providers.map(provider => {
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
                        <div class="key-display ${revealedKeys.has(provider.id) ? '' : 'hidden'}" 
                             id="key-${provider.id}">
                            ${revealedKeys.has(provider.id) ? '••••••••' : maskedKey}
                        </div>
                        <div class="key-actions">
                            <button class="btn-icon" 
                                    onclick="toggleRevealKey('${provider.id}')"
                                    id="reveal-btn-${provider.id}">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                    <circle cx="12" cy="12" r="3"/>
                                </svg>
                                ${revealedKeys.has(provider.id) ? 'Hide' : 'Reveal'}
                            </button>
                            <button class="btn-icon secondary" 
                                    onclick="copyKey('${provider.id}')"
                                    id="copy-btn-${provider.id}">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                                </svg>
                                Copy
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
    }).join('');
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
        <div class="info-card">
            <div class="info-card-label">Environment</div>
            <div class="info-card-value" style="font-size: 1.25rem; text-transform: capitalize;">
                ${configData.environment}
            </div>
        </div>
        <div class="info-card">
            <div class="info-card-label">Active LLM Provider</div>
            <div class="info-card-value" style="font-size: 1.25rem; text-transform: capitalize;">
                ${configData.llm_provider}
            </div>
        </div>
    `;
}

// Toggle Reveal Key
async function toggleRevealKey(provider) {
    const keyDisplay = document.getElementById(`key-${provider}`);
    const revealBtn = document.getElementById(`reveal-btn-${provider}`);
    
    if (revealedKeys.has(provider)) {
        // Hide the key
        revealedKeys.delete(provider);
        keyDisplay.textContent = configData.api_keys[provider].masked;
        keyDisplay.classList.add('hidden');
        revealBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
            </svg>
            Reveal
        `;
    } else {
        // Reveal the key
        revealBtn.innerHTML = '<span class="loading-spinner"></span> Loading...';
        revealBtn.disabled = true;
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/config/reveal-key?provider=${provider}`, {
                method: 'POST'
            });
            
            if (!response.ok) throw new Error('Failed to reveal key');
            
            const data = await response.json();
            revealedKeys.add(provider);
            keyDisplay.textContent = data.key;
            keyDisplay.classList.remove('hidden');
            revealBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
                Hide
            `;
            
            // Auto-hide after 30 seconds for security
            setTimeout(() => {
                if (revealedKeys.has(provider)) {
                    toggleRevealKey(provider);
                }
            }, 30000);
            
        } catch (error) {
            console.error('Error revealing key:', error);
            showError('Failed to reveal API key');
            revealBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                </svg>
                Reveal
            `;
        } finally {
            revealBtn.disabled = false;
        }
    }
}

// Copy Key to Clipboard
async function copyKey(provider) {
    const copyBtn = document.getElementById(`copy-btn-${provider}`);
    const keyDisplay = document.getElementById(`key-${provider}`);
    
    let keyToCopy = keyDisplay.textContent;
    
    // If key is not revealed, reveal it first
    if (!revealedKeys.has(provider)) {
        copyBtn.innerHTML = '<span class="loading-spinner"></span>';
        copyBtn.disabled = true;
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/config/reveal-key?provider=${provider}`, {
                method: 'POST'
            });
            
            if (!response.ok) throw new Error('Failed to get key');
            
            const data = await response.json();
            keyToCopy = data.key;
        } catch (error) {
            console.error('Error getting key:', error);
            showError('Failed to copy API key');
            copyBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
                Copy
            `;
            copyBtn.disabled = false;
            return;
        }
    }
    
    // Copy to clipboard
    try {
        await navigator.clipboard.writeText(keyToCopy);
        
        // Show success feedback
        const feedback = document.getElementById('copyFeedback');
        feedback.querySelector('span').textContent = `${provider.toUpperCase()} API key copied to clipboard!`;
        feedback.classList.add('show');
        
        // Update button to show success
        copyBtn.classList.add('success');
        copyBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
            Copied!
        `;
        
        setTimeout(() => {
            feedback.classList.remove('show');
            copyBtn.classList.remove('success');
            copyBtn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
                Copy
            `;
        }, 3000);
        
    } catch (error) {
        console.error('Error copying to clipboard:', error);
        showError('Failed to copy to clipboard');
    } finally {
        copyBtn.disabled = false;
    }
}

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
        { id: 'google', fields: [{ name: 'GOOGLE_API_KEY' }] },
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
    
    if (hasEmptyField) {
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
        
        // For OpenAI and Anthropic, use existing endpoint
        const response = await fetch(`${API_BASE_URL}/api/llm-config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) throw new Error('Failed to save API key');
        
        // Reload configuration
        await loadConfiguration();
        showSuccess(`${provider.toUpperCase()} API key saved successfully!`);
        
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
                <div class="form-group">
                    <label>Brands (Marques OVH)</label>
                    <textarea id="baseKeywordsBrands" class="keywords-textarea" rows="3" placeholder="OVH, OVHCloud, Kimsufi...">${(data.brands || []).join(', ')}</textarea>
                </div>
                <div class="form-group">
                    <label>Products (Produits OVH)</label>
                    <textarea id="baseKeywordsProducts" class="keywords-textarea" rows="3" placeholder="OVH domain, OVH hosting, OVH VPS...">${(data.products || []).join(', ')}</textarea>
                </div>
                <div class="form-group">
                    <label>Problems (Problèmes/Complaints)</label>
                    <textarea id="baseKeywordsProblems" class="keywords-textarea" rows="3" placeholder="OVH complaint, OVH support, OVH billing...">${(data.problems || []).join(', ')}</textarea>
                </div>
                <div class="form-group">
                    <label>Leadership (Direction OVH)</label>
                    <textarea id="baseKeywordsLeadership" class="keywords-textarea" rows="3" placeholder="Michel Paulin, Octave Klaba, OVH CEO...">${(data.leadership || []).join(', ')}</textarea>
                </div>
                <div class="form-actions">
                    <button class="btn-save-key" onclick="saveBaseKeywords()">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                            <polyline points="17 21 17 13 7 13 7 21"/>
                            <polyline points="7 3 7 8 15 8"/>
                        </svg>
                        Save Base Keywords
                    </button>
                </div>
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
