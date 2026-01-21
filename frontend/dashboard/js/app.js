// Main application entry point
import { API } from './api.js';
import { State } from './state.js';
import { initDashboard, updateDashboard } from './dashboard.js';
import { initCharts } from './charts.js';
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
        console.log('App: Constructor called');
        try {
            this.api = new API();
            console.log('App: API initialized, baseURL:', this.api.baseURL);
            this.state = new State();
            console.log('App: State initialized');
            this.init();
        } catch (error) {
            console.error('App: Error in constructor:', error);
            this.showError('Failed to initialize application: ' + error.message);
        }
    }
    
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'position: fixed; top: 20px; left: 50%; transform: translateX(-50%); background: #ef4444; color: white; padding: 20px; border-radius: 8px; z-index: 10000; max-width: 600px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);';
        errorDiv.innerHTML = `<strong>❌ Error:</strong> ${message}<br><small>Check console (F12) for details</small>`;
        document.body.appendChild(errorDiv);
        setTimeout(() => errorDiv.remove(), 10000);
    }
    
    async init() {
        console.log('App: Initializing...');
        
        // Initialize theme
        initializeTheme();
        
        // Setup theme toggle button
        setupThemeToggle();
        
        // Version loading is handled by version-loader.js module (loaded via script tag in HTML)
        
        // Load initial data FIRST, before initializing dashboard (which sets default date filters)
        // Add timeout to ensure loading indicator is hidden even if API hangs
        const loadingTimeout = setTimeout(() => {
            console.warn('App: Loading timeout - hiding loading indicator');
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
        }, 10000); // 10 second timeout
        
        try {
            console.log('App: Loading posts before initializing dashboard...');
            await this.loadPosts();
            clearTimeout(loadingTimeout);
            console.log('App: Posts loaded, now initializing dashboard...');
        } catch (error) {
            clearTimeout(loadingTimeout);
            console.error('App: Failed to load posts:', error);
            // Hide loading indicator even on error
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
        }
        
        // Initialize charts
        try {
            initCharts(this.state);
        } catch (error) {
            console.error('App: Error initializing charts:', error);
        }
        
        // Initialize dashboard (this will set default date filters, but posts are already loaded)
        try {
            initDashboard(this.state);
        } catch (error) {
            console.error('App: Error initializing dashboard:', error);
        }
        
        // Initialize source chart (with state for filtering)
        try {
            initSourceChart(this.state);
        } catch (error) {
            console.error('App: Error initializing source chart:', error);
        }
        
        // Initialize sentiment chart (with state for filtering)
        try {
            initSentimentChart(this.state);
        } catch (error) {
            console.error('App: Error initializing sentiment chart:', error);
        }
        
        // Manually trigger dashboard update after everything is initialized
        setTimeout(() => {
            if (typeof updateDashboard === 'function') {
                console.log('App: Triggering final dashboard update...');
                updateDashboard();
            } else {
                console.error('App: updateDashboard function not found');
            }
            // Ensure loading indicator is hidden
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
        }, 500);
    }
    
    async loadPosts() {
        try {
            console.log('App: Loading posts from API...');
            console.log('App: API Base URL:', this.api.baseURL);
            
            const url = `${this.api.baseURL}/posts?limit=1000&offset=0`;
            console.log('App: Full URL:', url);
            
            const posts = await this.api.getPosts(1000, 0);
            console.log('App: Posts loaded:', posts?.length || 0, 'posts');
            console.log('App: Posts type:', Array.isArray(posts) ? 'Array' : typeof posts);
            
            if (posts && posts.length > 0) {
                console.log('App: First post sample:', posts[0]);
            }
            
            if (!posts || posts.length === 0) {
                console.warn('App: No posts found in database');
                this.showError('No posts found in database. Go to Feedbacks Collection to scrape some data.');
                // Show empty state message
                const postsList = document.getElementById('postsList');
                if (postsList) {
                    postsList.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">No posts found. Go to Feedbacks Collection to scrape some data.</div>';
                }
                return;
            }
            
            console.log('App: Setting posts in state...');
            this.state.setPosts(posts);
            console.log('App: Posts set in state. Total posts:', this.state.posts?.length || 0);
            console.log('App: Filtered posts:', this.state.filteredPosts?.length || 0);
            
            // Hide loading indicator
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            
            // Dashboard will update automatically via state subscription in initDashboard
            // Also manually trigger dashboard update to ensure everything is displayed
            setTimeout(() => {
                if (typeof updateDashboard === 'function') {
                    console.log('App: Calling updateDashboard() with', this.state.filteredPosts?.length || 0, 'filtered posts');
                    updateDashboard();
                } else {
                    console.error('App: updateDashboard function not found');
                    this.showError('updateDashboard function not found. Check console for details.');
                }
            }, 100);
        } catch (error) {
            console.error('App: Failed to load posts:', error);
            console.error('App: Error details:', error.message);
            console.error('App: Error stack:', error.stack);
            
            // Hide loading indicator
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            
            this.showError(`Failed to load posts: ${error.message}. Check console (F12) for details.`);
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

