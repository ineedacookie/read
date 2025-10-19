/**
 * Date Range Picker Component JavaScript
 * 
 * Provides functionality for the reusable date range picker component
 * Includes navigation, date formatting, and callback handling
 */

// Global object to store date range picker instances
window.dateRangePickers = window.dateRangePickers || {};

/**
 * Initialize a date range picker component
 * @param {string} id - The unique identifier for the picker
 * @param {Object} options - Configuration options
 */
function initializeDateRangePicker(id, options = {}) {
    const defaults = {
        showNavigation: true,
        callbackFunction: null,
        initialRange: null,
        dateFormat: 'M j, Y'
    };
    
    const config = { ...defaults, ...options };
    
    // Store the instance configuration
    window.dateRangePickers[id] = config;
    
    // Get the input element
    const inputElement = document.getElementById(id);
    if (!inputElement) {
        console.error(`Date range picker element with id "${id}" not found`);
        return;
    }
    
    // Set initial value if provided, otherwise set to current week
    if (config.initialRange) {
        inputElement.value = config.initialRange;
    } else {
        inputElement.value = getCurrentWeekRange();
    }
    
    // Add change event listener
    inputElement.addEventListener('change', function() {
        if (config.callbackFunction && typeof window[config.callbackFunction] === 'function') {
            window[config.callbackFunction]();
        }
    });
    
    // Setup navigation buttons if enabled
    if (config.showNavigation) {
        setupNavigationButtons(id);
    }
    
    console.log(`📅 Date range picker "${id}" initialized with value:`, inputElement.value);
}

/**
 * Setup navigation buttons for a date range picker
 * @param {string} id - The picker identifier
 */
function setupNavigationButtons(id) {
    const prevButton = document.getElementById(`${id}_prev`);
    const nextButton = document.getElementById(`${id}_next`);
    
    if (prevButton) {
        prevButton.addEventListener('click', () => adjustDateRange(id, -7));
    }
    
    if (nextButton) {
        nextButton.addEventListener('click', () => adjustDateRange(id, 7));
    }
}

/**
 * Adjust the date range by a specified number of days
 * @param {string} id - The picker identifier
 * @param {number} days - Number of days to adjust (positive or negative)
 */
function adjustDateRange(id, days) {
    const inputElement = document.getElementById(id);
    const config = window.dateRangePickers[id];
    
    if (!inputElement || !config) {
        console.error(`Date range picker "${id}" not found`);
        return;
    }
    
    const currentRange = inputElement.value.split(' to ');
    if (currentRange.length !== 2) {
        console.error('Invalid date range format');
        return;
    }
    
    const startDate = new Date(currentRange[0]);
    const newStartDate = new Date(startDate.setDate(startDate.getDate() + days));
    
    inputElement.value = getWeekRange(newStartDate);
    
    // Trigger callback if configured
    if (config.callbackFunction && typeof window[config.callbackFunction] === 'function') {
        window[config.callbackFunction]();
    }
}

/**
 * Get the current week date range
 * @returns {string} Formatted date range string
 */
function getCurrentWeekRange() {
    return getWeekRange(new Date());
}

/**
 * Get a week date range for a specific date
 * @param {Date} date - The date to calculate week range for
 * @returns {string} Formatted date range string
 */
function getWeekRange(date = new Date()) {
    const curr = new Date(date);
    const first = curr.getDate() - curr.getDay(); // First day is Sunday
    const last = first + 6; // Last day is Saturday
    
    const firstDay = new Date(curr.setDate(first));
    const lastDay = new Date(curr.setDate(last));
    
    return `${formatDate(firstDay)} to ${formatDate(lastDay)}`;
}

/**
 * Format a date object to string
 * @param {Date} date - The date to format
 * @returns {string} Formatted date string
 */
function formatDate(date) {
    return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric', 
        year: 'numeric' 
    });
}

/**
 * Get the current value of a date range picker
 * @param {string} id - The picker identifier
 * @returns {string|null} Current date range value
 */
function getDateRangeValue(id) {
    const inputElement = document.getElementById(id);
    return inputElement ? inputElement.value : null;
}

/**
 * Set the value of a date range picker
 * @param {string} id - The picker identifier
 * @param {string} value - The date range value to set
 */
function setDateRangeValue(id, value) {
    const inputElement = document.getElementById(id);
    const config = window.dateRangePickers[id];
    
    if (inputElement) {
        inputElement.value = value;
        
        // Trigger callback if configured
        if (config && config.callbackFunction && typeof window[config.callbackFunction] === 'function') {
            window[config.callbackFunction]();
        }
    }
}

/**
 * Parse a date range string into start and end dates
 * @param {string} dateRangeString - Date range in "MMM d, yyyy to MMM d, yyyy" format
 * @returns {Object} Object with startDate and endDate properties
 */
function parseDateRange(dateRangeString) {
    if (!dateRangeString || !dateRangeString.includes(' to ')) {
        return { startDate: null, endDate: null };
    }
    
    const [startStr, endStr] = dateRangeString.split(' to ');
    
    return {
        startDate: new Date(startStr),
        endDate: new Date(endStr)
    };
}

// Export functions for global access
window.initializeDateRangePicker = initializeDateRangePicker;
window.adjustDateRange = adjustDateRange;
window.getCurrentWeekRange = getCurrentWeekRange;
window.getWeekRange = getWeekRange;
window.getDateRangeValue = getDateRangeValue;
window.setDateRangeValue = setDateRangeValue;
window.parseDateRange = parseDateRange;
