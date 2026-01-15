// Charts management for dashboard
import { State } from './state.js';
import { getProductLabel } from './product-detection.js';

let timelineChart = null;
let currentTimelineData = null; // Store current timeline data for onClick handler

export function initCharts(state) {
    state.subscribe((updatedState) => {
        updateTimelineChart(updatedState);
    });
}

export function updateTimelineChart(state) {
    const canvas = document.getElementById('timelineChart');
    if (!canvas) return;
    
    const posts = state.filteredPosts || [];
    
    // Group posts by date
    const grouped = {};
    posts.forEach(post => {
        const date = new Date(post.created_at);
        const key = date.toISOString().split('T')[0];
        if (!grouped[key]) {
            grouped[key] = { positive: 0, negative: 0, neutral: 0 };
        }
        grouped[key][post.sentiment_label || 'neutral']++;
    });
    
    // Sort by date
    const sortedKeys = Object.keys(grouped).sort();
    
    if (sortedKeys.length === 0) {
        // Show empty state
        if (timelineChart) {
            timelineChart.destroy();
            timelineChart = null;
        }
        return;
    }
    
    // Prepare data
    const labels = sortedKeys.map(key => {
        const date = new Date(key);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    const positiveData = sortedKeys.map(key => grouped[key].positive);
    const negativeData = sortedKeys.map(key => grouped[key].negative);
    const neutralData = sortedKeys.map(key => grouped[key].neutral);
    
    // Destroy existing chart first to prevent display issues
    if (timelineChart) {
        timelineChart.destroy();
        timelineChart = null;
    }
    
    // Store timeline data for onClick handler
    currentTimelineData = {
        sortedKeys: sortedKeys,
        grouped: grouped,
        posts: posts
    };
    
    // Wait a bit to ensure canvas is ready
    setTimeout(() => {
        // Create new chart
        timelineChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Positive',
                    data: positiveData,
                    backgroundColor: 'rgba(52, 211, 153, 0.7)',
                    borderColor: 'rgba(52, 211, 153, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Neutral',
                    data: neutralData,
                    backgroundColor: 'rgba(107, 114, 128, 0.7)',
                    borderColor: 'rgba(107, 114, 128, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Negative',
                    data: negativeData,
                    backgroundColor: 'rgba(239, 68, 68, 0.7)',
                    borderColor: 'rgba(239, 68, 68, 1)',
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
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        afterLabel: (context) => {
                            // Show product breakdown in tooltip
                            if (currentTimelineData) {
                                const index = context.dataIndex;
                                const dateKey = currentTimelineData.sortedKeys[index];
                                const datePosts = currentTimelineData.posts.filter(p => {
                                    const postDate = new Date(p.created_at).toISOString().split('T')[0];
                                    return postDate === dateKey;
                                });
                                
                                // Group by product
                                const productCounts = {};
                                datePosts.forEach(post => {
                                    const product = getProductLabel(post.id, post.content, post.language) || 'General';
                                    productCounts[product] = (productCounts[product] || 0) + 1;
                                });
                                
                                const topProducts = Object.entries(productCounts)
                                    .sort((a, b) => b[1] - a[1])
                                    .slice(0, 3)
                                    .map(([product, count]) => `${product}: ${count}`)
                                    .join(', ');
                                
                                return topProducts ? `Products: ${topProducts}` : '';
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        autoSkip: true,
                        maxTicksLimit: 20,
                        padding: 10
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        precision: 0
                    }
                }
            },
            layout: {
                padding: {
                    bottom: 30,
                    left: 10,
                    right: 10,
                    top: 10
                }
            },
            onClick: (event, elements) => {
                if (elements.length > 0 && currentTimelineData) {
                    const element = elements[0];
                    const index = element.index;
                    const datasetIndex = element.datasetIndex;
                    const clickedDate = currentTimelineData.sortedKeys[index];
                    
                    if (!clickedDate) return;
                    
                    // Get posts for this date
                    const datePosts = currentTimelineData.posts.filter(p => {
                        const postDate = new Date(p.created_at).toISOString().split('T')[0];
                        return postDate === clickedDate;
                    });
                    
                    // Check if it's a double-click (filter by product) or single click (filter by date)
                    const now = Date.now();
                    const lastClickTime = timelineChart._lastClickTime || 0;
                    const isDoubleClick = (now - lastClickTime) < 300; // 300ms threshold
                    timelineChart._lastClickTime = now;
                    
                    if (isDoubleClick && datePosts.length > 0) {
                        // Double-click: Filter by most common product for this date
                        const productCounts = {};
                        datePosts.forEach(post => {
                            const product = getProductLabel(post.id, post.content, post.language);
                            if (product) {
                                productCounts[product] = (productCounts[product] || 0) + 1;
                            }
                        });
                        
                        const topProduct = Object.entries(productCounts)
                            .sort((a, b) => b[1] - a[1])[0];
                        
                        if (topProduct) {
                            // Dispatch event to filter by product
                            const filterEvent = new CustomEvent('filterByProductFromTimeline', {
                                detail: { product: topProduct[0], date: clickedDate }
                            });
                            window.dispatchEvent(filterEvent);
                        }
                    } else {
                        // Single click: Filter by date
                        const filterEvent = new CustomEvent('filterByDate', {
                            detail: { date: clickedDate }
                        });
                        window.dispatchEvent(filterEvent);
                    }
                }
            }
        }
    });
    }, 50);
}

