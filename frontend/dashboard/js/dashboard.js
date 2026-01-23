// Dashboard UI management
import { API } from './api.js';
import { State } from './state.js';
import { getProductLabel, editProductLabel } from './product-detection.js';
import { updateWhatsHappening } from './whats-happening.js';
import { updateTimelineChart } from './charts.js';

const api = new API();
let state = null;
let updateDashboardTimeout = null;
let isUpdatingDashboard = false;

// Debounced updateDashboard to avoid multiple rapid updates
function debouncedUpdateDashboard() {
    if (updateDashboardTimeout) {
        clearTimeout(updateDashboardTimeout);
    }
    updateDashboardTimeout = setTimeout(() => {
        if (!isUpdatingDashboard) {
            isUpdatingDashboard = true;
            updateDashboard();
            isUpdatingDashboard = false;
        }
    }, 50); // 50ms debounce
}

export function initDashboard(appState) {
    console.log('[dashboard.js] initDashboard() called');
    state = appState;
    
    console.log('[dashboard.js] State:', {
        hasPosts: !!state.posts,
        postsCount: state.posts?.length || 0,
        hasFilteredPosts: !!state.filteredPosts,
        filteredPostsCount: state.filteredPosts?.length || 0
    });
    
    // Ensure all filters are reset to default values on initialization (no filters active)
    // This ensures the timeline displays all posts by default
    // Wait a bit to ensure posts are loaded first, then reset filters
    setTimeout(() => {
        // Reset all filters to default values
        state.filters.dateFrom = '';
        state.filters.dateTo = '';
        state.filters.sentiment = 'all';
        state.filters.language = 'all';
        state.filters.product = 'all';
        state.filters.answered = 'all';
        state.filters.source = '';
        state.filters.search = '';
        
        // Reapply filters to update filteredPosts with no filters
        // This ensures filteredPosts contains all posts when no filters are active
        state.applyFilters();
        
        // Clear date inputs to ensure no default dates are displayed
        const dateFromInput = document.getElementById('dateFrom');
        const dateToInput = document.getElementById('dateTo');
        const globalDateFrom = document.getElementById('globalDateFrom');
        const globalDateTo = document.getElementById('globalDateTo');
        
        if (dateFromInput) dateFromInput.value = '';
        if (dateToInput) dateToInput.value = '';
        if (globalDateFrom) globalDateFrom.value = '';
        if (globalDateTo) globalDateTo.value = '';
        
        // Reset date range preset selector
        const dateRangePreset = document.getElementById('dateRangePreset');
        if (dateRangePreset) dateRangePreset.value = 'all';
        
        // Also reset all filter selects to 'all'
        const sentimentFilter = document.getElementById('sentimentFilter');
        const languageFilter = document.getElementById('languageFilter');
        const productFilter = document.getElementById('productFilter');
        const answeredFilter = document.getElementById('answeredFilter');
        
        if (sentimentFilter) sentimentFilter.value = 'all';
        if (languageFilter) languageFilter.value = 'all';
        if (productFilter) productFilter.value = 'all';
        if (answeredFilter) answeredFilter.value = 'all';
        
        // Force timeline chart update to ensure it displays with no filters
        updateTimelineChart(state);
    }, 200); // Wait 200ms to ensure posts are loaded
    
    // Check for product filter from Improvements page
    const dashboardProductFilter = localStorage.getItem('dashboardProductFilter');
    if (dashboardProductFilter) {
        // Clear the localStorage flag so it doesn't persist
        localStorage.removeItem('dashboardProductFilter');
        
        // Apply the filter after a short delay to ensure DOM is ready and posts are loaded
        setTimeout(() => {
            // Set filter directly in state (it will use getProductLabel for matching)
            state.setFilter('product', dashboardProductFilter);
            
            // Also update the select if it exists
            const productFilter = document.getElementById('productFilter');
            if (productFilter) {
                // Check if the product exists in the select options
                const optionExists = Array.from(productFilter.options).some(opt => opt.value === dashboardProductFilter || opt.textContent === dashboardProductFilter);
                if (optionExists) {
                    // Find the matching option
                    const matchingOption = Array.from(productFilter.options).find(opt => opt.value === dashboardProductFilter || opt.textContent === dashboardProductFilter);
                    if (matchingOption) {
                        productFilter.value = matchingOption.value;
                    }
                }
            }
        }, 300);
    }
    
    // Don't initialize default date range automatically
    // Users should explicitly set date filters if they want to filter by date
    // This prevents unwanted filters from being active on page load
    
    // Initialize event listeners
    setupEventListeners();
    
    // Setup modal close handlers
    setupModalHandlers();
    
    // Subscribe to state changes to update dashboard automatically (debounced)
    state.subscribe((updatedState) => {
        console.log('[dashboard.js] State changed, calling debouncedUpdateDashboard()');
        debouncedUpdateDashboard();
    });
    
    // IMPORTANT: Call updateDashboard immediately if posts are already loaded
    // The subscription will handle future updates, but we need an initial render
    // Add a delay on first load to ensure backend has loaded API keys from .env
    if (state.posts && state.posts.length > 0) {
        console.log('[dashboard.js] Posts already loaded, calling updateDashboard() after delay');
        // Delay longer on first page load to ensure backend has loaded API keys
        const isFirstLoad = !sessionStorage.getItem('dashboardInitialized');
        const delay = isFirstLoad ? 1000 : 100; // 1 second on first load, 100ms otherwise
        sessionStorage.setItem('dashboardInitialized', 'true');
        
        setTimeout(() => {
            updateDashboard();
        }, delay);
    } else {
        console.log('[dashboard.js] No posts yet, will update when state changes');
    }
    
    // Posts are loaded by app.js, so we just update the dashboard
    // when state changes (via subscription)
    // No need to load data here
}

function initializeDefaultDateRange() {
    if (!state) {
        return;
    }
    
    // Temporarily disable notifications to avoid multiple updates
    const originalNotify = state.notifyListeners;
    let shouldNotify = false;
    state.notifyListeners = () => {
        shouldNotify = true;
    };
    
    // Check both state filters and HTML inputs
    const hasDateFromState = state.filters?.dateFrom && state.filters.dateFrom !== '';
    const hasDateToState = state.filters?.dateTo && state.filters.dateTo !== '';
    const dateFromInput = document.getElementById('dateFrom');
    const dateToInput = document.getElementById('dateTo');
    const hasDateFromInput = dateFromInput && dateFromInput.value !== '';
    const hasDateToInput = dateToInput && dateToInput.value !== '';
    
    // If dates are set in inputs but not in state, sync them
    // But if they filter all posts, clear them
    if (hasDateFromInput || hasDateToInput) {
        const inputDateFrom = dateFromInput?.value || '';
        const inputDateTo = dateToInput?.value || '';
        
        // Temporarily apply these dates to check if they filter all posts
        const originalDateFrom = state.filters.dateFrom;
        const originalDateTo = state.filters.dateTo;
        state.filters.dateFrom = inputDateFrom;
        state.filters.dateTo = inputDateTo;
        state.applyFilters();
        
        if (state.filteredPosts.length === 0 && state.posts.length > 0) {
            // Clear both inputs and state
            if (dateFromInput) dateFromInput.value = '';
            if (dateToInput) dateToInput.value = '';
            const globalDateFrom = document.getElementById('globalDateFrom');
            const globalDateTo = document.getElementById('globalDateTo');
            if (globalDateFrom) globalDateFrom.value = '';
            if (globalDateTo) globalDateTo.value = '';
            state.filters.dateFrom = '';
            state.filters.dateTo = '';
            state.applyFilters();
        } else {
            // Dates are valid, sync state with inputs (without triggering notifications)
            state.filters.dateFrom = inputDateFrom;
            state.filters.dateTo = inputDateTo;
            state.applyFilters();
        }
    } else if (!hasDateFromState && !hasDateToState) {
        // No dates set anywhere - don't set default dates automatically
        // Users should explicitly set date filters if they want to filter by date
        // This prevents unwanted filters from being active on page load
    } else {
        // Dates are in state but not in inputs - sync inputs only if dates are not empty
        // Don't sync empty dates to inputs (they should remain empty)
        if (hasDateFromState && dateFromInput && state.filters.dateFrom) {
            dateFromInput.value = state.filters.dateFrom;
        } else if (!hasDateFromState && dateFromInput) {
            // Ensure input is empty if state has no date
            dateFromInput.value = '';
        }
        if (hasDateToState && dateToInput && state.filters.dateTo) {
            dateToInput.value = state.filters.dateTo;
        } else if (!hasDateToState && dateToInput) {
            // Ensure input is empty if state has no date
            dateToInput.value = '';
        }
        // Also sync global date inputs
        const globalDateFrom = document.getElementById('globalDateFrom');
        const globalDateTo = document.getElementById('globalDateTo');
        if (hasDateFromState && globalDateFrom && state.filters.dateFrom) {
            globalDateFrom.value = state.filters.dateFrom;
        } else if (!hasDateFromState && globalDateFrom) {
            globalDateFrom.value = '';
        }
        if (hasDateToState && globalDateTo && state.filters.dateTo) {
            globalDateTo.value = state.filters.dateTo;
        } else if (!hasDateToState && globalDateTo) {
            globalDateTo.value = '';
        }
        
        // Sync date range preset selector
        const dateRangePreset = document.getElementById('dateRangePreset');
        if (dateRangePreset && globalDateFrom && globalDateTo) {
            if (hasDateFromState && hasDateToState && state.filters.dateFrom && state.filters.dateTo) {
                // Detect preset based on dates
                const fromDate = new Date(state.filters.dateFrom);
                const toDate = new Date(state.filters.dateTo);
                const today = new Date();
                today.setHours(0, 0, 0, 0);
                toDate.setHours(0, 0, 0, 0);
                
                if (toDate.getTime() === today.getTime()) {
                    const diffTime = today - fromDate;
                    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
                    if (diffDays === 30) dateRangePreset.value = '30';
                    else if (diffDays === 60) dateRangePreset.value = '60';
                    else if (diffDays === 90) dateRangePreset.value = '90';
                    else if (diffDays === 180) dateRangePreset.value = '180';
                    else if (diffDays === 365) dateRangePreset.value = '365';
                    else dateRangePreset.value = 'custom';
                } else {
                    dateRangePreset.value = 'custom';
                }
            } else {
                dateRangePreset.value = 'all';
            }
        }
        
        state.applyFilters();
    }
    
    // Restore notifications and trigger a single update if needed
    state.notifyListeners = originalNotify;
    if (shouldNotify) {
        debouncedUpdateDashboard();
    }
}

