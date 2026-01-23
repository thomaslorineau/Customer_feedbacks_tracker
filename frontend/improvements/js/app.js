// Improvements Opportunities App

// Store current product filter
let currentProductFilter = null;

// Store current period filter (in days)
let currentPeriodDays = 30; // Default to 30 days

// Helper function to get period text
function getPeriodText(days) {
    if (days === 30) return 'Last 30 days';
    if (days === 60) return 'Last 60 days';
    if (days === 90) return 'Last 90 days';
    if (days === 180) return 'Last 6 months';
    if (days === 365) return 'Last year';
    return `Last ${days} days`;
}

// Helper function to get date_from parameter for API calls
function getDateFrom(days) {
    const date = new Date();
    date.setDate(date.getDate() - days);
    return date.toISOString().split('T')[0];
}

// Initialize theme
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
    
    // Add transitioning class to prevent color transition artifacts
    body.classList.add('dark-mode-transitioning');
    
    if (isDark) {
        body.classList.remove('dark-mode');
        localStorage.setItem('theme', 'light');
    } else {
        body.classList.add('dark-mode');
        localStorage.setItem('theme', 'dark');
    }
    
    // Remove transitioning class after a short delay
    setTimeout(() => {
        body.classList.remove('dark-mode-transitioning');
    }, 200);
    
    // Dispatch event to notify other pages
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: isDark ? 'light' : 'dark' } }));
}

// Setup theme toggle
function setupThemeToggle() {
    const navThemeToggle = document.querySelector('.nav-menu-right .theme-toggle');
    if (navThemeToggle) {
        navThemeToggle.addEventListener('click', toggleTheme);
    }
}

// Load and display version
// Version loading is handled by version-loader.js module
async function _deprecated_loadVersion() {
    try {
        const response = await fetch(`${window.location.origin}/api/version`);
        if (response.ok) {
            const data = await response.json();
            const versionBadge = document.getElementById('versionBadge');
            if (versionBadge) {
                versionBadge.textContent = `v${data.version}`;
                versionBadge.title = `Version ${data.version} - Build: ${new Date(data.build_date).toLocaleDateString()}`;
            }
        }
    } catch (error) {
        console.warn('Failed to load version:', error);
    }
}

// Load improvements summary
async function loadImprovementsSummary() {
    try {
        const summaryEl = document.getElementById('improvementsSummary');
        if (summaryEl) {
            summaryEl.classList.add('loading');
        }
        
        const response = await fetch('/api/improvements-summary');
        if (response.ok) {
            const data = await response.json();
            if (summaryEl && data.summary) {
                summaryEl.textContent = data.summary;
                summaryEl.classList.remove('loading');
            } else if (summaryEl) {
                summaryEl.textContent = "💡 Improvement opportunities based on customer feedback";
                summaryEl.classList.remove('loading');
            }
        } else {
            console.error('Failed to load improvements summary:', response.status, response.statusText);
            if (summaryEl) {
                summaryEl.textContent = "💡 Improvement opportunities based on customer feedback";
                summaryEl.classList.remove('loading');
            }
        }
    } catch (error) {
        console.error('Error loading improvements summary:', error);
        const summaryEl = document.getElementById('improvementsSummary');
        if (summaryEl) {
            summaryEl.textContent = "💡 Improvement opportunities based on customer feedback";
            summaryEl.classList.remove('loading');
        }
    }
}

