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
            dateTo: '',
            answered: 'all'
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
        let filteredCount = 0;
        let excludedBySample = 0;
        let excludedBySearch = 0;
        let excludedBySentiment = 0;
        let excludedBySource = 0;
        let excludedByLanguage = 0;
        let excludedByProduct = 0;
        let excludedByDate = 0;
        let excludedByAnswered = 0;
        
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
                if (!matchesSearch) {
                    excludedBySearch++;
                    return false;
                }
            }
            
            // Sentiment filter
            if (this.filters.sentiment && this.filters.sentiment !== 'all' && post.sentiment_label !== this.filters.sentiment) {
                excludedBySentiment++;
                return false;
            }
            
            // Source filter (normalize GitHub and Mastodon sources)
            // Only filter if source is set and not empty
            if (this.filters.source && this.filters.source !== '' && this.filters.source !== 'all') {
                let normalizedSource = post.source;
                if (post.source === 'GitHub Issues' || post.source === 'GitHub Discussions') {
                    normalizedSource = 'GitHub';
                } else if (post.source && post.source.startsWith('Mastodon (')) {
                    normalizedSource = 'Mastodon';
                }
                if (normalizedSource !== this.filters.source && post.source !== this.filters.source) {
                    excludedBySource++;
                    return false;
                }
            }
            
            // Language filter - handle null/undefined and normalize comparison
            if (this.filters.language && this.filters.language !== 'all') {
                const postLanguage = (post.language || '').toLowerCase();
                const filterLanguage = (this.filters.language || '').toLowerCase();
                if (postLanguage !== filterLanguage) {
                    excludedByLanguage++;
                    return false;
                }
            }
            
            // Product filter - use keyword matching based on official OVH products
            if (this.filters.product && this.filters.product !== 'all') {
                const content = (post.content || '').toLowerCase();
                const productLower = this.filters.product.toLowerCase();
                // Extended keyword matching based on official OVH products (aligned with insights.py)
                const productKeywords = {
                    'VPS': ['vps', 'virtual private server', 'ovh vps', 'vps cloud', 'cloud vps'],
                    'Hosting': ['hosting', 'web hosting', 'shared hosting', 'ovh hosting', 'web hosting plan'],
                    'Domain': ['domain', 'domaine', 'domain name', 'domain registration', 'domain renewal', 'domain transfer', 'domain expiration', 'registrar', 'bureau d\'enregistrement', 'whois', 'domain management', '.ovh', '.com', '.net', '.org', '.fr', '.eu'],
                    'DNS': ['dns', 'dns zone', 'dns anycast', 'dnssec', 'dns record', 'dns configuration', 'nameserver', 'ns record', 'a record', 'mx record', 'cname record', 'txt record', 'dns management', 'dns hosting'],
                    'Email': ['email', 'mail', 'smtp', 'imap', 'pop3', 'email hosting', 'exchange', 'email account'],
                    'Storage': ['storage', 'object storage', 's3', 'cloud storage', 'object storage s3', 'high performance storage'],
                    'CDN': ['cdn', 'content delivery', 'content delivery network', 'ovh cdn'],
                    'Public Cloud': ['public cloud', 'publiccloud', 'ovh public cloud', 'public cloud instance', 'horizon', 'openstack'],
                    'Private Cloud': ['private cloud', 'privatecloud', 'ovh private cloud', 'vmware', 'vsphere', 'hosted private cloud'],
                    'Dedicated Server': ['dedicated', 'dedicated server', 'serveur dédié', 'bare metal', 'ovh dedicated', 'server', 'serveur'],
                    'API': ['api', 'rest api', 'graphql', 'ovh api', 'api ovh', 'ovhcloud api'],
                    'Load Balancer': ['load balancer', 'loadbalancer', 'lb', 'ip load balancing'],
                    'Failover IP': ['failover ip', 'failover', 'ip failover', 'additional ip'],
                    'SSL Certificate': ['ssl', 'ssl certificate', 'certificate', 'tls', 'https certificate'],
                    'Managed Kubernetes': ['kubernetes', 'k8s', 'managed kubernetes', 'ovh kubernetes'],
                    'Managed Databases': ['database', 'mysql', 'postgresql', 'mongodb', 'redis', 'managed database', 'ovh database'],
                    'Network': ['network', 'vrack', 'private network', 'vlan'],
                    'IP': ['ip address', 'ipv4', 'ipv6', 'ip block', 'ip range']
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
                if (postDateStr < filterDateFromStr) {
                    excludedByDate++;
                    return false;
                }
            }
            
            if (this.filters.dateTo) {
                const postDateStr = new Date(post.created_at).toISOString().split('T')[0];
                const filterDateToStr = this.filters.dateTo;
                // Compare date strings (YYYY-MM-DD format)
                if (postDateStr > filterDateToStr) {
                    excludedByDate++;
                    return false;
                }
            }
            
            // Answered filter
            if (this.filters.answered && this.filters.answered !== 'all') {
                const isAnswered = post.is_answered === 1 || post.is_answered === true;
                if (this.filters.answered === '1' && !isAnswered) {
                    excludedByAnswered++;
                    return false;
                }
                if (this.filters.answered === '0' && isAnswered) {
                    excludedByAnswered++;
                    return false;
                }
            }
            
            filteredCount++;
            return true;
        });
        
        // Auto-clear source filter if it filters all posts (but avoid infinite loop)
        if (this.filteredPosts.length === 0 && this.posts.length > 0 && this.filters.source && this.filters.source !== '' && this.filters.source !== 'all' && excludedBySource === this.posts.length) {
            this.filters.source = '';
            // Re-apply filters without source filter (but only once to avoid infinite loop)
            if (!this._clearingSourceFilter) {
                this._clearingSourceFilter = true;
                this.applyFilters();
                this._clearingSourceFilter = false;
            }
        }
    }
    
    subscribe(listener) {
        this.listeners.push(listener);
    }
    
    notifyListeners() {
        this.listeners.forEach(listener => listener(this));
    }
}