function setupEventListeners() {
    // Global search
    const globalSearch = document.getElementById('globalSearch');
    if (globalSearch) {
        globalSearch.addEventListener('input', (e) => {
            state.setFilter('search', e.target.value);
            updateResetFiltersButtonVisibility();
            updateDashboard();
            // Sync with All Posts section - update display immediately
            if (document.getElementById('postsGallery')) {
                postsCurrentOffset = 0; // Reset pagination
                updatePostsDisplay();
            }
        });
    }
    
    // Filters
    const sentimentFilter = document.getElementById('sentimentFilter');
    if (sentimentFilter) {
        sentimentFilter.addEventListener('change', (e) => {
            state.setFilter('sentiment', e.target.value);
            // Clear critical filter flag if user manually changes sentiment
            if (e.target.value !== 'negative') {
                state.criticalFilterActive = false;
            }
            updateResetFiltersButtonVisibility();
            updateDashboard();
        });
    }
    
    const languageFilter = document.getElementById('languageFilter');
    if (languageFilter) {
        languageFilter.addEventListener('change', (e) => {
            const value = e.target.value;
            state.setFilter('language', value);
            // Sync with All Posts section filter
            const postsLanguageFilterEl = document.getElementById('postsLanguageFilter');
            if (postsLanguageFilterEl && postsLanguageFilterEl.value !== value) {
                postsLanguageFilterEl.value = value;
            }
            updateResetFiltersButtonVisibility();
            updateDashboard();
            // Update All Posts display if it exists
            if (document.getElementById('postsGallery')) {
                postsCurrentOffset = 0; // Reset pagination
                updatePostsDisplay();
            }
        });
    }
    
    const productFilter = document.getElementById('productFilter');
    if (productFilter) {
        productFilter.addEventListener('change', (e) => {
            state.setFilter('product', e.target.value);
            updateResetFiltersButtonVisibility();
            updateDashboard();
        });
    }
    
    const answeredFilter = document.getElementById('answeredFilter');
    if (answeredFilter) {
        answeredFilter.addEventListener('change', (e) => {
            const value = e.target.value;
            state.setFilter('answered', value);
            // Sync with All Posts section filter
            const postsAnsweredFilterEl = document.getElementById('postsAnsweredFilter');
            if (postsAnsweredFilterEl && postsAnsweredFilterEl.value !== value) {
                postsAnsweredFilterEl.value = value;
            }
            updateResetFiltersButtonVisibility();
            updateDashboard();
            // Update All Posts display if it exists
            if (document.getElementById('postsGallery')) {
                postsCurrentOffset = 0; // Reset pagination
                updatePostsDisplay();
            }
        });
    }
    
    // Posts section answered filter
    const postsAnsweredFilter = document.getElementById('postsAnsweredFilter');
    if (postsAnsweredFilter) {
        postsAnsweredFilter.addEventListener('change', (e) => {
            const value = e.target.value;
            state.setFilter('answered', value);
            // Sync with timeline filter
            const answeredFilterEl = document.getElementById('answeredFilter');
            if (answeredFilterEl && answeredFilterEl.value !== value) {
                answeredFilterEl.value = value;
            }
            updateResetFiltersButtonVisibility();
            updateDashboard();
            // Update All Posts display
            if (document.getElementById('postsGallery')) {
                postsCurrentOffset = 0; // Reset pagination
                updatePostsDisplay();
            }
        });
    }
    
    // Global date slicer (common for all charts)
    const globalDateFrom = document.getElementById('globalDateFrom');
    const globalDateTo = document.getElementById('globalDateTo');
    const clearDatesBtn = document.getElementById('clearDatesBtn');
    const dateRangePreset = document.getElementById('dateRangePreset');
    
    // Function to detect current preset based on dates (accessible globally)
    window.detectCurrentPreset = function() {
        if (!globalDateFrom || !globalDateTo) return 'custom';
        
        const dateFrom = globalDateFrom.value;
        const dateTo = globalDateTo.value;
        
        if (!dateFrom || !dateTo) {
            return 'all';
        }
        
        const fromDate = new Date(dateFrom);
        const toDate = new Date(dateTo);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        toDate.setHours(0, 0, 0, 0);
        
        // Check if toDate is today
        if (toDate.getTime() !== today.getTime()) {
            return 'custom';
        }
        
        // Calculate days difference
        const diffTime = today - fromDate;
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
        
        // Match to preset
        if (diffDays === 30) return '30';
        if (diffDays === 60) return '60';
        if (diffDays === 90) return '90';
        if (diffDays === 180) return '180';
        if (diffDays === 365) return '365';
        
        return 'custom';
    };
    
    // Function to apply date range preset
    function applyDateRangePreset(days) {
        if (days === 'all') {
            // Clear all date filters
            state.setFilter('dateFrom', '');
            state.setFilter('dateTo', '');
            if (globalDateFrom) globalDateFrom.value = '';
            if (globalDateTo) globalDateTo.value = '';
        } else if (days === 'custom') {
            // Don't change dates, just mark as custom
            // The dates will be set by the date inputs
            return;
        } else {
            // Calculate date range
            const daysNum = parseInt(days);
            const today = new Date();
            const dateFrom = new Date(today);
            dateFrom.setDate(dateFrom.getDate() - daysNum);
            
            const dateFromStr = dateFrom.toISOString().split('T')[0];
            const dateToStr = today.toISOString().split('T')[0];
            
            // Apply filters
            state.setFilter('dateFrom', dateFromStr);
            state.setFilter('dateTo', dateToStr);
            
            // Update inputs
            if (globalDateFrom) globalDateFrom.value = dateFromStr;
            if (globalDateTo) globalDateTo.value = dateToStr;
            
            // Sync with local date inputs
            const dateFromInput = document.getElementById('dateFrom');
            const dateToInput = document.getElementById('dateTo');
            if (dateFromInput) dateFromInput.value = dateFromStr;
            if (dateToInput) dateToInput.value = dateToStr;
        }
        
        updateDefaultDateRangeIndicator();
        updateResetFiltersButtonVisibility();
        updateDashboard();
    }
    
    // Date range preset selector
    if (dateRangePreset) {
        dateRangePreset.addEventListener('change', (e) => {
            const presetValue = e.target.value;
            applyDateRangePreset(presetValue);
        });
    }
    
    if (globalDateFrom) {
        globalDateFrom.addEventListener('change', (e) => {
            const dateValue = e.target.value;
            state.setFilter('dateFrom', dateValue);
            // Sync with local date inputs
            const dateFromInput = document.getElementById('dateFrom');
            if (dateFromInput) dateFromInput.value = dateValue;
            // Update preset selector to "custom" if dates don't match a preset
            if (dateRangePreset && window.detectCurrentPreset) {
                const detectedPreset = window.detectCurrentPreset();
                dateRangePreset.value = detectedPreset;
            }
            updateDefaultDateRangeIndicator();
            updateResetFiltersButtonVisibility();
            updateDashboard();
        });
    }
    
    if (globalDateTo) {
        globalDateTo.addEventListener('change', (e) => {
            const dateValue = e.target.value;
            state.setFilter('dateTo', dateValue);
            // Sync with local date inputs
            const dateToInput = document.getElementById('dateTo');
            if (dateToInput) dateToInput.value = dateValue;
            // Update preset selector to "custom" if dates don't match a preset
            if (dateRangePreset && window.detectCurrentPreset) {
                const detectedPreset = window.detectCurrentPreset();
                dateRangePreset.value = detectedPreset;
            }
            updateDefaultDateRangeIndicator();
            updateResetFiltersButtonVisibility();
            updateDashboard();
        });
    }
    
    if (clearDatesBtn) {
        clearDatesBtn.addEventListener('click', () => {
            // Clear dates (don't set default dates)
            state.setFilter('dateFrom', '');
            state.setFilter('dateTo', '');
            if (globalDateFrom) globalDateFrom.value = '';
            if (globalDateTo) globalDateTo.value = '';
            // Reset preset selector to "all"
            if (dateRangePreset) dateRangePreset.value = 'all';
            // Sync with local date inputs
            const dateFromInput = document.getElementById('dateFrom');
            const dateToInput = document.getElementById('dateTo');
            if (dateFromInput) dateFromInput.value = '';
            if (dateToInput) dateToInput.value = '';
            updateDefaultDateRangeIndicator();
            updateResetFiltersButtonVisibility();
            updateDashboard();
        });
    }
    
    // Clear All Filters button
    const clearAllFiltersBtn = document.getElementById('clearAllFiltersBtn');
    if (clearAllFiltersBtn) {
        clearAllFiltersBtn.addEventListener('click', () => {
            resetFilters();
        });
    }
    
    // Generate PowerPoint Report button
    const generateReportBtn = document.getElementById('generateReportBtn');
    if (generateReportBtn) {
        generateReportBtn.addEventListener('click', () => {
            generatePowerPointReport();
        });
    }
    
    // Local date filters (in timeline panel - sync with global)
    const dateFromInput = document.getElementById('dateFrom');
    if (dateFromInput) {
        dateFromInput.addEventListener('change', (e) => {
            const dateValue = e.target.value;
            state.setFilter('dateFrom', dateValue);
            // Sync with global date slicer
            if (globalDateFrom) globalDateFrom.value = dateValue;
            updateDefaultDateRangeIndicator();
            updateDashboard();
        });
    }
    
    const dateToInput = document.getElementById('dateTo');
    if (dateToInput) {
        dateToInput.addEventListener('change', (e) => {
            const dateValue = e.target.value;
            state.setFilter('dateTo', dateValue);
            // Sync with global date slicer
            if (globalDateTo) globalDateTo.value = dateValue;
            updateDefaultDateRangeIndicator();
            updateDashboard();
        });
    }
    
    // Update indicator on page load
    setTimeout(() => {
        updateDefaultDateRangeIndicator();
    }, 100);
    
    // Open critical posts button
    const openCriticalPostsBtn = document.getElementById('openCriticalPostsBtn');
    if (openCriticalPostsBtn) {
        openCriticalPostsBtn.addEventListener('click', () => {
            openCriticalPosts();
        });
    }
    
    // Sort
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            const sortValue = e.target.value;
            console.log('Sort changed to:', sortValue);
            sortPosts(sortValue);
        });
    }
    
    // Clear Timeline Filter button
    const clearTimelineFilterBtn = document.getElementById('clearTimelineFilterBtn');
    if (clearTimelineFilterBtn) {
        clearTimelineFilterBtn.addEventListener('click', () => {
            clearTimelineFilter();
        });
    }
    
    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
    
    // Scrape All button
    const scrapeAllBtn = document.getElementById('scrapeAllBtn');
    if (scrapeAllBtn) {
        console.log('✅ Scrape All button found, attaching event listener');
        scrapeAllBtn.addEventListener('click', (e) => {
            console.log('🔵 Scrape All button clicked');
            e.preventDefault();
            scrapeAll();
        });
    } else {
        console.warn('⚠️ Scrape All button not found in DOM');
    }
    
    // Reset Filters button
    const resetFiltersBtn = document.getElementById('resetFiltersBtn');
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }
    
    // Show More Products button
    const showMoreProductsBtn = document.getElementById('showMoreProductsBtn');
    if (showMoreProductsBtn) {
        showMoreProductsBtn.addEventListener('click', showMoreProducts);
    }
    
    // Navigate Products buttons
    const navigateProductsPrevBtn = document.getElementById('navigateProductsPrevBtn');
    if (navigateProductsPrevBtn) {
        navigateProductsPrevBtn.addEventListener('click', () => navigateProducts(-1));
    }
    
    const navigateProductsNextBtn = document.getElementById('navigateProductsNextBtn');
    if (navigateProductsNextBtn) {
        navigateProductsNextBtn.addEventListener('click', () => navigateProducts(1));
    }
    
    // Listen for date filter events from timeline chart
    window.addEventListener('filterByDate', (event) => {
        const clickedDate = event.detail.date;
        if (clickedDate && state) {
            console.log('Filtering by date:', clickedDate);
            
            // Set date filter to the clicked date (show posts from that day)
            const dateFrom = clickedDate;
            const dateTo = clickedDate;
            
            // Update date filters (both global and local)
            const dateFromInput = document.getElementById('dateFrom');
            const dateToInput = document.getElementById('dateTo');
            const globalDateFrom = document.getElementById('globalDateFrom');
            const globalDateTo = document.getElementById('globalDateTo');
            
            if (dateFromInput) {
                dateFromInput.value = dateFrom;
                console.log('Set dateFrom input to:', dateFrom);
            }
            if (dateToInput) {
                dateToInput.value = dateTo;
                console.log('Set dateTo input to:', dateTo);
            }
            if (globalDateFrom) {
                globalDateFrom.value = dateFrom;
            }
            if (globalDateTo) {
                globalDateTo.value = dateTo;
            }
            
            // Update state filters
            state.setFilter('dateFrom', dateFrom);
            state.setFilter('dateTo', dateTo);
            
            console.log('State filters updated:', state.filters);
            
            // Update dashboard to show filtered posts
            updateDashboard();
            
            // Don't scroll - keep user on timeline
            // const postsSection = document.querySelector('.panel-bottom');
            // if (postsSection) {
            //     postsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            // }
        }
    });
    
    // Listen for date range selection from timeline chart (mouse drag)
    window.addEventListener('filterByDateRange', (event) => {
        const { dateFrom, dateTo } = event.detail;
        if (dateFrom && dateTo && state) {
            console.log('Filtering by date range:', dateFrom, 'to', dateTo);
            
            // Update date filters (both global and local)
            const dateFromInput = document.getElementById('dateFrom');
            const dateToInput = document.getElementById('dateTo');
            const globalDateFrom = document.getElementById('globalDateFrom');
            const globalDateTo = document.getElementById('globalDateTo');
            
            if (dateFromInput) dateFromInput.value = dateFrom;
            if (dateToInput) dateToInput.value = dateTo;
            if (globalDateFrom) globalDateFrom.value = dateFrom;
            if (globalDateTo) globalDateTo.value = dateTo;
            
            // Update state filters
            state.setFilter('dateFrom', dateFrom);
            state.setFilter('dateTo', dateTo);
            
            // Update dashboard to show filtered posts
            updateDashboard();
            
            // Don't scroll - keep user on timeline
            // const postsSection = document.querySelector('.panel-bottom');
            // if (postsSection) {
            //     postsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            // }
        }
    });
    
    // Listen for product filter events from timeline chart (double-click)
    window.addEventListener('filterByProductFromTimeline', (event) => {
        const { product, date } = event.detail;
        if (product && state) {
            console.log('Filtering by product from timeline:', product, 'on date:', date);
            
            // Set product filter
            const productFilter = document.getElementById('productFilter');
            if (productFilter) {
                productFilter.value = product;
            }
            state.setFilter('product', product);
            
            // Also set date filter if provided
            if (date) {
                const dateFromInput = document.getElementById('dateFrom');
                const dateToInput = document.getElementById('dateTo');
                if (dateFromInput) dateFromInput.value = date;
                if (dateToInput) dateToInput.value = date;
                state.setFilter('dateFrom', date);
                state.setFilter('dateTo', date);
            }
            
            // Update dashboard
            updateDashboard();
            
    // Don't scroll - keep user on current view
    // const postsSection = document.querySelector('.panel-bottom');
    // if (postsSection) {
    //     postsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    // }
        }
    });
    
    // Listen for source filter events from source chart
    window.addEventListener('filterBySource', (event) => {
        const { source } = event.detail;
        if (state) {
            console.log('Filtering by source:', source);
            
            // Set source filter
            state.setFilter('source', source || '');
            
            // Update dashboard
            updateDashboard();
        }
    });
    
    // Listen for sentiment filter events from sentiment chart
    window.addEventListener('filterBySentiment', (event) => {
        const { sentiment } = event.detail;
        if (state) {
            console.log('Filtering by sentiment:', sentiment);
            
            // Set sentiment filter
            const sentimentFilter = document.getElementById('sentimentFilter');
            if (sentimentFilter) {
                sentimentFilter.value = sentiment;
            }
            state.setFilter('sentiment', sentiment);
            
            // Update dashboard
            updateDashboard();
        }
    });
}

// Helper function to filter valid posts (exclude samples and relevance_score = 0)
// Same logic as in data collection page (index.html)
function filterValidPosts(posts) {
    return posts.filter(post => {
        // Filter out sample posts
        const url = post.url || '';
        const isSample = (
            url.includes('/sample') || 
            url.includes('example.com') ||
            url.includes('/status/174') ||
            url === 'https://trustpilot.com/sample'
        );
        if (isSample) return false;
        
        // Filter out posts with relevance_score = 0
        const relevanceScore = calculateRelevanceScore(post);
        if (relevanceScore === 0 || relevanceScore === null || relevanceScore === undefined) {
            return false;
        }
        
        return true;
    });
}

async function loadDashboardData() {
    try {
        const posts = await api.getPosts(1000, 0);
        
        if (!posts || posts.length === 0) {
            // Show empty state message
            const postsList = document.getElementById('postsList');
            if (postsList) {
                postsList.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-secondary);">No posts found. Go to Feedbacks Collection to scrape some data.</div>';
            }
            return;
        }
        
        // Filter valid posts (exclude samples and relevance_score = 0) to match data collection page
        const validPosts = filterValidPosts(posts);
        
        // Load posts first - don't apply date filter on initial load
        // The default 12 months filter will only be applied when clicking "Clear Filter"
        state.setPosts(validPosts);
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        // Show error message
        const postsList = document.getElementById('postsList');
        if (postsList) {
            postsList.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--error);">Error loading data: ${error.message}</div>`;
        }
    }
}

export function updateDashboard() {
    console.log('[dashboard.js] updateDashboard() called');
    
    if (!state) {
        console.warn('[dashboard.js] No state in updateDashboard()');
        return;
    }
    
    console.log('[dashboard.js] State in updateDashboard():', {
        hasPosts: !!state.posts,
        postsCount: state.posts?.length || 0,
        hasFilteredPosts: !!state.filteredPosts,
        filteredPostsCount: state.filteredPosts?.length || 0
    });
    
    if (!state.posts || state.posts.length === 0) {
        console.log('[dashboard.js] No posts in state, trying to load...');
        // Try to load posts if state is empty
        loadDashboardData().then(() => {
            // After loading, update again
            setTimeout(() => {
                updateDashboard();
            }, 100);
        });
        return;
    }
    
    console.log('[dashboard.js] Calling update functions...');
    updateStatsBanner();
    // updateWhatsHappening is async, but we don't wait for it to avoid blocking
    updateWhatsHappening(state).catch(error => {
        console.error('[dashboard.js] Error in updateWhatsHappening:', error);
    });
    updateProductDistribution();
    updatePostsList(); // This function checks if postsList exists, so it's safe
    updateCriticalPostsButton();
    updateResetFiltersButtonVisibility();
    updatePositiveSatisfactionKPI();
    updatePostsSourceFilter(); // Initialize source filter options
    
    // Initialize posts display in the "All Posts" section at the bottom
    const postsGallery = document.getElementById('postsGallery');
    if (postsGallery) {
        console.log('[dashboard.js] postsGallery found, calling updatePostsDisplay()');
        // Reset offset when dashboard updates to show first page
        postsCurrentOffset = 0;
        updatePostsDisplay();
    } else {
        console.warn('[dashboard.js] postsGallery not found');
    }
    
    console.log('[dashboard.js] updateDashboard() completed');
    // Charts will be updated by charts.js
}

function updateStatsBanner() {
    // Stats banner might not exist, so we skip it if not found
    const statsBanner = document.getElementById('statsBanner');
    if (!statsBanner) {
        // Element doesn't exist, skip silently
        return;
    }
    if (!state) {
        console.warn('State not initialized in updateStatsBanner');
        return;
    }
    
    const posts = state.filteredPosts || [];
    const allPosts = state.posts || [];
    
    const total = posts.length;
    const totalAll = allPosts.length;
    const positive = posts.filter(p => p.sentiment_label === 'positive').length;
    const negative = posts.filter(p => p.sentiment_label === 'negative').length;
    const neutral = posts.filter(p => p.sentiment_label === 'neutral' || !p.sentiment_label).length;
    
    statsBanner.innerHTML = `
        <div class="stats-banner-title">
            📊 FILTERED STATS
        </div>
        <div class="stats-banner-cards">
            <div class="stats-banner-card">
                <div class="stats-banner-card-value">${total}</div>
                <div class="stats-banner-card-label">Total Posts</div>
            </div>
            <div class="stats-banner-card positive">
                <div class="stats-banner-card-value">${positive}</div>
                <div class="stats-banner-card-label">Positive</div>
            </div>
            <div class="stats-banner-card negative">
                <div class="stats-banner-card-value">${negative}</div>
                <div class="stats-banner-card-label">Negative</div>
            </div>
            <div class="stats-banner-card neutral">
                <div class="stats-banner-card-value">${neutral}</div>
                <div class="stats-banner-card-label">Neutral</div>
            </div>
            <div class="stats-banner-card">
                <div class="stats-banner-card-value">${totalAll}</div>
                <div class="stats-banner-card-label">In Database</div>
            </div>
        </div>
    `;
}

let showAllProducts = false;

