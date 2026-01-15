// Charts management for dashboard
import { State } from './state.js';
import { getProductLabel } from './product-detection.js';

let timelineChart = null;
let currentTimelineData = null; // Store current timeline data for onClick handler
let isSelecting = false;
let selectionStart = null;
let selectionEnd = null;

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
        // Ensure canvas has proper dimensions
        const container = canvas.parentElement;
        if (container) {
            const containerHeight = container.offsetHeight || 280;
            canvas.style.height = containerHeight + 'px';
        }
        
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
                // If we just finished a selection, don't trigger click
                if (isSelecting) {
                    isSelecting = false;
                    return;
                }
                
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
            },
            onHover: (event, elements) => {
                const canvas = event.native.target;
                // Don't change cursor if we're dragging
                if (!isDragging) {
                    canvas.style.cursor = elements.length > 0 ? 'pointer' : 'crosshair';
                }
            }
        }
    });
    
    // Add mouse selection for date range (after chart is fully created)
    setTimeout(() => {
        const canvas = document.getElementById('timelineChart');
        if (canvas && timelineChart) {
            setupTimelineSelection(canvas, timelineChart);
        }
    }, 100);
    }, 50);
}

function setupTimelineSelection(canvas, chart) {
    let isDragging = false;
    let startX = null;
    let startIndex = null;
    let selectionRect = null;
    let selectionOverlay = null;
    let tooltip = null;
    
    // Create overlay div for better selection visualization
    const container = canvas.parentElement;
    if (container && !container.querySelector('.timeline-selection-overlay')) {
        selectionOverlay = document.createElement('div');
        selectionOverlay.className = 'timeline-selection-overlay';
        selectionOverlay.style.cssText = 'position: absolute; pointer-events: none; z-index: 10; display: none;';
        container.style.position = 'relative';
        container.appendChild(selectionOverlay);
        
        // Create tooltip for selection feedback
        tooltip = document.createElement('div');
        tooltip.className = 'timeline-selection-tooltip';
        tooltip.style.cssText = 'position: absolute; background: rgba(0, 0, 0, 0.8); color: white; padding: 8px 12px; border-radius: 6px; font-size: 0.85em; pointer-events: none; z-index: 11; display: none; white-space: nowrap;';
        container.appendChild(tooltip);
    } else {
        selectionOverlay = container?.querySelector('.timeline-selection-overlay');
        tooltip = container?.querySelector('.timeline-selection-tooltip');
    }
    
    // Show hint on hover when not dragging
    canvas.addEventListener('mousemove', (e) => {
        if (isDragging) {
            // Update selection during drag
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const chartArea = chart.chartArea;
            
            if (startX !== null && selectionRect) {
                selectionRect.width = x - startX;
                drawSelection(canvas, chart, selectionRect, selectionOverlay, tooltip, startIndex);
            }
        } else {
            // Show cursor hint
            const points = chart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, true);
            if (points.length > 0) {
                canvas.style.cursor = 'pointer';
            } else {
                canvas.style.cursor = 'crosshair';
            }
        }
    });
    
    canvas.addEventListener('mousedown', (e) => {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // Check if clicking on a bar (if so, let onClick handle it)
        const points = chart.getElementsAtEventForMode(e, 'nearest', { intersect: true }, true);
        if (points.length > 0) {
            // Small delay to allow onClick to fire first
            setTimeout(() => {
                if (!isSelecting) {
                    // onClick handled it, don't start selection
                    return;
                }
            }, 50);
            // Still allow selection if user drags
        }
        
        // Start selection
        isDragging = true;
        isSelecting = true;
        startX = x;
        
        // Find the index at start position
        const chartArea = chart.chartArea;
        const xScale = chart.scales.x;
        const relativeX = x - chartArea.left;
        startIndex = Math.round((relativeX / (chartArea.right - chartArea.left)) * (xScale.max - xScale.min) + xScale.min);
        startIndex = Math.max(0, Math.min(startIndex, currentTimelineData.sortedKeys.length - 1));
        
        // Create selection rectangle
        const containerRect = container.getBoundingClientRect();
        selectionRect = {
            startX: x,
            startY: chartArea.top,
            width: 0,
            height: chartArea.bottom - chartArea.top,
            containerLeft: containerRect.left,
            containerTop: containerRect.top,
            startIndex: startIndex // Store startIndex in rect for use in drawSelection
        };
        
        if (selectionOverlay) {
            selectionOverlay.style.display = 'block';
        }
        
        drawSelection(canvas, chart, selectionRect, selectionOverlay, tooltip, startIndex);
    });
    
    canvas.addEventListener('mouseup', (e) => {
        if (!isDragging || !startX || !currentTimelineData) {
            isDragging = false;
            return;
        }
        
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const chartArea = chart.chartArea;
        
        // Find end index
        const xScale = chart.scales.x;
        const relativeX = x - chartArea.left;
        let endIndex = Math.round((relativeX / (chartArea.right - chartArea.left)) * (xScale.max - xScale.min) + xScale.min);
        endIndex = Math.max(0, Math.min(endIndex, currentTimelineData.sortedKeys.length - 1));
        
        // Ensure startIndex <= endIndex
        const minIndex = Math.min(startIndex, endIndex);
        const maxIndex = Math.max(startIndex, endIndex);
        
        // Get date range
        const startDate = currentTimelineData.sortedKeys[minIndex];
        const endDate = currentTimelineData.sortedKeys[maxIndex];
        
        // Only filter if selection is meaningful (at least 2 different dates)
        if (startDate && endDate && Math.abs(endIndex - startIndex) > 0) {
            const startDateObj = new Date(startDate);
            const endDateObj = new Date(endDate);
            const dateRangeText = `${startDateObj.toLocaleDateString('fr-FR')} - ${endDateObj.toLocaleDateString('fr-FR')}`;
            
            // Show feedback
            if (tooltip) {
                tooltip.textContent = `Filtrage: ${dateRangeText}`;
                tooltip.style.display = 'block';
                setTimeout(() => {
                    if (tooltip) tooltip.style.display = 'none';
                }, 2000);
            }
            
            // Dispatch event to filter by date range
            const filterEvent = new CustomEvent('filterByDateRange', {
                detail: { dateFrom: startDate, dateTo: endDate }
            });
            window.dispatchEvent(filterEvent);
        } else {
            // Selection too small, cancel
            if (tooltip) {
                tooltip.textContent = 'Sélection trop petite';
                tooltip.style.display = 'block';
                setTimeout(() => {
                    if (tooltip) tooltip.style.display = 'none';
                }, 1000);
            }
        }
        
        // Clear selection
        isDragging = false;
        isSelecting = false;
        startX = null;
        startIndex = null;
        setTimeout(() => {
            isSelecting = false; // Reset after a delay to allow onClick
        }, 100);
        selectionRect = null;
        clearSelection(canvas, selectionOverlay);
    });
    
    canvas.addEventListener('mouseleave', () => {
        if (isDragging) {
            isDragging = false;
            isSelecting = false;
            startX = null;
            startIndex = null;
            selectionRect = null;
            clearSelection(canvas, selectionOverlay);
        }
    });
}

