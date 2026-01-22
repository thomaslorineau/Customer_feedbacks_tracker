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
                <span class="post-date">${formatDate(post.created_at)}</span>
            </div>
            <div class="post-body">
                <div class="post-author">${escapeHtml(post.author || 'Unknown')}</div>
                <div class="post-content">${escapeHtml(post.content || '')}</div>
            </div>
            <div class="post-footer">
                <div class="post-meta-badges">
                    <span class="sentiment ${getSentimentClass(post.sentiment_label)}" title="Sentiment Score: ${(post.sentiment_score || 0).toFixed(2)}">
                        ${post.sentiment_label === 'positive' ? '😊' : post.sentiment_label === 'negative' ? '😞' : '😐'} 
                        ${(post.sentiment_label || 'neutral').toUpperCase()} ${(post.sentiment_score || 0).toFixed(2)}
                    </span>
                    ${post.language && post.language !== 'unknown' ? `
                    <span class="language-badge" style="padding: 4px 10px; border-radius: 6px; font-size: 0.8em; font-weight: 600; background: rgba(139, 92, 246, 0.15); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.3);" title="Language: ${escapeHtml(post.language.toUpperCase())}">
                        🌐 ${escapeHtml(post.language.toUpperCase())}
                    </span>
                    ` : ''}
                    ${post.is_answered === 1 || post.is_answered === true ? `
                    <span class="answered-badge answered-yes" title="Post répondu${post.answered_by ? ' par ' + escapeHtml(post.answered_by) : ''}${post.answered_at ? ' le ' + escapeHtml(post.answered_at) : ''}">
                        ✓ Answered
                    </span>
                    ` : ''}
                    <span class="relevance-badge ${relevanceClass}" title="Score de pertinence : ${(relevanceScore * 100).toFixed(0)}% - Indique à quel point ce post est lié à OVH

Calculé à partir de :
• Marques OVH (40%) : OVH, OVHCloud, Kimsufi, etc.
• URLs OVH (30%) : Liens vers ovh.com, ovhcloud.com
• Direction OVH (20%) : Mentions de dirigeants OVH
• Produits OVH (10%) : VPS, hosting, domain, etc.

Les posts avec un score < 30% sont automatiquement filtrés.">
                        ${relevanceIcon} Relevance: ${(relevanceScore * 100).toFixed(0)}%
                    </span>
                </div>
                <div class="post-actions">
                    ${(() => {
                        const isAnswered = post.is_answered === 1 || post.is_answered === true;
                        // Toggle: if answered, clicking will set to false (not answered), and vice versa
                        const toggleValue = !isAnswered;
                        return isAnswered ? `
                    <button onclick="window.markPostAnswered && window.markPostAnswered(${post.id}, false)" class="post-action-btn btn-not-answered" title="Marquer comme non répondu">
                        <span class="btn-icon">✗</span>
                        <span class="btn-text">Not Answered</span>
                    </button>
                    ` : `
                    <button onclick="window.markPostAnswered && window.markPostAnswered(${post.id}, true)" class="post-action-btn btn-answered" title="Marquer comme répondu">
                        <span class="btn-icon">✓</span>
                        <span class="btn-text">Answered</span>
                    </button>
                    `;
                    })()}
                    <button onclick="${options.onPreviewClickName || 'openPostPreview'}(${post.id})" class="post-action-btn btn-preview">
                        <span class="btn-icon">👁️</span>
                        <span class="btn-text">Preview</span>
                    </button>
                    <a href="${escapeHtml(post.url || '#')}" target="_blank" class="post-action-btn btn-view">
                        <span class="btn-icon">🔗</span>
                        <span class="btn-text">View</span>
                    </a>
                    <button onclick="${options.onSaveClickName || 'addPostToBacklog'}(${post.id})" class="post-action-btn btn-save">
                        <span class="btn-icon">💾</span>
                        <span class="btn-text">Save</span>
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Make renderPostCard globally available
window.renderPostCard = renderPostCard;