function updateProductDistribution() {
    const productList = document.getElementById('productList');
    if (!productList || !state) {
        console.warn('updateProductDistribution: productList or state not available', { productList: !!productList, state: !!state });
        return;
    }
    
    const posts = state.filteredPosts || [];
    const productCounts = {};
    
    
    // List of language codes to exclude from product distribution
    const languageCodes = ['FR', 'EN', 'ES', 'DE', 'IT', 'PT', 'NL', 'PL', 'RU', 'ZH', 'JA', 'KO', 'AR', 'HI', 'TR', 'SV', 'DA', 'FI', 'NO', 'CS', 'HU', 'RO', 'BG', 'HR', 'SK', 'SL', 'ET', 'LV', 'LT', 'MT', 'EL', 'UK', 'BE', 'GA', 'CY', 'LU', 'UNKNOWN'];
    
    posts.forEach(post => {
        // Get product label (simplified - you may need to import getProductLabel from v1)
        const productLabel = getProductLabelSimple(post);
        // Only count if it's a real product, not a language code
        if (productLabel && !languageCodes.includes(productLabel.toUpperCase())) {
            productCounts[productLabel] = (productCounts[productLabel] || 0) + 1;
        }
    });
    
    
    // Sort by count
    const allProducts = Object.entries(productCounts)
        .sort((a, b) => b[1] - a[1]);
    
    const total = posts.length;
    const colors = ['#0099ff', '#34d399', '#f59e0b', '#ef4444', '#8b5cf6'];
    
    // Calculate how many products can fit in the available space dynamically
    // Get the panel-right container to calculate available space
    const panelRight = productList.closest('.panel-right');
    if (panelRight) {
        // Use requestAnimationFrame to ensure layout is calculated
        requestAnimationFrame(() => {
            const panelRect = panelRight.getBoundingClientRect();
            const header = panelRight.querySelector('.panel-header');
            const nav = panelRight.querySelector('.product-nav');
            const headerHeight = header ? header.getBoundingClientRect().height : 60;
            const navHeight = nav ? nav.getBoundingClientRect().height : 50;
            const padding = 32; // panel padding (16px top + 16px bottom)
            
            // Calculate available height: panel height - header - nav - padding
            const containerHeight = Math.max(200, panelRect.height - headerHeight - navHeight - padding);
            
            // Each product item: padding (6px top + 6px bottom = 12px) + gap (4px) + content (~24px) = ~40px per item
            const itemHeight = 40; // Approximate height per item
            // Calculate max items that fit, ensuring we use the space efficiently
            // Use all available space, show at least 5 items
            const maxVisibleItems = Math.max(5, Math.floor(containerHeight / itemHeight));
            
            // Show as many products as can fit, or all if showAllProducts is true
            const sortedProducts = showAllProducts ? allProducts : allProducts.slice(0, maxVisibleItems);
            const remainingCount = Math.max(0, allProducts.length - maxVisibleItems);
            
            renderProductList(sortedProducts, remainingCount, allProducts, total, colors);
        });
        return; // Exit early, renderProductList will be called in requestAnimationFrame
    }
    
    // Fallback: use default calculation if panel not found
    const containerHeight = 300;
    const itemHeight = 40;
    const maxVisibleItems = Math.max(5, Math.floor(containerHeight / itemHeight));
    const sortedProducts = showAllProducts ? allProducts : allProducts.slice(0, maxVisibleItems);
    const remainingCount = Math.max(0, allProducts.length - maxVisibleItems);
    
    renderProductList(sortedProducts, remainingCount, allProducts, total, colors);
}

function renderProductList(sortedProducts, remainingCount, allProducts, total, colors) {
    const productList = document.getElementById('productList');
    if (!productList) return;
    
    // Show message if no products detected or no posts
    if (sortedProducts.length === 0) {
        if (total === 0) {
            productList.innerHTML = '<div style="text-align: center; padding: 40px; color: var(--text-muted);">No posts available. Try adjusting your filters.</div>';
        } else {
            productList.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">No products detected in ${total} post${total > 1 ? 's' : ''}. Products are detected automatically from post content.</div>`;
        }
        // Hide "Show More" button when no products
        const showMoreProductsBtn = document.getElementById('showMoreProductsBtn');
        if (showMoreProductsBtn) {
            showMoreProductsBtn.style.display = 'none';
        }
        return;
    }
    
    // Calculate max count for relative scaling (makes bars longer)
    const maxCount = sortedProducts.length > 0 ? sortedProducts[0][1] : 1;
    
    productList.innerHTML = sortedProducts.map(([product, count], index) => {
        const percentage = total > 0 ? ((count / total) * 100).toFixed(0) : 0;
        // Use relative scaling based on max count for longer bars
        const relativeWidth = maxCount > 0 ? ((count / maxCount) * 100).toFixed(0) : 0;
        return `
            <div class="product-item" data-product="${product}">
                <div class="product-color" style="background: ${colors[index % colors.length]}"></div>
                <div class="product-bar-container">
                    <div class="product-bar" style="width: ${relativeWidth}%; background: ${colors[index % colors.length]}"></div>
                </div>
                <div class="product-info">
                    <span class="product-name">${product}</span>
                    <span class="product-percentage">${percentage}%</span>
                    <span class="product-count">${count} posts</span>
                </div>
            </div>
        `;
    }).join('');
    
    // Show active filter if any
    const activeProductFilter = state && state.filters.product && state.filters.product !== 'all';
    if (activeProductFilter) {
        const filterIndicator = document.createElement('div');
        filterIndicator.className = 'product-filter-active';
        filterIndicator.innerHTML = `
            Filtered by: ${activeProductFilter}
            <button onclick="clearProductFilter()" title="Clear filter">×</button>
        `;
        productList.insertBefore(filterIndicator, productList.firstChild);
    }
    
    // Add event listeners to product items
    productList.querySelectorAll('.product-item').forEach(item => {
        item.addEventListener('click', () => {
            const product = item.getAttribute('data-product');
            if (product) {
                filterByProduct(product);
            }
        });
    });
    
    // Update "Show More" button text
    const showMoreProductsBtn = document.getElementById('showMoreProductsBtn');
    if (showMoreProductsBtn) {
        if (showAllProducts) {
            showMoreProductsBtn.textContent = 'Show Less';
            showMoreProductsBtn.style.display = 'inline-block';
        } else if (remainingCount > 0) {
            const productText = remainingCount === 1 ? 'product' : 'products';
            showMoreProductsBtn.textContent = `+ ${remainingCount} ${productText}`;
            showMoreProductsBtn.style.display = 'inline-block';
        } else {
            showMoreProductsBtn.style.display = 'none';
        }
    }
    
    // Update "Top X" indicator
    const topIndicator = document.querySelector('.top-indicator');
    if (topIndicator && !showAllProducts) {
        if (sortedProducts.length === allProducts.length) {
            topIndicator.textContent = `Top ${sortedProducts.length}`;
        } else {
            topIndicator.textContent = `Top ${sortedProducts.length}`;
        }
    } else if (topIndicator && showAllProducts) {
        topIndicator.textContent = `All ${allProducts.length}`;
    }
}

function updatePostsList() {
    // This function is for the old "Priority Posts" section which no longer exists
    // Keep it for backward compatibility but make it a no-op if postsList doesn't exist
    const postsList = document.getElementById('postsList');
    if (!postsList || !state) {
        // If postsList doesn't exist, this is fine - we're using the new "All Posts" section instead
        return;
    }
    
    // Show active critical filter indicator if needed
    const panelHeader = document.querySelector('.panel-bottom .panel-header');
    if (panelHeader) {
        // Remove existing filter indicator
        const existingIndicator = panelHeader.querySelector('.critical-filter-active');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        
        // Add filter indicator if critical filter is active
        if (state.criticalFilterActive && state.filters.sentiment === 'negative') {
            const filterIndicator = document.createElement('div');
            filterIndicator.className = 'critical-filter-active';
            filterIndicator.style.cssText = 'margin-top: 12px; display: flex; align-items: center; gap: 8px;';
            filterIndicator.innerHTML = `
                <span style="display: flex; align-items: center; gap: 8px; padding: 6px 12px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px; font-size: 0.9em; color: #ef4444;">
                    <span>🔴 Filtered: Critical Posts Only</span>
                    <button onclick="clearCriticalFilter()" style="background: none; border: none; color: #ef4444; cursor: pointer; font-size: 1.2em; padding: 0 4px; line-height: 1;" title="Clear filter">×</button>
                </span>
            `;
            panelHeader.appendChild(filterIndicator);
        }
    }
    
    // Sort posts by recent/critical
    const sortValue = document.getElementById('sortSelect')?.value || 'recent';
    let sortedPosts = [...state.filteredPosts];
    
    if (sortValue === 'recent') {
        sortedPosts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    } else if (sortValue === 'critical') {
        sortedPosts.sort((a, b) => {
            // First, prioritize negative posts
            if (a.sentiment_label === 'negative' && b.sentiment_label !== 'negative') return -1;
            if (a.sentiment_label !== 'negative' && b.sentiment_label === 'negative') return 1;
            // Then by date (most recent first)
            return new Date(b.created_at) - new Date(a.created_at);
        });
    } else if (sortValue === 'engagement') {
        sortedPosts.sort((a, b) => {
            // Calculate engagement score (views + comments + reactions)
            const engagementA = (a.views || 0) + (a.comments || 0) + (a.reactions || 0);
            const engagementB = (b.views || 0) + (b.comments || 0) + (b.reactions || 0);
            // Sort by engagement descending
            if (engagementB !== engagementA) {
                return engagementB - engagementA;
            }
            // If same engagement, sort by date
            return new Date(b.created_at) - new Date(a.created_at);
        });
    }
    
    // Pagination: show posts in batches
    const POSTS_PER_PAGE = 10;
    const currentPage = state.postsPage || 1;
    const startIndex = 0;
    const endIndex = currentPage * POSTS_PER_PAGE;
    const postsToShow = sortedPosts.slice(startIndex, endIndex);
    const hasMore = sortedPosts.length > endIndex;
    
    // Clear existing content first
    postsList.innerHTML = '';
    
    // Create and append each post item separately to avoid nesting issues
    postsToShow.forEach(post => {
        const timeAgo = getTimeAgo(post.created_at);
        const sourceIcon = getSourceIcon(post.source);
        const category = getProductLabelSimple(post) || 'General';
        const sentiment = post.sentiment_label || 'neutral';
        
        const postElement = document.createElement('div');
        postElement.className = 'post-item';
        postElement.innerHTML = `
            <div class="post-source">
                <div class="source-icon ${post.source?.toLowerCase().replace(/\s+/g, '-')}">
                    ${sourceIcon}
                </div>
                <div style="flex: 1;">
                    <div class="source-name">${post.source || 'Unknown'}</div>
                    <div class="post-time">${timeAgo}</div>
                </div>
                <span class="sentiment-badge sentiment-${sentiment}">${sentiment}</span>
            </div>
            <div class="post-content">
                ${truncateText(post.content || 'No content', 200)}
            </div>
            <div class="post-meta">
                <span class="post-category">${category}</span>
                <button class="post-action" data-url="${post.url || '#'}">Go to post</button>
            </div>
        `;
        postsList.appendChild(postElement);
    });
    
    // Add event listeners to post action buttons
    postsList.querySelectorAll('.post-action').forEach(btn => {
        btn.addEventListener('click', () => {
            const url = btn.getAttribute('data-url');
            if (url && url !== '#') {
                openPost(url);
            }
        });
    });
    
    // Add "Load More" button if there are more posts
    if (hasMore) {
        const loadMoreBtn = document.createElement('button');
        loadMoreBtn.className = 'load-more-btn';
        loadMoreBtn.style.cssText = 'width: 100%; padding: 12px; margin-top: 20px; background: var(--accent-primary); color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; transition: all 0.3s ease;';
        loadMoreBtn.textContent = `Load More (${sortedPosts.length - endIndex} remaining)`;
        loadMoreBtn.addEventListener('click', () => {
            state.postsPage = (state.postsPage || 1) + 1;
            updatePostsList();
        });
        loadMoreBtn.addEventListener('mouseenter', () => {
            loadMoreBtn.style.transform = 'translateY(-2px)';
            loadMoreBtn.style.boxShadow = '0 4px 12px rgba(0, 212, 255, 0.4)';
        });
        loadMoreBtn.addEventListener('mouseleave', () => {
            loadMoreBtn.style.transform = 'translateY(0)';
            loadMoreBtn.style.boxShadow = 'none';
        });
        postsList.appendChild(loadMoreBtn);
    } else if (state.postsPage > 1) {
        // Reset page when filters change and no more posts
        state.postsPage = 1;
    }
}

function getProductLabelSimple(post) {
    return getProductLabel(post.id, post.content, post.language);
}

function getSourceIcon(source) {
    const icons = {
        'X/Twitter': '🐦',
        'Twitter': '🐦',
        'Trustpilot': '⭐',
        'Reddit': '🔴',
        'News': '📰',
        'Google News': '📰',
        'GitHub': '💻',
        'Stack Overflow': '📚'
    };
    return icons[source] || '📝';
}

function getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
}

function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

function sortPosts(sortValue) {
    if (!state) return;
    
    // Update the select value if provided
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect && sortValue) {
        sortSelect.value = sortValue;
    }
    
    // Force update the posts list with the new sort
    updatePostsList();
    
    // Don't scroll - keep user on current view
    // const postsSection = document.querySelector('.panel-bottom');
    // if (postsSection) {
    //     postsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    // }
}

function filterByProduct(product) {
    if (!state) return;
    const productFilter = document.getElementById('productFilter');
    if (productFilter) {
        productFilter.value = product;
        state.setFilter('product', product);
        updateDashboard();
    }
}

function clearProductFilter() {
    if (!state) return;
    const productFilter = document.getElementById('productFilter');
    if (productFilter) {
        productFilter.value = 'all';
        state.setFilter('product', 'all');
        updateDashboard();
    }
}

function showMoreProducts() {
    showAllProducts = !showAllProducts;
    updateProductDistribution();
}

function navigateProducts(direction) {
    // Implement navigation
    console.log('Navigate products', direction);
}

function clearTimelineFilter() {
    if (!state) return;
    
    // Clear all filters (don't set default dates)
    const dateFromInput = document.getElementById('dateFrom');
    const dateToInput = document.getElementById('dateTo');
    const globalDateFrom = document.getElementById('globalDateFrom');
    const globalDateTo = document.getElementById('globalDateTo');
    
    // Clear date filters
    if (dateFromInput) dateFromInput.value = '';
    if (dateToInput) dateToInput.value = '';
    if (globalDateFrom) globalDateFrom.value = '';
    if (globalDateTo) globalDateTo.value = '';
    
    // Reset other timeline filters
    const sentimentFilter = document.getElementById('sentimentFilter');
    const languageFilter = document.getElementById('languageFilter');
    const productFilter = document.getElementById('productFilter');
    const answeredFilter = document.getElementById('answeredFilter');
    
    if (sentimentFilter) sentimentFilter.value = 'all';
    if (languageFilter) languageFilter.value = 'all';
    if (productFilter) productFilter.value = 'all';
    if (answeredFilter) answeredFilter.value = 'all';
    
    // Update state - clear date filters (set to empty string, not default dates)
    state.setFilter('dateFrom', '');
    state.setFilter('dateTo', '');
    state.setFilter('sentiment', 'all');
    state.setFilter('language', 'all');
    state.setFilter('product', 'all');
    state.setFilter('answered', 'all');
    
    // Update indicator
    updateDefaultDateRangeIndicator();
    
    // Update dashboard
    updateDashboard();
}

function updateDefaultDateRangeIndicator() {
    // Sync date range preset selector instead of showing indicator
    const dateRangePreset = document.getElementById('dateRangePreset');
    if (dateRangePreset && window.detectCurrentPreset) {
        const detectedPreset = window.detectCurrentPreset();
        dateRangePreset.value = detectedPreset;
    }
}