// Load pain points
async function loadPainPoints() {
    const painPointsList = document.getElementById('painPointsList');
    if (!painPointsList) {
        console.error('painPointsList element not found in DOM');
        return;
    }
    
    try {
        console.log('Loading pain points...');
        const response = await fetch(`/api/pain-points?days=${currentPeriodDays}&limit=5`);
        console.log('Pain points response status:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Pain points error response:', errorText);
            painPointsList.innerHTML = `<div style="text-align: center; padding: 40px; color: #ef4444;">Error loading pain points: HTTP ${response.status}<br><small>${errorText}</small></div>`;
            throw new Error(`Failed to load pain points: ${response.status} ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Pain points data received:', data);
        
        // Filter pain points by product if filter is active
        let filteredPainPoints = data.pain_points || [];
        if (currentProductFilter) {
            // Filter pain points by checking if their posts match the product
            const dateFrom = getDateFrom(currentPeriodDays);
            
            // Import product detection function first
            const { getProductLabel } = await import('/dashboard/js/product-detection.js');
            
            // Fetch posts with date filter (don't use search filter, we'll filter by product label instead)
            const postsResponse = await fetch(`/api/posts-for-improvement?limit=1000&offset=0&date_from=${dateFrom}`);
            if (postsResponse.ok) {
                const postsData = await postsResponse.json();
                let allPosts = postsData.posts || [];
                
                // Filter posts to ensure they match the product label (more accurate than search)
                const productPosts = allPosts.filter(post => {
                    const productLabel = getProductLabel(post.id, post.content, post.language);
                    return productLabel === currentProductFilter;
                });
                
                // Filter pain points based on whether their keywords match posts with the product
                // AND recalculate post counts accurately
                filteredPainPoints = filteredPainPoints.map(pp => {
                    // Get keywords for this pain point
                    const keywords = PAIN_POINT_KEYWORDS[pp.title] || [];
                    if (keywords.length === 0) return null;
                    
                    // Find matching posts for this pain point within the product posts
                    const matchingPosts = productPosts.filter(post => {
                        const content = (post.content || '').toLowerCase();
                        return keywords.some(keyword => content.includes(keyword.toLowerCase()));
                    });
                    
                    // Only include pain points that have matching posts
                    if (matchingPosts.length === 0) return null;
                    
                    return {
                        ...pp,
                        posts_count: matchingPosts.length,
                        posts: matchingPosts.slice(0, 3) // Store sample posts for drawer
                    };
                }).filter(pp => pp !== null && pp.posts_count > 0);
                
                // Sort by post count (descending) to show most relevant first
                filteredPainPoints.sort((a, b) => b.posts_count - a.posts_count);
            }
        }
        
        if (!filteredPainPoints || filteredPainPoints.length === 0) {
            const periodText = getPeriodText(currentPeriodDays);
            const filterText = currentProductFilter ? ` for product "${currentProductFilter}"` : '';
            painPointsList.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">No pain points found${filterText} for the selected period (${periodText}).</div>`;
            return;
        }
        
        // Show only top 5, but store all filtered pain points
        const displayPainPoints = filteredPainPoints.slice(0, 5);
        
        painPointsList.innerHTML = displayPainPoints.map((pp, index) => `
            <div class="pain-point-item clickable-pain-point" onclick="openPainPointDrawer('${escapeHtml(pp.title)}', ${index})" style="cursor: pointer;">
                <div class="pain-point-icon">${pp.icon}</div>
                <div class="pain-point-content">
                    <div class="pain-point-title">${escapeHtml(pp.title)}</div>
                    <div class="pain-point-description">${escapeHtml(pp.description)}</div>
                    <div class="pain-point-posts">${pp.posts_count} posts</div>
                </div>
            </div>
        `).join('');
        
        // Store filtered pain points data globally for drawer access
        window.currentPainPoints = filteredPainPoints;
        
        // Show "View All" link if there are more pain points
        const viewAllLink = document.getElementById('viewAllPainPoints');
        if (viewAllLink && filteredPainPoints.length > 5) {
            viewAllLink.style.display = 'inline-block';
            viewAllLink.textContent = `View All ${filteredPainPoints.length} Pain Points >`;
        } else if (viewAllLink) {
            viewAllLink.style.display = 'none';
        }
    } catch (error) {
        console.error('Error loading pain points:', error);
        const painPointsList = document.getElementById('painPointsList');
        if (painPointsList) {
            painPointsList.innerHTML = `<div style="text-align: center; padding: 40px; color: #ef4444;">Error loading pain points: ${error.message}<br><small>Check console for details</small></div>`;
        }
    }
}

