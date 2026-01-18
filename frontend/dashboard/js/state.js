// Application state management
export class State {
    constructor() {
        this.posts = [];
        this.filteredPosts = [];
        this.listeners = [];
        this.postsPage = 1; // Pagination for posts list
        this.filters = {
            search: '',
            sentiment: 'all',
            source: '',
            language: 'all',
            product: 'all',
            dateFrom: '',
            dateTo: ''
        };
    }
    
    setPosts(posts) {
        this.posts = posts;
        this.applyFilters();
        this.notifyListeners();
    }
    
    setFilter(key, value) {
        // Don't apply filter if value is empty string and it's a date filter (allow showing all dates)
        if ((key === 'dateFrom' || key === 'dateTo') && value === '') {
            this.filters[key] = '';
        } else {
            this.filters[key] = value;
        }
        // Reset pagination when filters change
        this.postsPage = 1;
        this.applyFilters();
        this.notifyListeners();
    }
    
    applyFilters() {
        console.log('Applying filters:', this.filters);
        console.log('Total posts before filtering:', this.posts.length);
        this.filteredPosts = this.posts.filter(post => {
            // Filter out sample posts
            const url = post.url || '';
            const isSample = (
                url.includes('/sample') || 
                url.includes('example.com') ||
                url.includes('/status/174') ||
                url === 'https://trustpilot.com/sample'
            );
            if (isSample) return false;
            
            // Search filter
            if (this.filters.search) {
                const searchLower = this.filters.search.toLowerCase();
                const matchesSearch = 
                    post.content?.toLowerCase().includes(searchLower) ||
                    post.author?.toLowerCase().includes(searchLower) ||
                    post.url?.toLowerCase().includes(searchLower) ||
                    post.source?.toLowerCase().includes(searchLower);
                if (!matchesSearch) return false;
            }
            
            // Sentiment filter
            if (this.filters.sentiment && this.filters.sentiment !== 'all' && post.sentiment_label !== this.filters.sentiment) {
                return false;
            }
            
            // Source filter (normalize GitHub sources)
            if (this.filters.source) {
                const normalizedSource = (post.source === 'GitHub Issues' || post.source === 'GitHub Discussions') ? 'GitHub' : post.source;
                if (normalizedSource !== this.filters.source && post.source !== this.filters.source) {
                    return false;
                }
            }
            
            // Language filter
            if (this.filters.language && this.filters.language !== 'all' && post.language !== this.filters.language) {
                return false;
            }
            
            // Product filter - use getProductLabel
            if (this.filters.product && this.filters.product !== 'all') {
                // Import getProductLabel dynamically
                import('./product-detection.js').then(module => {
                    const productLabel = module.getProductLabel(post.id, post.content, post.language);
                    if (productLabel !== this.filters.product) {
                        return false;
                    }
                });
                // Synchronous check for now
                const content = (post.content || '').toLowerCase();
                const productLower = this.filters.product.toLowerCase();
                // Simple keyword matching as fallback
                const productKeywords = {
                    'Billing': ['billing', 'invoice', 'payment', 'charge', 'refund'],
                    'VPS': ['vps', 'virtual private server'],
                    'Hosting': ['hosting', 'web hosting', 'shared hosting'],
                    'Manager': ['manager', 'control panel', 'dashboard'],
                    'API': ['api', 'rest api', 'api key'],
                    'Domain': ['domain', 'dns', 'domain name'],
                    'Support': ['support', 'ticket', 'help', 'assistance'],
                    'Network': ['network', 'bandwidth', 'traffic', 'ddos'],
                    'Storage': ['storage', 'backup', 'snapshot'],
                    'Database': ['database', 'mysql', 'postgresql']
                };
                const keywords = productKeywords[this.filters.product] || [productLower];
                if (!keywords.some(kw => content.includes(kw))) {
                    return false;
                }
            }
            
            // Date filters
            if (this.filters.dateFrom) {
                const postDateStr = new Date(post.created_at).toISOString().split('T')[0];
                const filterDateFromStr = this.filters.dateFrom;
                // Compare date strings (YYYY-MM-DD format)
                if (postDateStr < filterDateFromStr) return false;
            }
            
            if (this.filters.dateTo) {
                const postDateStr = new Date(post.created_at).toISOString().split('T')[0];
                const filterDateToStr = this.filters.dateTo;
                // Compare date strings (YYYY-MM-DD format)
                if (postDateStr > filterDateToStr) return false;
            }
            
            return true;
        });
        console.log('Filtered posts count:', this.filteredPosts.length);
    }
    
    subscribe(listener) {
        this.listeners.push(listener);
    }
    
    notifyListeners() {
        this.listeners.forEach(listener => listener(this));
    }
}

