// Product detection logic (from v1)
export function detectOVHProduct(postContent) {
    if (!postContent) return null;
    
    const content = postContent.toLowerCase();
    
    // Product patterns with priority order (more specific first)
    const productPatterns = [
        // Web & Hosting
        { key: 'domain', pattern: /\b(domain|domaine|dns|zone|registrar|nameserver|\.ovh|\.com|\.net|\.org)\b/i, label: 'Domain' },
        { key: 'wordpress', pattern: /\b(wordpress|wp\s*host|wp\s*config)\b/i, label: 'WordPress' },
        { key: 'email', pattern: /\b(email|exchange|mail|mx\s*record|zimbra|smtp|imap|pop3|mailbox)\b/i, label: 'Email' },
        { key: 'web-hosting', pattern: /\b(web\s*host|hosting|hébergement|mutualisé|shared\s*host|web\s*server)\b/i, label: 'Hosting' },
        
        // Cloud & Servers
        { key: 'vps', pattern: /\b(vps|virtual\s*private\s*server|kimsufi)\b/i, label: 'VPS' },
        { key: 'dedicated', pattern: /\b(dedicated|dédié|bare\s*metal|server\s*dedicated|serveur\s*dédié)\b/i, label: 'Dedicated' },
        { key: 'public-cloud', pattern: /\b(public\s*cloud|openstack|instance|compute|ovhcloud|ovh\s*cloud)\b/i, label: 'Public Cloud' },
        { key: 'private-cloud', pattern: /\b(private\s*cloud|vmware|vsphere)\b/i, label: 'Private Cloud' },
        { key: 'kubernetes', pattern: /\b(kubernetes|k8s|managed\s*k8s|container|pod|deployment)\b/i, label: 'Kubernetes' },
        
        // Storage & Backup
        { key: 'object-storage', pattern: /\b(object\s*storage|swift|s3|storage|cloud\s*storage|object\s*store)\b/i, label: 'Storage' },
        { key: 'backup', pattern: /\b(backup|veeam|archive|snapshot|restore)\b/i, label: 'Backup' },
        
        // Network & CDN
        { key: 'cdn', pattern: /\b(cdn|content\s*delivery|cache)\b/i, label: 'CDN' },
        { key: 'load-balancer', pattern: /\b(load\s*balancer|iplb|lb|balancing)\b/i, label: 'Load Balancer' },
        { key: 'ddos', pattern: /\b(ddos|anti-ddos|protection|mitigation)\b/i, label: 'DDoS Protection' },
        { key: 'network', pattern: /\b(network|vrack|vlan|ip\s*address|subnet)\b/i, label: 'Network' },
        
        // Support & Billing (lower priority)
        { key: 'billing', pattern: /\b(billing|facture|invoice|payment|paiement|refund|rembours|subscription)\b/i, label: 'Billing' },
        { key: 'manager', pattern: /\b(manager|control\s*panel|espace\s*client|ovh\s*manager|panel)\b/i, label: 'Manager' },
        { key: 'api', pattern: /\b(api|sdk|integration|rest\s*api|webhook)\b/i, label: 'API' },
        { key: 'support', pattern: /\b(support|ticket|assistance|help|service\s*client|customer\s*service)\b/i, label: 'Support' },
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
    const labels = saved ? JSON.parse(saved) : {};
    
    // Clean up any language codes that were mistakenly saved as product labels
    const languageCodes = ['FR', 'EN', 'ES', 'DE', 'IT', 'PT', 'NL', 'PL', 'RU', 'ZH', 'JA', 'KO', 'AR', 'HI', 'TR', 'SV', 'DA', 'FI', 'NO', 'CS', 'HU', 'RO', 'BG', 'HR', 'SK', 'SL', 'ET', 'LV', 'LT', 'MT', 'EL', 'UK', 'BE', 'GA', 'CY', 'LU', 'UNKNOWN', 'fr', 'en', 'es', 'de', 'it', 'pt', 'nl', 'pl', 'ru', 'zh', 'ja', 'ko', 'ar', 'hi', 'tr', 'sv', 'da', 'fi', 'no', 'cs', 'hu', 'ro', 'bg', 'hr', 'sk', 'sl', 'et', 'lv', 'lt', 'mt', 'el', 'uk', 'be', 'ga', 'cy', 'lu', 'unknown'];
    let cleaned = false;
    
    for (const postId in labels) {
        const label = labels[postId];
        if (languageCodes.includes(label.toUpperCase()) || languageCodes.includes(label.toLowerCase())) {
            delete labels[postId];
            cleaned = true;
        }
    }
    
    // Save cleaned labels if any were removed
    if (cleaned) {
        localStorage.setItem('ovh_product_labels', JSON.stringify(labels));
    }
    
    return labels;
}

export function getProductLabel(postId, postContent, postLanguage) {
    // List of language codes to exclude (they are NOT products)
    const languageCodes = ['FR', 'EN', 'ES', 'DE', 'IT', 'PT', 'NL', 'PL', 'RU', 'ZH', 'JA', 'KO', 'AR', 'HI', 'TR', 'SV', 'DA', 'FI', 'NO', 'CS', 'HU', 'RO', 'BG', 'HR', 'SK', 'SL', 'ET', 'LV', 'LT', 'MT', 'EL', 'UK', 'BE', 'GA', 'CY', 'LU', 'UNKNOWN', 'fr', 'en', 'es', 'de', 'it', 'pt', 'nl', 'pl', 'ru', 'zh', 'ja', 'ko', 'ar', 'hi', 'tr', 'sv', 'da', 'fi', 'no', 'cs', 'hu', 'ro', 'bg', 'hr', 'sk', 'sl', 'et', 'lv', 'lt', 'mt', 'el', 'uk', 'be', 'ga', 'cy', 'lu', 'unknown'];
    
    // First check if there's a manually edited label
    const editedLabels = loadProductLabels();
    if (editedLabels[postId]) {
        const label = editedLabels[postId];
        // Filter out language codes even if manually set
        if (languageCodes.includes(label.toUpperCase()) || languageCodes.includes(label.toLowerCase())) {
            return null;
        }
        return label;
    }
    
    // Otherwise detect automatically
    const detectedProduct = detectOVHProduct(postContent);
    if (detectedProduct) {
        // Double-check that detected product is not a language code
        if (languageCodes.includes(detectedProduct.toUpperCase()) || languageCodes.includes(detectedProduct.toLowerCase())) {
            return null;
        }
        return detectedProduct;
    }
    
    // No fallback - return null if no product detected
    // (Language should not be used as product label per user request)
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

