// Charts management for dashboard
import { State } from './state.js';

let timelineChart = null;

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
                    intersect: false
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
                        maxTicksLimit: 20
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
            onClick: (event, elements) => {
                if (elements.length > 0) {
                    const index = elements[0].index;
                    const clickedDate = sortedKeys[index];
                    // Filter by date
                    console.log('Filter by date:', clickedDate);
                }
            }
        }
    });
    }, 50);
}