// Load product distribution
async function loadProductDistribution() {
    const productDistribution = document.getElementById('productDistribution');
    if (!productDistribution) {
        console.error('productDistribution element not found');
        return;
    }
    
    try {
        console.log('Loading product distribution...');
        // Add date filter to product opportunities
        const dateFrom = getDateFrom(currentPeriodDays);
        const response = await fetch(`/api/product-opportunities?date_from=${dateFrom}`);
        console.log('Product distribution response status:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Product distribution error response:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Product distribution data received:', data);
        
        if (!data || !data.products || data.products.length === 0) {
            productDistribution.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">No product data available.</div>';
            return;
        }
        
        // Show top 5, rest can be expanded
        const topProducts = data.products.slice(0, 5);
        const remainingProducts = data.products.slice(5);
        
        productDistribution.innerHTML = topProducts.map(product => {
            const negativeRatio = product.total_posts > 0 ? (product.negative_posts / product.total_posts) * 100 : 0;
            const positiveRatio = 100 - negativeRatio;
            
            // Escape product name for onclick attribute
            const escapedProduct = escapeHtml(product.product).replace(/'/g, "\\'");
            return `
                <div class="product-item ${currentProductFilter === product.product ? 'active-filter' : ''}" data-product="${escapeHtml(product.product)}" style="cursor: pointer;" onclick="filterByProduct('${escapedProduct}')" title="Click to filter this page by ${escapeHtml(product.product)}">
                    <div class="product-color" style="background: ${product.color};"></div>
                    <div class="product-bar-container">
                        <div class="product-bar" style="width: ${negativeRatio}%; background: ${product.color};"></div>
                        <div class="product-bar" style="width: ${positiveRatio}%; background: rgba(107, 114, 128, 0.3); margin-left: ${negativeRatio}%;"></div>
                    </div>
                    <div class="product-info">
                        <span class="product-name">${escapeHtml(product.product)}</span>
                        <span class="product-score">${product.opportunity_score}</span>
                    </div>
                </div>
            `;
        }).join('');
        
        // Show "more products" indicator
        const moreProductsIndicator = document.getElementById('moreProductsIndicator');
        if (moreProductsIndicator && remainingProducts.length > 0) {
            moreProductsIndicator.style.display = 'block';
            moreProductsIndicator.textContent = `+${remainingProducts.length} Other Products`;
            moreProductsIndicator.onclick = () => {
                // Toggle showing all products
                const isExpanded = moreProductsIndicator.dataset.expanded === 'true';
                if (!isExpanded) {
                    const allProductsHtml = data.products.slice(5).map(product => {
                        const negativeRatio = product.total_posts > 0 ? (product.negative_posts / product.total_posts) * 100 : 0;
                        const positiveRatio = 100 - negativeRatio;
                        // Escape product name for onclick attribute
                        const escapedProduct = escapeHtml(product.product).replace(/'/g, "\\'");
                        return `
                            <div class="product-item ${currentProductFilter === product.product ? 'active-filter' : ''}" data-product="${escapeHtml(product.product)}" style="cursor: pointer;" onclick="filterByProduct('${escapedProduct}')" title="Click to filter this page by ${escapeHtml(product.product)}">
                                <div class="product-color" style="background: ${product.color};"></div>
                                <div class="product-bar-container">
                                    <div class="product-bar" style="width: ${negativeRatio}%; background: ${product.color};"></div>
                                    <div class="product-bar" style="width: ${positiveRatio}%; background: rgba(107, 114, 128, 0.3); margin-left: ${negativeRatio}%;"></div>
                                </div>
                                <div class="product-info">
                                    <span class="product-name">${escapeHtml(product.product)}</span>
                                    <span class="product-score">${product.opportunity_score}</span>
                                </div>
                            </div>
                        `;
                    }).join('');
                    productDistribution.innerHTML += allProductsHtml;
                    moreProductsIndicator.textContent = 'Show Less';
                    moreProductsIndicator.dataset.expanded = 'true';
                } else {
                    // Reload to show only top 5
                    loadProductDistribution();
                    moreProductsIndicator.dataset.expanded = 'false';
                }
            };
        }
        
        // Update filter indicator after loading
        updateProductFilterIndicator();
    } catch (error) {
        console.error('Error loading product distribution:', error);
        productDistribution.innerHTML = `<div style="text-align: center; padding: 40px; color: #ef4444;">
            <strong>Error loading product distribution</strong><br>
            <small>${error.message}</small><br>
            <small style="color: var(--text-muted);">Check browser console (F12) for details</small>
        </div>`;
    }
}

// Load posts for improvement review
let currentOffset = 0;
const postsPerPage = 20;

async function loadPostsForImprovement(resetOffset = false, productFilter = null) {
    if (resetOffset) {
        currentOffset = 0;
    }
    
    // Use current filter if not specified
    const filterProduct = productFilter !== null ? productFilter : currentProductFilter;
    
    try {
        const search = document.getElementById('improvementsSearch')?.value || '';
        const language = document.getElementById('improvementsLanguage')?.value || 'all';
        const source = document.getElementById('improvementsSource')?.value || 'all';
        const sortBy = document.getElementById('improvementsSort')?.value || 'opportunity_score';
        
        const params = new URLSearchParams({
            limit: postsPerPage.toString(),
            offset: currentOffset.toString(),
            sort_by: sortBy
        });
        
        // Add date filter
        const dateFrom = getDateFrom(currentPeriodDays);
        params.append('date_from', dateFrom);
        
        // Add product filter if active (use search parameter for product filtering)
        if (filterProduct) {
            params.append('search', filterProduct);
        } else if (search) {
            params.append('search', search);
        }
        if (language !== 'all') params.append('language', language);
        if (source !== 'all') params.append('source', source);
        
        console.log('Loading posts for improvement with params:', params.toString());
        const response = await fetch(`/api/posts-for-improvement?${params}`);
        console.log('Posts response status:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Posts error response:', errorText);
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Posts data received:', data);
        
        // Cache posts for preview modal
        if (resetOffset) {
            allPostsCache = data.posts;
        } else {
            allPostsCache = [...allPostsCache, ...data.posts];
        }
        
        // Filter posts by product if filter is active
        let filteredPosts = data.posts;
        if (filterProduct) {
            // Import product detection function
            const { getProductLabel } = await import('/dashboard/js/product-detection.js');
            filteredPosts = data.posts.filter(post => {
                const productLabel = getProductLabel(post.id, post.content, post.language);
                return productLabel === filterProduct;
            });
            console.log(`Filtered ${filteredPosts.length} posts for product: ${filterProduct}`);
        }
        
        const postsList = document.getElementById('postsToReviewList');
        const resultsCount = document.getElementById('resultsCount');
        
        if (resultsCount) {
            resultsCount.textContent = filterProduct ? filteredPosts.length : data.total;
        }
        
        if (!postsList) return;
        
        if (resetOffset) {
            postsList.innerHTML = '';
        }
        
        if (filteredPosts.length === 0 && currentOffset === 0) {
            const noPostsMsg = filterProduct 
                ? `No posts found for product: ${filterProduct}`
                : 'No posts found matching the filters.';
            postsList.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">${noPostsMsg}</div>`;
            return;
        }
        
        const postsHtml = filteredPosts.map(post => {
            const sourceIcon = getSourceIcon(post.source);
            const timeAgo = getTimeAgo(post.created_at);
            const views = post.views || 0;
            const comments = post.comments || 0;
            const reactions = post.reactions || 0;
            const isRecent = isPostRecent(post.created_at);
            const isNegative = post.sentiment_label === 'negative';
            
            return `
                <div class="post-review-item" onclick="openPostPreviewModal(${post.id})" style="cursor: pointer;">
                    <div class="post-source-logo" style="background: ${getSourceColor(post.source)};">
                        ${sourceIcon}
                    </div>
                    <div class="post-content-wrapper">
                        <div class="post-meta-top">
                            <span class="post-source-name">${escapeHtml(post.source || 'Unknown')}</span>
                            <span class="post-time">${timeAgo}</span>
                        </div>
                        <div class="post-content-text">${escapeHtml(truncateText(post.content || 'No content', 200))}</div>
                        <div class="post-engagement">
                            ${isRecent ? '<span class="engagement-tag tag-new">New</span>' : ''}
                            ${isNegative ? '<span class="engagement-tag tag-negative">Negative</span>' : ''}
                            ${views > 0 ? `<span class="engagement-metric">👁️ ${formatNumber(views)}</span>` : ''}
                            ${comments > 0 ? `<span class="engagement-metric">💬 ${comments} replies</span>` : ''}
                        </div>
                    </div>
                    <div class="post-score">${post.opportunity_score || 0}</div>
                    <button class="post-action-btn" onclick="event.stopPropagation(); createImprovementTicket(${post.id})">
                        + Create Improvement Ticket
                    </button>
                </div>
            `;
        }).join('');
        
        if (resetOffset) {
            postsList.innerHTML = postsHtml;
        } else {
            postsList.innerHTML += postsHtml;
        }
        
        // Add load more button if there are more posts (only if not filtering by product)
        const totalToShow = filterProduct ? filteredPosts.length : data.total;
        if (!filterProduct && currentOffset + postsPerPage < data.total) {
            const loadMoreBtn = document.createElement('button');
            loadMoreBtn.className = 'post-action-btn';
            loadMoreBtn.style.margin = '20px auto';
            loadMoreBtn.style.display = 'block';
            loadMoreBtn.textContent = `Load More (${currentOffset + postsPerPage}/${data.total})`;
            loadMoreBtn.onclick = () => {
                currentOffset += postsPerPage;
                loadPostsForImprovement(false);
            };
            postsList.appendChild(loadMoreBtn);
        }
        
    } catch (error) {
        console.error('Error loading posts for improvement:', error);
        const postsList = document.getElementById('postsToReviewList');
        if (postsList) {
            postsList.innerHTML = `<div style="text-align: center; padding: 40px; color: #ef4444;">
                <strong>Error loading posts</strong><br>
                <small>${error.message}</small><br>
                <small style="color: var(--text-muted);">Check browser console (F12) for details</small>
            </div>`;
        }
    }
}

// Helper functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}

function isPostRecent(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = diffMs / 86400000;
    return diffDays <= 7;
}

function getSourceIcon(source) {
    const icons = {
        'X/Twitter': '🐦',
        'Twitter': '🐦',
        'Reddit': '🔴',
        'Trustpilot': '⭐',
        'OVH Forum': '💬',
        'News': '📰',
        'Stack Overflow': '📚',
        'GitHub': '💻'
    };
    return icons[source] || '📝';
}

function getSourceColor(source) {
    const colors = {
        'X/Twitter': 'rgba(29, 161, 242, 0.2)',
        'Twitter': 'rgba(29, 161, 242, 0.2)',
        'Reddit': 'rgba(255, 69, 0, 0.2)',
        'Trustpilot': 'rgba(0, 175, 160, 0.2)',
        'OVH Forum': 'rgba(0, 153, 255, 0.2)',
        'News': 'rgba(107, 114, 128, 0.2)'
    };
    return colors[source] || 'rgba(107, 114, 128, 0.2)';
}

function formatNumber(num) {
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'k';
    }
    return num.toString();
}

function createImprovementTicket(postId) {
    // TODO: Implement ticket creation
    alert(`Creating improvement ticket for post ${postId}...`);
    // This could open a modal or redirect to a ticket creation page
}

// Reload all data when period filter changes
async function reloadAllData() {
    try {
        await Promise.all([
            loadPainPoints(),
            loadProductDistribution(),
            loadPostsForImprovement(true)
        ]);
        await loadImprovementsAnalysis();
    } catch (error) {
        console.error('Error reloading data:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Period filter change handler
    const periodFilter = document.getElementById('improvementsPeriod');
    if (periodFilter) {
        periodFilter.addEventListener('change', async (e) => {
            currentPeriodDays = parseInt(e.target.value, 10);
            console.log('Period filter changed to:', currentPeriodDays, 'days');
            await reloadAllData();
        });
    }
    
    // Search input
    const searchInput = document.getElementById('improvementsSearch');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                loadPostsForImprovement(true);
            }, 500);
        });
    }
    
    // Filters
    const filters = ['improvementsLanguage', 'improvementsSource', 'improvementsSort'];
    filters.forEach(filterId => {
        const filter = document.getElementById(filterId);
        if (filter) {
            filter.addEventListener('change', () => {
                loadPostsForImprovement(true);
            });
        }
    });
}

