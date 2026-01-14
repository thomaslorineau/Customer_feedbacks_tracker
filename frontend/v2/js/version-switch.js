// Version switch functionality
import { API } from './api.js';

let api = null;

// Initialize API when DOM is ready
function initAPI() {
    if (!api) {
        api = new API();
    }
}

function openVersionModal() {
    const modal = document.getElementById('versionModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function closeVersionModal() {
    const modal = document.getElementById('versionModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function switchToVersion(version) {
    try {
        initAPI();
        const response = await api.setUIVersion(version);
        console.log('Version switched:', response);
        // Redirect to the appropriate version URL
        if (version === 'v1') {
            window.location.href = '/v1';
        } else {
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Failed to switch version:', error);
        alert('Failed to switch UI version: ' + error.message);
    }
}

// Setup event listeners when DOM is ready
function setupModalListeners() {
    // Version toggle button
    const versionToggleBtn = document.getElementById('versionToggleBtn');
    if (versionToggleBtn) {
        versionToggleBtn.addEventListener('click', openVersionModal);
    }
    
    // Close button
    const closeBtn = document.getElementById('closeVersionModalBtn');
    if (closeBtn) {
        closeBtn.addEventListener('click', closeVersionModal);
    }
    
    // Switch to V1 button
    const switchToV1Btn = document.getElementById('switchToV1Btn');
    if (switchToV1Btn) {
        switchToV1Btn.addEventListener('click', () => switchToVersion('v1'));
    }
    
    // Switch to V2 button
    const switchToV2Btn = document.getElementById('switchToV2Btn');
    if (switchToV2Btn) {
        switchToV2Btn.addEventListener('click', () => switchToVersion('v2'));
    }
    
    // Close modal on outside click
    const modal = document.getElementById('versionModal');
    if (modal) {
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeVersionModal();
            }
        });
    }
    
    // Close modal on Escape key
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            const modal = document.getElementById('versionModal');
            if (modal && modal.style.display !== 'none') {
                closeVersionModal();
            }
        }
    });
}

// Wait for DOM to be ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initAPI();
        setupModalListeners();
    });
} else {
    initAPI();
    setupModalListeners();
}

// Also make functions available globally for backward compatibility
window.openVersionModal = openVersionModal;
window.closeVersionModal = closeVersionModal;
window.switchToVersion = switchToVersion;

