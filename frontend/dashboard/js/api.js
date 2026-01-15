// API client for backend communication
export class API {
    constructor() {
        this.baseURL = this.getApiBase();
    }
    
    getApiBase() {
        // Detect API base URL from current location
        const hostname = window.location.hostname;
        const port = window.location.port;
        
        // Default to current hostname and port
        let baseURL = `${window.location.protocol}//${hostname}`;
        
        // If port is specified and not standard, use it
        if (port && port !== '80' && port !== '443') {
            baseURL += `:${port}`;
        } else if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
            // For external access, use port 11840
            baseURL += ':11840';
        } else {
            // Local development
            baseURL += ':8000';
        }
        
        return baseURL;
    }
    
    async getPosts(limit = 100, offset = 0) {
        const response = await fetch(`${this.baseURL}/posts?limit=${limit}&offset=${offset}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch posts: ${response.statusText}`);
        }
        return response.json();
    }
    
    async scrape(source, query = 'OVH', limit = 50) {
        const response = await fetch(`${this.baseURL}/scrape/${source}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, limit })
        });
        if (!response.ok) {
            throw new Error(`Failed to scrape ${source}: ${response.statusText}`);
        }
        return response.json();
    }
    
    async getUIVersion() {
        const response = await fetch(`${this.baseURL}/admin/get-ui-version`);
        if (!response.ok) {
            throw new Error(`Failed to get UI version: ${response.statusText}`);
        }
        return response.json();
    }
    
    async setUIVersion(version) {
        const response = await fetch(`${this.baseURL}/admin/set-ui-version`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ version })
        });
        if (!response.ok) {
            throw new Error(`Failed to set UI version: ${response.statusText}`);
        }
        return response.json();
    }
    
    async getRecommendedActions(posts, recentPosts, stats, maxActions = 5) {
        // Prepare posts data - include more context for LLM
        const postsForAnalysis = posts.slice(0, 30).map(p => ({
            content: (p.content || '').substring(0, 400),
            sentiment: p.sentiment_label,
            source: p.source,
            created_at: p.created_at,
            language: p.language,
            product: p.product || null
        }));
        
        const recentPostsForAnalysis = recentPosts.slice(0, 20).map(p => ({
            content: (p.content || '').substring(0, 400),
            sentiment: p.sentiment_label,
            source: p.source,
            created_at: p.created_at,
            language: p.language,
            product: p.product || null
        }));
        
        const response = await fetch(`${this.baseURL}/api/recommended-actions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                posts: posts,
                recent_posts: recentPosts,
                stats: stats,
                max_actions: maxActions
            })
        });
        if (!response.ok) {
            throw new Error(`Failed to get recommended actions: ${response.statusText}`);
        }
        return response.json();
    }
}


