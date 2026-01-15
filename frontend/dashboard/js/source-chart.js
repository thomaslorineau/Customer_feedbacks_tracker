/**
 * Posts by Source chart module
 * Displays distribution of posts by source (Reddit, Twitter, Trustpilot, etc.)
 * with click-to-filter functionality
 */

import { API } from './api.js';

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
    }
    
    // Initial load
    loadAndRenderSourceChart();
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
        const source = post.source || 'Unknown';
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
 * Load data and render the source chart
 */
async function loadAndRenderSourceChart() {
    try {
        const api = new API();
        const response = await fetch(`${api.baseURL}/api/posts-by-source`);
        if (!response.ok) {
            throw new Error(`Failed to fetch source data: ${response.statusText}`);
        }
        
        const data = await response.json();
        const sourceData = data.sources || {};
        const sentimentBySource = data.sentiment_by_source || {};
        
        renderSourceChart(sourceData, sentimentBySource);
        
    } catch (error) {
        console.error('Error loading source chart data:', error);
        const canvas = document.getElementById('sourceChart');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = 'var(--text-muted)';
            ctx.font = '14px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Unable to load data', canvas.width / 2, canvas.height / 2);
        }
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
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        footer: (tooltipItems) => {
                            const total = tooltipItems.reduce((sum, item) => sum + item.parsed.y, 0);
                            return `Total: ${total} posts`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    ticks: {
                        font: {
                            size: 11
                        },
                        maxRotation: 45,
                        minRotation: 0
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
                            size: 11
                        }
                    },
                    grid: {
                        color: 'var(--border-color)'
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