// Initialize app
async function init() {
    console.log('Initializing improvements app...');
    initializeTheme();
    setupThemeToggle();
    setupEventListeners();
    // Load version using the shared loader if available, otherwise use local function
    // Version loading is handled by version-loader.js module (loaded via script tag in HTML)
    if (window.loadVersion) {
        await window.loadVersion();
    }
    
    // Load all data with error handling
    try {
        console.log('Loading data...');
        await Promise.all([
            loadPainPoints(),
            loadProductDistribution(),
            loadPostsForImprovement(true)
        ]);
        console.log('All data loaded successfully');
        
        // Load LLM analysis after data is loaded
        await loadImprovementsAnalysis();
    } catch (error) {
        console.error('Error during initialization:', error);
    }
}

// Load improvements analysis with LLM
async function loadImprovementsAnalysis() {
    const analysisSection = document.getElementById('improvementsAnalysis');
    const insightsContainer = document.getElementById('improvementsInsights');
    const roiContainer = document.getElementById('improvementsROI');
    const overlay = document.getElementById('improvementsOverlay');
    
    if (!analysisSection || !insightsContainer || !roiContainer) {
        console.warn('Improvements analysis containers not found');
        return;
    }
    
    // Show overlay during LLM analysis
    if (overlay) {
        overlay.style.display = 'flex';
    }
    
    // Set a timeout to hide overlay after max 30 seconds (safety measure)
    const overlayTimeout = setTimeout(() => {
        if (overlay) {
            overlay.style.display = 'none';
        }
    }, 30000);
    
    try {
        // Get pain points and products data with current period filter
        const painPointsResponse = await fetch(`/api/pain-points?days=${currentPeriodDays}&limit=10`);
        const dateFrom = getDateFrom(currentPeriodDays);
        const productsResponse = await fetch(`/api/product-opportunities?date_from=${dateFrom}`);
        
        if (!painPointsResponse.ok || !productsResponse.ok) {
            throw new Error('Failed to load data for analysis');
        }
        
        const painPointsData = await painPointsResponse.json();
        const productsData = await productsResponse.json();
        
        // Filter pain points and products by current product filter if active
        let filteredPainPoints = painPointsData.pain_points || [];
        let filteredProducts = productsData.products || [];
        
        if (currentProductFilter) {
            // Filter products to only show the selected one
            filteredProducts = productsData.products.filter(p => p.product === currentProductFilter);
            // Filter pain points that mention the product (simplified - could be improved)
            filteredPainPoints = painPointsData.pain_points.filter(pp => {
                const titleLower = (pp.title || '').toLowerCase();
                const descLower = (pp.description || '').toLowerCase();
                const productLower = currentProductFilter.toLowerCase();
                return titleLower.includes(productLower) || descLower.includes(productLower);
            });
        }
        
        // Get total posts count (filtered if product filter is active)
        const postsParams = new URLSearchParams({ limit: '1000', date_from: dateFrom });
        if (currentProductFilter) {
            postsParams.append('search', currentProductFilter);
        }
        const postsResponse = await fetch(`/api/posts-for-improvement?${postsParams.toString()}`);
        let postsData = { total: 0, posts: [] };
        if (postsResponse.ok) {
            postsData = await postsResponse.json();
            // If filtering by product, count only posts matching that product
            if (currentProductFilter && postsData.posts) {
                const { getProductLabel } = await import('/dashboard/js/product-detection.js');
                const matchingPosts = postsData.posts.filter(post => {
                    const productLabel = getProductLabel(post.id, post.content, post.language);
                    return productLabel === currentProductFilter;
                });
                postsData.total = matchingPosts.length;
            }
        }
        
        // Call LLM analysis endpoint
        const analysisResponse = await fetch('/api/improvements-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                pain_points: filteredPainPoints,
                products: filteredProducts,
                total_posts: postsData.total || 0
            })
        });
        
        if (!analysisResponse.ok) {
            throw new Error('Failed to generate analysis');
        }
        
        const analysis = await analysisResponse.json();
        
        // Display insights
        if (analysis.insights && analysis.insights.length > 0) {
            insightsContainer.innerHTML = analysis.insights.map(insight => `
                <div class="insight-card" style="margin-bottom: 16px; padding: 16px; background: rgba(255, 255, 255, 0.5); border-radius: 8px; border-left: 4px solid var(--accent-primary);">
                    <div style="display: flex; align-items: start; gap: 12px;">
                        <span style="font-size: 1.5em;">${insight.icon || '💡'}</span>
                        <div style="flex: 1;">
                            <h3 style="margin: 0 0 8px 0; font-size: 1.1em; color: var(--text-primary);">${escapeHtml(insight.title)}</h3>
                            <p style="margin: 0 0 8px 0; color: var(--text-secondary); line-height: 1.6;">${escapeHtml(insight.description)}</p>
                            ${insight.metric ? `<div style="font-weight: 600; color: var(--accent-primary);">${escapeHtml(insight.metric)}</div>` : ''}
                            ${insight.roi_impact ? `<div style="margin-top: 8px; padding: 8px; background: rgba(16, 185, 129, 0.1); border-radius: 6px; color: #059669; font-size: 0.9em;"><strong>Impact:</strong> ${escapeHtml(insight.roi_impact)}</div>` : ''}
                        </div>
                    </div>
                </div>
            `).join('');
        } else {
            insightsContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">No insights available at this time.</div>';
        }
        
        // Display ROI summary
        if (analysis.roi_summary) {
            roiContainer.innerHTML = `
                <h3 style="margin: 0 0 12px 0; color: #059669; display: flex; align-items: center; gap: 8px;">
                    <span>💰</span>
                    <span>ROI & Customer Impact</span>
                </h3>
                <p style="margin: 0; color: var(--text-secondary); line-height: 1.7; font-size: 1.05em;">${escapeHtml(analysis.roi_summary)}</p>
            `;
        } else {
            roiContainer.innerHTML = '';
        }
        
        // Show the analysis section
        analysisSection.style.display = 'block';
        
    } catch (error) {
        console.error('Error loading improvements analysis:', error);
        if (insightsContainer) {
            insightsContainer.innerHTML = `<div style="text-align: center; padding: 20px; color: #ef4444;">
                <p>Error loading analysis: ${escapeHtml(error.message)}</p>
                <button onclick="refreshImprovementsAnalysis()" style="margin-top: 10px; padding: 8px 16px; background: var(--accent-primary); color: white; border: none; border-radius: 6px; cursor: pointer;">
                    🔄 Retry Analysis
                </button>
            </div>`;
        }
        // Show refresh button on error
        const refreshBtn = document.getElementById('refreshImprovementsAnalysisBtn');
        if (refreshBtn) {
            refreshBtn.style.display = 'flex';
        }
        // Still show the section even if there's an error
        if (analysisSection) {
            analysisSection.style.display = 'block';
        }
    } finally {
        // Always hide overlay, even if there was an error
        clearTimeout(overlayTimeout);
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
}

