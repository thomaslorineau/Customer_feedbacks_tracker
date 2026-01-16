// Main application entry point
import { API } from './api.js';
import { State } from './state.js';
import { renderGallery, initializeTheme } from './ui.js';

class App {
    constructor() {
        this.api = new API();
        this.state = new State();
        this.init();
    }
    
    async init() {
        // Initialize theme
        initializeTheme();
        
        // Subscribe to state changes
        this.state.subscribe((state) => {
            renderGallery(state);
        });
        
        // Load initial data
        try {
            await this.loadPosts();
        } catch (error) {
            console.error('Failed to load posts:', error);
            document.getElementById('app').innerHTML = `
                <div class="empty-state">
                    <h2>Error loading posts</h2>
                    <p>${error.message}</p>
                </div>
            `;
        }
    }
    
    async loadPosts() {
        const posts = await this.api.getPosts(1000, 0);
        this.state.setPosts(posts);
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new App());
} else {
    new App();
}













