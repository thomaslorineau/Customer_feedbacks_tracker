// Product detection logic (from v1)
export function detectOVHProduct(postContent) {
    if (!postContent) return null;
    
    const content = postContent.toLowerCase();
    
    // Product patterns with priority order (more specific first)
    const productPatterns = [
        // Web & Hosting
        { key: 'domain', pattern: /\b(domain|domaine|dns|zone|registrar|nameserver)\w*/i, label: 'Domain' },
        { key: 'wordpress', pattern: /\b(wordpress|wp\s*host)\w*/i, label: 'WordPress' },
        { key: 'email', pattern: /\b(email|exchange|mail|mx|zimbra|smtp|imap)\w*/i, label: 'Email' },
        { key: 'web-hosting', pattern: /\b(web\s*host|hosting|hébergement|mutualisé|shared\s*host)\w*/i, label: 'Hosting' },
        
        // Cloud & Servers
        { key: 'vps', pattern: /\b(vps|virtual\s*private\s*server)\w*/i, label: 'VPS' },
        { key: 'dedicated', pattern: /\b(dedicated|dédié|bare\s*metal|server\s*dedicated)\w*/i, label: 'Dedicated' },
        { key: 'public-cloud', pattern: /\b(public\s*cloud|openstack|instance|compute)\w*/i, label: 'Public Cloud' },
        { key: 'private-cloud', pattern: /\b(private\s*cloud|vmware)\w*/i, label: 'Private Cloud' },
        
        // Storage & Backup
        { key: 'object-storage', pattern: /\b(object\s*storage|swift|s3|storage)\w*/i, label: 'Storage' },
        { key: 'backup', pattern: /\b(backup|veeam|archive)\w*/i, label: 'Backup' },
        
        // Network & CDN
        { key: 'cdn', pattern: /\b(cdn|content\s*delivery)\w*/i, label: 'CDN' },
        { key: 'load-balancer', pattern: /\b(load\s*balancer|iplb)\w*/i, label: 'Load Balancer' },
        { key: 'ddos', pattern: /\b(ddos|anti-ddos|protection)\w*/i, label: 'DDoS Protection' },
        
        // Support & Billing (lower priority)
        { key: 'billing', pattern: /\b(billing|facture|invoice|payment|paiement|refund|rembours)\w*/i, label: 'Billing' },
        { key: 'manager', pattern: /\b(manager|control\s*panel|espace\s*client)\w*/i, label: 'Manager' },
        { key: 'api', pattern: /\b(api|sdk|integration)\w*/i, label: 'API' },
        { key: 'support', pattern: /\b(support|ticket|assistance|help|service\s*client)\w*/i, label: 'Support' },
    ];
    
    // Check patterns in order (first match wins)
    for (const product of productPatterns) {
        if (product.pattern.test(content)) {
            return product.label;
        }
    }
    
    return null;
}

// Store for manually edited product labels (post_id -> label)
function saveProductLabel(postId, label) {
    const labels = loadProductLabels();
    if (label && label.trim()) {
        labels[postId] = label.trim();
    } else {
        delete labels[postId]; // Remove if empty
    }
    localStorage.setItem('ovh_product_labels', JSON.stringify(labels));
}

function loadProductLabels() {
    const saved = localStorage.getItem('ovh_product_labels');
    return saved ? JSON.parse(saved) : {};
}

export function getProductLabel(postId, postContent, postLanguage) {
    // First check if there's a manually edited label
    const editedLabels = loadProductLabels();
    if (editedLabels[postId]) {
        return editedLabels[postId];
    }
    
    // Otherwise detect automatically
    const detectedProduct = detectOVHProduct(postContent);
    if (detectedProduct) {
        return detectedProduct;
    }
    
    // Fallback to language if not unknown
    if (postLanguage && postLanguage !== 'unknown') {
        return postLanguage.toUpperCase();
    }
    
    return null;
}

export function editProductLabel(postId, currentLabel) {
    const newLabel = prompt(`Edit product label for post #${postId}:\n\nCurrent: ${currentLabel || '(none)'}\n\nEnter new label (or leave empty to remove):`, currentLabel || '');
    
    if (newLabel !== null) { // User didn't cancel
        saveProductLabel(postId, newLabel);
        // Trigger a refresh of the posts display
        if (typeof window.updatePostsDisplay === 'function') {
            window.updatePostsDisplay();
        }
        // Show a simple notification (you can replace with a toast system if available)
        alert('Product label updated');
    }
}

// Expose to window for onclick handlers
window.editProductLabel = editProductLabel;

