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
        // Build URL with product filter if active
        let url = `/api/pain-points?days=${currentPeriodDays}&limit=5`;
        if (currentProductFilter) {
            url += `&product=${encodeURIComponent(currentProductFilter)}`;
            console.log('Loading pain points filtered by product:', currentProductFilter);
        }
        const response = await fetch(url);
        console.log('Pain points response status:', response.status, response.statusText);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Pain points error response:', errorText);
            painPointsList.innerHTML = `<div style="text-align: center; padding: 40px; color: #ef4444;">Error loading pain points: HTTP ${response.status}<br><small>${errorText}</small></div>`;
            throw new Error(`Failed to load pain points: ${response.status} ${errorText}`);
        }
        
        const data = await response.json();
        console.log('Pain points data received:', data);
        
        // Backend already filters by product if currentProductFilter is set
        // So we can use the pain points directly
        let filteredPainPoints = data.pain_points || [];
        
        // Store pain points globally for drawer access
        window.currentPainPoints = filteredPainPoints;
        
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
async function loadProductDistribution(periodDays = null) {
    const productDistribution = document.getElementById('productDistribution');
    if (!productDistribution) {
        console.error('productDistribution element not found');
        return;
    }
    
    // Use provided period or fall back to currentPeriodDays
    const period = periodDays !== null ? periodDays : currentPeriodDays;
    
    try {
        console.log('Loading product distribution for period:', period, 'days');
        // Add date filter to product opportunities
        const dateFrom = getDateFrom(period);
        console.log('Product distribution date_from:', dateFrom);
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
            // La barre représente maintenant le score d'opportunité directement (0-100)
            const scorePercentage = Math.min(product.opportunity_score, 100);
            
            // Escape product name for onclick attribute
            const escapedProduct = escapeHtml(product.product).replace(/'/g, "\\'");
            return `
                <div class="product-item ${currentProductFilter === product.product ? 'active-filter' : ''}" data-product="${escapeHtml(product.product)}" style="cursor: pointer;" onclick="filterByProduct('${escapedProduct}')" title="Click to filter this page by ${escapeHtml(product.product)}">
                    <div class="product-color" style="background: ${product.color};"></div>
                    <div class="product-bar-container" style="position: relative;">
                        <!-- Barre unique proportionnelle au score d'opportunité -->
                        <div class="product-bar" style="width: ${scorePercentage}%; background: ${product.color}; height: 100%; position: relative;">
                            <span style="position: absolute; left: 8px; top: 50%; transform: translateY(-50%); color: white; font-weight: 700; font-size: 0.85em; text-shadow: 0 1px 2px rgba(0,0,0,0.3); white-space: nowrap;">${product.negative_posts} negative post${product.negative_posts !== 1 ? 's' : ''}</span>
                        </div>
                    </div>
                    <div class="product-info">
                        <span class="product-name">${escapeHtml(product.product)}</span>
                        <span class="product-score" style="${getScoreStyle(product.opportunity_score)}; padding: 6px 12px; border-radius: 10px; display: inline-block;">${Math.round(product.opportunity_score)}</span>
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
                        // La barre représente maintenant le score d'opportunité directement (0-100)
                        const scorePercentage = Math.min(product.opportunity_score, 100);
                        // Escape product name for onclick attribute
                        const escapedProduct = escapeHtml(product.product).replace(/'/g, "\\'");
                        return `
                            <div class="product-item ${currentProductFilter === product.product ? 'active-filter' : ''}" data-product="${escapeHtml(product.product)}" style="cursor: pointer;" onclick="filterByProduct('${escapedProduct}')" title="Click to filter this page by ${escapeHtml(product.product)}">
                                <div class="product-color" style="background: ${product.color};"></div>
                                <div class="product-bar-container" style="position: relative;">
                                    <!-- Barre unique proportionnelle au score d'opportunité -->
                                    <div class="product-bar" style="width: ${scorePercentage}%; background: ${product.color}; height: 100%; position: relative;">
                                        <span style="position: absolute; left: 8px; top: 50%; transform: translateY(-50%); color: white; font-weight: 700; font-size: 0.85em; text-shadow: 0 1px 2px rgba(0,0,0,0.3); white-space: nowrap;">${product.negative_posts} negative post${product.negative_posts !== 1 ? 's' : ''}</span>
                                    </div>
                                </div>
                                <div class="product-info">
                                    <span class="product-name">${escapeHtml(product.product)}</span>
                                    <span class="product-score" style="${getScoreStyle(product.opportunity_score)}; padding: 6px 12px; border-radius: 10px; display: inline-block;">${Math.round(product.opportunity_score)}</span>
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
        const product = document.getElementById('improvementsProduct')?.value || 'all';
        const source = document.getElementById('improvementsSource')?.value || 'all';
        const answered = document.getElementById('improvementsAnswered')?.value || 'all';
        const periodPosts = document.getElementById('improvementsPeriodPosts')?.value || currentPeriodDays.toString();
        const periodDays = parseInt(periodPosts, 10);
        const sortBy = document.getElementById('improvementsSort')?.value || 'opportunity_score';
        
        const params = new URLSearchParams({
            limit: postsPerPage.toString(),
            offset: currentOffset.toString(),
            sort_by: sortBy
        });
        
        // Add date filter from period selector
        const dateFrom = getDateFrom(periodDays);
        params.append('date_from', dateFrom);
        
        // Add search filter (product or keyword search)
        if (filterProduct) {
            params.append('search', filterProduct);
        } else if (product !== 'all') {
            params.append('search', product);
        } else if (search) {
            params.append('search', search);
        }
        
        // Add other filters
        if (language !== 'all') params.append('language', language);
        if (source !== 'all') params.append('source', source);
        if (answered !== 'all') params.append('is_answered', answered);
        
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
                    <div class="post-score" style="${getScoreStyle(post.opportunity_score || 0)}; padding: 10px 16px; border-radius: 12px; font-size: 1.2em; min-width: 70px; text-align: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                        ${(post.opportunity_score || 0).toFixed(1)}
                    </div>
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

// Get color style for opportunity score (gradient from green to red)
function getScoreStyle(score) {
    // Normalize score to 0-100 range
    const normalizedScore = Math.max(0, Math.min(100, score));
    
    // Calculate color gradient: green (low) -> yellow (medium) -> red (high)
    // 0-50: green to yellow
    // 50-100: yellow to red
    let r, g, b;
    
    if (normalizedScore <= 50) {
        // Green (0, 200, 0) to Yellow (255, 200, 0)
        const ratio = normalizedScore / 50;
        r = Math.round(0 + (255 - 0) * ratio);
        g = 200;
        b = Math.round(0 + (0 - 0) * ratio);
    } else {
        // Yellow (255, 200, 0) to Red (255, 0, 0)
        const ratio = (normalizedScore - 50) / 50;
        r = 255;
        g = Math.round(200 - (200 - 0) * ratio);
        b = 0;
    }
    
    // Calculate background color (lighter) and text color (darker for contrast)
    const bgColor = `rgba(${r}, ${g}, ${b}, 0.15)`;
    const textColor = `rgb(${r}, ${g}, ${b})`;
    const borderColor = `rgba(${r}, ${g}, ${b}, 0.5)`;
    
    return `background: ${bgColor}; color: ${textColor}; border: 1px solid ${borderColor}; font-weight: 700;`;
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
        'GitHub': '💻',
        'Discord': '💬'
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
        console.log('reloadAllData called with currentPeriodDays:', currentPeriodDays);
        await Promise.all([
            loadPainPoints(),
            loadProductDistribution(currentPeriodDays), // Pass period explicitly
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
            const newPeriodDays = parseInt(e.target.value, 10);
            console.log('Period filter changed from', currentPeriodDays, 'to', newPeriodDays, 'days');
            currentPeriodDays = newPeriodDays;
            // Sync posts period filter
            const periodPostsFilter = document.getElementById('improvementsPeriodPosts');
            if (periodPostsFilter) {
                periodPostsFilter.value = currentPeriodDays.toString();
            }
            console.log('Reloading all data with period:', currentPeriodDays);
            await reloadAllData();
        });
    }
    
    // Period filter for posts section (sync with main filter)
    const periodPostsFilter = document.getElementById('improvementsPeriodPosts');
    if (periodPostsFilter) {
        // Sync with main period filter
        periodPostsFilter.value = currentPeriodDays.toString();
        periodPostsFilter.addEventListener('change', async (e) => {
            const days = parseInt(e.target.value, 10);
            console.log('Posts period filter changed from', currentPeriodDays, 'to', days, 'days');
            // Sync main filter
            if (periodFilter) {
                periodFilter.value = days.toString();
            }
            currentPeriodDays = days;
            console.log('Reloading all data with period:', currentPeriodDays);
            // Recharger toutes les données avec la nouvelle période
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
    
    // Filters (improvementsPeriodPosts is handled separately above)
    const filters = ['improvementsLanguage', 'improvementsSource', 'improvementsProduct', 'improvementsAnswered', 'improvementsSort'];
    filters.forEach(filterId => {
        const filter = document.getElementById(filterId);
        if (filter) {
            filter.addEventListener('change', () => {
                loadPostsForImprovement(true);
            });
        }
    });
    
    // Clear filters button
    const clearFiltersBtn = document.getElementById('clearImprovementsFiltersBtn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            clearImprovementsFilters();
        });
    }
    
    // Load products into product filter
    loadProductsForFilter();
    
    // PowerPoint report button
    const generateReportBtn = document.getElementById('generateImprovementsReportBtn');
    if (generateReportBtn) {
        generateReportBtn.addEventListener('click', () => {
            generateImprovementsPowerPointReport();
        });
    }
}

// Generate PowerPoint report for improvements page
async function generateImprovementsPowerPointReport() {
    const btn = document.getElementById('generateImprovementsReportBtn');
    if (!btn) return;
    
    const originalText = btn.textContent;
    
    // Show loading state
    btn.disabled = true;
    btn.textContent = '⏳ Generating...';
    
    try {
        // Get current filters
        const periodDays = parseInt(document.getElementById('improvementsPeriod')?.value || '30', 10);
        const dateFrom = getDateFrom(periodDays);
        const search = document.getElementById('improvementsSearch')?.value || '';
        const language = document.getElementById('improvementsLanguage')?.value || 'all';
        const product = document.getElementById('improvementsProduct')?.value || 'all';
        const source = document.getElementById('improvementsSource')?.value || 'all';
        const answered = document.getElementById('improvementsAnswered')?.value || 'all';
        
        const filters = {
            search: search,
            sentiment: 'all',
            language: language !== 'all' ? language : 'all',
            product: product !== 'all' ? product : 'all',
            source: source !== 'all' ? source : 'all',
            dateFrom: dateFrom,
            dateTo: new Date().toISOString().split('T')[0]
        };
        
        // Get improvements analysis insights
        const insights = window.currentImprovementsInsights || [];
        const improvementsAnalysis = insights.map(insight => ({
            title: insight.title || insight.get?.('title', ''),
            description: insight.description || insight.get?.('description', ''),
            metric: insight.metric || insight.get?.('metric', ''),
            roi_impact: insight.roi_impact || insight.get?.('roi_impact', '')
        }));
        
        // Prepare FormData
        const formData = new FormData();
        formData.append('filters', JSON.stringify(filters));
        formData.append('include_recommendations', 'true');
        formData.append('include_analysis', 'true');
        formData.append('improvements_analysis', JSON.stringify(improvementsAnalysis));
        formData.append('report_type', 'improvements');
        
        // Call API to generate report
        const response = await fetch('/api/generate-powerpoint-report', {
            method: 'POST',
            body: formData
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
        a.download = `OVH_Improvements_Report_${new Date().toISOString().split('T')[0]}.pptx`;
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
        btn.textContent = originalText;
    }
}

// Show toast notification (simple implementation)
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#0099ff'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        font-weight: 600;
        animation: slideIn 0.3s ease-out;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Load products into product filter dropdown
async function loadProductsForFilter() {
    try {
        const response = await fetch('/api/posts');
        if (!response.ok) return;
        
        const posts = await response.json();
        if (!Array.isArray(posts)) return;
        
        // Import product detection
        const { getProductLabel } = await import('/dashboard/js/product-detection.js');
        
        // Get unique products
        const products = new Set();
        posts.forEach(post => {
            const product = getProductLabel(post.id, post.content, post.language);
            if (product) {
                products.add(product);
            }
        });
        
        // Sort products alphabetically
        const sortedProducts = Array.from(products).sort();
        
        // Update select
        const productSelect = document.getElementById('improvementsProduct');
        if (productSelect) {
            // Keep "All Products" option
            const allOption = productSelect.querySelector('option[value="all"]');
            productSelect.innerHTML = '';
            if (allOption) {
                productSelect.appendChild(allOption);
            }
            
            // Add product options
            sortedProducts.forEach(product => {
                const option = document.createElement('option');
                option.value = product;
                option.textContent = product;
                productSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading products for filter:', error);
    }
}

// Clear all filters
function clearImprovementsFilters() {
    const searchInput = document.getElementById('improvementsSearch');
    const languageSelect = document.getElementById('improvementsLanguage');
    const productSelect = document.getElementById('improvementsProduct');
    const sourceSelect = document.getElementById('improvementsSource');
    const answeredSelect = document.getElementById('improvementsAnswered');
    const periodPostsSelect = document.getElementById('improvementsPeriodPosts');
    const sortSelect = document.getElementById('improvementsSort');
    
    if (searchInput) searchInput.value = '';
    if (languageSelect) languageSelect.value = 'all';
    if (productSelect) productSelect.value = 'all';
    if (sourceSelect) sourceSelect.value = 'all';
    if (answeredSelect) answeredSelect.value = 'all';
    if (periodPostsSelect) periodPostsSelect.value = currentPeriodDays.toString();
    if (sortSelect) sortSelect.value = 'opportunity_score';
    
    // Reload posts
    loadPostsForImprovement(true);
}

// Initialize app
async function init() {
    console.log('Initializing improvements app...');
    initializeTheme();
    setupThemeToggle();
    setupEventListeners();
    // Load products after a short delay to ensure DOM is ready
    setTimeout(() => {
        loadProductsForFilter();
    }, 500);
    
    // Show LLM analysis overlay IMMEDIATELY on page load
    const showImprovementsOverlay = () => {
        const analysisSection = document.getElementById('improvementsAnalysis');
        const overlay = document.getElementById('improvementsOverlay');
        if (analysisSection && overlay) {
            // Show section first so overlay can be visible
            analysisSection.style.setProperty('display', 'block', 'important');
            analysisSection.style.setProperty('position', 'relative', 'important');
            // Show overlay
            overlay.style.setProperty('display', 'flex', 'important');
            overlay.style.setProperty('z-index', '1000', 'important');
            overlay.style.setProperty('visibility', 'visible', 'important');
            overlay.style.setProperty('opacity', '1', 'important');
            overlay.style.setProperty('position', 'absolute', 'important');
            overlay.removeAttribute('hidden');
            // Remove any inline style that might hide it
            const currentStyle = overlay.getAttribute('style') || '';
            if (currentStyle.includes('display: none')) {
                overlay.setAttribute('style', currentStyle.replace(/display:\s*none[;]?/gi, ''));
            }
        }
    };
    // Multiple attempts to ensure overlay is visible
    showImprovementsOverlay();
    requestAnimationFrame(() => showImprovementsOverlay());
    setTimeout(() => showImprovementsOverlay(), 50);
    setTimeout(() => showImprovementsOverlay(), 100);
    setTimeout(() => showImprovementsOverlay(), 200);
    setTimeout(() => showImprovementsOverlay(), 500);
    
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
    
    if (!analysisSection || !insightsContainer || !roiContainer) {
        console.warn('Improvements analysis containers not found');
        return;
    }
    
    // Show the analysis section FIRST so overlay can be visible
    analysisSection.style.display = 'block';
    analysisSection.style.setProperty('position', 'relative', 'important');
    
    // Get overlay AFTER section is visible
    let overlay = document.getElementById('improvementsOverlay');
    
    // Show overlay IMMEDIATELY during LLM analysis
    const showOverlay = () => {
        // Re-get overlay in case it wasn't found initially
        if (!overlay) {
            overlay = document.getElementById('improvementsOverlay');
        }
        
        if (overlay && analysisSection) {
            // Ensure parent section is visible
            analysisSection.style.setProperty('display', 'block', 'important');
            analysisSection.style.setProperty('position', 'relative', 'important');
            
            // Force display with !important equivalent by setting style directly
            overlay.style.setProperty('display', 'flex', 'important');
            overlay.style.setProperty('z-index', '1000', 'important');
            overlay.style.setProperty('visibility', 'visible', 'important');
            overlay.style.setProperty('opacity', '1', 'important');
            overlay.style.setProperty('position', 'absolute', 'important');
            // Remove any inline style that might hide it
            overlay.removeAttribute('hidden');
            // Also remove the inline style="display: none" if present
            const currentStyle = overlay.getAttribute('style') || '';
            if (currentStyle.includes('display: none')) {
                overlay.setAttribute('style', currentStyle.replace(/display:\s*none[;]?/gi, ''));
            }
        }
    };
    
    // Show overlay immediately and also on next frame to ensure it's visible
    showOverlay();
    requestAnimationFrame(() => {
        showOverlay();
    });
    setTimeout(() => {
        showOverlay();
    }, 50);
    setTimeout(() => {
        showOverlay();
    }, 200);
    setTimeout(() => {
        showOverlay();
    }, 500);
    
    // Set a timeout to hide overlay after max 60 seconds (safety measure)
    const overlayTimeout = setTimeout(() => {
        const timeoutOverlay = document.getElementById('improvementsOverlay');
        if (timeoutOverlay) {
            timeoutOverlay.style.setProperty('display', 'none', 'important');
            timeoutOverlay.style.setProperty('visibility', 'hidden', 'important');
            timeoutOverlay.style.setProperty('opacity', '0', 'important');
            timeoutOverlay.setAttribute('hidden', '');
            console.log('[improvements] Overlay hidden by timeout (60s safety)');
        }
    }, 60000);
    
    try {
        // Get pain points and products data with current period filter
        // Build URL with product filter if active
        let painPointsUrl = `/api/pain-points?days=${currentPeriodDays}&limit=10`;
        if (currentProductFilter) {
            painPointsUrl += `&product=${encodeURIComponent(currentProductFilter)}`;
        }
        
        const dateFrom = getDateFrom(currentPeriodDays);
        const painPointsResponse = await fetch(painPointsUrl);
        const productsResponse = await fetch(`/api/product-opportunities?date_from=${dateFrom}`);
        
        if (!painPointsResponse.ok || !productsResponse.ok) {
            throw new Error('Failed to load data for analysis');
        }
        
        const painPointsData = await painPointsResponse.json();
        const productsData = await productsResponse.json();
        
        // Backend already filters pain points by product if currentProductFilter is set
        let filteredPainPoints = painPointsData.pain_points || [];
        let filteredProducts = productsData.products || [];
        
        if (currentProductFilter) {
            // Filter products to only show the selected one
            filteredProducts = productsData.products.filter(p => p.product === currentProductFilter);
        }
        
        // Get posts for analysis (filtered if product filter is active)
        const postsParams = new URLSearchParams({ limit: '1000', date_from: dateFrom });
        if (currentProductFilter) {
            postsParams.append('search', currentProductFilter);
        }
        const postsResponse = await fetch(`/api/posts-for-improvement?${postsParams.toString()}`);
        let postsData = { total: 0, posts: [] };
        if (postsResponse.ok) {
            postsData = await postsResponse.json();
            // If filtering by product, filter posts to only those matching the product
            if (currentProductFilter && postsData.posts) {
                const { getProductLabel } = await import('/dashboard/js/product-detection.js');
                const matchingPosts = postsData.posts.filter(post => {
                    const productLabel = getProductLabel(post.id, post.content, post.language);
                    return productLabel === currentProductFilter;
                });
                postsData.posts = matchingPosts;
                postsData.total = matchingPosts.length;
            }
        }
        
        // Get analysis focus from localStorage
        const analysisFocus = localStorage.getItem('analysisFocus') || '';
        
        // Get date_to (today)
        const dateTo = new Date().toISOString().split('T')[0];
        
        // Prepare request body
        const requestBody = {
            pain_points: filteredPainPoints,
            products: filteredProducts,
            total_posts: postsData.total || 0,
            posts: (postsData.posts || []).slice(0, 100), // Send up to 100 posts for analysis
            analysis_focus: analysisFocus,
            date_from: dateFrom,
            date_to: dateTo,
            product_filter: currentProductFilter || null
        };
        
        // Log request size for debugging
        const requestBodyStr = JSON.stringify(requestBody);
        const requestSizeKB = (new Blob([requestBodyStr]).size / 1024).toFixed(2);
        console.log(`[improvements] Request size: ${requestSizeKB} KB, Posts: ${requestBody.posts.length}`);
        
        // Call LLM analysis endpoint with posts and filters
        // Add timeout to prevent hanging requests
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutes timeout
        
        let analysisResponse;
        try {
            analysisResponse = await fetch('/api/improvements-analysis', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: requestBodyStr,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
        } catch (fetchError) {
            clearTimeout(timeoutId);
            if (fetchError.name === 'AbortError') {
                throw new Error('Request timeout: The analysis is taking too long. Please try again.');
            }
            throw new Error(`Network error: ${fetchError.message}. Please check if the server is running.`);
        }
        
        if (!analysisResponse.ok) {
            const errorText = await analysisResponse.text();
            let errorMessage = `Failed to generate analysis (${analysisResponse.status})`;
            try {
                const errorJson = JSON.parse(errorText);
                errorMessage = errorJson.detail || errorMessage;
            } catch (e) {
                // Si ce n'est pas du JSON, utiliser le texte brut
                errorMessage = errorText || analysisResponse.statusText || errorMessage;
            }
            throw new Error(errorMessage);
        }
        
        const analysis = await analysisResponse.json();
        console.log('[improvements] Analysis received, insights:', analysis.insights?.length || 0, 'llm_available:', analysis.llm_available);
        
        // Vérifier si l'analyse vient du LLM ou du fallback
        if (analysis.llm_available === false) {
            console.warn('[improvements] Analysis is using fallback (hardcoded data), not LLM');
            // Afficher un message d'avertissement
            if (insightsContainer) {
                insightsContainer.innerHTML = `
                    <div style="text-align: center; padding: 20px; background: rgba(245, 158, 11, 0.1); border-radius: 8px; border: 2px solid #f59e0b; margin-bottom: 20px;">
                        <h3 style="margin: 0 0 12px 0; color: #d97706;">⚠️ LLM Analysis Unavailable</h3>
                        <p style="margin: 0 0 16px 0; color: var(--text-secondary); line-height: 1.6;">
                            AI-powered analysis requires an API key. Please configure your OpenAI, Anthropic, or Mistral API key in <a href="/settings" style="color: var(--accent-primary); text-decoration: underline;">Settings</a> to enable intelligent insights based on your feedback analysis.
                        </p>
                        <p style="margin: 0; font-size: 0.9em; color: var(--text-muted);">
                            Without LLM, only basic statistics are available (not dynamic insights).
                        </p>
                    </div>
                `;
            }
            // Ne pas afficher les insights du fallback (données en dur)
            return;
        }
        
        // Store posts globally for drawer access
        window.currentImprovementsPosts = postsData.posts || [];
        window.currentImprovementsInsights = analysis.insights || [];
        
        // Display insights
        if (analysis.insights && analysis.insights.length > 0) {
            insightsContainer.innerHTML = analysis.insights.map((insight, index) => {
                // Use related_post_ids count as the source of truth
                const postsCount = insight.related_post_ids ? insight.related_post_ids.length : 0;
                const hasPosts = postsCount > 0;
                
                // Extract count from metric if it exists (for display purposes)
                let metricDisplay = insight.metric || '';
                // Only show metric if it's meaningful and provides additional context
                const metricCountMatch = metricDisplay.match(/(\d+)\s*posts?/i);
                const metricCount = metricCountMatch ? parseInt(metricCountMatch[1]) : null;
                // Don't show metric if:
                // 1. It's empty
                // 2. It's just a number without context (e.g., "7")
                // 3. It's just a post count that matches or is similar to postsCount (we already show "X related posts")
                const isJustNumber = /^\d+$/.test(metricDisplay.trim());
                const isPostCountOnly = /^\d+\s*posts?$/i.test(metricDisplay.trim());
                const shouldShowMetric = metricDisplay && metricDisplay.trim() !== '' && 
                                       !isJustNumber && // Not just a number
                                       !isPostCountOnly && // Not just "X posts" (we already show that)
                                       (metricCount === null || metricCount !== postsCount); // Different from actual count or not a post count
                
                return `
                <div class="insight-card" style="margin-bottom: 16px; padding: 16px; background: rgba(255, 255, 255, 0.5); border-radius: 8px; border-left: 4px solid var(--accent-primary);">
                    <div style="display: flex; align-items: start; gap: 12px;">
                        <span style="font-size: 1.5em;">${insight.icon || '💡'}</span>
                        <div style="flex: 1;">
                            <h3 style="margin: 0 0 8px 0; font-size: 1.1em; color: var(--text-primary);">${escapeHtml(insight.title)}</h3>
                            <p style="margin: 0 0 8px 0; color: var(--text-secondary); line-height: 1.6;">${escapeHtml(insight.description)}</p>
                            ${shouldShowMetric ? `<div style="margin-top: 8px; margin-bottom: 4px; font-weight: 600; color: var(--accent-primary); font-size: 0.95em;">${escapeHtml(metricDisplay)}</div>` : ''}
                            ${hasPosts ? `<div style="margin-top: ${shouldShowMetric ? '4' : '8'}px; margin-bottom: 8px; font-weight: 600; color: var(--accent-primary);">${postsCount} related posts</div>` : ''}
                            ${insight.roi_impact ? `<div style="margin-top: 8px; padding: 8px; background: rgba(245, 158, 11, 0.1); border-radius: 6px; color: #d97706; font-size: 0.9em;"><strong>Impact:</strong> ${escapeHtml(insight.roi_impact)}</div>` : ''}
                            ${hasPosts ? `<button onclick="openImprovementInsightDrawer(${index})" style="margin-top: 12px; padding: 8px 16px; background: var(--accent-primary); color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9em; font-weight: 500;">View ${postsCount} related posts →</button>` : ''}
                        </div>
                    </div>
                </div>
            `;
            }).join('');
        } else {
            insightsContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">No insights available at this time.</div>';
        }
        
        // Display ROI summary
        if (analysis.roi_summary) {
            roiContainer.innerHTML = `
                <h3 style="margin: 0 0 12px 0; color: #d97706; display: flex; align-items: center; gap: 8px;">
                    <span>💰</span>
                    <span>ROI & Customer Impact</span>
                </h3>
                <p style="margin: 0; color: var(--text-secondary); line-height: 1.7; font-size: 1.05em;">${escapeHtml(analysis.roi_summary)}</p>
            `;
        } else {
            roiContainer.innerHTML = '';
        }
        
        console.log('[improvements] Analysis display completed, hiding overlay...');
        
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
        // Refresh button is always visible - no need to show/hide it
        // Still show the section even if there's an error
        if (analysisSection) {
            analysisSection.style.display = 'block';
        }
    } finally {
        // Always hide overlay after analysis is complete, with a small delay for smooth transition
        clearTimeout(overlayTimeout);
        setTimeout(() => {
            const finalOverlay = document.getElementById('improvementsOverlay');
            if (finalOverlay) {
                // Use setProperty with important to override the display: flex !important
                finalOverlay.style.setProperty('display', 'none', 'important');
                finalOverlay.style.setProperty('visibility', 'hidden', 'important');
                finalOverlay.style.setProperty('opacity', '0', 'important');
                finalOverlay.setAttribute('hidden', '');
                console.log('[improvements] Overlay hidden after analysis');
            }
        }, 300);
    }
}

// Open drawer for improvement insight posts
window.openImprovementInsightDrawer = function(index) {
    if (!window.currentImprovementsInsights || !window.currentImprovementsInsights[index]) {
        console.error('[improvements] Insight not found at index:', index);
        return;
    }
    
    if (!window.currentImprovementsPosts || window.currentImprovementsPosts.length === 0) {
        console.error('[improvements] No posts available for drawer');
        return;
    }
    
    const insight = window.currentImprovementsInsights[index];
    const allPosts = window.currentImprovementsPosts;
    
    // Filter posts based on related_post_ids if available
    let filteredPosts = [];
    const expectedCount = insight.related_post_ids ? insight.related_post_ids.length : 0;
    
    if (insight.related_post_ids && insight.related_post_ids.length > 0) {
        filteredPosts = allPosts.filter(post => insight.related_post_ids.includes(post.id));
        
        // Log if there's a mismatch
        if (filteredPosts.length !== expectedCount) {
            console.warn(`[improvements] Count mismatch: Expected ${expectedCount} posts from related_post_ids, but found ${filteredPosts.length} in available posts`);
        }
    } else {
        // Fallback: try to match based on title/description keywords
        const searchText = (insight.title + ' ' + (insight.description || '')).toLowerCase();
        const searchKeywords = searchText.split(/\s+/).filter(k => k.length > 3);
        filteredPosts = allPosts.filter(post => {
            const content = (post.content || '').toLowerCase();
            return searchKeywords.some(keyword => content.includes(keyword));
        }).slice(0, 50); // Limit to 50 posts
    }
    
    // Sort by date (most recent first)
    filteredPosts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    // Use actual filtered count, not the expected count
    const actualCount = filteredPosts.length;
    
    console.log('[improvements] Opening drawer with', actualCount, 'posts (expected:', expectedCount, ') for insight:', insight.title);
    openImprovementInsightPostsDrawer(filteredPosts, insight.title, insight.description || '', {
        ...insight,
        actual_post_count: actualCount,
        expected_post_count: expectedCount
    });
};

// Open drawer for improvement insight posts
function openImprovementInsightPostsDrawer(posts, title, description, insight) {
    const drawer = document.getElementById('filteredPostsDrawer');
    if (!drawer) {
        console.error('[improvements] Drawer not found');
        return;
    }
    
    const drawerContent = document.getElementById('filteredPostsDrawerContent');
    if (!drawerContent) {
        console.error('[improvements] Drawer content not found');
        return;
    }
    
    // Calculate scrollbar width before hiding it
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.paddingRight = `${scrollbarWidth}px`;
    document.body.classList.add('drawer-open');
    drawer.classList.add('open');
    
    // Helper functions
    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function truncateText(text, maxLength) {
        if (!text) return 'No content';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
    
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
            'News': '📰',
            'GitHub': '🐙',
            'LinkedIn': '💼',
            'Stack Overflow': '💬',
            'Mastodon': '🐘',
            'Discord': '💬'
        };
        return icons[source] || '📝';
    }
    
    // Import getProductLabel dynamically
    let getProductLabel = null;
    (async () => {
        try {
            const productDetection = await import('/dashboard/js/product-detection.js');
            getProductLabel = productDetection.getProductLabel;
        } catch (e) {
            console.warn('[improvements] Could not load product-detection.js:', e);
        }
    })();
    
    // Build HTML
    let html = `
        <div class="drawer-header">
            <h3>${escapeHtml(title)}</h3>
            <button class="drawer-close" onclick="closeFilteredPostsDrawer()" aria-label="Close drawer">×</button>
        </div>
        <div class="drawer-info">
            <p style="margin: 0 0 16px 0; color: var(--text-secondary); line-height: 1.6;">${escapeHtml(description)}</p>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;">
                <div class="drawer-stats">
                    <span class="drawer-stat-value">${posts.length}</span>
                    <span class="drawer-stat-label">posts</span>
                    ${insight && insight.expected_post_count && insight.expected_post_count !== posts.length ? 
                        `<span class="drawer-stat-note" style="font-size: 0.85em; color: var(--text-muted); margin-left: 8px;">
                            (Backend estimated: ${insight.expected_post_count})
                        </span>` : ''}
                </div>
                <button onclick="createJiraTicketFromInsight('${escapeHtml(title)}', \`${escapeHtml(description)}\`, ${posts.length})" 
                        style="padding: 8px 16px; background: #0052CC; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9em; font-weight: 500; display: flex; align-items: center; gap: 6px;">
                    <span>🎫</span>
                    <span>Create Jira Ticket</span>
                </button>
            </div>
        </div>
        <div class="drawer-posts">
    `;
    
    if (posts.length === 0) {
        html += `
            <div class="drawer-empty">
                <p>No posts found matching this insight.</p>
            </div>
        `;
    } else {
        posts.forEach(post => {
            const sourceIcon = getSourceIcon(post.source);
            const timeAgo = getTimeAgo(post.created_at);
            const sentiment = post.sentiment_label || 'neutral';
            const category = getProductLabel ? getProductLabel(post.id, post.content, post.language) : null;
            
            html += `
                <div class="drawer-post-item">
                    <div class="drawer-post-header">
                        <div class="drawer-post-source">
                            <span class="drawer-source-icon">${sourceIcon}</span>
                            <span class="drawer-source-name">${escapeHtml(post.source || 'Unknown')}</span>
                            ${category && category !== 'General' ? `<span class="drawer-post-category" style="margin-left: 8px; padding: 3px 8px; background: rgba(0, 212, 255, 0.12); border-radius: 6px; color: var(--accent-primary); font-size: 0.75em; font-weight: 500; border: 1px solid rgba(0, 212, 255, 0.25);">📦 ${escapeHtml(category)}</span>` : ''}
                            <span class="drawer-post-time">${timeAgo}</span>
                        </div>
                        <span class="drawer-sentiment-badge sentiment-${sentiment}">${sentiment}</span>
                    </div>
                    <div class="drawer-post-content">${escapeHtml(truncateText(post.content || 'No content', 300))}</div>
                    <div class="drawer-post-meta">
                        ${category && category !== 'General' ? `<span class="drawer-post-category" style="padding: 4px 10px; background: rgba(0, 212, 255, 0.12); border-radius: 6px; color: var(--accent-primary); font-size: 0.8em; font-weight: 500; border: 1px solid rgba(0, 212, 255, 0.25);">📦 ${escapeHtml(category)}</span>` : '<span class="drawer-post-category" style="padding: 4px 10px; background: var(--bg-secondary, #f3f4f6); border-radius: 6px; color: var(--text-secondary, #6b7280); font-size: 0.8em;">General</span>'}
                        ${post.url ? `<a href="${post.url}" target="_blank" class="drawer-post-link">View post →</a>` : ''}
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

// Close drawer function
window.closeFilteredPostsDrawer = function() {
    const drawer = document.getElementById('filteredPostsDrawer');
    if (drawer) {
        drawer.classList.remove('open');
        document.body.classList.remove('drawer-open');
        document.body.style.paddingRight = '';
    }
    // Note: We don't trigger any analysis or refresh when closing the drawer
    // The drawer is just a view, closing it shouldn't affect the current state
};

// Refresh Improvements Analysis
window.refreshImprovementsAnalysis = async function() {
    const btn = document.getElementById('refreshImprovementsAnalysisBtn');
    if (btn) {
        btn.classList.add('refreshing');
        btn.disabled = true;
    }
    
    // Show overlay IMMEDIATELY when refresh is clicked
    const showOverlay = () => {
        const analysisSection = document.getElementById('improvementsAnalysis');
        const overlay = document.getElementById('improvementsOverlay');
        if (analysisSection && overlay) {
            // Show section first so overlay can be visible
            analysisSection.style.setProperty('display', 'block', 'important');
            analysisSection.style.setProperty('position', 'relative', 'important');
            // Show overlay
            overlay.style.setProperty('display', 'flex', 'important');
            overlay.style.setProperty('z-index', '1000', 'important');
            overlay.style.setProperty('visibility', 'visible', 'important');
            overlay.style.setProperty('opacity', '1', 'important');
            overlay.removeAttribute('hidden');
        }
    };
    showOverlay();
    requestAnimationFrame(() => showOverlay());
    setTimeout(() => showOverlay(), 50);
    
    try {
        await loadImprovementsAnalysis();
    } catch (error) {
        console.error('Error refreshing improvements analysis:', error);
    } finally {
        if (btn) {
            btn.classList.remove('refreshing');
            btn.disabled = false;
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
                <strong>Opportunity Score:</strong> <span style="${getScoreStyle(post.opportunity_score || 0)}; padding: 4px 10px; border-radius: 8px; display: inline-block; margin-left: 8px;">${(post.opportunity_score || 0).toFixed(1)}</span>
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
    
    // If pain point already has filtered posts (from product filter), use them directly
    // This ensures we show exactly the posts that match the product filter
    if (painPoint.posts && painPoint.posts.length > 0 && currentProductFilter) {
        // Use the already filtered posts from the pain point
        // These posts are already filtered by product AND keywords
        openPainPointDrawerContent(painPointTitle, painPoint.description, painPoint.posts, painPoint);
        return;
    }
    
    // Also check if we have posts_count but no posts array - in this case we need to reload
    // This handles the case where pain points were loaded without product filter initially
    if (painPoint.posts_count > 0 && (!painPoint.posts || painPoint.posts.length === 0) && currentProductFilter) {
        // We need to reload with product filter
        // Fall through to loadPainPointPosts
    }
    
    // Otherwise, load posts from API and filter
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
        
        // Import product detection function early
        const { getProductLabel } = await import('/dashboard/js/product-detection.js');
        
        // Build API URL with filters
        const params = new URLSearchParams({
            limit: '1000',
            offset: '0',
            date_from: dateFrom
        });
        
        // Fetch posts with date filter (don't use search filter, we'll filter by product label instead for accuracy)
        const response = await fetch(`/api/posts-for-improvement?${params.toString()}`);
        if (!response.ok) {
            throw new Error(`Failed to load posts: ${response.status}`);
        }
        
        const data = await response.json();
        let allPosts = data.posts || [];
        
        // If product filter is active, filter by product label FIRST (before keyword filtering)
        if (currentProductFilter) {
            allPosts = allPosts.filter(post => {
                const productLabel = getProductLabel(post.id, post.content, post.language);
                return productLabel === currentProductFilter;
            });
        }
        
        // Filter posts by sentiment first (only negative/neutral, matching backend logic)
        const sentimentFilteredPosts = allPosts.filter(post => {
            const sentiment = post.sentiment_label || 'neutral';
            return sentiment === 'negative' || sentiment === 'neutral';
        });
        
        // Then filter posts by keywords (case-insensitive)
        const filteredPosts = sentimentFilteredPosts.filter(post => {
            const content = (post.content || '').toLowerCase();
            return keywords.some(keyword => content.includes(keyword.toLowerCase()));
        });
        
        // Sort by opportunity score (descending)
        filteredPosts.sort((a, b) => (b.opportunity_score || 0) - (a.opportunity_score || 0));
        
        // Update pain point posts_count to match the actual filtered posts count
        if (painPoint) {
            painPoint.posts_count = filteredPosts.length;
            painPoint.posts = filteredPosts;
        }
        
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
            'Mastodon': '🐘',
            'G2 Crowd': '⭐',
            'Discord': '💬'
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
                <span class="drawer-stat-value">${painPoint && painPoint.posts_count !== undefined ? painPoint.posts_count : posts.length}</span>
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
                            ${post.opportunity_score ? `<span style="${getScoreStyle(post.opportunity_score)}; padding: 4px 10px; border-radius: 8px; font-size: 0.8em; display: inline-block;">Score: ${post.opportunity_score.toFixed(1)}</span>` : ''}
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

