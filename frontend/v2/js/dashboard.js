// Dashboard UI management
import { API } from './api.js';
import { State } from './state.js';
import { getProductLabel } from './product-detection.js';
import { updateWhatsHappening } from './whats-happening.js';

const api = new API();
let state = null;

export function initDashboard(appState) {
    state = appState;
    
    // Initialize event listeners
    setupEventListeners();
    
    // Load initial data
    loadDashboardData();
}

function setupEventListeners() {
    // Global search
    const globalSearch = document.getElementById('globalSearch');
    if (globalSearch) {
        globalSearch.addEventListener('input', (e) => {
            state.setFilter('search', e.target.value);
            updateDashboard();
        });
    }
    
    // Filters
    const sentimentFilter = document.getElementById('sentimentFilter');
    if (sentimentFilter) {
        sentimentFilter.addEventListener('change', (e) => {
            state.setFilter('sentiment', e.target.value);
            updateDashboard();
        });
    }
    
    const languageFilter = document.getElementById('languageFilter');
    if (languageFilter) {
        languageFilter.addEventListener('change', (e) => {
            state.setFilter('language', e.target.value);
            updateDashboard();
        });
    }
    
    const productFilter = document.getElementById('productFilter');
    if (productFilter) {
        productFilter.addEventListener('change', (e) => {
            state.setFilter('product', e.target.value);
            updateDashboard();
        });
    }
    
    // Sort
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            sortPosts(e.target.value);
        });
    }
    
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
    
    // Scrape All button
    const scrapeAllBtn = document.getElementById('scrapeAllBtn');
    if (scrapeAllBtn) {
        scrapeAllBtn.addEventListener('click', scrapeAll);
    }
    
    // Reset Filters button
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }
    
    // Show More Products button
    const showMoreProductsBtn = document.getElementById('showMoreProductsBtn');
    if (showMoreProductsBtn) {
        showMoreProductsBtn.addEventListener('click', showMoreProducts);
    }
    
    // Navigate Products buttons
    const navigateProductsPrevBtn = document.getElementById('navigateProductsPrevBtn');
    if (navigateProductsPrevBtn) {
        navigateProductsPrevBtn.addEventListener('click', () => navigateProducts(-1));
    }
    
    const navigateProductsNextBtn = document.getElementById('navigateProductsNextBtn');
    if (navigateProductsNextBtn) {
        navigateProductsNextBtn.addEventListener('click', () => navigateProducts(1));
    }
}

async function loadDashboardData() {
    try {
        const posts = await api.getPosts(1000, 0);
        state.setPosts(posts);
        updateDashboard();
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
    }
}

function updateDashboard() {
    updateWhatsHappening(state);
    updateProductDistribution();
    updatePostsList();
    // Charts will be updated by charts.js
}

function updateStatsBanner() {
    const statsBanner = document.getElementById('statsBanner');
    if (!statsBanner || !state) return;
    
    const posts = state.filteredPosts || [];
    const allPosts = state.posts || [];
    
    const total = posts.length;
    const totalAll = allPosts.length;
    const positive = posts.filter(p => p.sentiment_label === 'positive').length;
    const negative = posts.filter(p => p.sentiment_label === 'negative').length;
    const neutral = posts.filter(p => p.sentiment_label === 'neutral' || !p.sentiment_label).length;
    
    statsBanner.innerHTML = `
        <div class="stats-banner-title">
            📊 FILTERED STATS
        </div>
        <div class="stats-banner-cards">
            <div class="stats-banner-card">
                <div class="stats-banner-card-value">${total}</div>
                <div class="stats-banner-card-label">Total Posts</div>
            </div>
            <div class="stats-banner-card positive">
                <div class="stats-banner-card-value">${positive}</div>
                <div class="stats-banner-card-label">Positive</div>
            </div>
            <div class="stats-banner-card negative">
                <div class="stats-banner-card-value">${negative}</div>
                <div class="stats-banner-card-label">Negative</div>
            </div>
            <div class="stats-banner-card neutral">
                <div class="stats-banner-card-value">${neutral}</div>
                <div class="stats-banner-card-label">Neutral</div>
            </div>
            <div class="stats-banner-card">
                <div class="stats-banner-card-value">${totalAll}</div>
                <div class="stats-banner-card-label">In Database</div>
            </div>
        </div>
    `;
}

function updateProductDistribution() {
    const productList = document.getElementById('productList');
    if (!productList || !state) return;
    
    const posts = state.filteredPosts;
    const productCounts = {};
    
    posts.forEach(post => {
        // Get product label (simplified - you may need to import getProductLabel from v1)
        const productLabel = getProductLabelSimple(post);
        if (productLabel) {
            productCounts[productLabel] = (productCounts[productLabel] || 0) + 1;
        }
    });
    
    // Sort by count
    const sortedProducts = Object.entries(productCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);
    
    const total = posts.length;
    const colors = ['#0099ff', '#34d399', '#f59e0b', '#ef4444', '#8b5cf6'];
    
    productList.innerHTML = sortedProducts.map(([product, count], index) => {
        const percentage = total > 0 ? ((count / total) * 100).toFixed(0) : 0;
        return `
            <div class="product-item" data-product="${product}">
                <div class="product-color" style="background: ${colors[index % colors.length]}"></div>
                <div class="product-bar-container">
                    <div class="product-bar" style="width: ${percentage}%; background: ${colors[index % colors.length]}"></div>
                </div>
                <div class="product-info">
                    <span class="product-name">${product}</span>
                    <span class="product-percentage">${percentage}%</span>
                    <span class="product-count">${count} posts</span>
                </div>
            </div>
        `;
    }).join('');
    
    // Show active filter if any
    const activeProductFilter = state && state.filters.product && state.filters.product !== 'all';
    if (activeProductFilter) {
        const filterIndicator = document.createElement('div');
        filterIndicator.className = 'product-filter-active';
        filterIndicator.innerHTML = `
            Filtered by: ${activeProductFilter}
            <button onclick="clearProductFilter()" title="Clear filter">×</button>
        `;
        productList.insertBefore(filterIndicator, productList.firstChild);
    }
    
    // Add event listeners to product items
    productList.querySelectorAll('.product-item').forEach(item => {
        item.addEventListener('click', () => {
            const product = item.getAttribute('data-product');
            if (product) {
                filterByProduct(product);
            }
        });
    });
}

