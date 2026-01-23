// Main application entry point
import { API } from './api.js';
import { State } from './state.js';
import { initDashboard, updateDashboard } from './dashboard.js';
import { initCharts } from './charts.js';
import { initSourceChart } from './source-chart-v2.js';
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
        try {
            this.api = new API();
            this.state = new State();
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
        // Initialize theme
        initializeTheme();
        
        // Setup theme toggle button
        setupThemeToggle();
        
        // Version loading is handled by version-loader.js module (loaded via script tag in HTML)
        
        // Show LLM analysis overlay IMMEDIATELY on page load
        const showWhatsHappeningOverlay = () => {
            const overlay = document.getElementById('whatsHappeningOverlay');
            if (overlay) {
                overlay.style.setProperty('display', 'flex', 'important');
                overlay.style.setProperty('z-index', '1000', 'important');
                overlay.style.setProperty('visibility', 'visible', 'important');
                overlay.style.setProperty('opacity', '1', 'important');
                overlay.removeAttribute('hidden');
            }
        };
        showWhatsHappeningOverlay();
        requestAnimationFrame(() => showWhatsHappeningOverlay());
        setTimeout(() => showWhatsHappeningOverlay(), 100);
        
        // Load initial data FIRST, before initializing dashboard (which sets default date filters)
        // Add timeout to ensure loading indicator is hidden even if API hangs
        const loadingTimeout = setTimeout(() => {
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
        }, 10000); // 10 second timeout
        
        try {
            await this.loadPosts();
            clearTimeout(loadingTimeout);
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
        
        // Ensure loading indicator is hidden after initialization
        setTimeout(() => {
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
        }, 500);
    }
    
    // Helper function to filter valid posts (exclude samples and relevance_score = 0)
    // Same logic as in data collection page (index.html) and dashboard.js
    filterValidPosts(posts) {
        return posts.filter(post => {
            // Filter out sample posts
            const url = post.url || '';
            const isSample = (
                url.includes('/sample') || 
                url.includes('example.com') ||
                url.includes('/status/174') ||
                url === 'https://trustpilot.com/sample'
            );
            if (isSample) return false;
            
            // Filter out posts with relevance_score = 0
            // Calculate relevance score (same logic as calculateRelevanceScore)
            let relevanceScore = post.relevance_score;
            if (relevanceScore === undefined || relevanceScore === null || relevanceScore <= 0) {
                // Calculate on frontend if not stored
                const content = (post.content || '').toLowerCase();
                const urlLower = (post.url || '').toLowerCase();
                const OVH_BRANDS = ['ovh', 'ovhcloud', 'ovh cloud', 'kimsufi', 'ovh.com', 'ovhcloud.com'];
                const hasBrand = OVH_BRANDS.some(brand => content.includes(brand) || urlLower.includes(brand));
                relevanceScore = hasBrand ? 0.5 : 0.0; // Simple check, full calculation is in dashboard.js
            }
            
            if (relevanceScore === 0 || relevanceScore === null || relevanceScore === undefined) {
                return false;
            }
            
            return true;
        });
    }

    async loadPosts() {
        try {
            const posts = await this.api.getPosts(10000, 0);  // Get all posts to ensure complete sync
            
            if (!posts || posts.length === 0) {
                this.showError('No posts found in database. Go to Feedbacks Collection to scrape some data.');
                // Show empty state message
                const postsList = document.getElementById('postsList');
                if (postsList) {
                    postsList.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">No posts found. Go to Feedbacks Collection to scrape some data.</div>';
                }
                return;
            }
            
            // Filter valid posts (exclude samples and relevance_score = 0) to match data collection page
            const validPosts = this.filterValidPosts(posts);
            
            // Set posts in state (will trigger dashboard update via subscription)
            this.state.setPosts(validPosts);
            
            // Hide loading indicator
            const loadingIndicator = document.getElementById('loadingIndicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
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

