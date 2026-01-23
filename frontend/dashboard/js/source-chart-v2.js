/**
 * Posts by Source chart module
 * Displays distribution of posts by source (Reddit, Twitter, Trustpilot, etc.)
 * with click-to-filter functionality
 * 
 * Version: 2.2 - No API calls, uses state data only
 * File renamed to source-chart-v2.js to force browser cache refresh
 * Last updated: 2025-01-23
 */

let sourceChart = null;
let currentState = null;

/**
 * Initialize the source chart
 * IMPORTANT: This function NEVER makes API calls - it only uses state data
 * Version 2.2 - source-chart-v2.js - NO API CALLS EVER
 */
export function initSourceChart(state) {
    // CRITICAL: This is source-chart-v2.js - NO API CALLS
    // If you see this message, the new file is loaded correctly
    console.log('[source-chart-v2.js] Initializing - NO API calls will be made');
    
    // Ensure we never make API calls - only use state data
    if (!state) {
        return;
    }
    
    currentState = state;
    
    // Subscribe to state changes to update chart with filtered data
    state.subscribe((updatedState) => {
        currentState = updatedState;
        try {
            updateSourceChartFromState(updatedState);
        } catch (e) {
            // Silently ignore errors - chart will update when ready
        }
    });
    
    // Initial load from state (if posts are already loaded)
    // NEVER make API calls - only use state data
    if (state.posts && state.posts.length > 0) {
        try {
            updateSourceChartFromState(state);
        } catch (e) {
            // Silently ignore errors - chart will update when ready
        }
    } else {
        // Wait a bit for posts to load, then update from state
        // NO API CALLS - only wait for state to be populated
        setTimeout(() => {
            if (currentState && currentState.posts && currentState.posts.length > 0) {
                try {
                    updateSourceChartFromState(currentState);
                } catch (e) {
                    // Silently ignore errors - chart will update when ready
                }
            }
        }, 500);
    }
}

/**
 * Update chart from state (uses filtered posts)
 */
function updateSourceChartFromState(state) {
    if (!state) {
        console.warn('[source-chart-v2.js] No state provided to updateSourceChartFromState');
        return;
    }
    
    const posts = state.filteredPosts || state.posts || [];
    console.log(`[source-chart-v2.js] Updating chart with ${posts.length} posts`);
    
    if (posts.length === 0) {
        console.warn('[source-chart-v2.js] No posts available to render chart');
        return;
    }
    
    // Count posts by source
    const sourceData = {};
    const sentimentBySource = {};
    
    posts.forEach(post => {
        // Normalize GitHub sources: GitHub Issues and GitHub Discussions → GitHub
        // Normalize Mastodon sources: Mastodon (instance) → Mastodon
        let source = post.source || 'Unknown';
        if (source === 'GitHub Issues' || source === 'GitHub Discussions') {
            source = 'GitHub';
        } else if (source && source.startsWith('Mastodon (')) {
            source = 'Mastodon';
        }
        const sentiment = post.sentiment_label || 'neutral';
        
        if (!sourceData[source]) {
            sourceData[source] = 0;
            sentimentBySource[source] = { positive: 0, negative: 0, neutral: 0 };
        }
        
        sourceData[source]++;
        if (sentimentBySource[source][sentiment] !== undefined) {
            sentimentBySource[source][sentiment]++;
        }
    });
    
    console.log(`[source-chart-v2.js] Source data:`, sourceData);
    renderSourceChart(sourceData, sentimentBySource);
}

// REMOVED: loadAndRenderSourceChart() function completely removed
// This function was causing API calls in cached browser versions
// All functionality now uses updateSourceChartFromState() directly
// No API calls are ever made - all data comes from state

/**
 * Render the source chart using Chart.js
 */