// Refresh Improvements Analysis
window.refreshImprovementsAnalysis = async function() {
    const refreshBtn = document.getElementById('refreshImprovementsAnalysisBtn');
    if (refreshBtn) {
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 18px; height: 18px;"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg> Refreshing...';
    }
    
    try {
        await loadImprovementsAnalysis();
    } catch (error) {
        console.error('Error refreshing improvements analysis:', error);
    } finally {
        if (refreshBtn) {
            refreshBtn.disabled = false;
            refreshBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 18px; height: 18px;"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg> Refresh Analysis';
        }
    }
};

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Open post preview modal
function openPostPreviewModal(postId) {
    const post = allPostsCache.find(p => p.id === postId);
    if (!post) {
        console.error('Post not found:', postId);
        return;
    }
    
    const modal = document.getElementById('postPreviewModal');
    const contentDiv = document.getElementById('postPreviewContent');
    const linkDiv = document.getElementById('postPreviewLink');
    
    if (!modal || !contentDiv || !linkDiv) {
        console.error('Preview modal elements not found');
        return;
    }
    
    // Format date
    const postDate = new Date(post.created_at).toLocaleString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    // Get sentiment class
    const sentimentClass = post.sentiment_label === 'negative' ? 'sentiment-negative' : 
                          post.sentiment_label === 'positive' ? 'sentiment-positive' : 'sentiment-neutral';
    
    // Build content HTML
    contentDiv.innerHTML = `
        <div style="margin-bottom: 20px; padding: 15px; background: rgba(0, 153, 255, 0.1); border-radius: 8px; border-left: 4px solid var(--accent-primary);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
                <div>
                    <strong style="color: var(--accent-primary); font-size: 1.1em;">${escapeHtml(post.source || 'Unknown Source')}</strong>
                </div>
                <span class="${sentimentClass}" style="font-size: 0.95em; padding: 4px 12px; border-radius: 6px;">
                    ${(post.sentiment_label || 'neutral').toUpperCase()} ${post.sentiment_score ? `(${(post.sentiment_score).toFixed(2)})` : ''}
                </span>
            </div>
            <div style="color: var(--text-secondary); font-size: 0.9em; margin-bottom: 10px;">
                <strong>Author:</strong> ${escapeHtml(post.author || 'Unknown')}
            </div>
            <div style="color: var(--text-secondary); font-size: 0.9em; margin-bottom: 10px;">
                <strong>Date:</strong> ${postDate}
            </div>
            ${post.language && post.language !== 'unknown' ? `<div style="color: var(--text-secondary); font-size: 0.9em; margin-bottom: 10px;">
                <strong>Language:</strong> ${escapeHtml(post.language.toUpperCase())}
            </div>` : ''}
            <div style="color: var(--text-secondary); font-size: 0.9em; margin-bottom: 10px;">
                <strong>Opportunity Score:</strong> ${post.opportunity_score || 0}
            </div>
        </div>
        
        <div style="padding: 20px; background: var(--bg-card); border-radius: 8px; border: 1px solid rgba(0, 153, 255, 0.2);">
            <h3 style="color: var(--accent-primary); margin-top: 0; margin-bottom: 15px; font-size: 1.2em;">Content:</h3>
            <div style="color: var(--text-primary); white-space: pre-wrap; word-wrap: break-word; line-height: 1.6; max-height: none; overflow-y: visible; padding: 15px; background: var(--bg-secondary); border-radius: 6px; border: 1px solid var(--border-color);">
                ${escapeHtml(post.content || 'No content available')}
            </div>
        </div>
    `;
    
    // Set link
    if (post.url && post.url !== '#') {
        linkDiv.href = post.url;
        linkDiv.target = '_blank';
        linkDiv.style.display = 'inline-block';
    } else {
        linkDiv.style.display = 'none';
    }
    
    // Show modal
    modal.style.display = 'block';
}