function drawSelection(canvas, chart, rect, overlay, tooltip, startIdx) {
    if (!chart || !rect) return;
    
    const chartArea = chart.chartArea;
    const container = canvas.parentElement;
    if (!container) return;
    
    // Use overlay div for better visibility
    if (overlay) {
        const containerRect = container.getBoundingClientRect();
        const canvasRect = canvas.getBoundingClientRect();
        
        const left = Math.min(rect.startX, rect.startX + rect.width);
        const width = Math.abs(rect.width);
        
        overlay.style.left = (canvasRect.left - containerRect.left + left) + 'px';
        overlay.style.top = (canvasRect.top - containerRect.top + chartArea.top) + 'px';
        overlay.style.width = width + 'px';
        overlay.style.height = (chartArea.bottom - chartArea.top) + 'px';
        overlay.style.background = 'rgba(0, 212, 255, 0.25)';
        overlay.style.border = '2px solid rgba(0, 212, 255, 0.8)';
        overlay.style.borderRadius = '4px';
        overlay.style.display = 'block';
    }
    
    // Update tooltip position
    if (tooltip && rect.width !== 0 && startIdx !== null && currentTimelineData) {
        const canvasRect = canvas.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        const tooltipX = canvasRect.left - containerRect.left + rect.startX + rect.width / 2;
        const tooltipY = canvasRect.top - containerRect.top + chartArea.top - 35;
        
        tooltip.style.left = tooltipX + 'px';
        tooltip.style.top = tooltipY + 'px';
        tooltip.style.transform = 'translateX(-50%)';
        
        // Calculate date range for tooltip
        const xScale = chart.scales.x;
        const endX = rect.startX + rect.width;
        const relativeEndX = endX - chartArea.left;
        let endIndex = Math.round((relativeEndX / (chartArea.right - chartArea.left)) * (xScale.max - xScale.min) + xScale.min);
        endIndex = Math.max(0, Math.min(endIndex, currentTimelineData.sortedKeys.length - 1));
        
        const minIdx = Math.min(startIdx, endIndex);
        const maxIdx = Math.max(startIdx, endIndex);
        const startDate = currentTimelineData.sortedKeys[minIdx];
        const endDate = currentTimelineData.sortedKeys[maxIdx];
        
        if (startDate && endDate) {
            const startDateObj = new Date(startDate);
            const endDateObj = new Date(endDate);
            tooltip.textContent = `${startDateObj.toLocaleDateString('fr-FR')} → ${endDateObj.toLocaleDateString('fr-FR')}`;
            tooltip.style.display = 'block';
        }
    }
}

function clearSelection(canvas, overlay) {
    if (overlay) {
        overlay.style.display = 'none';
    }
    const tooltip = canvas.parentElement?.querySelector('.timeline-selection-tooltip');
    if (tooltip) {
        tooltip.style.display = 'none';
    }
}

