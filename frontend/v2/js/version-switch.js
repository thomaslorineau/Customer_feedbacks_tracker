// Version switching functionality
import { API } from './api.js';

const api = new API();

export function openVersionModal() {
    document.getElementById('versionModal').style.display = 'flex';
}

export function closeVersionModal() {
    document.getElementById('versionModal').style.display = 'none';
}

export async function switchToVersion(version) {
    try {
        await api.setUIVersion(version);
        // Reload page to apply new version
        window.location.reload();
    } catch (error) {
        console.error('Failed to switch version:', error);
        alert(`Failed to switch to ${version}: ${error.message}`);
    }
}

// Make functions available globally for onclick handlers
window.openVersionModal = openVersionModal;
window.closeVersionModal = closeVersionModal;
window.switchToVersion = switchToVersion;

// Close modal on outside click
document.addEventListener('click', (event) => {
    const modal = document.getElementById('versionModal');
    if (event.target === modal) {
        closeVersionModal();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        const modal = document.getElementById('versionModal');
        if (modal && modal.style.display !== 'none') {
            closeVersionModal();
        }
    }
});

