function closePostPreviewModal() {
    const modal = document.getElementById('postPreviewModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Make functions available globally
window.createImprovementTicket = createImprovementTicket;
window.filterByProduct = filterByProduct;
window.filterDashboardByProduct = filterDashboardByProduct;
window.openProductAnalysis = openProductAnalysis; // Keep for backward compatibility
window.openPostPreviewModal = openPostPreviewModal;
window.closePostPreviewModal = closePostPreviewModal;

function toggleHelpMenu() {
    const menu = document.getElementById('helpMenu');
    if (menu) {
        menu.classList.toggle('active');
    }
}

window.toggleHelpMenu = toggleHelpMenu;

// Initialize when DOM is ready
// Filter by product (replaces openProductAnalysis - no drawer)
async function filterByProduct(productName) {
    // Toggle filter: if same product clicked, clear filter
    if (currentProductFilter === productName) {
        currentProductFilter = null;
    } else {
        currentProductFilter = productName;
    }
    
    console.log('Filtering by product:', currentProductFilter || 'none');
    
    // Update visual indicator
    updateProductFilterIndicator();
    
    // Reload all data with filter
    await Promise.all([
        loadPainPoints(),
        loadProductDistribution(),
        loadPostsForImprovement(true, currentProductFilter)
    ]);
    
    // Reload LLM analysis with filter
    await loadImprovementsAnalysis();
}

// Filter Dashboard by product (opens Dashboard with product filter applied)
function filterDashboardByProduct(productName) {
    console.log('Filtering Dashboard by product:', productName);
    
    // Store product filter in localStorage for Dashboard to read
    localStorage.setItem('dashboardProductFilter', productName);
    
    // Navigate to Dashboard
    window.location.href = '/dashboard/';
}

// Update product filter indicator
function updateProductFilterIndicator() {
    const productDistribution = document.getElementById('productDistribution');
    if (!productDistribution) return;
    
    // Update all product items styling
    productDistribution.querySelectorAll('.product-item').forEach(item => {
        const product = item.getAttribute('data-product');
        if (currentProductFilter === product) {
            item.classList.add('active-filter');
            item.style.border = '2px solid var(--accent-primary)';
            item.style.boxShadow = '0 0 0 3px rgba(0, 153, 255, 0.2)';
            item.style.borderRadius = '8px';
        } else {
            item.classList.remove('active-filter');
            item.style.border = '';
            item.style.boxShadow = '';
        }
    });
    
    // Show/hide clear filter button
    let clearFilterBtn = document.getElementById('clearProductFilterBtn');
    if (currentProductFilter) {
        if (!clearFilterBtn) {
            clearFilterBtn = document.createElement('button');
            clearFilterBtn.id = 'clearProductFilterBtn';
            clearFilterBtn.className = 'filter-clear-btn';
            clearFilterBtn.innerHTML = `Clear filter: ${escapeHtml(currentProductFilter)} ×`;
            clearFilterBtn.onclick = () => filterByProduct(currentProductFilter); // Toggle to clear
            clearFilterBtn.style.cssText = 'margin: 16px 0; padding: 8px 16px; background: var(--accent-primary); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;';
            
            const productDistributionSection = document.querySelector('.product-distribution-section');
            if (productDistributionSection) {
                productDistributionSection.insertBefore(clearFilterBtn, productDistributionSection.firstChild);
            }
        } else {
            clearFilterBtn.innerHTML = `Clear filter: ${escapeHtml(currentProductFilter)} ×`;
            clearFilterBtn.style.display = 'block';
        }
    } else {
        if (clearFilterBtn) {
            clearFilterBtn.style.display = 'none';
        }
    }
}

// Product Analysis Drawer (kept for backward compatibility but not used)
async function openProductAnalysis(productName) {
    // Redirect to filter function instead
    await filterByProduct(productName);
}

function closeProductAnalysisDrawer() {
    const drawer = document.getElementById('productAnalysisDrawer');
    if (drawer) {
        drawer.classList.remove('open');
    }
}

// Pain point keywords mapping (same as backend)
const PAIN_POINT_KEYWORDS = {
    'Performance Issues': ['slow', 'lent', 'performance', 'lag', 'timeout', 'time out', 'slowly', 'slowness', 'slow response', 'slow loading', 'slowly loading'],
    'Downtime & Outages': ['down', 'outage', 'offline', 'unavailable', 'unreachable', 'not working', 'doesn\'t work', 'not accessible', 'service unavailable', 'error 503', 'error 502', 'error 500'],
    'Billing Problems': ['billing', 'invoice', 'payment', 'charge', 'charged', 'refund', 'cost', 'price', 'expensive', 'overcharge', 'facture', 'paiement', 'facturation'],
    'Support Issues': ['support', 'ticket', 'help', 'assistance', 'response time', 'no response', 'no reply', 'customer service', 'service client'],
    'Configuration Problems': ['config', 'configuration', 'setup', 'install', 'installation', 'configure', 'setting', 'settings', 'cannot configure', 'can\'t configure'],
    'API & Integration Issues': ['api', 'integration', 'endpoint', 'connection', 'connect', 'authentication', 'auth', 'token', 'credential'],
    'Data Loss & Backup': ['lost', 'delete', 'deleted', 'backup', 'restore', 'recovery', 'data loss', 'lost data', 'missing data'],
    'Security Concerns': ['security', 'hack', 'breach', 'vulnerability', 'exploit', 'unauthorized', 'access', 'secure', 'protection'],
    'Migration Problems': ['migration', 'migrate', 'transfer', 'move', 'upgrade', 'update', 'migration failed', 'cannot migrate'],
    'Network Issues': ['network', 'connection', 'latency', 'bandwidth', 'ddos', 'attack', 'traffic', 'routing', 'dns']
};

// Open drawer for pain point posts
window.openPainPointDrawer = function(painPointTitle, painPointIndex) {
    const painPoint = window.currentPainPoints && window.currentPainPoints[painPointIndex];
    if (!painPoint) {
        console.error('Pain point not found:', painPointTitle);
        return;
    }
    
    // Get keywords for this pain point
    const keywords = PAIN_POINT_KEYWORDS[painPointTitle] || [];
    if (keywords.length === 0) {
        console.warn('No keywords found for pain point:', painPointTitle);
        return;
    }
    
    // Load all posts and filter by keywords
    loadPainPointPosts(painPointTitle, keywords, painPoint);
};

async function loadPainPointPosts(painPointTitle, keywords, painPoint) {
    try {
        // Get date filter
        const dateFrom = getDateFrom(currentPeriodDays);
        
        // Build API URL with filters
        const params = new URLSearchParams({
            limit: '1000',
            offset: '0',
            date_from: dateFrom
        });
        
        // Add product filter if active
        if (currentProductFilter) {
            params.append('search', currentProductFilter);
        }
        
        // Fetch posts with date and product filters
        const response = await fetch(`/api/posts-for-improvement?${params.toString()}`);
        if (!response.ok) {
            throw new Error(`Failed to load posts: ${response.status}`);
        }
        
        const data = await response.json();
        let allPosts = data.posts || [];
        
        // If product filter is active, also filter by product label to ensure accuracy
        if (currentProductFilter) {
            // Import product detection function
            const { getProductLabel } = await import('/dashboard/js/product-detection.js');
            allPosts = allPosts.filter(post => {
                const productLabel = getProductLabel(post.id, post.content, post.language);
                return productLabel === currentProductFilter;
            });
        }
        
        // Filter posts by keywords (case-insensitive)
        const filteredPosts = allPosts.filter(post => {
            const content = (post.content || '').toLowerCase();
            return keywords.some(keyword => content.includes(keyword.toLowerCase()));
        });
        
        // Sort by opportunity score (descending)
        filteredPosts.sort((a, b) => (b.opportunity_score || 0) - (a.opportunity_score || 0));
        
        // Open drawer with filtered posts
        openPainPointDrawerContent(painPointTitle, painPoint.description, filteredPosts, painPoint);
        
    } catch (error) {
        console.error('Error loading pain point posts:', error);
        alert(`Error loading posts for ${painPointTitle}: ${error.message}`);
    }
}

function openPainPointDrawerContent(title, description, posts, painPoint) {
    const drawer = document.getElementById('painPointsDrawer');
    if (!drawer) {
        console.error('Pain points drawer not found');
        return;
    }
    
    const drawerContent = document.getElementById('painPointsDrawerContent');
    if (!drawerContent) {
        console.error('Pain points drawer content not found');
        return;
    }
    
    // Show drawer
    drawer.style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    // Show drawer
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.paddingRight = `${scrollbarWidth}px`;
    document.body.classList.add('drawer-open');
    drawer.style.display = 'block';
    drawer.classList.add('open');
    
    // Helper functions
    function getTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    }
    
    function getSourceIcon(source) {
        const icons = {
            'X/Twitter': '🐦',
            'Twitter': '🐦',
            'Reddit': '🔴',
            'Trustpilot': '⭐',
            'OVH Forum': '💬',
            'Stack Overflow': '📚',
            'GitHub': '💻',
            'Google News': '📰',
            'Mastodon': '🐘',
            'G2 Crowd': '⭐'
        };
        return icons[source] || '📝';
    }
    
    // Build HTML with product filter indicator if active
    const productFilterIndicator = currentProductFilter ? 
        `<div style="margin-top: 8px; padding: 6px 12px; background: rgba(0, 153, 255, 0.1); border-radius: 6px; display: inline-block;">
            <span style="color: var(--accent-primary); font-size: 0.85em; font-weight: 600;">📦 Filtered by: ${escapeHtml(currentProductFilter)}</span>
        </div>` : '';
    
    let html = `
        <div class="drawer-header">
            <div>
                <h3>${painPoint.icon || '📊'} ${escapeHtml(title)}</h3>
                <p style="margin: 8px 0 0 0; color: var(--text-secondary); font-size: 0.9em;">${escapeHtml(description)}</p>
                ${productFilterIndicator}
            </div>
            <button class="drawer-close" onclick="closePainPointDrawer()" aria-label="Close drawer">×</button>
        </div>
        <div class="drawer-info">
            <div class="drawer-stats">
                <span class="drawer-stat-value">${posts.length}</span>
                <span class="drawer-stat-label">posts${currentProductFilter ? ` (${escapeHtml(currentProductFilter)})` : ''}</span>
            </div>
        </div>
        <div class="drawer-posts">
    `;
    
    if (posts.length === 0) {
        html += `
            <div class="drawer-empty">
                <p>No posts found matching this pain point.</p>
            </div>
        `;
    } else {
        posts.forEach(post => {
            const sourceIcon = getSourceIcon(post.source);
            const timeAgo = getTimeAgo(post.created_at);
            const sentiment = post.sentiment_label || 'neutral';
            const sentimentClass = sentiment === 'negative' ? 'sentiment-negative' : 
                                 sentiment === 'positive' ? 'sentiment-positive' : 'sentiment-neutral';
            
            html += `
                <div class="drawer-post-item" onclick="openPostPreviewModal(${post.id})" style="cursor: pointer;">
                    <div class="drawer-post-header">
                        <div class="drawer-post-source">
                            <span class="drawer-source-icon">${sourceIcon}</span>
                            <span class="drawer-source-name">${escapeHtml(post.source || 'Unknown')}</span>
                            <span class="drawer-post-time">${timeAgo}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span class="drawer-sentiment-badge ${sentimentClass}">${sentiment}</span>
                            ${post.opportunity_score ? `<span style="padding: 4px 8px; background: rgba(0, 153, 255, 0.1); border-radius: 4px; color: var(--accent-primary); font-size: 0.8em; font-weight: 600;">Score: ${post.opportunity_score}</span>` : ''}
                        </div>
                    </div>
                    <div class="drawer-post-content">${escapeHtml(truncateText(post.content || 'No content', 300))}</div>
                    <div class="drawer-post-meta">
                        ${post.url ? `<a href="${post.url}" target="_blank" class="drawer-post-link" onclick="event.stopPropagation();">View post →</a>` : ''}
                    </div>
                </div>
            `;
        });
    }
    
    html += `
        </div>
    `;
    
    drawerContent.innerHTML = html;
}

window.closePainPointDrawer = function() {
    const drawer = document.getElementById('painPointsDrawer');
    if (drawer) {
        drawer.classList.remove('open');
        drawer.style.display = 'none';
        document.body.classList.remove('drawer-open');
        document.body.style.paddingRight = '';
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

