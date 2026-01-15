/**
 * Sentiment Distribution chart module
 * Displays global sentiment distribution with click-to-filter functionality
 */

import { API } from './api.js';

let sentimentChart = null;

/**
 * Initialize the sentiment chart
 */
export function initSentimentChart(state) {
    // Subscribe to state changes to update chart
    if (state) {
        state.subscribe((updatedState) => {
            updateSentimentChart(updatedState);
        });
    }
    
    // Initial load
    if (state && state.posts) {
        updateSentimentChart(state);
    }
}

/**
 * Update the sentiment chart based on current state
 */
function updateSentimentChart(state) {
    const canvas = document.getElementById('sentimentChart');
    if (!canvas) {
        console.warn('Sentiment chart canvas not found');
        return;
    }
    
    const posts = state.filteredPosts || state.posts || [];
    
    // Count sentiments
    const sentimentCounts = {
        positive: 0,
        negative: 0,
        neutral: 0
    };
    
    posts.forEach(post => {
        const sentiment = post.sentiment_label || 'neutral';
        if (sentimentCounts.hasOwnProperty(sentiment)) {
            sentimentCounts[sentiment]++;
        } else {
            sentimentCounts.neutral++;
        }
    });
    
    renderSentimentChart(sentimentCounts, state);
}

/**
 * Render the sentiment chart using Chart.js
 */
function renderSentimentChart(sentimentCounts, state) {
    const canvas = document.getElementById('sentimentChart');
    if (!canvas) {
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart if it exists
    if (sentimentChart) {
        sentimentChart.destroy();
    }
    
    const total = sentimentCounts.positive + sentimentCounts.negative + sentimentCounts.neutral;
    
    // Prepare data
    const labels = ['Positive', 'Neutral', 'Negative'];
    const data = [
        sentimentCounts.positive,
        sentimentCounts.neutral,
        sentimentCounts.negative
    ];
    
    const colors = ['#34d399', '#9ca3af', '#ef4444']; // Green, Gray, Red
    const hoverColors = ['#10b981', '#6b7280', '#dc2626'];
    
    // Create donut chart
    sentimentChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: '#ffffff',
                borderWidth: 2,
                hoverBackgroundColor: hoverColors,
                hoverBorderColor: '#ffffff',
                hoverBorderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            },
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const element = elements[0];
                    const index = element.index;
                    const sentiment = ['positive', 'neutral', 'negative'][index];
                    
                    // Toggle filter: if already filtered by this sentiment, clear it
                    const currentSentiment = state?.filters?.sentiment || 'all';
                    const newSentiment = currentSentiment === sentiment ? 'all' : sentiment;
                    
                    // Dispatch event to update filter
                    const filterEvent = new CustomEvent('filterBySentiment', {
                        detail: { sentiment: newSentiment }
                    });
                    window.dispatchEvent(filterEvent);
                }
            },
            onHover: (event, elements) => {
                canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default';
            }
        }
    });
}

/**
 * Refresh the sentiment chart
 */
export function refreshSentimentChart(state) {
    if (state) {
        updateSentimentChart(state);
    }
}

