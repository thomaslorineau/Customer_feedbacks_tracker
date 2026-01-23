/**
 * Posts by Source chart module
 * Displays distribution of posts by source (Reddit, Twitter, Trustpilot, etc.)
 * with click-to-filter functionality
 */

let sourceChart = null;
let currentState = null;

/**
 * Initialize the source chart
 */
export function initSourceChart(state) {
    currentState = state;
    
    // Subscribe to state changes to update chart with filtered data
    if (state) {
        state.subscribe((updatedState) => {
            currentState = updatedState;
            updateSourceChartFromState(updatedState);
        });
        
        // Initial load from state (if posts are already loaded)
        if (state.posts && state.posts.length > 0) {
            updateSourceChartFromState(state);
        } else {
            // Wait a bit for posts to load, then update from state
            setTimeout(() => {
                if (currentState && currentState.posts && currentState.posts.length > 0) {
                    updateSourceChartFromState(currentState);
                }
            }, 500);
        }
    }
}

/**
 * Update chart from state (uses filtered posts)
 */
function updateSourceChartFromState(state) {
    const posts = state.filteredPosts || state.posts || [];
    
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
    
    renderSourceChart(sourceData, sentimentBySource);
}

/**
 * Load data and render the source chart (deprecated - now uses state directly)
 * Kept for backward compatibility but should use updateSourceChartFromState instead
 * This function NO LONGER makes API calls - it only uses state data
 */
async function loadAndRenderSourceChart() {
    // This function is deprecated and should not be called directly
    // Use updateSourceChartFromState instead
    // No API calls are made - all data comes from state
    
    try {
        // Use state data directly instead of API call
        if (currentState && currentState.posts && currentState.posts.length > 0) {
            updateSourceChartFromState(currentState);
            return;
        }
        
        // If no state available, wait a bit and try again (state might be loading)
        setTimeout(() => {
            if (currentState && currentState.posts && currentState.posts.length > 0) {
                updateSourceChartFromState(currentState);
            } else {
                // Show empty state silently - no error message
                const canvas = document.getElementById('sourceChart');
                if (canvas) {
                    try {
                        const ctx = canvas.getContext('2d');
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        ctx.fillStyle = 'var(--text-muted)';
                        ctx.font = '14px sans-serif';
                        ctx.textAlign = 'center';
                        ctx.fillText('No data available', canvas.width / 2, canvas.height / 2);
                    } catch (e) {
                        // Silently ignore canvas errors
                    }
                }
            }
        }, 500);
    } catch (error) {
        // Silently handle all errors - chart will update when state is available
        // Do not log or throw errors to avoid console noise
    }
}

/**
 * Render the source chart using Chart.js
 */
function renderSourceChart(sourceData, sentimentBySource) {
    const canvas = document.getElementById('sourceChart');
    if (!canvas) {
        console.warn('Source chart canvas not found');
        return;
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
}

/**
 * Refresh the source chart
 */
export function refreshSourceChart() {
    loadAndRenderSourceChart();
}