function renderSourceChart(sourceData, sentimentBySource) {
    const canvas = document.getElementById('sourceChart');
    if (!canvas) {
        console.warn('[source-chart-v2.js] Canvas element "sourceChart" not found');
        return;
    }
    
    console.log(`[source-chart-v2.js] Rendering chart with ${Object.keys(sourceData).length} sources`);
    
    // Check canvas dimensions and visibility
    const rect = canvas.getBoundingClientRect();
    const computedStyle = window.getComputedStyle(canvas);
    console.log('[source-chart-v2.js] Canvas dimensions:', {
        width: canvas.width,
        height: canvas.height,
        clientWidth: canvas.clientWidth,
        clientHeight: canvas.clientHeight,
        boundingRect: { width: rect.width, height: rect.height },
        display: computedStyle.display,
        visibility: computedStyle.visibility,
        opacity: computedStyle.opacity,
        zIndex: computedStyle.zIndex
    });
    
    // Check if overlay is blocking and force hide it if visible
    const overlay = document.getElementById('whatsHappeningOverlay');
    if (overlay) {
        const overlayStyle = window.getComputedStyle(overlay);
        const isOverlayVisible = overlayStyle.display !== 'none' && overlayStyle.visibility !== 'hidden';
        console.log('[source-chart-v2.js] Overlay state:', {
            display: overlayStyle.display,
            visibility: overlayStyle.visibility,
            opacity: overlayStyle.opacity,
            zIndex: overlayStyle.zIndex,
            isVisible: isOverlayVisible
        });
        
        // Force hide overlay if it's blocking (should have been hidden by whats-happening.js)
        if (isOverlayVisible) {
            console.warn('[source-chart-v2.js] Overlay is still visible, forcing hide...');
            overlay.style.setProperty('display', 'none', 'important');
            overlay.style.setProperty('visibility', 'hidden', 'important');
            overlay.style.setProperty('opacity', '0', 'important');
            overlay.style.setProperty('z-index', '-1', 'important');
        }
    }
    
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart if it exists
    if (sourceChart) {
        sourceChart.destroy();
    }
    
    // Prepare data
    const sources = Object.keys(sourceData);
    const counts = Object.values(sourceData);
    
    // Sort by count (descending) and take top 8
    const sortedData = sources
        .map((source, index) => ({ source, count: counts[index] }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 8);
    
    const sortedSources = sortedData.map(d => d.source);
    const sortedCounts = sortedData.map(d => d.count);
    
    // Prepare sentiment data for stacked bars
    const positiveData = sortedSources.map(source => sentimentBySource[source]?.positive || 0);
    const negativeData = sortedSources.map(source => sentimentBySource[source]?.negative || 0);
    const neutralData = sortedSources.map(source => sentimentBySource[source]?.neutral || 0);
    
    // Colors for sources (distinct colors)
    const sourceColors = [
        '#3b82f6', // Blue
        '#10b981', // Green
        '#f59e0b', // Orange
        '#ef4444', // Red
        '#8b5cf6', // Purple
        '#ec4899', // Pink
        '#06b6d4', // Cyan
        '#84cc16', // Lime
    ];
    
    // Create chart
    try {
        console.log('[source-chart-v2.js] Creating Chart.js instance...');
        console.log('[source-chart-v2.js] Chart available?', typeof Chart !== 'undefined');
        sourceChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sortedSources,
            datasets: [
                {
                    label: 'Positive',
                    data: positiveData,
                    backgroundColor: '#34d399',
                    borderColor: '#10b981',
                    borderWidth: 1
                },
                {
                    label: 'Neutral',
                    data: neutralData,
                    backgroundColor: '#9ca3af',
                    borderColor: '#6b7280',
                    borderWidth: 1
                },
                {
                    label: 'Negative',
                    data: negativeData,
                    backgroundColor: '#ef4444',
                    borderColor: '#dc2626',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    bottom: 5,
                    top: 5,
                    left: 5,
                    right: 5
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 8,
                        font: {
                            size: 11
                        },
                        boxWidth: 12,
                        boxHeight: 12
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    titleFont: {
                        size: 13,
                        weight: 'bold'
                    },
                    bodyFont: {
                        size: 12
                    },
                    footerFont: {
                        size: 11,
                        style: 'italic'
                    },
                    padding: 12,
                    backgroundColor: 'rgba(0, 0, 0, 0.85)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    footerColor: '#e0e0e0',
                    callbacks: {
                        title: (tooltipItems) => {
                            if (tooltipItems.length > 0) {
                                return `Source: ${tooltipItems[0].label}`;
                            }
                            return 'Posts by Source';
                        },
                        label: (context) => {
                            const label = context.dataset.label || '';
                            const value = context.parsed.y || 0;
                            return `${label}: ${value} posts`;
                        },
                        footer: (tooltipItems) => {
                            if (tooltipItems.length > 0) {
                                const total = tooltipItems.reduce((sum, item) => sum + item.parsed.y, 0);
                                return `Total: ${total} posts | Hover to see breakdown by sentiment`;
                            }
                            return 'Hover over bars to see detailed sentiment breakdown';
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    categoryPercentage: 0.8,
                    barPercentage: 0.9,
                    ticks: {
                        font: {
                            size: 11,
                            weight: '600',
                            family: 'system-ui, -apple-system, sans-serif'
                        },
                        maxRotation: 0,
                        minRotation: 0,
                        color: 'var(--text-primary)',
                        padding: 4,
                        autoSkip: false
                    },
                    grid: {
                        display: false
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: {
                            size: 10,
                            family: 'system-ui, -apple-system, sans-serif'
                        },
                        padding: 5,
                        color: 'var(--text-secondary)'
                    },
                    grid: {
                        color: 'var(--border-color)',
                        lineWidth: 1,
                        drawBorder: false
                    }
                }
            },
            interaction: {
                mode: 'index',
                intersect: false
            },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const element = elements[0];
                    const index = element.index;
                    const source = sortedSources[index];
                    
                    // Toggle filter: if already filtered by this source, clear it
                    const currentSource = currentState?.filters?.source || '';
                    const newSource = currentSource === source ? '' : source;
                    
                    // Dispatch event to filter by source
                    const filterEvent = new CustomEvent('filterBySource', {
                        detail: { source: newSource }
                    });
                    window.dispatchEvent(filterEvent);
                }
            },
            onHover: (event, elements) => {
                const canvas = document.getElementById('sourceChart');
                if (canvas) {
                    canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                }
            }
        }
    });
    
    // Log after chart creation
    console.log('[source-chart-v2.js] Chart instance created:', {
        chartId: sourceChart?.id,
        dataPoints: sourceChart?.data?.datasets?.[0]?.data?.length || 0,
        labels: sourceChart?.data?.labels?.length || 0
    });
    
        // Log after chart creation
        console.log('[source-chart-v2.js] Chart instance created:', {
            chartId: sourceChart?.id,
            dataPoints: sourceChart?.data?.datasets?.[0]?.data?.length || 0,
            labels: sourceChart?.data?.labels?.length || 0
        });
        
        // Force chart update to ensure rendering
        if (sourceChart) {
            sourceChart.update();
            console.log('[source-chart-v2.js] Chart update() called');
        }
    } catch (error) {
        console.error('[source-chart-v2.js] Error creating chart:', error);
        console.error('[source-chart-v2.js] Error details:', error.message, error.stack);
    }
}

/**
 * Refresh the source chart
 * Uses state data directly - no API calls
 * IMPORTANT: This function NEVER makes API calls - it only uses state data
 */
export function refreshSourceChart() {
    // Silently refresh - no errors if state not ready
    // Directly use updateSourceChartFromState - NO API CALLS
    if (currentState) {
        try {
            updateSourceChartFromState(currentState);
        } catch (e) {
            // Silently ignore - chart will update via state subscription
        }
    }
}

