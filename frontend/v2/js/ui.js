// UI rendering functions
import { State } from './state.js';

export function renderGallery(state) {
    const app = document.getElementById('app');
    if (!app) return;
    
    if (state.filteredPosts.length === 0) {
        app.innerHTML = `
            <div class="empty-state">
                <h2>No posts found</h2>
                <p>Try adjusting your filters or scrape new data.</p>
            </div>
        `;
        return;
    }
    
    const postsHTML = state.filteredPosts.map(post => `
        <div class="post-card">
            <div class="post-header">
                <span class="post-source source-${post.source?.toLowerCase().replace(/\s+/g, '-')}">
                    ${post.source || 'Unknown'}
                </span>
                <span class="post-date">${new Date(post.created_at).toLocaleDateString()}</span>
            </div>
            <div class="post-author">by ${post.author || 'Unknown'}</div>
            <div class="post-content">${post.content || 'No content'}</div>
            <div class="post-footer">
                <span class="sentiment sentiment-${post.sentiment_label || 'neutral'}">
                    ${(post.sentiment_label || 'neutral').toUpperCase()}
                </span>
                <a href="${post.url || '#'}" target="_blank" class="post-url">View Original</a>
            </div>
        </div>
    `).join('');
    
    app.innerHTML = `
        <div class="gallery">
            ${postsHTML}
        </div>
    `;
}

export function toggleTheme() {
    const body = document.body;
    const isDark = !body.classList.contains('light-mode');
    
    if (isDark) {
        body.classList.add('light-mode');
        localStorage.setItem('theme', 'light');
    } else {
        body.classList.remove('light-mode');
        localStorage.setItem('theme', 'dark');
    }
}

export function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
    }
}

// Make toggleTheme available globally for onclick
window.toggleTheme = toggleTheme;