function resetFilters() {
    if (!state) return;
    
    // Reset all filters (including dates to empty)
    state.setFilter('search', '');
    state.setFilter('sentiment', 'all');
    state.setFilter('language', 'all');
    state.setFilter('product', 'all');
    state.setFilter('source', '');
    state.setFilter('dateFrom', ''); // Clear dates
    state.setFilter('dateTo', ''); // Clear dates
    state.setFilter('answered', 'all');
    
    // Reset UI elements
    const globalSearch = document.getElementById('globalSearch');
    if (globalSearch) globalSearch.value = '';
    
    const sentimentFilter = document.getElementById('sentimentFilter');
    if (sentimentFilter) sentimentFilter.value = 'all';
    
    const languageFilter = document.getElementById('languageFilter');
    if (languageFilter) languageFilter.value = 'all';
    
    const productFilter = document.getElementById('productFilter');
    if (productFilter) productFilter.value = 'all';
    
    const answeredFilter = document.getElementById('answeredFilter');
    if (answeredFilter) answeredFilter.value = 'all';
    
    // Reset global date slicer to empty
    const globalDateFrom = document.getElementById('globalDateFrom');
    const globalDateTo = document.getElementById('globalDateTo');
    if (globalDateFrom) globalDateFrom.value = '';
    if (globalDateTo) globalDateTo.value = '';
    
    // Reset local date inputs to empty
    const dateFromInput = document.getElementById('dateFrom');
    const dateToInput = document.getElementById('dateTo');
    if (dateFromInput) dateFromInput.value = '';
    if (dateToInput) dateToInput.value = '';
    
    // Clear critical filter flag
    state.criticalFilterActive = false;
    
    // Hide reset filters button
    updateResetFiltersButtonVisibility();
    
    // Update dashboard (this will trigger state subscription which updates timeline)
    updateDashboard();
    
    // Force timeline chart update to ensure it refreshes
    // The state subscription should handle this, but we ensure it happens
    setTimeout(() => {
        updateTimelineChart(state);
    }, 150);
}

function updateResetFiltersButtonVisibility() {
    if (!state) return;
    
    const resetBtn = document.getElementById('resetFiltersBtn');
    if (!resetBtn) return;
    
    // Check if any filters are active
    const hasSearch = state.filters?.search && state.filters.search.trim() !== '';
    const hasSentiment = state.filters?.sentiment && state.filters.sentiment !== 'all';
    const hasLanguage = state.filters?.language && state.filters.language !== 'all';
    const hasProduct = state.filters?.product && state.filters.product !== 'all';
    const hasDateFrom = state.filters?.dateFrom && state.filters.dateFrom !== '';
    const hasDateTo = state.filters?.dateTo && state.filters.dateTo !== '';
    
    const hasActiveFilters = hasSearch || hasSentiment || hasLanguage || hasProduct || hasDateFrom || hasDateTo;
    
    resetBtn.style.display = hasActiveFilters ? 'block' : 'none';
}

// Job tracking for background scraping
let currentJobId = null;
let jobStatusInterval = null;

// Persist job ID to localStorage so it can be resumed after page navigation
function persistLastJob(jobId, sourceName = '') {
    if (!jobId) {
        localStorage.removeItem('ovh_last_job');
        localStorage.removeItem('ovh_last_job_source');
    } else {
        localStorage.setItem('ovh_last_job', jobId);
        if (sourceName) {
            localStorage.setItem('ovh_last_job_source', sourceName);
        }
    }
}

function loadLastJob() {
    const jobId = localStorage.getItem('ovh_last_job');
    const sourceName = localStorage.getItem('ovh_last_job_source') || '';
    
    // Auto-cleanup: if job ID matches the problematic one, remove it immediately
    if (jobId && jobId.includes('84d4fd06-ae2e-43a1-9387-e037a668f75a')) {
        console.warn('🧹 Auto-cleaning stale job ID from localStorage');
        localStorage.removeItem('ovh_last_job');
        localStorage.removeItem('ovh_last_job_source');
        return { jobId: null, sourceName: '' };
    }
    
    // Validate that jobId is a string (not an object that was stringified)
    if (jobId && typeof jobId !== 'string') {
        console.warn('loadLastJob: Invalid jobId type, clearing localStorage');
        localStorage.removeItem('ovh_last_job');
        localStorage.removeItem('ovh_last_job_source');
        return { jobId: null, sourceName: '' };
    }
    
    // Check if jobId looks like it might be a stringified object
    if (jobId && (jobId.startsWith('{') || jobId.startsWith('['))) {
        console.warn('loadLastJob: jobId appears to be a stringified object, clearing localStorage');
        localStorage.removeItem('ovh_last_job');
        localStorage.removeItem('ovh_last_job_source');
        return { jobId: null, sourceName: '' };
    }
    
    return {
        jobId: jobId,
        sourceName: sourceName
    };
}

