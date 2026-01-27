/**
 * Post Card Component - Shared component for rendering post cards
 * Used by both Dashboard and Data Collection pages
 */

/**
 * Render a post card HTML string
 * @param {Object} post - Post object with all properties
 * @param {Object} options - Options for rendering
 * @param {Function} options.getProductLabel - Function to get product label
 * @param {Function} options.calculateRelevanceScore - Function to calculate relevance score
 * @param {Function} options.getSourceClass - Function to get source CSS class
 * @param {Function} options.getSentimentClass - Function to get sentiment CSS class
 * @param {Function} options.formatDate - Function to format date
 * @param {Function} options.escapeHtml - Function to escape HTML
 * @param {Function} options.onPreviewClick - Callback for preview button click
 * @param {Function} options.onSaveClick - Callback for save button click
 * @param {Function} options.onEditProductLabel - Callback for edit product label
 * @returns {string} HTML string for the post card
 */
function renderPostCard(post, options = {}) {
    const {
        getProductLabel = (id, content, language) => null,
        calculateRelevanceScore = (post) => post.relevance_score || 0,
        getSourceClass = (source) => 'post-source',
        getSentimentClass = (label) => 'sentiment-neutral',
        formatDate = (date) => new Date(date).toLocaleDateString(),
        escapeHtml = (text) => {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },
        onPreviewClick = (id) => console.log('Preview', id),
        onSaveClick = (id) => console.log('Save', id),
        onEditProductLabel = (id, currentLabel) => console.log('Edit label', id, currentLabel)
    } = options;

    // Filter out sample data
    const isSample = post.url && (
        post.url.includes('/sample') || 
        post.url.includes('example.com') ||
        post.url.includes('/status/174') ||
        post.url === 'https://trustpilot.com/sample'
    );
    if (isSample) return '';

    const productLabel = getProductLabel(post.id, post.content, post.language);
    const relevanceScore = calculateRelevanceScore(post);
    
    // Filter out posts with relevance_score = 0
    if (relevanceScore === 0 || relevanceScore === null || relevanceScore === undefined) {
        return '';
    }
    
    const relevanceClass = relevanceScore >= 0.7 ? 'relevance-high' : relevanceScore >= 0.4 ? 'relevance-medium' : 'relevance-low';
    const relevanceIcon = relevanceScore >= 0.7 ? '✓' : relevanceScore >= 0.4 ? '~' : '?';

    return `
        <div class="post-card">
            <div class="post-card-header">
                <div class="post-header-left">
                    <span class="${getSourceClass(post.source)}">${escapeHtml(post.source || 'Unknown')}</span>
                    ${productLabel ? `
                        <span style="font-size:0.75em; background:linear-gradient(135deg, rgba(0,212,255,0.15) 0%, rgba(0,212,255,0.08) 100%); padding:5px 10px; border-radius:6px; display:inline-flex; align-items:center; gap:5px; border:1px solid rgba(0,212,255,0.3); color:var(--accent-primary); font-weight:500;">
                            📦 ${escapeHtml(productLabel)}
                            <button onclick="window.editProductLabel && window.editProductLabel(${post.id}, '${escapeHtml(productLabel).replace(/'/g, "\\'")}')" 
                                    style="background:none; border:none; color:var(--accent-primary); cursor:pointer; padding:0; margin:0; font-size:0.85em; opacity:0.7; line-height:1; transition: opacity 0.2s ease;"
                                    onmouseover="this.style.opacity='1'"
                                    onmouseout="this.style.opacity='0.7'"
                                    title="Edit product label">✏️</button>
                        </span>
                    ` : `
                        <button onclick="window.editProductLabel && window.editProductLabel(${post.id}, '')" 
                                style="font-size:0.75em; background:rgba(0,212,255,0.08); padding:5px 10px; border-radius:6px; border:1px dashed rgba(0,212,255,0.4); color:var(--accent-primary); cursor:pointer; font-weight:500; display:inline-flex; align-items:center; gap:4px; transition: all 0.2s ease;"
                                onmouseover="this.style.background='rgba(0,212,255,0.12)'; this.style.borderColor='rgba(0,212,255,0.5)'"
                                onmouseout="this.style.background='rgba(0,212,255,0.08)'; this.style.borderColor='rgba(0,212,255,0.4)'"
                                title="Add product label">+ Label</button>
                    `}
                </div>
                <div class="post-header-right">
                    <span class="post-date">${formatDate(post.created_at)}</span>
                    ${post.language && post.language !== 'unknown' ? `
                    <span class="language-badge-header" title="Language: ${escapeHtml(post.language.toUpperCase())}">
                        🌐 ${escapeHtml(post.language.toUpperCase())}
                    </span>
                    ` : ''}
                </div>
            </div>
            <div class="post-body">
                <div class="post-author">${escapeHtml(post.author || 'Unknown')}</div>
                <div class="post-content">${escapeHtml(post.content || '')}</div>
            </div>
            <div class="post-footer">
                <div class="footer-columns">
                    <!-- Column 1: Info -->
                    <div class="footer-col footer-info">
                        <div class="info-item">
                            <span class="info-icon ${getSentimentClass(post.sentiment_label)}">${post.sentiment_label === 'positive' ? '😊' : post.sentiment_label === 'negative' ? '😞' : '😐'}</span>
                            <span class="info-label">${(post.sentiment_label || 'neutral').charAt(0).toUpperCase() + (post.sentiment_label || 'neutral').slice(1)}</span>
                            <span class="info-value">${(post.sentiment_score || 0).toFixed(2)}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-icon ${relevanceClass}">${relevanceScore >= 0.7 ? '🟢' : relevanceScore >= 0.4 ? '🟡' : '🔴'}</span>
                            <span class="info-label">Relevance</span>
                            <span class="info-value">${(relevanceScore * 100).toFixed(0)}%</span>
                        </div>
                    </div>
                    
                    <!-- Column 2: Status -->
                    <div class="footer-col footer-status">
                        ${(() => {
                            const isAnswered = post.is_answered === 1 || post.is_answered === true;
                            return `
                        <button class="status-btn ${isAnswered ? 'status-active' : ''}" 
                                onclick="window.markPostAnswered && window.markPostAnswered(${post.id}, ${!isAnswered})">
                            ${isAnswered ? '✓' : '○'} ${isAnswered ? 'Answered' : 'Answer'}
                        </button>
                        `;
                        })()}
                        ${(() => {
                            const isFalsePositive = post.is_false_positive === true || post.is_false_positive === 1 || post.is_false_positive === '1';
                            return `
                        <button class="status-btn ${isFalsePositive ? 'status-warning' : ''}" 
                                onclick="window.markAsFalsePositive && window.markAsFalsePositive(${post.id}, ${!isFalsePositive})">
                            ✗ ${isFalsePositive ? 'False positive' : 'False positive'}
                        </button>
                        `;
                        })()}
                    </div>
                    
                    <!-- Column 3: Actions -->
                    <div class="footer-col footer-actions">
                        <button onclick="${options.onPreviewClickName || 'openPostPreview'}(${post.id})" class="action-btn" title="Preview">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                <circle cx="12" cy="12" r="3"/>
                            </svg>
                            Preview
                        </button>
                        <a href="${escapeHtml(post.url || '#')}" target="_blank" class="action-btn" title="View">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                                <polyline points="15 3 21 3 21 9"/>
                                <line x1="10" y1="14" x2="21" y2="3"/>
                            </svg>
                            View
                        </a>
                        <button onclick="${options.onSaveClickName || 'addPostToBacklog'}(${post.id})" class="action-btn action-primary" title="Save">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                                <polyline points="17 21 17 13 7 13 7 21"/>
                                <polyline points="7 3 7 8 15 8"/>
                            </svg>
                            Save
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Make renderPostCard globally available
window.renderPostCard = renderPostCard;

