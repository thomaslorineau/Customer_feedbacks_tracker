// Improvements Opportunities App

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
    
    if (isDark) {
        body.classList.remove('dark-mode');
        localStorage.setItem('theme', 'light');
    } else {
        body.classList.add('dark-mode');
        localStorage.setItem('theme', 'dark');
    }
    
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
async function loadVersion() {
    try {
        const response = await fetch('/api/version');
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
        const response = await fetch('/api/improvements-summary');
        if (response.ok) {
            const data = await response.json();
            const summaryEl = document.getElementById('improvementsSummary');
            if (summaryEl && data.summary) {
                summaryEl.textContent = data.summary;
            } else if (summaryEl) {
                summaryEl.textContent = "💡 Improvement opportunities based on customer feedback";
            }
        } else {
            console.error('Failed to load improvements summary:', response.status, response.statusText);
            const summaryEl = document.getElementById('improvementsSummary');
            if (summaryEl) {
                summaryEl.textContent = "💡 Improvement opportunities based on customer feedback";
            }
        }
    } catch (error) {
        console.error('Error loading improvements summary:', error);
        const summaryEl = document.getElementById('improvementsSummary');
        if (summaryEl) {
            summaryEl.textContent = "💡 Improvement opportunities based on customer feedback";
        }
    }
}

// Load pain points
async function loadPainPoints() {
    try {
        console.log('Loading pain points...');
        const response = await fetch('/api/pain-points?days=30&limit=5');
        console.log('Pain points response status:', response.status);
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Pain points error response:', errorText);
            throw new Error(`Failed to load pain points: ${response.status} ${errorText}`);
        }
        const data = await response.json();
        console.log('Pain points data:', data);
        
        const painPointsList = document.getElementById('painPointsList');
        if (!painPointsList) {
            console.error('painPointsList element not found');
            return;
        }
        
        if (!data.pain_points || data.pain_points.length === 0) {
            painPointsList.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">No pain points found in the last 30 days.</div>';
            return;
        }
        
        painPointsList.innerHTML = data.pain_points.map(pp => `
            <div class="pain-point-item">
                <div class="pain-point-icon">${pp.icon}</div>
                <div class="pain-point-content">
                    <div class="pain-point-title">${escapeHtml(pp.title)}</div>
                    <div class="pain-point-description">${escapeHtml(pp.description)}</div>
                    <div class="pain-point-posts">${pp.posts_count} posts</div>
                </div>
            </div>
        `).join('');
        
        // Show "View All" link if there are more pain points
        const viewAllLink = document.getElementById('viewAllPainPoints');
        if (viewAllLink && data.total_pain_points > 5) {
            viewAllLink.style.display = 'inline-block';
            viewAllLink.textContent = `View All ${data.total_pain_points} Pain Points >`;
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
        const response = await fetch('/api/product-opportunities');
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
            
            return `
                <div class="product-item">
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
                        return `
                            <div class="product-item">
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

async function loadPostsForImprovement(resetOffset = false) {
    if (resetOffset) {
        currentOffset = 0;
    }
    
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
        
        if (search) params.append('search', search);
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
        
        const postsList = document.getElementById('postsToReviewList');
        const resultsCount = document.getElementById('resultsCount');
        
        if (resultsCount) {
            resultsCount.textContent = data.total;
        }
        
        if (!postsList) return;
        
        if (resetOffset) {
            postsList.innerHTML = '';
        }
        
        if (data.posts.length === 0 && currentOffset === 0) {
            postsList.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">No posts found matching the filters.</div>';
            return;
        }
        
        const postsHtml = data.posts.map(post => {
            const sourceIcon = getSourceIcon(post.source);
            const timeAgo = getTimeAgo(post.created_at);
            const views = post.views || 0;
            const comments = post.comments || 0;
            const reactions = post.reactions || 0;
            const isRecent = isPostRecent(post.created_at);
            const isNegative = post.sentiment_label === 'negative';
            
            return `
                <div class="post-review-item">
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
                    <button class="post-action-btn" onclick="createImprovementTicket(${post.id})">
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
        
        // Add load more button if there are more posts
        if (currentOffset + postsPerPage < data.total) {
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

// Setup event listeners
function setupEventListeners() {
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
    
    // Load all data with error handling
    try {
        console.log('Loading data...');
        await Promise.all([
            loadImprovementsSummary(),
            loadPainPoints(),
            loadProductDistribution(),
            loadPostsForImprovement(true)
        ]);
        console.log('All data loaded successfully');
    } catch (error) {
        console.error('Error during initialization:', error);
    }
}

// Make functions available globally
window.createImprovementTicket = createImprovementTicket;

function toggleHelpMenu() {
    const menu = document.getElementById('helpMenu');
    if (menu) {
        menu.classList.toggle('active');
    }
}

window.toggleHelpMenu = toggleHelpMenu;

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

