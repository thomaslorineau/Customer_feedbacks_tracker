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
        if (port && port !== '80' && port !== '443' && port !== '') {
            baseURL += `:${port}`;
        } else if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
            // For external access, use port 11840
            baseURL += ':11840';
        } else {
            // Local development - use same port as current page
            // If no port specified, try 8000
            if (!port || port === '') {
                baseURL += ':8000';
            }
        }
        
        return baseURL;
    }
    
    async getPosts(limit = 100, offset = 0) {
        const url = `${this.baseURL}/posts?limit=${limit}&offset=${offset}`;
        console.log('[API] Fetching posts from:', url);
        
        try {
            const response = await fetch(url);
            console.log('[API] Response status:', response.status, response.statusText);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('[API] Error response:', errorText);
                throw new Error(`Failed to fetch posts: ${response.status} ${response.statusText}. ${errorText}`);
            }
            
            const contentType = response.headers.get('content-type');
            console.log('[API] Content-Type:', contentType);
            
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                console.error('[API] Unexpected content type. Response:', text.substring(0, 200));
                throw new Error(`Unexpected content type: ${contentType}`);
            }
            
            const data = await response.json();
            console.log('[API] Data received:', {
                isArray: Array.isArray(data),
                length: Array.isArray(data) ? data.length : 'N/A',
                type: typeof data,
                firstItem: Array.isArray(data) && data.length > 0 ? data[0] : null
            });
            
            if (!Array.isArray(data)) {
                console.error('[API] Expected array but got:', typeof data, data);
                throw new Error('API returned non-array data');
            }
            
            console.log('[API] Returning', data.length, 'posts');
            return data;
        } catch (error) {
            console.error('[API] Fetch error:', error.message);
            console.error('[API] Error type:', error.name);
            if (error.cause) {
                console.error('[API] Error cause:', error.cause);
            }
            throw error;
        }
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
    
    async getVersion(timestamp = null) {
        try {
            // Add cache-busting timestamp to URL if provided
            let url = `${this.baseURL}/api/version`;
            if (timestamp) {
                url += `?t=${timestamp}`;
            }
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to get version: ${response.statusText}`);
            }
            return response.json();
        } catch (error) {
            console.warn('Failed to fetch version from API:', error);
            // Return default version
            return { version: '1.0.1' };
        }
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
    
    async getWhatsHappeningInsights(posts, stats, activeFilters, analysisFocus = '') {
        // Prepare posts data for LLM analysis - include more posts for better analysis
        const postsForAnalysis = posts.slice(0, 50).map(p => ({
            content: (p.content || '').substring(0, 600), // Increased from 400 to 600 for more context
            sentiment: p.sentiment_label,
            source: p.source,
            created_at: p.created_at,
            language: p.language,
            product: p.product || null,
            url: p.url || null
        }));
        
        const response = await fetch(`${this.baseURL}/api/whats-happening`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                posts: postsForAnalysis,
                stats: stats,
                active_filters: activeFilters,
                analysis_focus: analysisFocus || ''
            })
        });
        if (!response.ok) {
            throw new Error(`Failed to get What's Happening insights: ${response.statusText}`);
        }
        return response.json();
    }
    
    async startScrapingJob(keywords, limit = 50, concurrency = 2, delay = 0.5) {
        const response = await fetch(`${this.baseURL}/scrape/keywords?limit=${limit}&concurrency=${concurrency}&delay=${delay}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keywords })
        });
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `Failed to start scraping job: ${response.statusText}`);
        }
        return response.json();
    }
    
    async getJobStatus(jobId) {
        const response = await fetch(`${this.baseURL}/scrape/jobs/${jobId}`);
        if (!response.ok) {
            const error = new Error(`Failed to get job status: ${response.statusText}`);
            error.status = response.status;
            error.statusText = response.statusText;
            throw error;
        }
        return response.json();
    }
    
    async cancelJob(jobId) {
        const response = await fetch(`${this.baseURL}/scrape/jobs/${jobId}/cancel`, {
            method: 'POST'
        });
        if (!response.ok) {
            throw new Error(`Failed to cancel job: ${response.statusText}`);
        }
        return response.json();
    }
    
    async getSavedKeywords() {
        try {
            const response = await fetch(`${this.baseURL}/api/keywords`);
            if (!response.ok) {
                return [];
            }
            return response.json();
        } catch (error) {
            console.warn('Failed to fetch saved keywords:', error);
            return [];
        }
    }
}


