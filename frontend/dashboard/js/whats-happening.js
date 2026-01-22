// What's Happening analysis module
import { getProductLabel } from './product-detection.js';
// API will be imported dynamically when needed to avoid cache issues
import { updateDashboard } from './dashboard.js';

// Store state reference for click handlers
let currentState = null;

// Track if click handler has been attached to avoid duplicates
let statsCardsClickHandlerAttached = false;

export async function updateWhatsHappening(state) {
    // Store state reference for click handlers
    currentState = state;
    
    const posts = state.filteredPosts || [];
    const allPosts = state.posts || [];
    
    if (posts.length === 0) {
        // No posts available
        const statsCards = document.getElementById('statsCards');
        if (statsCards) {
            statsCards.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">No data available</div>';
        }
        document.getElementById('whatsHappeningContent').innerHTML = '';
        document.getElementById('recommendedActions').innerHTML = '';
        return;
    }
    
    // Calculate statistics based on filtered posts
    const total = posts.length;
    const positive = posts.filter(p => p.sentiment_label === 'positive').length;
    const negative = posts.filter(p => p.sentiment_label === 'negative').length;
    const neutral = posts.filter(p => p.sentiment_label === 'neutral' || !p.sentiment_label).length;
    
    // Calculate recent posts (last 48 hours) from filtered posts
    const now = new Date();
    const last48h = new Date(now.getTime() - 48 * 60 * 60 * 1000);
    const recentPosts = posts.filter(p => {
        const postDate = new Date(p.created_at);
        return postDate >= last48h;
    });
    const recentNegative = recentPosts.filter(p => p.sentiment_label === 'negative').length;
    
    // Calculate average negative posts per 48h (from filtered posts, last 7 days)
    // This makes the spike detection relative to the current filter context
    const last7days = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const filteredRecentPosts = posts.filter(p => {
        const postDate = new Date(p.created_at);
        return postDate >= last7days;
    });
    const avgNegativePer48h = filteredRecentPosts.length > 0 
        ? Math.round((filteredRecentPosts.filter(p => p.sentiment_label === 'negative').length / 7) * 2)
        : 0;
    
    // Detect spike
    const spikeDetected = avgNegativePer48h > 0 && recentNegative > avgNegativePer48h * 2.3; // 230% increase
    const spikePercentage = avgNegativePer48h > 0 ? Math.round(((recentNegative - avgNegativePer48h) / avgNegativePer48h) * 100) : 0;
    
    // Prepare stats for LLM analysis
    const statsForLLM = {
        total,
        positive,
        negative,
        neutral,
        recent_negative: recentNegative,
        recent_total: recentPosts.length,
        spike_detected: spikeDetected,
        spike_percentage: spikePercentage
    };
    
    // Get active filters description
    const activeFilters = getActiveFilters(state);
    const activeFiltersDescription = activeFilters.description || 'All posts (no filters)';
    
    // Call LLM API to generate insights
    let insights = [];
    let llmAvailable = false;
    try {
        // Try to use API class, but fallback to direct fetch if not available
        let apiInstance = null;
        try {
            const apiModule = await import(`./api.js?t=${Date.now()}`);
            const API = apiModule.API;
            apiInstance = new API();
            
            if (typeof apiInstance.getWhatsHappeningInsights === 'function') {
                const response = await apiInstance.getWhatsHappeningInsights(posts, statsForLLM, activeFiltersDescription);
                insights = response.insights || [];
                llmAvailable = response.llm_available !== false;
                console.log('LLM insights generated via API class:', insights);
            } else {
                throw new Error('Method not available in API class');
            }
        } catch (apiError) {
            // Fallback to direct fetch
            console.warn('API class not available, using direct fetch:', apiError);
            const baseURL = window.location.origin;
            const postsForAnalysis = posts.slice(0, 30).map(p => ({
                content: (p.content || '').substring(0, 400),
                sentiment: p.sentiment_label,
                source: p.source,
                created_at: p.created_at,
                language: p.language,
                product: p.product || null
            }));
            
            const response = await fetch(`${baseURL}/api/whats-happening`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    posts: postsForAnalysis,
                    stats: statsForLLM,
                    active_filters: activeFiltersDescription
                })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to get What's Happening insights: ${response.statusText}`);
            }
            
            const data = await response.json();
            insights = data.insights || [];
            llmAvailable = data.llm_available !== false;
            console.log('LLM insights generated via direct fetch:', insights);
        }
    } catch (error) {
        console.warn('Failed to get LLM insights, using fallback:', error);
        // Fallback to hardcoded logic if LLM fails
        const productCounts = {};
        posts.filter(p => p.sentiment_label === 'negative').forEach(post => {
            const product = getProductLabel(post.id, post.content, post.language);
            if (product) {
                productCounts[product] = (productCounts[product] || 0) + 1;
            }
        });
        const topProduct = Object.entries(productCounts)
            .sort((a, b) => b[1] - a[1])[0];
        const topProductPercentage = negative > 0 && topProduct 
            ? Math.round((topProduct[1] / negative) * 100) 
            : 0;
        
        const negativePosts = posts.filter(p => p.sentiment_label === 'negative');
        const wordCounts = {};
        negativePosts.forEach(post => {
            const words = (post.content || '').toLowerCase()
                .replace(/[^\w\s]/g, ' ')
                .split(/\s+/)
                .filter(w => w.length > 4);
            words.forEach(word => {
                if (!['ovh', 'ovhcloud', 'customer', 'service', 'support', 'issue', 'problem'].includes(word)) {
                    wordCounts[word] = (wordCounts[word] || 0) + 1;
                }
            });
        });
        const topIssue = Object.entries(wordCounts)
            .sort((a, b) => b[1] - a[1])[0];
        
        // Convert to insights format for consistency
        if (spikeDetected) {
            insights.push({
                type: 'spike',
                title: 'Spike in Negative Feedback Detected',
                description: `${spikePercentage > 0 ? `+${spikePercentage}%` : 'Significant'} more than average. ${recentNegative} negative posts in past 48h.`,
                icon: '⚠️',
                metric: spikePercentage > 0 ? `+${spikePercentage}%` : '',
                count: recentNegative
            });
        }
        if (topProduct) {
            insights.push({
                type: 'top_product',
                title: `Top Product Impacted: ${topProduct[0]}`,
                description: `${topProductPercentage}% of negative posts are relating to ${topProduct[0]} issues.`,
                icon: '🎁',
                metric: `${topProductPercentage}%`,
                count: topProduct[1]
            });
        }
        if (topIssue) {
            insights.push({
                type: 'top_issue',
                title: `Top Issue: "${topIssue[0].charAt(0).toUpperCase() + topIssue[0].slice(1)}"`,
                description: `${topIssue[1]} posts mention issues related to ${topIssue[0]} requests.`,
                icon: '💬',
                metric: '',
                count: topIssue[1]
            });
        }
    }
    
    // Update stats cards with click handlers
    const statsCards = document.getElementById('statsCards');
    if (!statsCards) {
        console.error('[Stats Cards] ❌ Container #statsCards not found!');
        console.error('[Stats Cards] Available elements:', document.querySelectorAll('[id*="stat"]'));
        return;
    }
    
    // Calculate answered stats from filtered posts (for display in filtered context)
    const answered = posts.filter(p => p.is_answered === 1 || p.is_answered === true).length;
    const notAnswered = posts.filter(p => !p.is_answered || p.is_answered === 0 || p.is_answered === false).length;
    const totalForAnswered = posts.length;
    const answeredPercentage = totalForAnswered > 0 ? ((answered / totalForAnswered) * 100).toFixed(0) : '0';
    
    // Calculate satisfaction (same logic as updatePositiveSatisfactionKPI)
    const satisfactionPositive = posts.filter(p => p.sentiment_label === 'positive').length;
    const satisfactionPercentage = total > 0 ? Math.round((satisfactionPositive / total) * 100) : 0;
    
    // Fetch global answered stats from API (for accurate global statistics)
    let globalAnsweredStats = null;
    try {
        const response = await fetch('/posts/stats/answered');
        if (response.ok) {
            globalAnsweredStats = await response.json();
            console.log('Global answered stats from API:', globalAnsweredStats);
        } else {
            console.warn('Failed to fetch global answered stats:', response.status, response.statusText);
        }
    } catch (e) {
        console.error('Could not fetch global answered stats from API:', e);
    }
    
    // Calculate percentages for sentiment cards
    const positivePercentage = total > 0 ? Math.round((positive / total) * 100) : 0;
    const negativePercentage = total > 0 ? Math.round((negative / total) * 100) : 0;
    const neutralPercentage = total > 0 ? Math.round((neutral / total) * 100) : 0;
    const recentPercentage = total > 0 ? Math.round((recentPosts.length / total) * 100) : 0;
    
    // Create stats cards with clickable-stat-card class (except Total Posts)
    const htmlContent = `
        <div class="stat-card" data-filter-type="all" title="Total posts">
            <div class="stat-card-icon" style="font-size: 1.5em; margin-bottom: 4px;">📊</div>
            <div class="stat-card-value" style="font-size: 1.8em; font-weight: 700;">${total}</div>
            <div class="stat-card-label">Total Posts</div>
            <div style="display: flex; gap: 8px; margin-top: 6px; font-size: 0.75em; justify-content: center; flex-wrap: wrap;">
                <span style="color: #10b981; font-weight: 600;">😊 ${positive}</span>
                <span style="color: #ef4444; font-weight: 600;">😞 ${negative}</span>
                <span style="color: #6b7280; font-weight: 600;">😐 ${neutral}</span>
            </div>
        </div>
        <div class="stat-card positive clickable-stat-card" data-filter-type="sentiment" data-filter-value="positive" title="Click to filter by positive sentiment">
            <div class="stat-card-icon" style="font-size: 1.5em; margin-bottom: 4px;">😊</div>
            <div class="stat-card-value" style="font-size: 1.8em; font-weight: 700; color: #10b981;">${positivePercentage}%</div>
            <div class="stat-card-label">Positive</div>
            <div style="display: flex; gap: 8px; margin-top: 6px; font-size: 0.75em; justify-content: center;">
                <span style="color: #10b981; font-weight: 600;">😊 ${positive}</span>
                <span style="color: var(--text-muted); font-weight: 600;">/ ${total}</span>
            </div>
        </div>
        <div class="stat-card negative clickable-stat-card" data-filter-type="sentiment" data-filter-value="negative" title="Click to filter by negative sentiment">
            <div class="stat-card-icon" style="font-size: 1.5em; margin-bottom: 4px;">😞</div>
            <div class="stat-card-value" style="font-size: 1.8em; font-weight: 700; color: #ef4444;">${negativePercentage}%</div>
            <div class="stat-card-label">Negative</div>
            <div style="display: flex; gap: 8px; margin-top: 6px; font-size: 0.75em; justify-content: center;">
                <span style="color: #ef4444; font-weight: 600;">😞 ${negative}</span>
                <span style="color: var(--text-muted); font-weight: 600;">/ ${total}</span>
            </div>
        </div>
        <div class="stat-card neutral clickable-stat-card" data-filter-type="sentiment" data-filter-value="neutral" title="Click to filter by neutral sentiment">
            <div class="stat-card-icon" style="font-size: 1.5em; margin-bottom: 4px;">😐</div>
            <div class="stat-card-value" style="font-size: 1.8em; font-weight: 700; color: #6b7280;">${neutralPercentage}%</div>
            <div class="stat-card-label">Neutral</div>
            <div style="display: flex; gap: 8px; margin-top: 6px; font-size: 0.75em; justify-content: center;">
                <span style="color: #6b7280; font-weight: 600;">😐 ${neutral}</span>
                <span style="color: var(--text-muted); font-weight: 600;">/ ${total}</span>
            </div>
        </div>
        <div class="stat-card clickable-stat-card" data-filter-type="recent" title="Click to filter posts from last 48 hours">
            <div class="stat-card-icon" style="font-size: 1.5em; margin-bottom: 4px;">⏰</div>
            <div class="stat-card-value" style="font-size: 1.8em; font-weight: 700; color: var(--accent-primary);">${recentPercentage}%</div>
            <div class="stat-card-label">Recent (48h)</div>
            <div style="display: flex; gap: 8px; margin-top: 6px; font-size: 0.75em; justify-content: center;">
                <span style="color: var(--accent-primary); font-weight: 600;">⏰ ${recentPosts.length}</span>
                <span style="color: var(--text-muted); font-weight: 600;">/ ${total}</span>
            </div>
        </div>
        <div class="stat-card answered-stats-card clickable-stat-card" data-filter-type="answered" data-filter-value="1" title="Click to filter by answered posts${globalAnsweredStats ? ` (Global: ${globalAnsweredStats.answered_percentage}%)` : ''}">
            <div class="stat-card-icon" style="font-size: 1.5em; margin-bottom: 4px;">💬</div>
            <div class="stat-card-value" style="font-size: 1.8em; font-weight: 700; color: var(--accent-primary);">${globalAnsweredStats ? globalAnsweredStats.answered_percentage : answeredPercentage}%</div>
            <div class="stat-card-label">Answered</div>
            <div style="display: flex; gap: 8px; margin-top: 6px; font-size: 0.75em; justify-content: center;">
                <span style="color: #10b981; font-weight: 600;">✓ ${globalAnsweredStats ? globalAnsweredStats.answered : answered}</span>
                <span style="color: #ef4444; font-weight: 600;">✗ ${globalAnsweredStats ? globalAnsweredStats.not_answered : notAnswered}</span>
            </div>
            ${globalAnsweredStats && totalForAnswered < globalAnsweredStats.total ? `
            <div style="font-size: 0.7em; color: var(--text-muted); margin-top: 4px; text-align: center;">
                (${totalForAnswered} filtered / ${globalAnsweredStats.total} total)
            </div>
            ` : ''}
        </div>
        <div class="stat-card positive clickable-stat-card" data-filter-type="sentiment" data-filter-value="positive" title="Click to filter by positive sentiment (satisfaction)">
            <div class="stat-card-icon" style="font-size: 1.5em; margin-bottom: 4px;">😊</div>
            <div class="stat-card-value" style="font-size: 1.8em; font-weight: 700; color: #10b981;">${satisfactionPercentage}%</div>
            <div class="stat-card-label">Satisfaction</div>
            <div style="display: flex; gap: 8px; margin-top: 6px; font-size: 0.75em; justify-content: center;">
                <span style="color: #10b981; font-weight: 600;">😊 ${satisfactionPositive}</span>
                <span style="color: #ef4444; font-weight: 600;">😞 ${negative}</span>
            </div>
        </div>
    `;
    
    statsCards.innerHTML = htmlContent;
    
    // Ensure clickable-stat-card class is applied (fallback in case HTML is modified by other code)
    // Skip index 0 (Total Posts) - it should not be clickable
    setTimeout(() => {
        const allStatCards = statsCards.querySelectorAll('.stat-card');
        allStatCards.forEach((card, index) => {
            // Skip Total Posts (index 0) - don't make it clickable
            if (index === 0) {
                // Ensure Total Posts is NOT clickable
                card.classList.remove('clickable-stat-card');
                if (!card.dataset.filterType) {
                    card.dataset.filterType = 'all';
                }
                return;
            }
            
            // Add clickable class to other cards if missing
            if (!card.classList.contains('clickable-stat-card')) {
                card.classList.add('clickable-stat-card');
            }
            
            // Add data attributes if missing
            if (index === 1 && !card.dataset.filterType) {
                card.dataset.filterType = 'sentiment';
                card.dataset.filterValue = 'positive';
            } else if (index === 2 && !card.dataset.filterType) {
                card.dataset.filterType = 'sentiment';
                card.dataset.filterValue = 'negative';
            } else if (index === 3 && !card.dataset.filterType) {
                card.dataset.filterType = 'sentiment';
                card.dataset.filterValue = 'neutral';
            } else if (index === 4 && !card.dataset.filterType) {
                card.dataset.filterType = 'recent';
            }
        });
    }, 100);
    
    // Add click handlers to stat cards using event delegation
    // Use event delegation on the parent container to avoid losing listeners when HTML is recreated
    // Only attach once to avoid duplicate listeners
    if (!statsCardsClickHandlerAttached) {
        statsCards.addEventListener('click', handleStatsCardClick);
        statsCardsClickHandlerAttached = true;
    }
    
    // Add cursor pointer style and ensure cards are interactive
    const clickableCards = statsCards.querySelectorAll('.clickable-stat-card');
    clickableCards.forEach((card) => {
        // Force cursor pointer via inline style
        card.style.cursor = 'pointer';
        card.style.userSelect = 'none';
        card.style.transition = 'all 0.2s ease';
        
        // Add hover effects
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-3px) scale(1.02)';
            card.style.boxShadow = '0 6px 16px rgba(0, 0, 0, 0.25)';
            card.style.borderColor = '#3b82f6';
            card.style.borderWidth = '2px';
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
            card.style.boxShadow = '';
            card.style.borderColor = '';
            card.style.borderWidth = '';
        });
    });
    
    
    // Update What's Happening content with LLM insights
    const content = document.getElementById('whatsHappeningContent');
    if (!content) return;
    
    let contentHTML = '';
    
    // Render insights from LLM (or fallback)
    if (insights && insights.length > 0) {
        insights.forEach(insight => {
            if (insight.type === 'spike') {
                contentHTML += `
                    <div class="alert-box">
                        <div class="alert-box-icon">${insight.icon || '⚠️'}</div>
                        <div class="alert-box-content">
                            <h3>${insight.title}</h3>
                            <p>${insight.description}</p>
                        </div>
                    </div>
                `;
            } else {
                contentHTML += `
                    <div class="insight-box">
                        <div class="insight-box-icon">${insight.icon || '📊'}</div>
                        <div class="insight-box-content">
                            <h4>${insight.title}</h4>
                            <p>${insight.description}</p>
                        </div>
                    </div>
                `;
            }
        });
    }
    
    if (!contentHTML) {
        contentHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">No significant alerts at this time.</div>';
    }
    
    content.innerHTML = contentHTML;
    
    // Update Recommended Actions with full context (using stats from LLM analysis)
    // Note: activeFilters was already declared earlier in the function
    const statsForActions = {
        ...statsForLLM,
        top_product: insights.find(i => i.type === 'top_product')?.title?.replace('Top Product Impacted: ', '') || 'N/A',
        top_product_count: insights.find(i => i.type === 'top_product')?.count || 0,
        top_product_percentage: parseInt(insights.find(i => i.type === 'top_product')?.metric?.replace('%', '') || '0'),
        top_issue: insights.find(i => i.type === 'top_issue')?.title?.replace('Top Issue: ', '').replace(/"/g, '') || 'N/A',
        top_issue_count: insights.find(i => i.type === 'top_issue')?.count || 0,
        active_filters: activeFilters.description,
        filtered_context: activeFilters.description !== 'All posts (no filters)',
        search_term: state.filters?.search || ''
    };
    // Extract top product and top issue from insights for Recommended Actions
    const topProductInsight = insights.find(i => i.type === 'top_product');
    const topIssueInsight = insights.find(i => i.type === 'top_issue');
    const topProduct = topProductInsight ? [topProductInsight.title.replace('Top Product Impacted: ', ''), topProductInsight.count] : null;
    const topIssue = topIssueInsight ? [topIssueInsight.title.replace('Top Issue: ', '').replace(/"/g, ''), topIssueInsight.count] : null;
    
    updateRecommendedActions(posts, recentPosts, recentNegative, spikeDetected, topProduct, topIssue, activeFilters);
}

// Separate function for the click handler
function handleStatsCardClick(e) {
    const card = e.target.closest('.clickable-stat-card');
    if (!card) {
        return;
    }
    
    // Use the stored state reference
    const state = currentState;
    if (!state) {
        return;
    }
    
    const filterType = card.dataset.filterType;
    const filterValue = card.dataset.filterValue;
    
    // Skip 'all' filter type - Total Posts should not trigger any action
    if (filterType === 'all') {
        return;
    }
    
    if (filterType === 'sentiment') {
        // Filter by sentiment
        const currentSentiment = state.filters?.sentiment || 'all';
        const newSentiment = currentSentiment === filterValue ? 'all' : filterValue;
        state.setFilter('sentiment', newSentiment);
        
        // Sync UI element
        const sentimentFilter = document.getElementById('sentimentFilter');
        if (sentimentFilter) sentimentFilter.value = newSentiment;
        
        // Update dashboard and open drawer
        updateDashboard();
        openFilteredPostsDrawer(state);
    } else if (filterType === 'answered') {
        // Filter by answered status
        const currentAnswered = state.filters?.answered || 'all';
        const newAnswered = currentAnswered === filterValue ? 'all' : filterValue;
        state.setFilter('answered', newAnswered);
        
        // Sync UI element
        const answeredFilter = document.getElementById('answeredFilter');
        if (answeredFilter) answeredFilter.value = newAnswered;
        
        // Update dashboard and open drawer
        updateDashboard();
        openFilteredPostsDrawer(state);
    } else if (filterType === 'recent') {
        // Filter by last 48 hours
        const currentNow = new Date();
        const dateFrom = new Date(currentNow.getTime() - 48 * 60 * 60 * 1000);
        const dateFromStr = dateFrom.toISOString().split('T')[0];
        const dateToStr = currentNow.toISOString().split('T')[0];
        
        // Check if already filtered by recent 48h
        const currentDateFrom = state.filters?.dateFrom || '';
        if (currentDateFrom === dateFromStr) {
            // Reset date filter
            state.setFilter('dateFrom', '');
            state.setFilter('dateTo', '');
            
            // Sync UI elements
            const globalDateFrom = document.getElementById('globalDateFrom');
            const globalDateTo = document.getElementById('globalDateTo');
            if (globalDateFrom) globalDateFrom.value = '';
            if (globalDateTo) globalDateTo.value = '';
        } else {
            state.setFilter('dateFrom', dateFromStr);
            state.setFilter('dateTo', dateToStr);
            
            // Sync UI elements
            const globalDateFrom = document.getElementById('globalDateFrom');
            const globalDateTo = document.getElementById('globalDateTo');
            if (globalDateFrom) globalDateFrom.value = dateFromStr;
            if (globalDateTo) globalDateTo.value = dateToStr;
        }
        
        // Update dashboard and open drawer
        updateDashboard();
        openFilteredPostsDrawer(state);
    }
}

// Drawer functions for filtered posts
function openFilteredPostsDrawer(state) {
    const drawer = document.getElementById('filteredPostsDrawer');
    if (!drawer) return;
    
    // Calculate scrollbar width before hiding it
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    
    // Prevent body scroll and compensate for scrollbar to prevent layout shift
    document.body.style.paddingRight = `${scrollbarWidth}px`;
    document.body.classList.add('drawer-open');
    
    drawer.classList.add('open');
    updateFilteredPostsDrawer(state);
}

function closeFilteredPostsDrawer() {
    const drawer = document.getElementById('filteredPostsDrawer');
    if (drawer) {
        drawer.classList.remove('open');
    }
    
    // Restore body scroll and remove padding
    document.body.classList.remove('drawer-open');
    document.body.style.paddingRight = '';
    
    // Clear filters when drawer is closed
    if (currentState) {
        // Reset sentiment filter
        currentState.setFilter('sentiment', 'all');
        
        // Reset date filters
        currentState.setFilter('dateFrom', '');
        currentState.setFilter('dateTo', '');
        
        // Sync UI elements
        const sentimentFilter = document.getElementById('sentimentFilter');
        if (sentimentFilter) sentimentFilter.value = 'all';
        
        const globalDateFrom = document.getElementById('globalDateFrom');
        const globalDateTo = document.getElementById('globalDateTo');
        if (globalDateFrom) globalDateFrom.value = '';
        if (globalDateTo) globalDateTo.value = '';
        
        // Update dashboard to reflect cleared filters
        updateDashboard();
    }
}

function updateFilteredPostsDrawer(state) {
    const drawerContent = document.getElementById('filteredPostsDrawerContent');
    if (!drawerContent || !state) return;
    
    const posts = state.filteredPosts || [];
    const totalPosts = state.posts?.length || 0;
    
    // Get active filters for display
    const activeFilters = [];
    if (state.filters?.sentiment && state.filters.sentiment !== 'all') {
        activeFilters.push(`Sentiment: ${state.filters.sentiment}`);
    }
    if (state.filters?.dateFrom) {
        activeFilters.push(`From: ${state.filters.dateFrom}`);
    }
    if (state.filters?.dateTo) {
        activeFilters.push(`To: ${state.filters.dateTo}`);
    }
    
    let html = `
        <div class="drawer-header">
            <h3>Filtered Posts</h3>
            <button class="drawer-close" onclick="closeFilteredPostsDrawer()" aria-label="Close drawer">×</button>
        </div>
        <div class="drawer-info">
            <div class="drawer-stats">
                <span class="drawer-stat-value">${posts.length}</span>
                <span class="drawer-stat-label">of ${totalPosts} posts</span>
            </div>
            ${activeFilters.length > 0 ? `
                <div class="drawer-filters">
                    ${activeFilters.map(f => `<span class="filter-tag">${f}</span>`).join('')}
                </div>
            ` : ''}
        </div>
        <div class="drawer-posts">
    `;
    
    if (posts.length === 0) {
        html += `
            <div class="drawer-empty">
                <p>No posts match the current filters.</p>
            </div>
        `;
    } else {
        // Show first 50 posts
        const postsToShow = posts.slice(0, 50);
        postsToShow.forEach(post => {
            const timeAgo = getTimeAgo(post.created_at);
            const sourceIcon = getSourceIcon(post.source);
            const sentiment = post.sentiment_label || 'neutral';
            const category = getProductLabel(post.id, post.content, post.language) || 'General';
            
            html += `
                <div class="drawer-post-item">
                    <div class="drawer-post-header">
                        <div class="drawer-post-source">
                            <span class="drawer-source-icon">${sourceIcon}</span>
                            <span class="drawer-source-name">${post.source || 'Unknown'}</span>
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
        
        if (posts.length > 50) {
            html += `
                <div class="drawer-more">
                    <p>Showing 50 of ${posts.length} posts</p>
                </div>
            `;
        }
    }
    
    html += `</div>`;
    drawerContent.innerHTML = html;
}

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
        'twitter': '🐦',
        'x': '🐦',
        'reddit': '🔴',
        'github': '💻',
        'stackoverflow': '📚',
        'trustpilot': '⭐',
        'default': '📝'
    };
    return icons[source?.toLowerCase()] || icons.default;
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make closeFilteredPostsDrawer available globally
window.closeFilteredPostsDrawer = closeFilteredPostsDrawer;

function getActiveFilters(state) {
    const filters = {
        search: state.filters?.search || '',
        sentiment: state.filters?.sentiment || 'all',
        language: state.filters?.language || 'all',
        product: state.filters?.product || 'all',
        dateFrom: state.filters?.dateFrom || null,
        dateTo: state.filters?.dateTo || null,
        source: state.filters?.source || 'all'
    };
    
    // Build filter description
    const activeFilterList = [];
    if (filters.search) activeFilterList.push(`Search: "${filters.search}"`);
    if (filters.sentiment !== 'all') activeFilterList.push(`Sentiment: ${filters.sentiment}`);
    if (filters.language !== 'all') activeFilterList.push(`Language: ${filters.language}`);
    if (filters.product !== 'all') activeFilterList.push(`Product: ${filters.product}`);
    if (filters.dateFrom) activeFilterList.push(`From: ${filters.dateFrom}`);
    if (filters.dateTo) activeFilterList.push(`To: ${filters.dateTo}`);
    if (filters.source !== 'all') activeFilterList.push(`Source: ${filters.source}`);
    
    return {
        ...filters,
        description: activeFilterList.length > 0 ? activeFilterList.join(', ') : 'All posts (no filters)'
    };
}

async function updateRecommendedActions(posts, recentPosts, recentNegative, spikeDetected, topProduct, topIssue, activeFilters) {
    const actionsContainer = document.getElementById('recommendedActions');
    if (!actionsContainer) {
        console.warn('[Recommended Actions] Container not found');
        return;
    }
    
    console.log('[Recommended Actions] Updating with', posts.length, 'posts, recent:', recentPosts.length);
    
    // Show loading state
    actionsContainer.innerHTML = `
        <div class="recommended-actions-header">
            <h3>Recommended Actions</h3>
        </div>
        <div class="recommended-actions-list">
            <div class="action-item" style="opacity: 0.6;">
                <span class="action-icon">⏳</span>
                <span class="action-text">Analyzing ${posts.length} posts...</span>
            </div>
        </div>
    `;
    
    try {
        // Prepare comprehensive stats for LLM
        const stats = {
            total: posts.length,
            positive: posts.filter(p => p.sentiment_label === 'positive').length,
            negative: posts.filter(p => p.sentiment_label === 'negative').length,
            neutral: posts.filter(p => p.sentiment_label === 'neutral' || !p.sentiment_label).length,
            recent_negative: recentNegative,
            recent_total: recentPosts.length,
            spike_detected: spikeDetected,
            top_product: topProduct ? topProduct[0] : 'N/A',
            top_product_count: topProduct ? topProduct[1] : 0,
            top_issue: topIssue ? topIssue[0] : 'N/A',
            top_issue_count: topIssue ? topIssue[1] : 0,
            active_filters: activeFilters.description,
            filtered_context: activeFilters.description !== 'All posts (no filters)',
            search_term: activeFilters.search || ''  // Include search term explicitly
        };
        
        // Call LLM API with full context
        // Import API dynamically to ensure it's loaded
        const { API } = await import('./api.js');
        const api = new API();
        const response = await api.getRecommendedActions(posts, recentPosts, stats, 5);
        const actions = response.actions || [];
        const llmAvailable = response.llm_available !== false; // Default to true if not specified
        
        // Render actions
        if (actions.length > 0) {
            actionsContainer.innerHTML = `
                <div class="recommended-actions-header">
                    <h3>Recommended Actions</h3>
                </div>
                <div class="recommended-actions-list">
                    ${actions.map(action => `
                        <div class="action-item action-${action.priority}">
                            <span class="action-icon">${action.icon}</span>
                            <span class="action-text">${action.text}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        } else if (!llmAvailable) {
            // No LLM API key configured - show nice message
            actionsContainer.innerHTML = `
                <div class="recommended-actions-header">
                    <h3>Recommended Actions</h3>
                </div>
                <div class="recommended-actions-list">
                    <div class="action-item action-no-llm">
                        <span class="action-icon">🤖</span>
                        <div class="action-text-container">
                            <span class="action-text">AI-powered recommendations require an API key</span>
                            <span class="action-hint">Configure your OpenAI or Anthropic API key in <a href="/settings" style="color: var(--accent-primary); text-decoration: underline;">Settings</a> to enable intelligent recommendations based on your feedback analysis.</span>
                        </div>
                    </div>
                </div>
            `;
        } else {
            // LLM available but no actions generated - show a message
            console.warn('[Recommended Actions] LLM available but no actions generated');
            actionsContainer.innerHTML = `
                <div class="recommended-actions-header">
                    <h3>Recommended Actions</h3>
                </div>
                <div class="recommended-actions-list">
                    <div class="action-item" style="opacity: 0.7;">
                        <span class="action-icon">💡</span>
                        <span class="action-text">No specific recommendations at this time. Try adjusting your filters or search terms.</span>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error generating recommended actions:', error);
        // Show error state
        actionsContainer.innerHTML = `
            <div class="recommended-actions-header">
                <h3>Recommended Actions</h3>
            </div>
            <div class="recommended-actions-list">
                <div class="action-item" style="opacity: 0.6;">
                    <span class="action-icon">⚠️</span>
                    <span class="action-text">Unable to generate recommendations. Please try again later.</span>
                </div>
            </div>
        `;
    }
}
