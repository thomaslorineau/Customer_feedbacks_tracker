// Dashboard UI management
import { API } from './api.js';
import { State } from './state.js';
import { getProductLabel } from './product-detection.js';
import { updateWhatsHappening } from './whats-happening.js';
import { updateTimelineChart } from './charts.js';

const api = new API();
let state = null;

export function initDashboard(appState) {
    state = appState;
    
    // Initialize event listeners
    setupEventListeners();
    
    // Posts are loaded by app.js, so we just update the dashboard
    // when state changes (via subscription in charts.js)
    // No need to load data here
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
            // Clear critical filter flag if user manually changes sentiment
            if (e.target.value !== 'negative') {
                state.criticalFilterActive = false;
            }
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
    
    // Global date slicer (common for all charts)
    const globalDateFrom = document.getElementById('globalDateFrom');
    const globalDateTo = document.getElementById('globalDateTo');
    const clearDatesBtn = document.getElementById('clearDatesBtn');
    
    if (globalDateFrom) {
        globalDateFrom.addEventListener('change', (e) => {
            const dateValue = e.target.value;
            state.setFilter('dateFrom', dateValue);
            // Sync with local date inputs
            const dateFromInput = document.getElementById('dateFrom');
            if (dateFromInput) dateFromInput.value = dateValue;
            updateDashboard();
        });
    }
    
    if (globalDateTo) {
        globalDateTo.addEventListener('change', (e) => {
            const dateValue = e.target.value;
            state.setFilter('dateTo', dateValue);
            // Sync with local date inputs
            const dateToInput = document.getElementById('dateTo');
            if (dateToInput) dateToInput.value = dateValue;
            updateDashboard();
        });
    }
    
    if (clearDatesBtn) {
        clearDatesBtn.addEventListener('click', () => {
            state.setFilter('dateFrom', '');
            state.setFilter('dateTo', '');
            if (globalDateFrom) globalDateFrom.value = '';
            if (globalDateTo) globalDateTo.value = '';
            // Sync with local date inputs
            const dateFromInput = document.getElementById('dateFrom');
            const dateToInput = document.getElementById('dateTo');
            if (dateFromInput) dateFromInput.value = '';
            if (dateToInput) dateToInput.value = '';
            updateDashboard();
        });
    }
    
    // Clear All Filters button
    const clearAllFiltersBtn = document.getElementById('clearAllFiltersBtn');
    if (clearAllFiltersBtn) {
        clearAllFiltersBtn.addEventListener('click', () => {
            resetFilters();
        });
    }
    
    // Generate PowerPoint Report button
    const generateReportBtn = document.getElementById('generateReportBtn');
    if (generateReportBtn) {
        generateReportBtn.addEventListener('click', () => {
            generatePowerPointReport();
        });
    }
    
    // Local date filters (in timeline panel - sync with global)
    const dateFromInput = document.getElementById('dateFrom');
    if (dateFromInput) {
        dateFromInput.addEventListener('change', (e) => {
            const dateValue = e.target.value;
            state.setFilter('dateFrom', dateValue);
            // Sync with global date slicer
            if (globalDateFrom) globalDateFrom.value = dateValue;
            updateDashboard();
        });
    }
    
    const dateToInput = document.getElementById('dateTo');
    if (dateToInput) {
        dateToInput.addEventListener('change', (e) => {
            const dateValue = e.target.value;
            state.setFilter('dateTo', dateValue);
            // Sync with global date slicer
            if (globalDateTo) globalDateTo.value = dateValue;
            updateDashboard();
        });
    }
    
    // Open critical posts button
    const openCriticalPostsBtn = document.getElementById('openCriticalPostsBtn');
    if (openCriticalPostsBtn) {
        openCriticalPostsBtn.addEventListener('click', () => {
            openCriticalPosts();
        });
    }
    
    // Sort
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            const sortValue = e.target.value;
            console.log('Sort changed to:', sortValue);
            sortPosts(sortValue);
        });
    }
    
    // Clear Timeline Filter button
    const clearTimelineFilterBtn = document.getElementById('clearTimelineFilterBtn');
    if (clearTimelineFilterBtn) {
        clearTimelineFilterBtn.addEventListener('click', () => {
            clearTimelineFilter();
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
    
    // Listen for date filter events from timeline chart
    window.addEventListener('filterByDate', (event) => {
        const clickedDate = event.detail.date;
        if (clickedDate && state) {
            console.log('Filtering by date:', clickedDate);
            
            // Set date filter to the clicked date (show posts from that day)
            const dateFrom = clickedDate;
            const dateTo = clickedDate;
            
            // Update date filters (both global and local)
            const dateFromInput = document.getElementById('dateFrom');
            const dateToInput = document.getElementById('dateTo');
            const globalDateFrom = document.getElementById('globalDateFrom');
            const globalDateTo = document.getElementById('globalDateTo');
            
            if (dateFromInput) {
                dateFromInput.value = dateFrom;
                console.log('Set dateFrom input to:', dateFrom);
            }
            if (dateToInput) {
                dateToInput.value = dateTo;
                console.log('Set dateTo input to:', dateTo);
            }
            if (globalDateFrom) {
                globalDateFrom.value = dateFrom;
            }
            if (globalDateTo) {
                globalDateTo.value = dateTo;
            }
            
            // Update state filters
            state.setFilter('dateFrom', dateFrom);
            state.setFilter('dateTo', dateTo);
            
            console.log('State filters updated:', state.filters);
            
            // Update dashboard to show filtered posts
            updateDashboard();
            
            // Don't scroll - keep user on timeline
            // const postsSection = document.querySelector('.panel-bottom');
            // if (postsSection) {
            //     postsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            // }
        }
    });
    
    // Listen for date range selection from timeline chart (mouse drag)
    window.addEventListener('filterByDateRange', (event) => {
        const { dateFrom, dateTo } = event.detail;
        if (dateFrom && dateTo && state) {
            console.log('Filtering by date range:', dateFrom, 'to', dateTo);
            
            // Update date filters (both global and local)
            const dateFromInput = document.getElementById('dateFrom');
            const dateToInput = document.getElementById('dateTo');
            const globalDateFrom = document.getElementById('globalDateFrom');
            const globalDateTo = document.getElementById('globalDateTo');
            
            if (dateFromInput) dateFromInput.value = dateFrom;
            if (dateToInput) dateToInput.value = dateTo;
            if (globalDateFrom) globalDateFrom.value = dateFrom;
            if (globalDateTo) globalDateTo.value = dateTo;
            
            // Update state filters
            state.setFilter('dateFrom', dateFrom);
            state.setFilter('dateTo', dateTo);
            
            // Update dashboard to show filtered posts
            updateDashboard();
            
            // Don't scroll - keep user on timeline
            // const postsSection = document.querySelector('.panel-bottom');
            // if (postsSection) {
            //     postsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            // }
        }
    });
    
    // Listen for product filter events from timeline chart (double-click)
    window.addEventListener('filterByProductFromTimeline', (event) => {
        const { product, date } = event.detail;
        if (product && state) {
            console.log('Filtering by product from timeline:', product, 'on date:', date);
            
            // Set product filter
            const productFilter = document.getElementById('productFilter');
            if (productFilter) {
                productFilter.value = product;
            }
            state.setFilter('product', product);
            
            // Also set date filter if provided
            if (date) {
                const dateFromInput = document.getElementById('dateFrom');
                const dateToInput = document.getElementById('dateTo');
                if (dateFromInput) dateFromInput.value = date;
                if (dateToInput) dateToInput.value = date;
                state.setFilter('dateFrom', date);
                state.setFilter('dateTo', date);
            }
            
            // Update dashboard
            updateDashboard();
            
    // Don't scroll - keep user on current view
    // const postsSection = document.querySelector('.panel-bottom');
    // if (postsSection) {
    //     postsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    // }
        }
    });
    
    // Listen for source filter events from source chart
    window.addEventListener('filterBySource', (event) => {
        const { source } = event.detail;
        if (state) {
            console.log('Filtering by source:', source);
            
            // Set source filter
            state.setFilter('source', source || '');
            
            // Update dashboard
            updateDashboard();
        }
    });
    
    // Listen for sentiment filter events from sentiment chart
    window.addEventListener('filterBySentiment', (event) => {
        const { sentiment } = event.detail;
        if (state) {
            console.log('Filtering by sentiment:', sentiment);
            
            // Set sentiment filter
            const sentimentFilter = document.getElementById('sentimentFilter');
            if (sentimentFilter) {
                sentimentFilter.value = sentiment;
            }
            state.setFilter('sentiment', sentiment);
            
            // Update dashboard
            updateDashboard();
        }
    });
}

async function loadDashboardData() {
    try {
        console.log('Loading dashboard data...');
        const posts = await api.getPosts(1000, 0);
        console.log('Posts loaded:', posts?.length || 0, 'posts');
        
        if (!posts || posts.length === 0) {
            console.warn('No posts found in database');
            // Show empty state message
            const postsList = document.getElementById('postsList');
            if (postsList) {
                postsList.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">No posts found. Go to Feedbacks Collection to scrape some data.</div>';
            }
            return;
        }
        
        // Load posts first - don't apply date filter on initial load
        // The default 12 months filter will only be applied when clicking "Clear Filter"
        state.setPosts(posts);
        console.log('Posts set in state. Filtered posts:', state.filteredPosts?.length || 0);
        updateDashboard();
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        // Show error message
        const postsList = document.getElementById('postsList');
        if (postsList) {
            postsList.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--error);">Error loading data: ${error.message}</div>`;
        }
    }
}

function updateDashboard() {
    console.log('Updating dashboard...');
    console.log('State:', state ? 'initialized' : 'NOT initialized');
    console.log('Total posts:', state?.posts?.length || 0);
    console.log('State filtered posts:', state?.filteredPosts?.length || 0);
    if (!state) {
        console.error('State is not initialized');
        return;
    }
    if (!state.posts || state.posts.length === 0) {
        console.warn('No posts in state, trying to load...');
        // Try to load posts if state is empty
        loadDashboardData();
        return;
    }
    updateStatsBanner();
    updateWhatsHappening(state);
    updateProductDistribution();
    updatePostsList();
    updateCriticalPostsButton();
    updatePositiveSatisfactionKPI();
    // Charts will be updated by charts.js
}

function updateStatsBanner() {
    // Stats banner might not exist in v2, so we skip it if not found
    const statsBanner = document.getElementById('statsBanner');
    if (!statsBanner) {
        // Element doesn't exist, skip silently
        return;
    }
    if (!state) {
        console.warn('State not initialized in updateStatsBanner');
        return;
    }
    
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

let showAllProducts = false;

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
    const allProducts = Object.entries(productCounts)
        .sort((a, b) => b[1] - a[1]);
    
    // Show top 5 or all products based on state
    const sortedProducts = showAllProducts ? allProducts : allProducts.slice(0, 5);
    const remainingCount = allProducts.length - 5;
    
    const total = posts.length;
    const colors = ['#0099ff', '#34d399', '#f59e0b', '#ef4444', '#8b5cf6'];
    
    // Calculate max count for relative scaling (makes bars longer)
    const maxCount = sortedProducts.length > 0 ? sortedProducts[0][1] : 1;
    
    productList.innerHTML = sortedProducts.map(([product, count], index) => {
        const percentage = total > 0 ? ((count / total) * 100).toFixed(0) : 0;
        // Use relative scaling based on max count for longer bars
        const relativeWidth = maxCount > 0 ? ((count / maxCount) * 100).toFixed(0) : 0;
        return `
            <div class="product-item" data-product="${product}">
                <div class="product-color" style="background: ${colors[index % colors.length]}"></div>
                <div class="product-bar-container">
                    <div class="product-bar" style="width: ${relativeWidth}%; background: ${colors[index % colors.length]}"></div>
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
    
    // Update "Show More" button text
    const showMoreProductsBtn = document.getElementById('showMoreProductsBtn');
    if (showMoreProductsBtn) {
        if (showAllProducts) {
            showMoreProductsBtn.textContent = 'Show Less';
            showMoreProductsBtn.style.display = 'inline-block';
        } else if (remainingCount > 0) {
            showMoreProductsBtn.textContent = `+ ${remainingCount} Other Products`;
            showMoreProductsBtn.style.display = 'inline-block';
        } else {
            showMoreProductsBtn.style.display = 'none';
        }
    }
}

function updatePostsList() {
    const postsList = document.getElementById('postsList');
    if (!postsList || !state) return;
    
    // Show active critical filter indicator if needed
    const panelHeader = document.querySelector('.panel-bottom .panel-header');
    if (panelHeader) {
        // Remove existing filter indicator
        const existingIndicator = panelHeader.querySelector('.critical-filter-active');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        // Add filter indicator if critical filter is active
        if (state.criticalFilterActive && state.filters.sentiment === 'negative') {
            const filterIndicator = document.createElement('div');
            filterIndicator.className = 'critical-filter-active';
            filterIndicator.style.cssText = 'margin-top: 12px; display: flex; align-items: center; gap: 8px;';
            filterIndicator.innerHTML = `
                <span style="display: flex; align-items: center; gap: 8px; padding: 6px 12px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; font-size: 0.9em; color: #ef4444;">
                    <span>🔴 Filtered: Critical Posts Only</span>
                    <button onclick="clearCriticalFilter()" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 1.2em; padding: 0 4px; line-height: 1;" title="Clear filter">×</button>
                </span>
            `;
            panelHeader.appendChild(filterIndicator);
        }
    }
    
    // Sort posts by recent/critical
    const sortValue = document.getElementById('sortSelect')?.value || 'recent';
    let sortedPosts = [...state.filteredPosts];
    
    if (sortValue === 'recent') {
        sortedPosts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    } else if (sortValue === 'critical') {
        sortedPosts.sort((a, b) => {
            // First, prioritize negative posts
            if (a.sentiment_label === 'negative' && b.sentiment_label !== 'negative') return -1;
            if (a.sentiment_label !== 'negative' && b.sentiment_label === 'negative') return 1;
            // Then by date (most recent first)
            return new Date(b.created_at) - new Date(a.created_at);
        });
    } else if (sortValue === 'engagement') {
        sortedPosts.sort((a, b) => {
            // Calculate engagement score (views + comments + reactions)
            const engagementA = (a.views || 0) + (a.comments || 0) + (a.reactions || 0);
            const engagementB = (b.views || 0) + (b.comments || 0) + (b.reactions || 0);
            // Sort by engagement descending
            if (engagementB !== engagementA) {
                return engagementB - engagementA;
            }
            // If same engagement, sort by date
            return new Date(b.created_at) - new Date(a.created_at);
        });
    }
    
    // Pagination: show posts in batches
    const POSTS_PER_PAGE = 10;
    const currentPage = state.postsPage || 1;
    const startIndex = 0;
    const endIndex = currentPage * POSTS_PER_PAGE;
    const postsToShow = sortedPosts.slice(startIndex, endIndex);
    const hasMore = sortedPosts.length > endIndex;
    
    // Clear existing content first
    postsList.innerHTML = '';
    
    // Create and append each post item separately to avoid nesting issues
    postsToShow.forEach(post => {
        const timeAgo = getTimeAgo(post.created_at);
        const sourceIcon = getSourceIcon(post.source);
        const category = getProductLabelSimple(post) || 'General';
        const sentiment = post.sentiment_label || 'neutral';
        
        const postElement = document.createElement('div');
        postElement.className = 'post-item';
        postElement.innerHTML = `
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
        `;
        postsList.appendChild(postElement);
    });
    
    // Add event listeners to post action buttons
    postsList.querySelectorAll('.post-action').forEach(btn => {
        btn.addEventListener('click', () => {
            const url = btn.getAttribute('data-url');
            if (url && url !== '#') {
                openPost(url);
            }
        });
    });
    
    // Add "Load More" button if there are more posts
    if (hasMore) {
        const loadMoreBtn = document.createElement('button');
        loadMoreBtn.className = 'load-more-btn';
        loadMoreBtn.style.cssText = 'width: 100%; padding: 12px; margin-top: 20px; background: var(--accent-primary); color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: all 0.3s ease;';
        loadMoreBtn.textContent = `Load More (${sortedPosts.length - endIndex} remaining)`;
        loadMoreBtn.addEventListener('click', () => {
            state.postsPage = (state.postsPage || 1) + 1;
            updatePostsList();
        });
        loadMoreBtn.addEventListener('mouseenter', () => {
            loadMoreBtn.style.transform = 'translateY(-2px)';
            loadMoreBtn.style.boxShadow = '0 4px 12px rgba(0, 212, 255, 0.4)';
        });
        loadMoreBtn.addEventListener('mouseleave', () => {
            loadMoreBtn.style.transform = 'translateY(0)';
            loadMoreBtn.style.boxShadow = 'none';
        });
        postsList.appendChild(loadMoreBtn);
    } else if (state.postsPage > 1) {
        // Reset page when filters change and no more posts
        state.postsPage = 1;
    }
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
    if (!state) return;
    
    // Update the select value if provided
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect && sortValue) {
        sortSelect.value = sortValue;
    }
    
    // Force update the posts list with the new sort
    updatePostsList();
    
    // Don't scroll - keep user on current view
    // const postsSection = document.querySelector('.panel-bottom');
    // if (postsSection) {
    //     postsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    // }
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
    showAllProducts = !showAllProducts;
    updateProductDistribution();
}

function navigateProducts(direction) {
    // Implement navigation
    console.log('Navigate products', direction);
}

function clearTimelineFilter() {
    if (!state) return;
    
    // Reset to default: last 12 months
    const now = new Date();
    const twelveMonthsAgo = new Date();
    twelveMonthsAgo.setMonth(now.getMonth() - 12);
    
    const dateFromStr = twelveMonthsAgo.toISOString().split('T')[0];
    const dateToStr = now.toISOString().split('T')[0];
    
    // Update date filters
    const dateFromInput = document.getElementById('dateFrom');
    const dateToInput = document.getElementById('dateTo');
    const globalDateFrom = document.getElementById('globalDateFrom');
    const globalDateTo = document.getElementById('globalDateTo');
    
    if (dateFromInput) dateFromInput.value = dateFromStr;
    if (dateToInput) dateToInput.value = dateToStr;
    if (globalDateFrom) globalDateFrom.value = dateFromStr;
    if (globalDateTo) globalDateTo.value = dateToStr;
    
    // Reset other timeline filters
    const sentimentFilter = document.getElementById('sentimentFilter');
    const languageFilter = document.getElementById('languageFilter');
    const productFilter = document.getElementById('productFilter');
    
    if (sentimentFilter) sentimentFilter.value = 'all';
    if (languageFilter) languageFilter.value = 'all';
    if (productFilter) productFilter.value = 'all';
    
    // Update state
    state.setFilter('dateFrom', dateFromStr);
    state.setFilter('dateTo', dateToStr);
    state.setFilter('sentiment', 'all');
    state.setFilter('language', 'all');
    state.setFilter('product', 'all');
    
    // Update dashboard
    updateDashboard();
}

function resetFilters() {
    if (!state) return;
    
    // Reset all filters (including dates to empty)
    state.setFilter('search', '');
    state.setFilter('sentiment', 'all');
    state.setFilter('language', 'all');
    state.setFilter('product', 'all');
    state.setFilter('source', '');
    state.setFilter('dateFrom', ''); // Clear dates
    state.setFilter('dateTo', ''); // Clear dates
    
    // Reset UI elements
    const globalSearch = document.getElementById('globalSearch');
    if (globalSearch) globalSearch.value = '';
    
    const sentimentFilter = document.getElementById('sentimentFilter');
    if (sentimentFilter) sentimentFilter.value = 'all';
    
    const languageFilter = document.getElementById('languageFilter');
    if (languageFilter) languageFilter.value = 'all';
    
    const productFilter = document.getElementById('productFilter');
    if (productFilter) productFilter.value = 'all';
    
    // Reset global date slicer to empty
    const globalDateFrom = document.getElementById('globalDateFrom');
    const globalDateTo = document.getElementById('globalDateTo');
    if (globalDateFrom) globalDateFrom.value = '';
    if (globalDateTo) globalDateTo.value = '';
    
    // Reset local date inputs to empty
    const dateFromInput = document.getElementById('dateFrom');
    const dateToInput = document.getElementById('dateTo');
    if (dateFromInput) dateFromInput.value = '';
    if (dateToInput) dateToInput.value = '';
    
    // Clear critical filter flag
    state.criticalFilterActive = false;
    
    // Update dashboard (this will trigger state subscription which updates timeline)
    updateDashboard();
    
    // Force timeline chart update to ensure it refreshes
    // The state subscription should handle this, but we ensure it happens
    setTimeout(() => {
        updateTimelineChart(state);
    }, 150);
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

function updateCriticalPostsButton() {
    if (!state) return;
    
    const btn = document.getElementById('openCriticalPostsBtn');
    const countSpan = document.getElementById('criticalPostsCount');
    if (!btn || !countSpan) return;
    
    // Calculate critical posts (negative + recent)
    const now = new Date();
    const last48h = new Date(now.getTime() - 48 * 60 * 60 * 1000);
    const criticalPosts = (state.filteredPosts || []).filter(p => {
        const postDate = new Date(p.created_at);
        const isRecent = postDate >= last48h;
        const isNegative = p.sentiment_label === 'negative';
        return isRecent && isNegative;
    });
    
    const count = criticalPosts.length;
    countSpan.textContent = count;
    
    if (count > 0) {
        btn.style.display = 'inline-flex';
    } else {
        btn.style.display = 'none';
    }
}

function openCriticalPosts() {
    if (!state) return;
    
    // Set filter to show only negative posts
    state.setFilter('sentiment', 'negative');
    
    // Set sort to critical
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.value = 'critical';
    }
    
    // Update sentiment filter dropdown
    const sentimentFilter = document.getElementById('sentimentFilter');
    if (sentimentFilter) {
        sentimentFilter.value = 'negative';
    }
    
    // Mark that critical filter is active
    state.criticalFilterActive = true;
    
    // Update dashboard
    updateDashboard();
    
    // Don't scroll - keep user on current view
    // const postsSection = document.querySelector('.panel-bottom');
    // if (postsSection) {
    //     postsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    // }
    
    // Highlight the section briefly (if needed)
        postsSection.style.transition = 'box-shadow 0.3s ease';
        postsSection.style.boxShadow = '0 0 20px rgba(0, 153, 255, 0.5)';
        setTimeout(() => {
            postsSection.style.boxShadow = '';
        }, 2000);
    }
}

function clearCriticalFilter() {
    if (!state) return;
    
    // Remove critical filter
    state.setFilter('sentiment', 'all');
    state.criticalFilterActive = false;
    
    // Update sentiment filter dropdown
    const sentimentFilter = document.getElementById('sentimentFilter');
    if (sentimentFilter) {
        sentimentFilter.value = 'all';
    }
    
    // Reset sort to recent
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.value = 'recent';
    }
    
    // Update dashboard
    updateDashboard();
}

// Update Positive Satisfaction KPI
function updatePositiveSatisfactionKPI() {
    if (!state) return;
    
    const posts = state.filteredPosts || [];
    const total = posts.length;
    
    if (total === 0) {
        const kpiValue = document.getElementById('positiveSatisfactionValue');
        if (kpiValue) kpiValue.textContent = '--%';
        return;
    }
    
    const positive = posts.filter(p => p.sentiment_label === 'positive').length;
    const percentage = Math.round((positive / total) * 100);
    
    const kpiValue = document.getElementById('positiveSatisfactionValue');
    if (kpiValue) {
        kpiValue.textContent = `${percentage}%`;
        
        // Update color based on percentage
        if (percentage >= 70) {
            kpiValue.style.color = '#10b981'; // Green
        } else if (percentage >= 50) {
            kpiValue.style.color = '#f59e0b'; // Orange
        } else {
            kpiValue.style.color = '#ef4444'; // Red
        }
    }
}

// Generate PowerPoint Report
async function generatePowerPointReport() {
    const btn = document.getElementById('generateReportBtn');
    if (!btn) return;
    
    const btnText = btn.querySelector('.btn-text');
    const btnSpinner = btn.querySelector('.btn-spinner');
    
    // Show loading state
    btn.disabled = true;
    if (btnText) btnText.textContent = 'Generating...';
    if (btnSpinner) btnSpinner.style.display = 'block';
    
    try {
        // Get current filters and state
        const filters = {
            search: state.filters?.search || '',
            sentiment: state.filters?.sentiment || 'all',
            language: state.filters?.language || 'all',
            product: state.filters?.product || 'all',
            source: state.filters?.source || 'all',
            dateFrom: state.filters?.dateFrom || '',
            dateTo: state.filters?.dateTo || ''
        };
        
        // Call API to generate report
        const response = await fetch(`${api.baseURL}/api/generate-powerpoint-report`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filters: filters,
                include_charts: ['timeline', 'product', 'source', 'sentiment'],
                include_recommendations: true,
                include_analysis: true
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Failed to generate report' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        // Get the file as blob
        const blob = await response.blob();
        
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `OVH_Feedback_Report_${new Date().toISOString().split('T')[0]}.pptx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        // Show success message
        showToast('PowerPoint report generated successfully!', 'success');
        
    } catch (error) {
        console.error('Error generating PowerPoint report:', error);
        showToast(`Failed to generate report: ${error.message}`, 'error');
    } finally {
        // Reset button state
        btn.disabled = false;
        if (btnText) btnText.textContent = '📊 PowerPoint';
        if (btnSpinner) btnSpinner.style.display = 'none';
    }
}

function showToast(message, type = 'info') {
    // Simple toast notification
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        font-weight: 500;
        animation: slideIn 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => document.body.removeChild(toast), 300);
    }, 3000);
}

// Make functions available globally
window.filterByProduct = filterByProduct;
window.clearProductFilter = clearProductFilter;
window.showMoreProducts = showMoreProducts;
window.navigateProducts = navigateProducts;
window.resetFilters = resetFilters;
window.scrapeAll = scrapeAll;
window.openPost = openPost;
window.clearCriticalFilter = clearCriticalFilter;

export { updateDashboard, updateProductDistribution, updatePostsList };