function updatePostsList() {
    const postsList = document.getElementById('postsList');
    if (!postsList || !state) return;
    
    // Sort posts by recent/critical
    const sortValue = document.getElementById('sortSelect')?.value || 'recent';
    let sortedPosts = [...state.filteredPosts];
    
    if (sortValue === 'recent') {
        sortedPosts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    } else if (sortValue === 'critical') {
        sortedPosts.sort((a, b) => {
            if (a.sentiment_label === 'negative' && b.sentiment_label !== 'negative') return -1;
            if (a.sentiment_label !== 'negative' && b.sentiment_label === 'negative') return 1;
            return new Date(b.created_at) - new Date(a.created_at);
        });
    }
    
    // Show top 10
    sortedPosts = sortedPosts.slice(0, 10);
    
    postsList.innerHTML = sortedPosts.map(post => {
        const timeAgo = getTimeAgo(post.created_at);
        const sourceIcon = getSourceIcon(post.source);
        const category = getProductLabelSimple(post) || 'General';
        const sentiment = post.sentiment_label || 'neutral';
        
        return `
            <div class="post-item">
                <div class="post-source">
                    <div class="source-icon ${post.source?.toLowerCase().replace(/\s+/g, '-')}">
                        ${sourceIcon}
                    </div>
                    <div style="flex: 1;">
                        <div class="source-name">${post.source || 'Unknown'}</div>
                        <div class="post-time">${timeAgo}</div>
                    </div>
                    <span class="sentiment-badge sentiment-${sentiment}">${sentiment}</span>
                </div>
                <div class="post-content">
                    ${truncateText(post.content || 'No content', 200)}
                </div>
                <div class="post-meta">
                    <span class="post-category">${category}</span>
                    <button class="post-action" data-url="${post.url || '#'}">Go to post</button>
                </div>
            </div>
        `;
    }).join('');
    
    // Add event listeners to post action buttons
    postsList.querySelectorAll('.post-action').forEach(btn => {
        btn.addEventListener('click', () => {
            const url = btn.getAttribute('data-url');
            if (url && url !== '#') {
                openPost(url);
            }
        });
    });
}

function getProductLabelSimple(post) {
    return getProductLabel(post.id, post.content, post.language);
}

function getSourceIcon(source) {
    const icons = {
        'X/Twitter': '🐦',
        'Twitter': '🐦',
        'Trustpilot': '⭐',
        'Reddit': '🔴',
        'News': '📰',
        'Google News': '📰',
        'GitHub': '💻',
        'Stack Overflow': '📚'
    };
    return icons[source] || '📝';
}

function getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function sortPosts(sortValue) {
    updatePostsList();
}

function filterByProduct(product) {
    if (!state) return;
    const productFilter = document.getElementById('productFilter');
    if (productFilter) {
        productFilter.value = product;
        state.setFilter('product', product);
        updateDashboard();
    }
}

function clearProductFilter() {
    if (!state) return;
    const productFilter = document.getElementById('productFilter');
    if (productFilter) {
        productFilter.value = 'all';
        state.setFilter('product', 'all');
        updateDashboard();
    }
}

function showMoreProducts() {
    // Implement pagination or expand view
    console.log('Show more products');
}

function navigateProducts(direction) {
    // Implement navigation
    console.log('Navigate products', direction);
}

function resetFilters() {
    if (!state) return;
    state.filters = {
        search: '',
        sentiment: 'all',
        source: '',
        language: 'all',
        product: 'all',
        dateFrom: '',
        dateTo: ''
    };
    
    const globalSearch = document.getElementById('globalSearch');
    if (globalSearch) globalSearch.value = '';
    
    const sentimentFilter = document.getElementById('sentimentFilter');
    if (sentimentFilter) sentimentFilter.value = 'all';
    
    const languageFilter = document.getElementById('languageFilter');
    if (languageFilter) languageFilter.value = 'all';
    
    const productFilter = document.getElementById('productFilter');
    if (productFilter) productFilter.value = 'all';
    
    state.applyFilters();
    updateDashboard();
}

function scrapeAll() {
    // Implement scrape all functionality
    console.log('Scrape all sources');
    // You can import and use the scrape functions from v1
}

function openPost(url) {
    if (url && url !== '#') {
        window.open(url, '_blank');
    }
}

// Make functions available globally
window.filterByProduct = filterByProduct;
window.clearProductFilter = clearProductFilter;
window.showMoreProducts = showMoreProducts;
window.navigateProducts = navigateProducts;
window.resetFilters = resetFilters;
window.scrapeAll = scrapeAll;
window.openPost = openPost;

export { updateDashboard, updateProductDistribution, updatePostsList };

