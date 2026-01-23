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
        console.warn('[source-chart-v2.js] No state provided to initSourceChart');
        return;
    }
    
    currentState = state;
    console.log('[source-chart-v2.js] State received:', {
        hasPosts: !!state.posts,
        postsCount: state.posts?.length || 0,
        hasFilteredPosts: !!state.filteredPosts,
        filteredPostsCount: state.filteredPosts?.length || 0
    });
    
    // Subscribe to state changes to update chart with filtered data
    state.subscribe((updatedState) => {
        console.log('[source-chart-v2.js] State updated via subscription:', {
            postsCount: updatedState.posts?.length || 0,
            filteredPostsCount: updatedState.filteredPosts?.length || 0
        });
        currentState = updatedState;
        try {
            updateSourceChartFromState(updatedState);
        } catch (e) {
            console.error('[source-chart-v2.js] Error updating chart from subscription:', e);
        }
    });
    
    // Initial load from state (if posts are already loaded)
    // NEVER make API calls - only use state data
    const posts = state.filteredPosts || state.posts || [];
    if (posts.length > 0) {
        console.log(`[source-chart-v2.js] Posts already available (${posts.length}), updating chart immediately`);
        try {
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => {
                    setTimeout(() => updateSourceChartFromState(state), 100);
                });
            } else {
                setTimeout(() => updateSourceChartFromState(state), 100);
            }
        } catch (e) {
            console.error('[source-chart-v2.js] Error updating chart on init:', e);
        }
    } else {
        console.log('[source-chart-v2.js] No posts yet, waiting for state update...');
        // Wait a bit for posts to load, then update from state
        // NO API CALLS - only wait for state to be populated
        // Try multiple times with increasing delays
        const tryUpdate = (attempt = 1) => {
            const maxAttempts = 10;
            const delay = attempt * 200; // 200ms, 400ms, 600ms, etc.
            
            setTimeout(() => {
                const currentPosts = currentState?.filteredPosts || currentState?.posts || [];
                if (currentPosts.length > 0) {
                    console.log(`[source-chart-v2.js] Posts loaded after ${delay}ms (${currentPosts.length} posts), updating chart`);
                    try {
                        updateSourceChartFromState(currentState);
                    } catch (e) {
                        console.error('[source-chart-v2.js] Error updating chart after wait:', e);
                    }
                } else if (attempt < maxAttempts) {
                    console.log(`[source-chart-v2.js] Attempt ${attempt}/${maxAttempts}: Still no posts, retrying...`);
                    tryUpdate(attempt + 1);
                } else {
                    console.warn('[source-chart-v2.js] Max attempts reached, no posts found');
                }
            }, delay);
        };
        
        tryUpdate();
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
    console.log(`[source-chart-v2.js] Updating chart with ${posts.length} posts (filtered: ${state.filteredPosts?.length || 0}, total: ${state.posts?.length || 0})`);
    
    if (posts.length === 0) {
        console.warn('[source-chart-v2.js] No posts available to render chart. State:', {
            hasPosts: !!state.posts,
            postsCount: state.posts?.length || 0,
            hasFilteredPosts: !!state.filteredPosts,
            filteredPostsCount: state.filteredPosts?.length || 0
        });
        // Don't return - try to render empty chart or wait
        // Maybe data is still loading, so we'll retry via subscription
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
    
    // Check if overlay is blocking - but DON'T force hide if LLM analysis is in progress
    const overlay = document.getElementById('whatsHappeningOverlay');
    if (overlay) {
        const overlayStyle = window.getComputedStyle(overlay);
        const isOverlayVisible = overlayStyle.display !== 'none' && overlayStyle.visibility !== 'hidden';
        
        if (isOverlayVisible) {
            // Check if LLM analysis is in progress by looking for "Analyzing with AI..." text
            const overlayText = overlay.textContent || '';
            const isAnalyzing = overlayText.includes('Analyzing') || overlayText.includes('AI');
            
            // Also check if content is empty (analysis just started)
            const content = document.getElementById('whatsHappeningContent');
            const hasContent = content && content.innerHTML.trim() !== '';
            
            if (isAnalyzing || !hasContent) {
                // LLM analysis is in progress - don't hide overlay
                console.log('[source-chart-v2.js] Overlay visible but LLM analysis in progress, keeping it visible');
                // Set a timeout to detect if overlay is stuck (loop detection)
                if (!overlay.dataset.chartHideTimeout) {
                    overlay.dataset.chartHideTimeout = 'set';
                    setTimeout(() => {
                        const stillVisible = window.getComputedStyle(overlay).display !== 'none';
                        const stillAnalyzing = overlay.textContent.includes('Analyzing');
                        if (stillVisible && stillAnalyzing) {
                            console.error('[source-chart-v2.js] ERROR: Overlay stuck in analyzing state for >5s - possible loop!');
                        }
                    }, 5000);
                }
            } else {
                // Analysis should be complete but overlay is still visible - this might be an error
                console.warn('[source-chart-v2.js] Overlay visible but analysis appears complete - checking if this is an error...');
                // Don't force hide - let whats-happening.js handle it
                // Only log a warning if it's been visible for a while
            }
        }
    }
    
    // Destroy existing chart if it exists
    if (sourceChart) {
        sourceChart.destroy();
        sourceChart = null;
    }
    
    // Wait for next frame to ensure DOM is fully rendered
    // This is critical for Chart.js to calculate dimensions correctly
    requestAnimationFrame(() => {
        // Re-get canvas in case DOM changed
        const canvasElement = document.getElementById('sourceChart');
        if (!canvasElement) {
            console.warn('[source-chart-v2.js] Canvas not found in requestAnimationFrame');
            return;
        }
        
        // Get container dimensions for Chart.js
        const container = canvasElement.parentElement;
        if (!container) {
            console.warn('[source-chart-v2.js] Container not found');
            return;
        }
        
        // Ensure container is visible
        const containerStyle = window.getComputedStyle(container);
        if (containerStyle.display === 'none' || containerStyle.visibility === 'hidden') {
            console.warn('[source-chart-v2.js] Container is hidden, making visible...');
            container.style.display = 'flex';
            container.style.visibility = 'visible';
        }
        
        // Chart.js will handle dimensions with responsive: true
        // We just need to ensure the container has dimensions
        const containerRect = container.getBoundingClientRect();
        if (containerRect.width === 0 || containerRect.height === 0) {
            console.warn('[source-chart-v2.js] Container has zero dimensions, retrying...');
            setTimeout(() => renderSourceChart(sourceData, sentimentBySource), 100);
            return;
        }
        
        console.log('[source-chart-v2.js] Container dimensions:', {
            width: containerRect.width,
            height: containerRect.height,
            display: containerStyle.display,
            visibility: containerStyle.visibility
        });
        
        // Ensure canvas is visible and has proper dimensions
        canvasElement.style.display = 'block';
        canvasElement.style.visibility = 'visible';
        canvasElement.style.opacity = '1';
        // Remove any inline styles that might interfere
        canvasElement.style.width = '';
        canvasElement.style.height = '';
        
        const ctx = canvasElement.getContext('2d');
        if (!ctx) {
            console.error('[source-chart-v2.js] Failed to get 2D context');
            return;
        }
        
        // Ensure overlay is hidden BEFORE creating chart
        if (overlay) {
            overlay.style.setProperty('display', 'none', 'important');
            overlay.style.setProperty('visibility', 'hidden', 'important');
            overlay.style.setProperty('opacity', '0', 'important');
            overlay.style.setProperty('z-index', '-1', 'important');
            overlay.setAttribute('hidden', '');
            console.log('[source-chart-v2.js] Overlay forcefully hidden before chart creation');
        }
        
        // Don't set explicit width/height on canvas - let Chart.js handle it with responsive: true
        // Chart.js will use the container dimensions automatically
        console.log('[source-chart-v2.js] Canvas ready for Chart.js, container:', {
            width: containerRect.width,
            height: containerRect.height,
            canvasStyle: {
                display: canvasElement.style.display,
                width: canvasElement.style.width,
                height: canvasElement.style.height
            }
        });
        
        // Small delay to ensure overlay is fully hidden and DOM is stable
        setTimeout(() => {
            createChartInstance(ctx, canvasElement, sourceData, sentimentBySource);
        }, 50);
    });
}

// Separate function to create chart instance
function createChartInstance(ctx, canvas, sourceData, sentimentBySource) {
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
        console.log('[source-chart-v2.js] Chart data:', {
            labels: sortedSources,
            positiveData: positiveData,
            negativeData: negativeData,
            neutralData: neutralData,
            hasPositiveValues: positiveData.some(v => v > 0),
            hasNegativeValues: negativeData.some(v => v > 0),
            hasNeutralValues: neutralData.some(v => v > 0)
        });
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
            maintainAspectRatio: false, // Let container control height
            animation: {
                duration: 0 // Disable animation for immediate rendering
            },
            devicePixelRatio: window.devicePixelRatio || 1, // Handle high DPI displays
            animation: {
                duration: 0 // Disable animation for immediate rendering
            },
            devicePixelRatio: window.devicePixelRatio || 1, // Handle high DPI displays
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
    
    // Force chart update to ensure rendering
    if (sourceChart) {
        // Use 'active' mode to ensure full rendering
        sourceChart.update('active');
        console.log('[source-chart-v2.js] Chart update() called');
        
        // Force canvas to be visible and ensure proper rendering
        setTimeout(() => {
            if (canvas) {
                canvas.style.display = 'block';
                canvas.style.visibility = 'visible';
                canvas.style.opacity = '1';
                
                // Force a resize to ensure Chart.js recalculates dimensions
                if (sourceChart && sourceChart.resize) {
                    sourceChart.resize();
                    console.log('[source-chart-v2.js] Chart resize() called');
                }
                
                // Force another update after resize
                sourceChart.update('active');
                
                // Log final canvas state
                const finalRect = canvas.getBoundingClientRect();
                const finalStyle = window.getComputedStyle(canvas);
                const chartData = sourceChart?.data;
                console.log('[source-chart-v2.js] Final canvas state:', {
                    width: canvas.width,
                    height: canvas.height,
                    clientWidth: canvas.clientWidth,
                    clientHeight: canvas.clientHeight,
                    boundingRect: { width: finalRect.width, height: finalRect.height },
                    display: finalStyle.display,
                    visibility: finalStyle.visibility,
                    opacity: finalStyle.opacity,
                    chartVisible: sourceChart && !sourceChart.destroyed,
                    chartData: chartData ? {
                        labels: chartData.labels || [],
                        datasetsCount: chartData.datasets?.length || 0,
                        datasets: chartData.datasets?.map(ds => ({
                            label: ds.label,
                            data: ds.data || [],
                            dataLength: ds.data?.length || 0
                        })) || []
                    } : null
                });
                
                // Check if chart actually has data to render
                if (chartData && chartData.datasets && chartData.datasets.length > 0) {
                    const hasData = chartData.datasets.some(ds => ds.data && ds.data.length > 0 && ds.data.some(v => v > 0));
                    console.log('[source-chart-v2.js] Chart has data to render:', hasData);
                    
                    if (!hasData) {
                        console.warn('[source-chart-v2.js] Chart has no data values > 0, chart will be empty');
                    }
                }
                
                // Force one more update with animation to ensure rendering
                if (sourceChart && !sourceChart.destroyed) {
                    // Try to force a full re-render by destroying and recreating if needed
                    const ctx = canvas.getContext('2d');
                    if (ctx) {
                        // Clear canvas first
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        // Then update chart
                        sourceChart.update('active');
                        console.log('[source-chart-v2.js] Final update() called with active mode after clear');
                    }
                }
            }
        }, 200);
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

