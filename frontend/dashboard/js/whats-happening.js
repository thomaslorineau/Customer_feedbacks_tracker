// What's Happening analysis module
import { getProductLabel } from './product-detection.js';
import { API } from './api.js';

export function updateWhatsHappening(state) {
    const posts = state.filteredPosts || [];
    const allPosts = state.posts || [];
    
    if (posts.length === 0) {
        document.getElementById('statsCards').innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">No data available</div>';
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
    
    // Top product impacted
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
    
    // Top issue (most common word in negative posts)
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
    
    // Update stats cards
    const statsCards = document.getElementById('statsCards');
    statsCards.innerHTML = `
        <div class="stat-card">
            <div class="stat-card-value">${total}</div>
            <div class="stat-card-label">Total Posts</div>
        </div>
        <div class="stat-card positive">
            <div class="stat-card-value">${positive}</div>
            <div class="stat-card-label">Positive</div>
        </div>
        <div class="stat-card negative">
            <div class="stat-card-value">${negative}</div>
            <div class="stat-card-label">Negative</div>
        </div>
        <div class="stat-card neutral">
            <div class="stat-card-value">${neutral}</div>
            <div class="stat-card-label">Neutral</div>
        </div>
        <div class="stat-card">
            <div class="stat-card-value">${recentPosts.length}</div>
            <div class="stat-card-label">Recent (48h)</div>
        </div>
    `;
    
    // Update content
    const content = document.getElementById('whatsHappeningContent');
    let contentHTML = '';
    
    if (spikeDetected && recentNegative > 0) {
        contentHTML += `
            <div class="alert-box">
                <div class="alert-box-icon">⚡</div>
                <div class="alert-box-content">
                    <h3>Spike in Negative Feedback Detected</h3>
                    <p>${spikePercentage > 0 ? `+${spikePercentage}%` : 'Significant'} more than average. ${recentNegative} negative posts in past 48h.</p>
                </div>
            </div>
        `;
    }
    
    if (topProduct) {
        contentHTML += `
            <div class="insight-box">
                <div class="insight-box-icon">🎁</div>
                <div class="insight-box-content">
                    <h4>Top Product Impacted: ${topProduct[0]}</h4>
                    <p>${topProductPercentage}% of negative posts are relating to ${topProduct[0]} issues.</p>
                </div>
            </div>
        `;
    }
    
    if (topIssue) {
        contentHTML += `
            <div class="insight-box">
                <div class="insight-box-icon">💬</div>
                <div class="insight-box-content">
                    <h4>Top Issue: "${topIssue[0].charAt(0).toUpperCase() + topIssue[0].slice(1)}"</h4>
                    <p>${topIssue[1]} posts mention issues related to ${topIssue[0]} requests.</p>
                </div>
            </div>
        `;
    }
    
    if (!contentHTML) {
        contentHTML = '<div style="text-align: center; color: var(--text-muted); padding: 20px;">No significant alerts at this time.</div>';
    }
    
    content.innerHTML = contentHTML;
    
    // Get active filters for context
    const activeFilters = getActiveFilters(state);
    
    // Update Recommended Actions with full context
    updateRecommendedActions(posts, recentPosts, recentNegative, spikeDetected, topProduct, topIssue, activeFilters);
}

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
                            <span class="action-hint">Configure your OpenAI or Anthropic API key in <a href="/dashboard/settings" style="color: var(--accent-primary); text-decoration: underline;">Settings</a> to enable intelligent recommendations based on your feedback analysis.</span>
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

