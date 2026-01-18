// Main application entry point
import { API } from './api.js';
import { State } from './state.js';
import { initDashboard, updateDashboard } from './dashboard.js';
import { initCharts } from './charts.js';
import { initWorldMap } from './world-map.js';
import { initSourceChart } from './source-chart.js';
import { initSentimentChart } from './sentiment-chart.js';
// Version loading is handled by version-loader.js module (loaded via script tag in HTML)

function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
    
    // Listen for theme changes from other pages
    window.addEventListener('storage', (e) => {
        if (e.key === 'theme') {
            if (e.newValue === 'dark') {
                document.body.classList.add('dark-mode');
            } else {
                document.body.classList.remove('dark-mode');
            }
        }
    });
    
    // Listen for theme change events
    window.addEventListener('themeChanged', (e) => {
        if (e.detail.theme === 'dark') {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
    });
}

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

// Setup theme toggle button (can be in nav menu or standalone)
function setupThemeToggle() {
    // Try to find theme toggle in nav menu first
    const navThemeToggle = document.querySelector('.nav-menu-right .theme-toggle');
    if (navThemeToggle) {
        navThemeToggle.addEventListener('click', toggleTheme);
    }
    
    // Fallback to standalone button if exists
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }
}

// Make toggleTheme available globally for backward compatibility
window.toggleTheme = toggleTheme;

class App {
    constructor() {
        this.api = new API();
        this.state = new State();
        this.init();
    }
    
    async init() {
        // Initialize theme
        initializeTheme();
        
        // Setup theme toggle button
        setupThemeToggle();
        
        // Version loading is handled by version-loader.js module (loaded via script tag in HTML)
        
        // Initialize charts
        initCharts(this.state);
        
        // Initialize dashboard
        initDashboard(this.state);
        
        // Initialize world map (hidden by default)
        initWorldMap();
        
        // Initialize source chart (with state for filtering)
        initSourceChart(this.state);
        
        // Initialize sentiment chart (with state for filtering)
        initSentimentChart(this.state);
        
        // Load initial data
        try {
            await this.loadPosts();
            // Manually trigger dashboard update after posts are loaded
            setTimeout(() => {
                if (typeof updateDashboard === 'function') {
                    updateDashboard();
                }
            }, 100);
        } catch (error) {
            console.error('Failed to load posts:', error);
        }
    }
    
    async loadPosts() {
        try {
            console.log('App: Loading posts from API...');
            console.log('App: API Base URL:', this.api.baseURL);
            const posts = await this.api.getPosts(1000, 0);
            console.log('App: Posts loaded:', posts?.length || 0, 'posts');
            console.log('App: First post sample:', posts?.[0]);
            
            if (!posts || posts.length === 0) {
                console.warn('App: No posts found in database');
                // Show empty state message
                const postsList = document.getElementById('postsList');
                if (postsList) {
                    postsList.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">No posts found. Go to Feedbacks Collection to scrape some data.</div>';
                }
                return;
            }
            
            this.state.setPosts(posts);
            console.log('App: Posts set in state. Filtered posts:', this.state.filteredPosts?.length || 0);
            
            // Dashboard will update automatically via state subscription in initDashboard
            // Also manually trigger dashboard update to ensure everything is displayed
            setTimeout(() => {
                if (typeof updateDashboard === 'function') {
                    console.log('App: Calling updateDashboard() with', this.state.filteredPosts?.length || 0, 'filtered posts');
                    updateDashboard();
                } else {
                    console.error('App: updateDashboard function not found');
                }
            }, 100);
        } catch (error) {
            console.error('App: Failed to load posts:', error);
            console.error('App: Error details:', error.message, error.stack);
            // Show error message
            const postsList = document.getElementById('postsList');
            if (postsList) {
                postsList.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--error);">Error loading data: ${error.message}<br>Check console for details.</div>`;
            }
        }
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new App());
} else {
    new App();
}

