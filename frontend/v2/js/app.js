// Main application entry point
import { API } from './api.js';
import { State } from './state.js';
import { initDashboard } from './dashboard.js';
import { initCharts } from './charts.js';
import { initWorldMap } from './world-map.js';
import { initSourceChart } from './source-chart.js';
import { initSentimentChart } from './sentiment-chart.js';

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
    
    if (isDark) {
        body.classList.remove('dark-mode');
        localStorage.setItem('theme', 'light');
    } else {
        body.classList.add('dark-mode');
        localStorage.setItem('theme', 'dark');
    }
    
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
        } catch (error) {
            console.error('Failed to load posts:', error);
        }
    }
    
    async loadPosts() {
        const posts = await this.api.getPosts(1000, 0);
        this.state.setPosts(posts);
        // Dashboard will update automatically via state subscription
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new App());
} else {
    new App();
}

