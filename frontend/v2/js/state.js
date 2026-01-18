// Application state management
export class State {
    constructor() {
        this.posts = [];
        this.filteredPosts = [];
        this.filters = {
            search: '',
            sentiment: '',
            source: '',
            language: '',
            product: '',
            dateFrom: '',
            dateTo: ''
        };
        this.listeners = [];
    }
    
    setPosts(posts) {
        this.posts = posts;
        this.applyFilters();
        this.notifyListeners();
    }
    
    setFilter(key, value) {
        this.filters[key] = value;
        this.applyFilters();
        this.notifyListeners();
    }
    
    applyFilters() {
        this.filteredPosts = this.posts.filter(post => {
            // Search filter
            if (this.filters.search) {
                const searchLower = this.filters.search.toLowerCase();
                const matchesSearch = 
                    post.content?.toLowerCase().includes(searchLower) ||
                    post.author?.toLowerCase().includes(searchLower) ||
                    post.url?.toLowerCase().includes(searchLower);
                if (!matchesSearch) return false;
            }
            
            // Sentiment filter
            if (this.filters.sentiment && post.sentiment_label !== this.filters.sentiment) {
                return false;
            }
            
            // Source filter
            if (this.filters.source && post.source !== this.filters.source) {
                return false;
            }
            
            // Language filter
            if (this.filters.language && post.language !== this.filters.language) {
                return false;
            }
            
            // Date filters
            if (this.filters.dateFrom) {
                const postDate = new Date(post.created_at).toISOString().split('T')[0];
                if (postDate < this.filters.dateFrom) return false;
            }
            
            if (this.filters.dateTo) {
                const postDate = new Date(post.created_at).toISOString().split('T')[0];
                if (postDate > this.filters.dateTo) return false;
            }
            
            return true;
        });
    }
    
    subscribe(listener) {
        this.listeners.push(listener);
        return () => {
            this.listeners = this.listeners.filter(l => l !== listener);
        };
    }
    
    notifyListeners() {
        this.listeners.forEach(listener => listener(this));
    }
}























