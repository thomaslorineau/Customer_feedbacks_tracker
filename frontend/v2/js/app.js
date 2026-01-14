// Main application entry point
import { API } from './api.js';
import { State } from './state.js';
import { initDashboard } from './dashboard.js';
import { initCharts } from './charts.js';

function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
    }
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
}

// Setup theme toggle button
function setupThemeToggle() {
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