// Global job notification system (works across all pages)
function showJobNotification(jobStatus, sourceName, message, totalAdded = 0) {
    // Create notification element if it doesn't exist
    let notification = document.getElementById('globalJobNotification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'globalJobNotification';
        notification.style.cssText = `
            position: fixed;
            top: 80px;
            right: 24px;
            z-index: 10000;
            min-width: 300px;
            max-width: 500px;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
            animation: slideInRight 0.3s ease-out;
            cursor: pointer;
        `;
        document.body.appendChild(notification);
        
        // Add animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideInRight {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOutRight {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Set notification content based on status
    let bgColor, icon, title;
    if (jobStatus === 'completed') {
        bgColor = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
        icon = '✅';
        title = 'Scraping terminé';
    } else if (jobStatus === 'failed') {
        bgColor = 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)';
        icon = '❌';
        title = 'Scraping échoué';
    } else if (jobStatus === 'cancelled') {
        bgColor = 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)';
        icon = '⏹️';
        title = 'Scraping annulé';
    } else {
        return; // Don't show notification for other statuses
    }
    
    notification.style.background = bgColor;
    notification.style.color = 'white';
    notification.innerHTML = `
        <div style="display: flex; align-items: flex-start; gap: 12px;">
            <div style="font-size: 24px;">${icon}</div>
            <div style="flex: 1;">
                <div style="font-weight: 700; font-size: 1.1em; margin-bottom: 8px;">${title}</div>
                <div style="font-size: 0.95em; opacity: 0.95;">${sourceName ? `${sourceName}: ` : ''}${message}</div>
                ${totalAdded > 0 ? `<div style="margin-top: 8px; font-weight: 600;">${totalAdded} nouveau${totalAdded > 1 ? 'x' : ''} post${totalAdded > 1 ? 's' : ''} ajouté${totalAdded > 1 ? 's' : ''}</div>` : ''}
            </div>
            <button onclick="this.closest('#globalJobNotification').remove()" style="background: rgba(255,255,255,0.2); border: none; color: white; width: 24px; height: 24px; border-radius: 50%; cursor: pointer; font-size: 18px; line-height: 1; padding: 0;">×</button>
        </div>
    `;
    
    // Auto-remove after 8 seconds
    setTimeout(() => {
        if (notification && notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                if (notification && notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 8000);
    
    // Click to dismiss
    notification.onclick = (e) => {
        if (e.target.tagName !== 'BUTTON') {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                if (notification && notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    };
}

async function scrapeAll() {
    console.log('🔵 scrapeAll() called from dashboard');
    
    // Get saved keywords from localStorage (same as Feedbacks Collection page)
    function loadKeywords() {
        const saved = localStorage.getItem('ovh_queries');
        return saved ? JSON.parse(saved) : [];
    }
    
    function saveKeywords(keywords) {
        localStorage.setItem('ovh_queries', JSON.stringify(keywords));
    }
    
    let keywords = loadKeywords();
    
    // Liste des keywords par défaut à supprimer s'ils sont présents
    const defaultKeywords1 = ['ovhcloud', 'ovh vps', 'ovh hosting', 'ovh dedicated', 'ovh cloud', 'ovh support', 'ovh billing'];
    const defaultKeywords2 = ['ovhcloud', 'ovh cloud', 'ovh hosting'];
    
    // Vérifier si les keywords correspondent exactement aux valeurs par défaut
    const isDefaultSet1 = keywords.length === defaultKeywords1.length && 
                           defaultKeywords1.every(kw => keywords.includes(kw));
    const isDefaultSet2 = keywords.length === defaultKeywords2.length && 
                           defaultKeywords2.every(kw => keywords.includes(kw));
    
    if (isDefaultSet1 || isDefaultSet2) {
        // Supprimer les keywords par défaut
        console.log('Removing default keywords from localStorage');
        saveKeywords([]);
        keywords = [];
    }
    
    // No default custom keywords - base keywords (from Settings) will be used automatically by backend
    if (!keywords || keywords.length === 0) {
        console.log('No custom keywords found - backend will use base keywords from Settings');
    } else {
        console.log('Loaded custom keywords from localStorage:', keywords);
    }
    
    // Stop any existing job polling
    if (jobStatusInterval) {
        clearInterval(jobStatusInterval);
        jobStatusInterval = null;
    }
    
    const scrapeBtn = document.getElementById('scrapeAllBtn');
    const progressBar = document.getElementById('scrapingProgressBar');
    const progressContainer = document.getElementById('scrapingProgressContainer');
    
    try {
        // Show progress bar
        if (progressContainer) {
            progressContainer.style.display = 'block';
            progressContainer.setAttribute('data-status', 'running');
            progressContainer.setAttribute('data-percentage', '0%');
        }
        if (progressBar) {
            progressBar.style.width = '0%';
            progressBar.setAttribute('aria-valuenow', 0);
        }
        if (scrapeBtn) {
            scrapeBtn.disabled = true;
            scrapeBtn.innerHTML = '<span class="btn-text">⏳ Starting...</span>';
        }
        
        // Launch background job
        console.log('🚀 Launching background scraping job with keywords:', keywords);
        const jobData = await api.startScrapingJob(keywords, 50, 2, 0.5);
        currentJobId = jobData.job_id;
        
        // Persist job ID so it can be resumed after page navigation
        persistLastJob(currentJobId, 'All Sources');
        
        console.log(`✅ Job started! Job ID: ${currentJobId.substring(0, 8)}...`);
        
        // Show cancel button
        showCancelButton(true);
        
        // Start polling job status
        pollJobStatus(currentJobId);
        
        // Re-enable button immediately (job is running in background)
        if (scrapeBtn) {
            scrapeBtn.disabled = false;
            scrapeBtn.innerHTML = '<span class="btn-text">🆕 Scrape New Data</span>';
        }
        
        // Show toast notification
        showToast('Scraping job started! You can continue using the dashboard.', 'info');
        
    } catch (error) {
        console.error(`Error starting scraping job: ${error.message}`);
        showToast(`Error starting job: ${error.message}`, 'error');
        
        if (scrapeBtn) {
            scrapeBtn.disabled = false;
            scrapeBtn.innerHTML = '<span class="btn-text">🆕 Scrape New Data</span>';
        }
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }
}

async function pollJobStatus(jobId) {
    if (jobStatusInterval) {
        clearInterval(jobStatusInterval);
    }
    
    const progressBar = document.getElementById('scrapingProgressBar');
    const progressText = document.getElementById('scrapingProgressText');
    const progressContainer = document.getElementById('scrapingProgressContainer');
    
    // Verify elements exist
    if (!progressBar) console.error('[Progress] progressBar element not found!');
    if (!progressText) console.error('[Progress] progressText element not found!');
    if (!progressContainer) console.error('[Progress] progressContainer element not found!');
    
    // Track last progress to detect stuck jobs
    let lastProgress = { completed: 0, total: 0, timestamp: Date.now() };
    const STUCK_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes
    
    jobStatusInterval = setInterval(async () => {
        try {
            let job;
            try {
                job = await api.getJobStatus(jobId);
            } catch (error) {
                // If job doesn't exist (404) or is gone (410), stop polling
                if (error.status === 404 || error.status === 410 || 
                    (error.message && (error.message.includes('404') || error.message.includes('410')))) {
                    const statusCode = error.status || (error.message.includes('410') ? 410 : 404);
                    console.warn(`Job ${jobId.substring(0, 8)}... not found (${statusCode}), stopping polling`);
                    clearInterval(jobStatusInterval);
                    jobStatusInterval = null;
                    currentJobId = null;
                    persistLastJob(null); // Clear persisted job
                    const progressContainer = document.getElementById('scrapingProgressContainer');
                    if (progressContainer) {
                        if (statusCode === 410) {
                            if (progressText) {
                                progressText.textContent = '⚠️ Job was permanently removed. Please refresh the page.';
                            }
                            setTimeout(() => {
                                if (progressContainer) {
                                    progressContainer.style.display = 'none';
                                }
                            }, 5000);
                        } else {
                            progressContainer.style.display = 'none';
                        }
                    }
                    showCancelButton(false);
                    return;
                }
                console.error(`Error polling job status: ${error.message}`);
                // Don't stop polling for other errors, just log them and return early
                return;
            }
            
            // If job is undefined (error was caught), skip processing
            if (!job) {
                console.warn('[Progress] Job data is undefined');
                return;
            }
            
            // Log raw job data for debugging (only first time or when status changes)
            if (!window._lastJobStatus || window._lastJobStatus !== job.status) {
                console.log('[Progress] Raw job data received:', JSON.stringify(job, null, 2));
                window._lastJobStatus = job.status;
            }
            
            const status = job.status || 'unknown';
            const progress = job.progress || { total: 0, completed: 0 };
            const completed = Number(progress.completed) || 0;
            const total = Number(progress.total) || 0;
            
            // Log parsed values every time to track changes
            console.log(`[Progress] Parsed: status=${status}, completed=${completed}, total=${total}, progress object:`, progress);
            
            // Detect stuck jobs: if status is running but progress hasn't changed in 5 minutes
            if (status === 'running' && total > 0) {
                const currentProgress = { completed, total, timestamp: Date.now() };
                const progressChanged = currentProgress.completed !== lastProgress.completed || 
                                      currentProgress.total !== lastProgress.total;
                
                if (!progressChanged) {
                    const timeSinceLastProgress = Date.now() - lastProgress.timestamp;
                    if (timeSinceLastProgress > STUCK_THRESHOLD_MS) {
                        console.warn(`Job ${jobId.substring(0, 8)} appears stuck: no progress for ${Math.round(timeSinceLastProgress / 1000 / 60)} minutes`);
                        if (progressText) {
                            progressText.textContent = `⚠️ Job appears stuck (no progress for ${Math.round(timeSinceLastProgress / 1000 / 60)} min). Click Cancel to stop.`;
                        }
                        // Show cancel button if hidden
                        showCancelButton(true);
                    }
                } else {
                    // Progress changed, reset tracking
                    lastProgress = currentProgress;
                }
            } else if (status === 'running') {
                // Reset tracking when status changes
                lastProgress = { completed, total, timestamp: Date.now() };
            }
            
            // Debug logs - always log to help diagnose issues
            console.log(`[Progress] Job ${jobId.substring(0, 8)}: status=${status}, progress=${completed}/${total} (${total > 0 ? Math.round((completed/total)*100) : 0}%)`);
            
            // Force update if we have valid progress data
            if (status === 'running' && total > 0 && completed >= 0) {
                console.log(`[Progress] Updating UI: ${completed}/${total} = ${Math.round((completed/total)*100)}%`);
            }
            
            // Always update progress bar if we have progress data (even if total is 0 initially)
            if (progressBar && progressContainer) {
                // Ensure container is visible
                if (progressContainer.style.display === 'none') {
                    progressContainer.style.display = 'block';
                    console.log('[Progress] Made progress container visible');
                }
                
                if (total > 0 && completed >= 0) {
                    const percentage = Math.min(100, Math.max(0, Math.round((completed / total) * 100)));
                    console.log(`[Progress] ✅ Updating progress bar: ${completed}/${total} = ${percentage}%`);
                    
                    // Update progress bar width - use !important to override any CSS
                    progressBar.style.setProperty('width', `${percentage}%`, 'important');
                    progressBar.setAttribute('aria-valuenow', percentage);
                    
                    // Ensure the bar is visible
                    progressBar.style.setProperty('display', 'block', 'important');
                    progressBar.style.setProperty('visibility', 'visible', 'important');
                    progressBar.style.setProperty('opacity', '1', 'important');
                    progressBar.style.setProperty('height', '100%', 'important');
                    
                    // Force a repaint by reading the style
                    void progressBar.offsetWidth;
                    
                    // Verify the update worked
                    const actualWidth = progressBar.style.width;
                    const computedWidth = window.getComputedStyle(progressBar).width;
                    const computedDisplay = window.getComputedStyle(progressBar).display;
                    console.log(`[Progress] Progress bar - style: ${actualWidth}, computed: ${computedWidth}, display: ${computedDisplay}`);
                    
                    // Also check parent container
                    const parent = progressBar.parentElement;
                    if (parent) {
                        const parentWidth = window.getComputedStyle(parent).width;
                        const parentDisplay = window.getComputedStyle(parent).display;
                        console.log(`[Progress] Parent container - width: ${parentWidth}, display: ${parentDisplay}`);
                    }
                    
                    // Update container attributes
                    progressContainer.setAttribute('data-percentage', `${percentage}%`);
                    progressContainer.setAttribute('data-status', status === 'running' ? 'running' : status);
                } else if (status === 'running' || status === 'pending') {
                    // Show indeterminate progress when job is running but total not yet calculated
                    console.log(`[Progress] ⏳ Showing indeterminate progress (total=${total}, status=${status})`);
                    progressBar.style.setProperty('width', '10%', 'important');
                    progressBar.setAttribute('aria-valuenow', 0);
                    progressBar.style.setProperty('display', 'block', 'important');
                    progressContainer.setAttribute('data-percentage', '...');
                    progressContainer.setAttribute('data-status', 'running');
                } else {
                    console.log(`[Progress] ⚠️ No progress update: total=${total}, completed=${completed}, status=${status}`);
                }
            } else {
                if (!progressBar) console.error('[Progress] ❌ progressBar element not found!');
                if (!progressContainer) console.error('[Progress] ❌ progressContainer element not found!');
            }
            
            // Update progress text
            if (progressText) {
                if (status === 'pending') {
                    // Job is pending - show that it's starting
                    if (total > 0) {
                        progressText.textContent = `Starting scraping job... ${total} tasks queued`;
                    } else {
                        progressText.textContent = 'Initializing scraping job...';
                    }
                } else if (total > 0) {
                    const percentage = Math.round((completed / total) * 100);
                    progressText.textContent = `Scraping in progress: ${completed}/${total} tasks completed (${percentage}%)`;
                } else if (status === 'running') {
                    progressText.textContent = 'Scraping job running... Calculating tasks...';
                } else {
                    progressText.textContent = 'Scraping job initialized...';
                }
            }
            
            // Check if job is complete
            if (status === 'completed') {
                clearInterval(jobStatusInterval);
                jobStatusInterval = null;
                currentJobId = null;
                persistLastJob(null); // Clear persisted job
                
                // Calculate total added
                const results = job.results || [];
                let totalAdded = 0;
                results.forEach(r => {
                    if (r.added) totalAdded += r.added;
                });
                
                // Update progress bar to 100%
                if (progressBar) {
                    progressBar.style.width = '100%';
                    progressBar.setAttribute('aria-valuenow', 100);
                }
                if (progressContainer) {
                    progressContainer.setAttribute('data-percentage', '100%');
                    progressContainer.setAttribute('data-status', 'completed');
                }
                if (progressText) {
                    progressText.textContent = `Scraping complete! Added ${totalAdded} new posts.`;
                }
                
                showToast(`Scraping complete! ${totalAdded} new posts added`, 'success');
                
                // Hide progress bar after 3 seconds
                setTimeout(() => {
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                }, 3000);
                
                // Reload dashboard data
                if (state && api) {
                    try {
                        const posts = await api.getPosts(1000, 0);
                        if (posts && posts.length > 0) {
                            state.setPosts(posts);
                            updateDashboard();
                        }
                    } catch (error) {
                        console.error('Failed to reload posts after scraping:', error);
                    }
                }
                
                showCancelButton(false);
            } else if (status === 'failed' || status === 'cancelled') {
                clearInterval(jobStatusInterval);
                jobStatusInterval = null;
                currentJobId = null;
                persistLastJob(null); // Clear persisted job
                
                const errorMsg = job.error || 'Unknown error';
                if (progressContainer) {
                    progressContainer.setAttribute('data-status', 'failed');
                }
                if (progressText) {
                    progressText.textContent = `Job ${status}: ${errorMsg}`;
                }
                showToast(`Job ${status}`, 'error');
                
                // Hide progress bar after 5 seconds
                setTimeout(() => {
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                }, 5000);
                
                showCancelButton(false);
            }
        } catch (e) {
            // If job doesn't exist (404), stop polling
            if (e.status === 404 || (e.message && e.message.includes('404'))) {
                console.warn(`Job ${jobId.substring(0, 8)}... not found (404), stopping polling`);
                clearInterval(jobStatusInterval);
                jobStatusInterval = null;
                currentJobId = null;
                persistLastJob(null); // Clear persisted job
                const progressContainer = document.getElementById('scrapingProgressContainer');
                if (progressContainer) {
                    progressContainer.style.display = 'none';
                }
                showCancelButton(false);
                return;
            }
            console.error(`Error polling job status: ${e.message}`);
            // Don't stop polling for other errors, just log them
        }
    }, 2000); // Poll every 2 seconds
}

function showCancelButton(show) {
    // Hide cancel button in menu
    const cancelBtn = document.getElementById('cancelScrapingBtn');
    if (cancelBtn) {
        cancelBtn.style.display = 'none';
    }
    
    // Show/hide cancel button near progress bar
    const cancelProgressBtn = document.getElementById('cancelScrapingProgressBtn');
    if (cancelProgressBtn) {
        cancelProgressBtn.style.display = show ? 'block' : 'none';
    }
}

async function cancelScraping() {
    if (currentJobId) {
        try {
            await api.cancelJob(currentJobId);
            showToast('Job cancellation requested', 'info');
        } catch (error) {
            console.error(`Error cancelling job: ${error.message}`);
            showToast(`Error cancelling job: ${error.message}`, 'error');
        }
        
        // Stop polling
        if (jobStatusInterval) {
            clearInterval(jobStatusInterval);
            jobStatusInterval = null;
        }
        currentJobId = null;
        persistLastJob(null); // Clear persisted job
        showCancelButton(false);
        
        const progressContainer = document.getElementById('scrapingProgressContainer');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }
}

function showToast(message, type = 'info') {
    // Simple toast notification (you can enhance this with a proper toast library)
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        padding: 12px 24px;
        background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#34d399' : '#00d4ff'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        z-index: 10000;
        font-weight: 500;
        animation: slideIn 0.3s ease-out;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function openPost(url) {
    if (url && url !== '#') {
        window.open(url, '_blank');
    }
}

function updateCriticalPostsButton() {
    if (!state) return;
    
    const btn = document.getElementById('openCriticalPostsBtn');
    const countSpan = document.getElementById('criticalPostsCount');
    if (!btn || !countSpan) return;
    
    // Calculate critical posts (negative + last 7 days)
    // Apply global search filter if present
    const allPosts = state.posts || [];
    const globalSearch = state.filters?.search || '';
    const now = new Date();
    const last7Days = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const criticalPosts = allPosts.filter(p => {
        const postDate = new Date(p.created_at);
        const isRecent = postDate >= last7Days;
        const isNegative = p.sentiment_label === 'negative';
        
        if (!isRecent || !isNegative) {
            return false;
        }
        
        // Apply global search filter if present
        if (globalSearch && globalSearch.trim() !== '') {
            const searchLower = globalSearch.toLowerCase();
            const productLabel = getProductLabel(p.id, p.content, p.language);
            const matchesSearch = 
                p.content?.toLowerCase().includes(searchLower) ||
                p.author?.toLowerCase().includes(searchLower) ||
                p.url?.toLowerCase().includes(searchLower) ||
                p.source?.toLowerCase().includes(searchLower) ||
                (productLabel && productLabel.toLowerCase().includes(searchLower));
            if (!matchesSearch) {
                return false;
            }
        }
        
        return true;
    });
    
    const count = criticalPosts.length;
    if (countSpan) countSpan.textContent = count;
    
    if (count > 0) {
        btn.style.display = 'inline-flex';
    } else {
        btn.style.display = 'none';
    }
}

function openCriticalPosts() {
    if (!state) return;
    
    // Open drawer with default filters (negative posts only, last 7 days, sorted by score)
    openCriticalPostsDrawer({ periodDays: 7, sortBy: 'score' });
}

function getFilteredCriticalPosts(sentiment, periodDays, sortBy = 'score') {
    if (!state) return [];
    
    // Get all posts (not just filtered ones)
    const allPosts = state.posts || [];
    
    // Get global search filter from state
    const globalSearch = state.filters?.search || '';
    
    // Filter by sentiment and period
    const now = new Date();
    const periodStart = new Date(now.getTime() - periodDays * 24 * 60 * 60 * 1000);
    // Set to start of day for accurate comparison
    periodStart.setHours(0, 0, 0, 0);
    
    console.log(`Filtering posts: periodDays=${periodDays}, periodStart=${periodStart.toISOString()}, sentiment=${sentiment}, search=${globalSearch}`);
    
    let filteredPosts = allPosts.filter(p => {
        if (!p.created_at) return false;
        
        const postDate = new Date(p.created_at);
        // Reset time to start of day for accurate comparison
        postDate.setHours(0, 0, 0, 0);
        
        const isRecent = postDate >= periodStart;
        const matchesSentiment = sentiment === 'all' || p.sentiment_label === sentiment;
        
        if (!isRecent || !matchesSentiment) {
            return false;
        }
        
        // Apply global search filter if present
        if (globalSearch && globalSearch.trim() !== '') {
            const searchLower = globalSearch.toLowerCase();
            const productLabel = getProductLabel(p.id, p.content, p.language);
            const matchesSearch = 
                p.content?.toLowerCase().includes(searchLower) ||
                p.author?.toLowerCase().includes(searchLower) ||
                p.url?.toLowerCase().includes(searchLower) ||
                p.source?.toLowerCase().includes(searchLower) ||
                (productLabel && productLabel.toLowerCase().includes(searchLower));
            if (!matchesSearch) {
                return false;
            }
        }
        
        return true;
    });
    
    console.log(`Filtered ${filteredPosts.length} posts from ${allPosts.length} total`);
    
    // Sort based on sortBy parameter
    if (sortBy === 'score') {
        // Sort by score (most negative/positive first) then by date (most recent first)
        filteredPosts = filteredPosts.sort((a, b) => {
            const scoreA = a.sentiment_score || 0;
            const scoreB = b.sentiment_score || 0;
            
            // For negative posts: more negative (lower score) = higher priority
            // For positive posts: more positive (higher score) = higher priority
            // Use absolute value for comparison, but preserve sign for negative priority
            if (sentiment === 'negative') {
                // For negative: -0.9 is more critical than -0.5
                // So we want lower scores (more negative) first
                if (scoreA !== scoreB) {
                    return scoreA - scoreB; // Lower score (more negative) first
                }
            } else {
                // For positive/neutral/all: higher absolute score first
                const absA = Math.abs(scoreA);
                const absB = Math.abs(scoreB);
                if (absB !== absA) {
                    return absB - absA; // Higher absolute score first
                }
            }
            // If scores are equal, sort by date (most recent first)
            return new Date(b.created_at) - new Date(a.created_at);
        });
    } else if (sortBy === 'recent') {
        // Sort by date (most recent first) then by score
        filteredPosts = filteredPosts.sort((a, b) => {
            const dateA = new Date(a.created_at);
            const dateB = new Date(b.created_at);
            if (dateB.getTime() !== dateA.getTime()) {
                return dateB - dateA; // Most recent first
            }
            // If dates are equal, sort by score (most negative/positive first)
            const scoreA = a.sentiment_score || 0;
            const scoreB = b.sentiment_score || 0;
            if (sentiment === 'negative') {
                return scoreA - scoreB; // More negative first
            } else {
                return Math.abs(scoreB) - Math.abs(scoreA); // Higher absolute score first
            }
        });
    }
    
    return filteredPosts;
}

function openCriticalPostsDrawer(filters) {
    const drawer = document.getElementById('filteredPostsDrawer');
    if (!drawer) return;
    
    // Default filters (focused on negative posts only)
    const defaultFilters = {
        sentiment: 'negative', // Always negative for critical posts
        periodDays: filters?.periodDays || 7,
        sortBy: filters?.sortBy || 'score'
    };
    
    // Calculate scrollbar width before hiding it
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    
    // Prevent body scroll and compensate for scrollbar to prevent layout shift
    document.body.style.paddingRight = `${scrollbarWidth}px`;
    document.body.classList.add('drawer-open');
    
    drawer.classList.add('open');
    updateCriticalPostsDrawer(defaultFilters);
}

function updateCriticalPostsDrawer(filters) {
    const drawerContent = document.getElementById('filteredPostsDrawerContent');
    if (!drawerContent) {
        console.error('drawerContent not found');
        return;
    }
    
    console.log('updateCriticalPostsDrawer called with filters:', filters);
    
    // Ensure filters have all required properties
    const effectiveFilters = {
        sentiment: filters.sentiment || 'negative',
        periodDays: filters.periodDays || 7,
        sortBy: filters.sortBy || 'score'
    };
    
    // Get filtered posts based on current filters
    const posts = getFilteredCriticalPosts(effectiveFilters.sentiment, effectiveFilters.periodDays, effectiveFilters.sortBy);
    const totalPosts = state?.posts?.length || 0;
    
    console.log(`Filtered ${posts.length} posts from ${totalPosts} total posts`);
    
    // Helper functions (same as in whats-happening.js)
    function getTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString();
    }
    
    function getSourceIcon(source) {
        const icons = {
            'twitter': '🐦',
            'x': '🐦',
            'reddit': '🔴',
            'github': '💻',
            'stackoverflow': '📚',
            'trustpilot': '⭐',
            'default': '📝'
        };
        return icons[source?.toLowerCase()] || icons.default;
    }
    
    function truncateText(text, maxLength) {
        if (!text) return 'No content';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Generate period label
    function getPeriodLabel(days) {
        if (days === 1) return 'Last 24 hours';
        if (days === 7) return 'Last 7 days';
        if (days === 30) return 'Last 30 days';
        if (days === 90) return 'Last 90 days';
        return `Last ${days} days`;
    }
    
    // Generate sentiment label
    function getSentimentLabel(sentiment) {
        const labels = {
            'all': 'All Sentiments',
            'negative': 'Negative',
            'positive': 'Positive',
            'neutral': 'Neutral'
        };
        return labels[sentiment] || sentiment;
    }
    
    // Generate title with dynamic period
    const periodLabel = getPeriodLabel(effectiveFilters.periodDays);
    const title = `Critical Posts (Negative - ${periodLabel})`;
    
    let html = `
        <div class="drawer-header">
            <h3 id="drawerTitle">${title}</h3>
            <button class="drawer-close" onclick="closeFilteredPostsDrawer()" aria-label="Close drawer">×</button>
        </div>
        <div class="drawer-info">
            <div class="drawer-stats">
                <span class="drawer-stat-value" style="color: #ef4444; font-weight: 700;">${posts.length}</span>
                <span class="drawer-stat-label">of ${totalPosts} posts</span>
            </div>
            <div class="drawer-filters" style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                <select id="drawerPeriodFilter" onchange="updateDrawerFilters()" style="padding: 6px 12px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-card); color: var(--text-primary); font-size: 0.9em; cursor: pointer;">
                    <option value="1" ${effectiveFilters.periodDays === 1 ? 'selected' : ''}>Last 24 hours</option>
                    <option value="7" ${effectiveFilters.periodDays === 7 ? 'selected' : ''}>Last 7 days</option>
                    <option value="30" ${effectiveFilters.periodDays === 30 ? 'selected' : ''}>Last 30 days</option>
                    <option value="90" ${effectiveFilters.periodDays === 90 ? 'selected' : ''}>Last 90 days</option>
                </select>
                <select id="drawerSortFilter" onchange="updateDrawerFilters()" style="padding: 6px 12px; border: 1px solid var(--border-color); border-radius: 6px; background: var(--bg-card); color: var(--text-primary); font-size: 0.9em; cursor: pointer;">
                    <option value="score" ${effectiveFilters.sortBy === 'score' ? 'selected' : ''}>Sort by: Score (highest)</option>
                    <option value="recent" ${effectiveFilters.sortBy === 'recent' ? 'selected' : ''}>Sort by: Recent</option>
                </select>
            </div>
        </div>
        <div class="drawer-posts">
    `;
    
    if (posts.length === 0) {
        html += `
            <div class="drawer-empty">
                <p>No critical posts found.</p>
            </div>
        `;
    } else {
        // Show first 50 posts
        const postsToShow = posts.slice(0, 50);
        postsToShow.forEach(post => {
            const timeAgo = getTimeAgo(post.created_at);
            const sourceIcon = getSourceIcon(post.source);
            const sentiment = post.sentiment_label || 'neutral';
            const category = getProductLabel(post.id, post.content, post.language) || 'General';
            const score = post.sentiment_score ? post.sentiment_score.toFixed(2) : 'N/A';
            
            html += `
                <div class="drawer-post-item">
                    <div class="drawer-post-header">
                        <div class="drawer-post-source">
                            <span class="drawer-source-icon">${sourceIcon}</span>
                            <span class="drawer-source-name">${post.source || 'Unknown'}</span>
                            ${category && category !== 'General' ? `<span class="drawer-post-category" style="margin-left: 8px; padding: 3px 8px; background: rgba(0, 212, 255, 0.12); border-radius: 6px; color: var(--accent-primary); font-size: 0.75em; font-weight: 500; border: 1px solid rgba(0, 212, 255, 0.25);">📦 ${escapeHtml(category)}</span>` : ''}
                            <span class="drawer-post-time">${timeAgo}</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span class="drawer-sentiment-badge sentiment-${sentiment}">${sentiment}</span>
                            <span style="font-size: 0.85em; color: #ef4444; font-weight: bold;">Score: ${score}</span>
                        </div>
                    </div>
                    <div class="drawer-post-content">${escapeHtml(truncateText(post.content || 'No content', 300))}</div>
                    <div class="drawer-post-meta" style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
                        ${category && category !== 'General' ? `<span class="drawer-post-category" style="padding: 4px 10px; background: rgba(0, 212, 255, 0.12); border-radius: 6px; color: var(--accent-primary); font-size: 0.8em; font-weight: 500; border: 1px solid rgba(0, 212, 255, 0.25);">📦 ${escapeHtml(category)}</span>` : '<span class="drawer-post-category" style="padding: 4px 10px; background: var(--bg-secondary, #f3f4f6); border-radius: 6px; color: var(--text-secondary, #6b7280); font-size: 0.8em;">General</span>'}
                        <div style="display: flex; gap: 8px; align-items: center;">
                            <button onclick="addPostToBacklog(${post.id})" style="padding: 6px 12px; background: var(--accent-primary); border: none; border-radius: 6px; color: #ffffff; font-size: 0.85em; font-weight: 500; cursor: pointer; transition: all 0.2s ease;" 
                                onmouseover="this.style.background='var(--accent-secondary)'; this.style.transform='translateY(-1px)';"
                                onmouseout="this.style.background='var(--accent-primary)'; this.style.transform='translateY(0)';"
                                title="Add to backlog for improvements">
                                📋 Add to Backlog
                            </button>
                            ${post.url ? `<a href="${post.url}" target="_blank" class="drawer-post-link">View post →</a>` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        
        if (posts.length > 50) {
            html += `
                <div class="drawer-more">
                    <p>Showing 50 of ${posts.length} posts</p>
                </div>
            `;
        }
    }
    
    html += `</div>`;
    drawerContent.innerHTML = html;
    
    // Store current filters in drawer element for update function
    drawerContent.dataset.sentiment = effectiveFilters.sentiment;
    drawerContent.dataset.periodDays = effectiveFilters.periodDays;
    drawerContent.dataset.sortBy = effectiveFilters.sortBy;
    
    // Update title dynamically when filters change
    const titleElement = document.getElementById('drawerTitle');
    if (titleElement) {
        const periodLabel = getPeriodLabel(effectiveFilters.periodDays);
        titleElement.textContent = `Critical Posts (Negative - ${periodLabel})`;
    }
}

function updateDrawerFilters() {
    console.log('updateDrawerFilters called');
    
    // Small delay to ensure DOM is ready
    setTimeout(() => {
        const periodFilter = document.getElementById('drawerPeriodFilter');
        const sortFilter = document.getElementById('drawerSortFilter');
        
        if (!periodFilter || !sortFilter) {
            console.error('Filters not found:', { periodFilter: !!periodFilter, sortFilter: !!sortFilter });
            return;
        }
        
        const newFilters = {
            sentiment: 'negative', // Always negative for critical posts
            periodDays: parseInt(periodFilter.value) || 7,
            sortBy: sortFilter.value || 'score'
        };
        
        console.log('Applying filters:', newFilters);
        updateCriticalPostsDrawer(newFilters);
    }, 10);
}

// Make function globally accessible
window.updateDrawerFilters = updateDrawerFilters;

function addPostToBacklog(postId) {
    if (!state || !state.posts) {
        console.error('State or posts not available');
        return;
    }
    
    const post = state.posts.find(p => p.id === postId);
    if (!post) {
        console.error('Post not found:', postId);
        return;
    }
    
    // Load existing backlog from localStorage
    const backlog = JSON.parse(localStorage.getItem('ovh_backlog') || '[]');
    
    // Check if post already exists in backlog
    if (backlog.find(p => p.id === postId)) {
        alert('This post is already in the backlog.');
        return;
    }
    
    // Add post to backlog
    backlog.push(post);
    localStorage.setItem('ovh_backlog', JSON.stringify(backlog));
    
    // Show success message
    const button = event?.target || document.querySelector(`button[onclick="addPostToBacklog(${postId})"]`);
    if (button) {
        const originalText = button.textContent;
        button.textContent = '✓ Added!';
        button.style.background = '#10b981';
        setTimeout(() => {
            button.textContent = originalText;
            button.style.background = 'var(--accent-primary)';
        }, 2000);
    }
    
    // Optional: Open improvements page
    const goToImprovements = confirm('Post added to backlog! Do you want to go to the Improvements page?');
    if (goToImprovements) {
        window.location.href = '/improvements';
    }
}

function clearCriticalFilter() {
    if (!state) return;
    
    // Remove critical filter
    state.setFilter('sentiment', 'all');
    state.criticalFilterActive = false;
    
    // Update sentiment filter dropdown
    const sentimentFilter = document.getElementById('sentimentFilter');
    if (sentimentFilter) {
        sentimentFilter.value = 'all';
    }
    
    // Reset sort to recent
    const sortSelect = document.getElementById('sortSelect');
    if (sortSelect) {
        sortSelect.value = 'recent';
    }
    
    // Update dashboard
    updateDashboard();
}

// Update Positive Satisfaction KPI
function updatePositiveSatisfactionKPI() {
    if (!state) return;
    
    const posts = state.filteredPosts || [];
    const total = posts.length;
    
    const kpiCard = document.querySelector('.kpi-card-left');
    const kpiIcon = kpiCard?.querySelector('.kpi-icon');
    const kpiValue = document.getElementById('positiveSatisfactionValue');
    const kpiLabel = document.getElementById('positiveSatisfactionLabel');
    
    if (total === 0) {
        if (kpiValue) kpiValue.textContent = '--%';
        if (kpiLabel) kpiLabel.textContent = 'Positive Satisfaction';
        // Reset to default (positive/green)
        if (kpiCard) {
            kpiCard.style.background = 'linear-gradient(135deg, rgba(52, 211, 153, 0.15) 0%, rgba(52, 211, 153, 0.08) 100%)';
            kpiCard.style.border = '2px solid rgba(52, 211, 153, 0.3)';
            kpiCard.style.borderColor = 'rgba(52, 211, 153, 0.3)';
            kpiCard.style.boxShadow = '0 4px 16px rgba(52, 211, 153, 0.1)';
        }
        if (kpiIcon) {
            kpiIcon.textContent = '😊';
            kpiIcon.style.filter = 'drop-shadow(0 2px 4px rgba(52, 211, 153, 0.3))';
        }
        if (kpiValue) kpiValue.style.color = '#10b981';
        return;
    }
    
    const positive = posts.filter(p => p.sentiment_label === 'positive').length;
    const negative = posts.filter(p => p.sentiment_label === 'negative').length;
    const percentage = Math.round((positive / total) * 100);
    
    if (kpiValue) {
        kpiValue.textContent = `${percentage}%`;
    }
    
    // Determine color, emoji, and label based on percentage threshold
    // Échelle : >= 70% = Vert (bon), 50-69% = Jaune (moyen-bon), 30-49% = Orange (moyen), < 30% = Rouge (mauvais)
    if (percentage >= 70) {
        // Green background and happy emoji for good satisfaction (>= 70%)
        if (kpiLabel) kpiLabel.textContent = 'Excellent Satisfaction';
        if (kpiCard) {
            kpiCard.style.setProperty('background', 'linear-gradient(135deg, rgba(52, 211, 153, 0.15) 0%, rgba(52, 211, 153, 0.08) 100%)', 'important');
            kpiCard.style.setProperty('border-color', 'rgba(52, 211, 153, 0.3)', 'important');
            kpiCard.style.setProperty('border', '2px solid rgba(52, 211, 153, 0.3)', 'important');
        }
        if (kpiIcon) {
            kpiIcon.textContent = '😊';
            kpiIcon.style.setProperty('filter', 'drop-shadow(0 2px 4px rgba(52, 211, 153, 0.3))', 'important');
        }
        if (kpiValue) kpiValue.style.color = '#10b981'; // Green
    } else if (percentage >= 50) {
        // Yellow background and neutral emoji for medium-good satisfaction (50-69%)
        if (kpiLabel) kpiLabel.textContent = 'Good Satisfaction';
        if (kpiCard) {
            kpiCard.style.setProperty('background', 'linear-gradient(135deg, rgba(234, 179, 8, 0.15) 0%, rgba(234, 179, 8, 0.08) 100%)', 'important');
            kpiCard.style.setProperty('border-color', 'rgba(234, 179, 8, 0.3)', 'important');
            kpiCard.style.setProperty('border', '2px solid rgba(234, 179, 8, 0.3)', 'important');
        }
        if (kpiIcon) {
            kpiIcon.textContent = '😐';
            kpiIcon.style.setProperty('filter', 'drop-shadow(0 2px 4px rgba(234, 179, 8, 0.3))', 'important');
        }
        if (kpiValue) kpiValue.style.color = '#eab308'; // Yellow
    } else if (percentage >= 30) {
        // Orange background and neutral emoji for medium satisfaction (30-49%)
        if (kpiLabel) kpiLabel.textContent = 'Fair Satisfaction';
        if (kpiCard) {
            kpiCard.style.setProperty('background', 'linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(245, 158, 11, 0.08) 100%)', 'important');
            kpiCard.style.setProperty('border-color', 'rgba(245, 158, 11, 0.3)', 'important');
            kpiCard.style.setProperty('border', '2px solid rgba(245, 158, 11, 0.3)', 'important');
        }
        if (kpiIcon) {
            kpiIcon.textContent = '😐';
            kpiIcon.style.setProperty('filter', 'drop-shadow(0 2px 4px rgba(245, 158, 11, 0.3))', 'important');
        }
        if (kpiValue) kpiValue.style.color = '#f59e0b'; // Orange
    } else {
        // Red background and sad emoji for poor satisfaction (< 30%)
        if (kpiLabel) kpiLabel.textContent = 'Poor Satisfaction';
        if (kpiCard) {
            kpiCard.style.setProperty('background', 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.08) 100%)', 'important');
            kpiCard.style.setProperty('border-color', 'rgba(239, 68, 68, 0.3)', 'important');
            kpiCard.style.setProperty('border', '2px solid rgba(239, 68, 68, 0.3)', 'important');
        }
        if (kpiIcon) {
            kpiIcon.textContent = '😞';
            kpiIcon.style.setProperty('filter', 'drop-shadow(0 2px 4px rgba(239, 68, 68, 0.3))', 'important');
        }
        if (kpiValue) kpiValue.style.color = '#ef4444'; // Red
    }
}

// Mark post as answered/not answered
async function markPostAnswered(postId, answered) {
    try {
        const response = await fetch(`/posts/${postId}/mark-answered?answered=${answered}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(`Failed to mark post: ${errorData.detail || response.statusText}`);
        }
        
        const result = await response.json();
        console.log(`✅ Post ${postId} successfully marked as ${answered ? 'answered' : 'not answered'} in database`);
        
        // Reload ALL posts from server to ensure complete sync with database
        try {
            console.log('🔄 Reloading all posts from server to sync with database...');
            const postsResponse = await fetch(`/posts?limit=10000`);
            if (postsResponse.ok) {
                const updatedPosts = await postsResponse.json();
                console.log(`✅ Reloaded ${updatedPosts.length} posts from server`);
                
                if (state) {
                    // Filter valid posts (exclude samples and relevance_score = 0)
                    const validPosts = filterValidPosts(updatedPosts);
                    
                    // Completely replace state.posts with fresh data from server
                    state.setPosts(validPosts);
                    console.log(`✅ State updated with ${validPosts.length} valid posts`);
                    console.log(`📊 Posts answered in fresh data: ${validPosts.filter(p => p.is_answered === 1 || p.is_answered === true).length}`);
                }
            } else {
                throw new Error(`Failed to reload posts: ${postsResponse.status} ${postsResponse.statusText}`);
            }
        } catch (reloadError) {
            console.error('❌ Could not reload posts from server:', reloadError);
            // Fallback: update local state only (but this is not ideal)
            if (state && state.posts) {
                const post = state.posts.find(p => p.id === postId);
                if (post) {
                    post.is_answered = answered ? 1 : 0;
                    post.answered_at = answered ? new Date().toISOString() : null;
                    post.answered_by = answered ? 'Manual' : null;
                    post.answer_detection_method = 'manual';
                    state.applyFilters();
                    state.notifyListeners();
                    console.warn('⚠️ Using local state update (not synced with database)');
                }
            }
        }
        
        // Refresh the dashboard and posts display
        updateDashboard();
        if (document.getElementById('postsGallery')) {
            updatePostsDisplay();
        }
        
        return result;
    } catch (error) {
        console.error('❌ Error marking post as answered:', error);
        alert(`Erreur lors du marquage du post: ${error.message}`);
        throw error;
    }
}

// Make markPostAnswered globally available
window.markPostAnswered = markPostAnswered;

// Generate PowerPoint Report
/**
 * Capture a Chart.js canvas as base64 image
 */
function captureChartAsImage(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.warn(`Canvas ${canvasId} not found`);
        return null;
    }
    
    try {
        // Get the Chart.js instance from the canvas
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js not available');
            return null;
        }
        
        const chart = Chart.getChart(canvas);
        if (!chart) {
            console.warn(`Chart instance not found for ${canvasId}`);
            return null;
        }
        
        // Get the base64 image from the chart
        return chart.toBase64Image('image/png', 1.0);
    } catch (error) {
        console.error(`Error capturing chart ${canvasId}:`, error);
        return null;
    }
}

async function generatePowerPointReport() {
    const btn = document.getElementById('generateReportBtn');
    if (!btn) return;
    
    const originalText = btn.textContent;
    
    // Show loading state
    btn.disabled = true;
    btn.textContent = '⏳ Generating...';
    
    try {
        // Get current filters and state
        const filters = {
            search: state.filters?.search || '',
            sentiment: state.filters?.sentiment || 'all',
            language: state.filters?.language || 'all',
            product: state.filters?.product || 'all',
            source: state.filters?.source || 'all',
            dateFrom: state.filters?.dateFrom || '',
            dateTo: state.filters?.dateTo || ''
        };
        
        // Capture chart images from the dashboard
        const chartImages = {
            timeline: captureChartAsImage('timelineChart'),
            source: captureChartAsImage('sourceChart'),
            sentiment: captureChartAsImage('sentimentChart')
        };
        
        // Prepare FormData to send images
        const formData = new FormData();
        formData.append('filters', JSON.stringify(filters));
        formData.append('include_recommendations', 'true');
        formData.append('include_analysis', 'true');
        
        // Add chart images if available
        // Convert base64 data URI directly to blob (avoid CSP issues with fetch)
        function base64ToBlob(base64, mimeType = 'image/png') {
            const base64Data = base64.split(',')[1] || base64;
            const byteCharacters = atob(base64Data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            return new Blob([byteArray], { type: mimeType });
        }
        
        if (chartImages.timeline) {
            const timelineBlob = base64ToBlob(chartImages.timeline);
            formData.append('timeline_chart', timelineBlob, 'timeline.png');
        }
        if (chartImages.source) {
            const sourceBlob = base64ToBlob(chartImages.source);
            formData.append('source_chart', sourceBlob, 'source.png');
        }
        if (chartImages.sentiment) {
            const sentimentBlob = base64ToBlob(chartImages.sentiment);
            formData.append('sentiment_chart', sentimentBlob, 'sentiment.png');
        }
        
        // Call API to generate report
        const response = await fetch(`${api.baseURL}/api/generate-powerpoint-report`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Failed to generate report' }));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        // Get the file as blob
        const blob = await response.blob();
        
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `OVH_Feedback_Report_${new Date().toISOString().split('T')[0]}.pptx`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        // Show success message
        showToast('PowerPoint report generated successfully!', 'success');
        
    } catch (error) {
        console.error('Error generating PowerPoint report:', error);
        showToast(`Failed to generate report: ${error.message}`, 'error');
    } finally {
        // Reset button state
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Posts Section Functions
let postsCurrentOffset = 0;
const postsPerPage = 20;

function scrollToPostsSection() {
    // Try multiple selectors to find posts section
    const postsSection = document.getElementById('postsSection') || 
                         document.getElementById('postsGallery')?.closest('section') ||
                         document.querySelector('section:has(#postsGallery)');
    if (postsSection) {
        postsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        setTimeout(() => {
            updatePostsDisplay();
            const backBtn = document.getElementById('backToSearchBtn');
            if (backBtn) {
                backBtn.style.display = 'block';
            }
        }, 800); // Increased timeout to ensure scroll completes
    }
}

function scrollToSearch() {
    console.log('scrollToSearch() called');
    const searchSection = document.querySelector('.search-section-with-kpi');
    if (searchSection) {
        console.log('Found search section, scrolling...');
        searchSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        setTimeout(() => {
            const backBtn = document.getElementById('backToSearchBtn');
            if (backBtn) {
                backBtn.style.display = 'none';
            }
        }, 500);
    } else {
        console.warn('Search section not found, trying alternative selectors...');
        // Try alternative selectors
        const altSearchSection = document.querySelector('.search-section') || 
                                 document.getElementById('searchSection') ||
                                 document.querySelector('section:has(.search-input)') ||
                                 document.querySelector('section:has([id*="search"])');
        if (altSearchSection) {
            console.log('Found alternative search section, scrolling...');
            altSearchSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            setTimeout(() => {
                const backBtn = document.getElementById('backToSearchBtn');
                if (backBtn) {
                    backBtn.style.display = 'none';
                }
            }, 500);
        } else {
            console.error('No search section found!');
            // Fallback: scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
            setTimeout(() => {
                const backBtn = document.getElementById('backToSearchBtn');
                if (backBtn) {
                    backBtn.style.display = 'none';
                }
            }, 500);
        }
    }
}

// Show/hide back button based on scroll position
window.addEventListener('scroll', () => {
    const backBtn = document.getElementById('backToSearchBtn');
    if (!backBtn) return;
    
    const searchSection = document.querySelector('.search-section-with-kpi');
    const postsSection = document.getElementById('postsSection');
    
    if (searchSection && postsSection) {
        const searchTop = searchSection.getBoundingClientRect().top;
        const postsTop = postsSection.getBoundingClientRect().top;
        const viewportHeight = window.innerHeight;
        
        // Show button when:
        // - Posts section is visible (top of posts is above bottom of viewport)
        // - Search section is not visible (top of search is below viewport or scrolled past)
        const postsVisible = postsTop < viewportHeight;
        const searchVisible = searchTop >= 0 && searchTop < viewportHeight;
        
        if (postsVisible && !searchVisible) {
            backBtn.style.display = 'block';
        } else if (searchVisible) {
            // Hide when search section is visible
            backBtn.style.display = 'none';
        }
    }
}, { passive: true });

function updatePostsDisplay() {
    if (!state || !state.posts) {
        console.log('No posts available');
        return;
    }

    const gallery = document.getElementById('postsGallery');
    if (!gallery) return;

    const sortBy = document.getElementById('postsSortBy')?.value || 'date-desc';
    const sentimentFilter = document.getElementById('postsSentimentFilter')?.value || 'all';
    const sourceFilter = document.getElementById('postsSourceFilter')?.value || 'all';
    const languageFilter = document.getElementById('postsLanguageFilter')?.value || 'all';
    const answeredFilter = document.getElementById('postsAnsweredFilter')?.value || 'all';
    const dateFrom = document.getElementById('postsDateFrom')?.value || '';
    const dateTo = document.getElementById('postsDateTo')?.value || '';
    
    // Get global search filter from state
    const globalSearch = state.filters?.search || '';
    
    // Sync local filters with global state filters if they exist
    if (state.filters) {
        // Sync sentiment filter
        if (state.filters.sentiment && state.filters.sentiment !== 'all') {
            const postsSentimentFilterEl = document.getElementById('postsSentimentFilter');
            if (postsSentimentFilterEl && postsSentimentFilterEl.value !== state.filters.sentiment) {
                postsSentimentFilterEl.value = state.filters.sentiment;
            }
        }
        
        // Sync source filter
        if (state.filters.source) {
            const postsSourceFilterEl = document.getElementById('postsSourceFilter');
            if (postsSourceFilterEl && postsSourceFilterEl.value !== state.filters.source) {
                postsSourceFilterEl.value = state.filters.source;
            }
        }
        
        // Sync language filter
        if (state.filters.language && state.filters.language !== 'all') {
            const postsLanguageFilterEl = document.getElementById('postsLanguageFilter');
            if (postsLanguageFilterEl && postsLanguageFilterEl.value !== state.filters.language) {
                postsLanguageFilterEl.value = state.filters.language;
            }
        }
        
        // Sync answered filter
        if (state.filters.answered !== undefined) {
            const postsAnsweredFilterEl = document.getElementById('postsAnsweredFilter');
            if (postsAnsweredFilterEl && postsAnsweredFilterEl.value !== state.filters.answered) {
                postsAnsweredFilterEl.value = state.filters.answered;
            }
        }
        
        // Sync date filters
        if (state.filters.dateFrom) {
            const postsDateFromEl = document.getElementById('postsDateFrom');
            if (postsDateFromEl && postsDateFromEl.value !== state.filters.dateFrom) {
                postsDateFromEl.value = state.filters.dateFrom;
            }
        }
        
        if (state.filters.dateTo) {
            const postsDateToEl = document.getElementById('postsDateTo');
            if (postsDateToEl && postsDateToEl.value !== state.filters.dateTo) {
                postsDateToEl.value = state.filters.dateTo;
            }
        }
    }
    
    // Use synced values after potential updates
    const finalSentimentFilter = document.getElementById('postsSentimentFilter')?.value || 'all';
    const finalSourceFilter = document.getElementById('postsSourceFilter')?.value || 'all';
    const finalLanguageFilter = document.getElementById('postsLanguageFilter')?.value || 'all';
    const finalAnsweredFilter = document.getElementById('postsAnsweredFilter')?.value || 'all';
    const finalDateFrom = document.getElementById('postsDateFrom')?.value || '';
    const finalDateTo = document.getElementById('postsDateTo')?.value || '';
    
    // Update state with answered filter if it changed
    if (state && state.filters) {
        if (state.filters.answered !== finalAnsweredFilter) {
            state.setFilter('answered', finalAnsweredFilter);
        }
        // Also update other filters to ensure state is in sync
        if (state.filters.sentiment !== finalSentimentFilter) {
            state.setFilter('sentiment', finalSentimentFilter);
        }
        // Only set source filter if it's not empty and not 'all'
        const normalizedSourceFilter = finalSourceFilter === 'all' ? '' : finalSourceFilter;
        if (state.filters.source !== normalizedSourceFilter) {
            state.setFilter('source', normalizedSourceFilter);
        }
        
        // Check if source filter is filtering all posts - if so, clear it
        if (state.filters.source && state.filters.source !== '' && state.filteredPosts.length === 0 && state.posts.length > 0) {
            console.warn('Source filter is filtering all posts, clearing it. Source was:', state.filters.source);
            state.setFilter('source', '');
            const postsSourceFilterEl = document.getElementById('postsSourceFilter');
            if (postsSourceFilterEl) postsSourceFilterEl.value = 'all';
        }
        if (state.filters.language !== finalLanguageFilter) {
            state.setFilter('language', finalLanguageFilter);
        }
        if (state.filters.dateFrom !== finalDateFrom) {
            state.setFilter('dateFrom', finalDateFrom);
        }
        if (state.filters.dateTo !== finalDateTo) {
            state.setFilter('dateTo', finalDateTo);
        }
    }

    // Filter posts manually (don't rely on filteredPosts as it might not include all filters)
    let filtered = state.posts.filter(post => {
        // Filter out sample data
        const isSample = post.url && (
            post.url.includes('/sample') || 
            post.url.includes('example.com') ||
            post.url.includes('/status/174') ||
            post.url === 'https://trustpilot.com/sample'
        );
        if (isSample) return false;
        
        // Apply global search filter (from main search bar)
        if (globalSearch) {
            const searchLower = globalSearch.toLowerCase();
            const productLabel = getProductLabel(post.id, post.content, post.language);
            const matchesSearch = 
                post.content?.toLowerCase().includes(searchLower) ||
                post.author?.toLowerCase().includes(searchLower) ||
                post.url?.toLowerCase().includes(searchLower) ||
                post.source?.toLowerCase().includes(searchLower) ||
                (productLabel && productLabel.toLowerCase().includes(searchLower));
            if (!matchesSearch) return false;
        }

        // Apply filters
        const normalizedSource = (post.source === 'GitHub Issues' || post.source === 'GitHub Discussions') ? 'GitHub' : post.source;
        const matchesSource = !finalSourceFilter || finalSourceFilter === 'all' || normalizedSource === finalSourceFilter || post.source === finalSourceFilter;
        const matchesSentiment = !finalSentimentFilter || finalSentimentFilter === 'all' || post.sentiment_label === finalSentimentFilter;
        // Language filter - handle null/undefined and normalize comparison
        const postLanguage = (post.language || '').toLowerCase();
        const filterLanguage = (finalLanguageFilter || '').toLowerCase();
        const matchesLanguage = !finalLanguageFilter || finalLanguageFilter === 'all' || postLanguage === filterLanguage;
        
        // Answered filter
        const isAnswered = post.is_answered === 1 || post.is_answered === true || post.is_answered === '1';
        let matchesAnswered = true;
        if (finalAnsweredFilter && finalAnsweredFilter !== 'all') {
            if (finalAnsweredFilter === '1') {
                // Filter for answered posts only
                matchesAnswered = isAnswered;
            } else if (finalAnsweredFilter === '0') {
                // Filter for not answered posts only
                matchesAnswered = !isAnswered;
            }
        }
        
        // Date range filter
        let matchesDate = true;
        if (finalDateFrom || finalDateTo) {
            const postDate = new Date(post.created_at).toISOString().split('T')[0];
            if (finalDateFrom && postDate < finalDateFrom) matchesDate = false;
            if (finalDateTo && postDate > finalDateTo) matchesDate = false;
        }

        return matchesSource && matchesSentiment && matchesLanguage && matchesAnswered && matchesDate;
    });

    // Filter out posts with relevance_score = 0 BEFORE pagination
    filtered = filtered.filter(post => {
        const relevanceScore = calculateRelevanceScore(post);
        return relevanceScore !== 0 && relevanceScore !== null && relevanceScore !== undefined;
    });

    // Apply sorting
    if (sortBy === 'date-desc') {
        filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    } else if (sortBy === 'date-asc') {
        filtered.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    } else if (sortBy === 'sentiment-desc') {
        filtered.sort((a, b) => (a.sentiment_score || 0) - (b.sentiment_score || 0));
    } else if (sortBy === 'sentiment-asc') {
        filtered.sort((a, b) => (b.sentiment_score || 0) - (a.sentiment_score || 0));
    } else if (sortBy === 'relevancy-desc') {
        filtered.sort((a, b) => {
            const relevanceA = calculateRelevanceScore(a);
            const relevanceB = calculateRelevanceScore(b);
            if (relevanceB !== relevanceA) {
                return relevanceB - relevanceA; // Highest first
            }
            // If same relevance, sort by date (most recent first)
            return new Date(b.created_at) - new Date(a.created_at);
        });
    } else if (sortBy === 'relevancy-asc') {
        filtered.sort((a, b) => {
            const relevanceA = calculateRelevanceScore(a);
            const relevanceB = calculateRelevanceScore(b);
            if (relevanceA !== relevanceB) {
                return relevanceA - relevanceB; // Lowest first
            }
            // If same relevance, sort by date (most recent first)
            return new Date(b.created_at) - new Date(a.created_at);
        });
    } else if (sortBy === 'source-asc') {
        filtered.sort((a, b) => (a.source || '').localeCompare(b.source || ''));
    } else if (sortBy === 'source-desc') {
        filtered.sort((a, b) => (b.source || '').localeCompare(a.source || ''));
    }

    // Pagination (after filtering relevance_score = 0)
    const totalPosts = filtered.length;
    const paginated = filtered.slice(postsCurrentOffset, postsCurrentOffset + postsPerPage);

    // Render posts - using same format as data collection page
    if (filtered.length === 0) {
        gallery.innerHTML = '<div class="empty-state" style="grid-column: 1 / -1; text-align: center; padding: 40px;"><h2>No posts found</h2><p>Try adjusting your filters.</p></div>';
        return;
    }

    gallery.innerHTML = paginated.map(post => {
        // Use shared post card component
        return renderPostCard(post, {
            getProductLabel: getProductLabel,
            calculateRelevanceScore: calculateRelevanceScore,
            getSourceClass: getSourceClass,
            getSentimentClass: getSentimentClass,
            formatDate: formatDate,
            escapeHtml: escapeHtml,
            onPreviewClickName: 'openPostPreview',
            onSaveClickName: 'addPostToBacklog'
        });
    }).filter(html => html !== '').join('');

    // Update pagination
    const paginationDiv = document.getElementById('postsPagination');
    if (paginationDiv) {
        if (postsCurrentOffset + postsPerPage < totalPosts) {
            paginationDiv.innerHTML = `
                <button onclick="loadMorePosts()" style="padding: 12px 30px; background: #00d4ff; color: #1a1a2e; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 1em;">
                    📥 Load More (${totalPosts - (postsCurrentOffset + postsPerPage)} remaining)
                </button>
            `;
        } else {
            paginationDiv.innerHTML = `<p style="color: var(--text-secondary);">Showing ${totalPosts} of ${totalPosts} posts</p>`;
        }
    }

    // Update source filter options
    updatePostsSourceFilter();
}

function loadMorePosts() {
    postsCurrentOffset += postsPerPage;
    updatePostsDisplay();
}

function handlePostsLanguageFilterChange() {
    const value = document.getElementById('postsLanguageFilter')?.value || 'all';
    // Update global state
    if (state) {
        state.setFilter('language', value);
    }
    // Sync with global filter if it exists
    const languageFilterEl = document.getElementById('languageFilter');
    if (languageFilterEl && languageFilterEl.value !== value) {
        languageFilterEl.value = value;
    }
    // Reset pagination and update display
    postsCurrentOffset = 0;
    updatePostsDisplay();
    // Update dashboard stats
    updateDashboard();
    updateResetFiltersButtonVisibility();
}

function clearPostsFilters() {
    document.getElementById('postsSortBy').value = 'date-desc';
    document.getElementById('postsSentimentFilter').value = 'all';
    document.getElementById('postsSourceFilter').value = 'all';
    document.getElementById('postsLanguageFilter').value = 'all';
    document.getElementById('postsAnsweredFilter').value = 'all';
    document.getElementById('postsDateFrom').value = '';
    document.getElementById('postsDateTo').value = '';
    // Clear global state filters
    if (state) {
        state.setFilter('language', 'all');
    }
    // Sync global filter
    const languageFilterEl = document.getElementById('languageFilter');
    if (languageFilterEl) {
        languageFilterEl.value = 'all';
    }
    postsCurrentOffset = 0;
    updatePostsDisplay();
    updateDashboard();
    updateResetFiltersButtonVisibility();
}

function updatePostsSourceFilter() {
    if (!state || !state.posts) return;
    
    const sourceFilter = document.getElementById('postsSourceFilter');
    if (!sourceFilter) return;

    // Get unique sources
    const sources = new Set();
    state.posts.forEach(post => {
        if (post.source) {
            let normalized = post.source;
            if (post.source === 'GitHub Issues' || post.source === 'GitHub Discussions') {
                normalized = 'GitHub';
            } else if (post.source.startsWith('Mastodon (')) {
                normalized = 'Mastodon';
            }
            sources.add(normalized);
        }
    });

    const currentValue = sourceFilter.value;
    sourceFilter.innerHTML = '<option value="all">All Sources</option>' + 
        Array.from(sources).sort().map(s => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
    
    if (currentValue && Array.from(sources).includes(currentValue)) {
        sourceFilter.value = currentValue;
    }
}

// Helper functions (from data collection page)
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatDate(dateStr) {
    if (!dateStr) return 'Unknown date';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (e) {
        return dateStr;
    }
}

function getSentimentClass(label) {
    if (!label) return 'sentiment-neutral';
    return `sentiment-${label.toLowerCase()}`;
}

function getSourceClass(source) {
    if (!source) return 'post-source';
    // Normalize source names to match CSS classes
    const normalized = source.toLowerCase()
        .replace(/\s+/g, '-')
        .replace(/github\s*(issues|discussions)?/i, 'github')
        .replace(/x\s*(twitter)?/i, 'x')
        .replace(/stack\s*overflow/i, 'stackoverflow');
    return `post-source source-${normalized}`;
}

function calculateRelevanceScore(post) {
    if (post.relevance_score !== undefined && post.relevance_score !== null && post.relevance_score > 0) {
        return post.relevance_score;
    }

    const content = (post.content || '').toLowerCase();
    const url = (post.url || '').toLowerCase();
    const author = (post.author || '').toLowerCase();

    if (!content && !url && !author) return 0.0;

    let score = 0.0;

    const OVH_BRANDS = ['ovh', 'ovhcloud', 'ovh cloud', 'kimsufi', 'ovh.com', 'ovhcloud.com'];
    const OVH_PRODUCTS = ['vps', 'dedicated server', 'dedicated', 'hosting', 'domain', 'email', 'public cloud', 'private cloud', 'object storage', 'cdn', 'ssl', 'backup', 'storage'];
    const OVH_LEADERSHIP_NAMES = ['michel paulin', 'michel-paulin', 'octave klaba', 'octave-klaba', 'henryk klaba', 'henryk-klaba', 'klaba family', 'famille klaba'];
    const OVH_LEADERSHIP_TITLES = ['ceo ovh', 'ovh ceo', 'pdg ovh', 'ovh pdg', 'founder ovh', 'ovh founder', 'fondateur ovh', 'ovh management', 'ovh direction', 'ovh executives', 'ovh leadership', 'dirigeant ovh', 'ovh dirigeant'];

    // 1. OVH Brands (35% of score)
    const brand_matches = OVH_BRANDS.filter(brand => content.includes(brand)).length;
    if (brand_matches > 0) {
        score += 0.35 * Math.min(brand_matches / 2, 1.0);
    }

    // 2. OVH URL (25% of score)
    if (OVH_BRANDS.some(brand => url.includes(brand))) {
        score += 0.25;
    }

    // 3. OVH Leadership (20% of score)
    let leadership_score = 0.0;
    OVH_LEADERSHIP_NAMES.forEach(name => {
        if (content.includes(name) || author.includes(name)) leadership_score += 0.1;
    });
    OVH_LEADERSHIP_TITLES.forEach(title => {
        if (content.includes(title)) leadership_score += 0.1;
    });

    if (leadership_score > 0 && brand_matches > 0) {
        score += 0.2 * Math.min(leadership_score, 1.0);
    } else if (leadership_score > 0) {
        score += 0.1 * Math.min(leadership_score, 1.0);
    }

    // 4. OVH Products (20% of score)
    const product_matches = OVH_PRODUCTS.filter(product => content.includes(product)).length;
    if (product_matches > 0 && brand_matches > 0) {
        score += 0.2 * Math.min(product_matches / 3, 1.0);
    }

    // Ensure a minimum score if OVH is mentioned at all
    if (score === 0 && (brand_matches > 0 || OVH_BRANDS.some(brand => url.includes(brand)))) {
        score = 0.2;
    }

    return Math.min(score, 1.0);
}

// Make functions available globally
window.filterByProduct = filterByProduct;
window.clearProductFilter = clearProductFilter;
window.showMoreProducts = showMoreProducts;
window.navigateProducts = navigateProducts;
window.resetFilters = resetFilters;
window.scrapeAll = scrapeAll;
window.cancelScraping = cancelScraping;
window.openPost = openPost;
window.clearCriticalFilter = clearCriticalFilter;
window.scrollToPostsSection = scrollToPostsSection;
window.scrollToSearch = scrollToSearch;
window.updatePostsDisplay = updatePostsDisplay;
window.loadMorePosts = loadMorePosts;
window.clearPostsFilters = clearPostsFilters;
window.handlePostsLanguageFilterChange = handlePostsLanguageFilterChange;

// Ensure button event listener is set up after DOM is ready
// Resume last job on page load (so jobs continue even if user navigates away)
(function resumeLastJob() {
    try {
        // Auto-cleanup problematic job ID before loading
        const storedJobId = localStorage.getItem('ovh_last_job');
        if (storedJobId && storedJobId.includes('84d4fd06-ae2e-43a1-9387-e037a668f75a')) {
            console.warn('🧹 Auto-cleaning problematic job ID on page load');
            localStorage.removeItem('ovh_last_job');
            localStorage.removeItem('ovh_last_job_source');
            // Stop any running intervals
            if (typeof jobStatusInterval !== 'undefined' && jobStatusInterval) {
                clearInterval(jobStatusInterval);
                jobStatusInterval = null;
            }
            return; // Don't resume this job
        }
        
        const lastJob = loadLastJob();
        const lastJobId = lastJob?.jobId;
        
        // Validate that lastJobId is a string and not an object
        if (!lastJobId || typeof lastJobId !== 'string' || lastJobId.trim() === '' || lastJobId === '[object Object]' || lastJobId.startsWith('{') || lastJobId.startsWith('[')) {
            if (lastJobId) {
                console.warn('ResumeLastJob: Invalid jobId detected, clearing localStorage:', lastJobId);
                localStorage.removeItem('ovh_last_job');
                localStorage.removeItem('ovh_last_job_source');
            }
            return;
        }
        
        console.log('ResumeLastJob: Found valid job ID:', lastJobId.substring(0, 8) + '...');
        // Try to fetch job status first, if 404, clear localStorage and don't start polling
        api.getJobStatus(lastJobId)
            .then(job => {
                // Job exists, check if still running
                if (job.status === 'running' || job.status === 'pending') {
                    // Job still running, resume polling
                    console.log(`Resuming job ${lastJobId.substring(0, 8)}... after page navigation`);
                    currentJobId = lastJobId;
                    
                    // Show progress bar
                    const progressContainer = document.getElementById('scrapingProgressContainer');
                    if (progressContainer) {
                        progressContainer.style.display = 'block';
                    }
                    
                    // Show cancel button
                    showCancelButton(true);
                    
                    // Start polling
                    pollJobStatus(lastJobId);
                } else {
                    // Job finished, clean up
                    console.log(`Job ${lastJobId.substring(0, 8)}... is ${job.status}, cleaning up`);
                    persistLastJob(null);
                    const progressContainer = document.getElementById('scrapingProgressContainer');
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                    showCancelButton(false);
                }
            })
            .catch(error => {
                // Job doesn't exist (404) or error, clean up
                if (error.status === 404 || (error.message && error.message.includes('404')) || (error.message && error.message.includes('not found'))) {
                    console.warn(`Job ${lastJobId.substring(0, 8)}... not found (404), clearing persisted job`);
                    persistLastJob(null);
                    // Clear any polling intervals
                    if (jobStatusInterval) {
                        clearInterval(jobStatusInterval);
                        jobStatusInterval = null;
                    }
                    currentJobId = null;
                    const progressContainer = document.getElementById('scrapingProgressContainer');
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                    showCancelButton(false);
                } else {
                    console.warn('Could not check job status on page load:', error);
                    persistLastJob(null);
                }
            });
    } catch (error) {
        console.error('ResumeLastJob: Error in resumeLastJob function:', error);
        // Clean up localStorage on any error
        localStorage.removeItem('ovh_last_job');
        localStorage.removeItem('ovh_last_job_source');
    }
})();

document.addEventListener('DOMContentLoaded', () => {
    const goToPostsBtn = document.getElementById('goToPostsBtn');
    if (goToPostsBtn) {
        goToPostsBtn.addEventListener('click', () => {
            scrollToPostsSection();
        });
    }
    
    // Also try to resume job on DOMContentLoaded (in case the IIFE ran too early)
    try {
        const lastJob = loadLastJob();
        const lastJobId = lastJob?.jobId;
        
        // Validate that lastJobId is a string and not an object
        if (!lastJobId || typeof lastJobId !== 'string' || lastJobId.trim() === '' || lastJobId === '[object Object]' || lastJobId.startsWith('{') || lastJobId.startsWith('[') || currentJobId) {
            if (lastJobId && lastJobId !== '[object Object]') {
                console.warn('DOMContentLoaded: Invalid jobId detected, clearing localStorage:', lastJobId);
                localStorage.removeItem('ovh_last_job');
                localStorage.removeItem('ovh_last_job_source');
            }
            return;
        }
        
        console.log('DOMContentLoaded: Found valid job ID:', lastJobId.substring(0, 8) + '...');
        api.getJobStatus(lastJobId)
            .then(job => {
                if (job.status === 'running' || job.status === 'pending') {
                    console.log(`Resuming job ${lastJobId.substring(0, 8)}... on DOMContentLoaded`);
                    currentJobId = lastJobId;
                    const progressContainer = document.getElementById('scrapingProgressContainer');
                    if (progressContainer) {
                        progressContainer.style.display = 'block';
                    }
                    showCancelButton(true);
                    pollJobStatus(lastJobId);
                } else {
                    // Job finished, clean up
                    console.log(`Job ${lastJobId.substring(0, 8)}... is ${job.status}, cleaning up`);
                    persistLastJob(null);
                    const progressContainer = document.getElementById('scrapingProgressContainer');
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                    showCancelButton(false);
                }
            })
            .catch(error => {
                // Job doesn't exist (404) or error, clean up
                if (error.status === 404 || (error.message && error.message.includes('404')) || (error.message && error.message.includes('not found'))) {
                    console.warn(`Job ${lastJobId.substring(0, 8)}... not found (404), clearing persisted job`);
                    persistLastJob(null);
                    if (jobStatusInterval) {
                        clearInterval(jobStatusInterval);
                        jobStatusInterval = null;
                    }
                    currentJobId = null;
                    const progressContainer = document.getElementById('scrapingProgressContainer');
                    if (progressContainer) {
                        progressContainer.style.display = 'none';
                    }
                    showCancelButton(false);
                } else {
                    console.warn('Could not check job status on DOMContentLoaded:', error);
                    persistLastJob(null);
                }
            });
    } catch (error) {
        console.error('DOMContentLoaded: Error in resume job function:', error);
        // Clean up localStorage on any error
        localStorage.removeItem('ovh_last_job');
        localStorage.removeItem('ovh_last_job_source');
    }
});

// Also set up immediately if DOM is already loaded
if (document.readyState === 'loading') {
    // DOM is still loading, wait for DOMContentLoaded
} else {
    // DOM is already loaded, set up immediately
    const goToPostsBtn = document.getElementById('goToPostsBtn');
    if (goToPostsBtn) {
        goToPostsBtn.addEventListener('click', () => {
            scrollToPostsSection();
        });
    }
}

// Post preview function (displays modal like in index.html)
function openPostPreview(postId) {
    if (!state || !state.posts) {
        console.error('State or posts not available');
        return;
    }

    const post = state.posts.find(p => p.id === postId);
    if (!post) {
        console.error('Post not found:', postId);
        return;
    }
    
    const modal = document.getElementById('postPreviewModal');
    const contentDiv = document.getElementById('postPreviewContent');
    const linkDiv = document.getElementById('postPreviewLink');
    
    if (!modal || !contentDiv || !linkDiv) {
        console.error('Preview modal elements not found');
        return;
    }
    
    // Get product label
    const productLabel = getProductLabel(post.id, post.content, post.language);
    
    // Format date
    const postDate = new Date(post.created_at).toLocaleString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    // Build content HTML
    contentDiv.innerHTML = `
        <div style="margin-bottom: 20px; padding: 15px; background: rgba(0, 212, 255, 0.1); border-radius: 8px; border-left: 4px solid var(--accent-primary);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
                <div>
                    <strong style="color: var(--accent-primary); font-size: 1.1em;">${escapeHtml(post.source || 'Unknown Source')}</strong>
                    ${productLabel ? `<span style="margin-left: 10px; padding: 4px 8px; background: rgba(52, 211, 153, 0.2); border-radius: 4px; color: #34d399; font-size: 0.9em;">${escapeHtml(productLabel)}</span>` : ''}
                </div>
                <span class="${getSentimentClass(post.sentiment_label)}" style="font-size: 0.95em;">
                    ${(post.sentiment_label || 'neutral').toUpperCase()} (${(post.sentiment_score || 0).toFixed(2)})
                </span>
            </div>
            <div style="color: var(--text-secondary); font-size: 0.9em; margin-bottom: 10px;">
                <strong>Author:</strong> ${escapeHtml(post.author || 'Unknown')}
            </div>
            <div style="color: var(--text-secondary); font-size: 0.9em; margin-bottom: 10px;">
                <strong>Date:</strong> ${postDate}
            </div>
            ${post.language && post.language !== 'unknown' ? `<div style="color: var(--text-secondary); font-size: 0.9em; margin-bottom: 10px;">
                <strong>Language:</strong> ${escapeHtml(post.language.toUpperCase())}
            </div>` : ''}
        </div>
        
        <div style="padding: 20px; background: var(--bg-card); border-radius: 8px; border: 1px solid rgba(0, 212, 255, 0.2);">
            <h3 style="color: var(--accent-primary); margin-top: 0; margin-bottom: 15px; font-size: 1.2em;">Content:</h3>
            <div style="color: var(--text-primary); white-space: pre-wrap; word-wrap: break-word; line-height: 1.6; max-height: 500px; overflow-y: auto;">
                ${escapeHtml(post.content || 'No content available')}
            </div>
        </div>
    `;
    
    // Set link
    linkDiv.href = post.url || '#';
    if (!post.url || post.url === '#') {
        linkDiv.style.display = 'none';
    } else {
        linkDiv.style.display = 'inline-block';
    }
    
    // Show modal
    modal.style.display = 'block';
}

function closePostPreviewModal() {
    const modal = document.getElementById('postPreviewModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

window.closePostPreviewModal = closePostPreviewModal;

function setupModalHandlers() {
    // Close modal when clicking outside
    document.addEventListener('click', function(event) {
        const postPreviewModal = document.getElementById('postPreviewModal');
        if (postPreviewModal && event.target === postPreviewModal) {
            closePostPreviewModal();
        }
    });
    
    // Close modal with Escape key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            const postPreviewModal = document.getElementById('postPreviewModal');
            if (postPreviewModal && postPreviewModal.style.display !== 'none') {
                closePostPreviewModal();
            }
        }
    });
}

window.openPostPreview = openPostPreview;
window.addPostToBacklog = addPostToBacklog;
window.updatePostsDisplay = updatePostsDisplay;

export { updateProductDistribution, updatePostsList };

