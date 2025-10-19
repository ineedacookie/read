/**
 * API utility functions to reduce code duplication in AJAX calls
 * Provides standardized patterns for making API requests and handling responses
 */

// Global API configuration
const API_CONFIG = {
    timeout: 30000, // 30 seconds
    retryAttempts: 3,
    retryDelay: 1000, // 1 second
    csrfToken: null
};

// Initialize CSRF token
function initializeCSRF() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfToken) {
        API_CONFIG.csrfToken = csrfToken.value;
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', initializeCSRF);

/**
 * Show loading state for an element
 * @param {HTMLElement|string} element - Element or selector
 * @param {string} loadingText - Text to show while loading
 */
function showLoading(element, loadingText = 'Loading...') {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el) {
        el.dataset.originalContent = el.innerHTML;
        el.innerHTML = `<i class="spinner-border spinner-border-sm me-2"></i>${loadingText}`;
        el.disabled = true;
    }
}

/**
 * Hide loading state for an element
 * @param {HTMLElement|string} element - Element or selector
 */
function hideLoading(element) {
    const el = typeof element === 'string' ? document.querySelector(element) : element;
    if (el && el.dataset.originalContent) {
        el.innerHTML = el.dataset.originalContent;
        el.disabled = false;
        delete el.dataset.originalContent;
    }
}

/**
 * Show alert message
 * @param {string} type - Alert type (success, error, warning, info)
 * @param {string} message - Alert message
 * @param {string} container - Container selector (default: '#alert-container')
 */
function showAlert(type = 'info', message = '', container = '#alert-container') {
    const alertContainer = document.querySelector(container);
    if (!alertContainer) return;

    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';

    const alertHTML = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    alertContainer.innerHTML = alertHTML;

    // Auto-dismiss after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            const alert = alertContainer.querySelector('.alert');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    }
}

/**
 * Clear all alerts
 * @param {string} container - Container selector
 */
function clearAlerts(container = '#alert-container') {
    const alertContainer = document.querySelector(container);
    if (alertContainer) {
        alertContainer.innerHTML = '';
    }
}

/**
 * Create standardized fetch options
 * @param {string} method - HTTP method
 * @param {Object} data - Request data
 * @param {Object} options - Additional options
 * @returns {Object} Fetch options
 */
function createFetchOptions(method = 'GET', data = null, options = {}) {
    const fetchOptions = {
        method: method.toUpperCase(),
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            ...options.headers
        },
        credentials: 'same-origin',
        ...options
    };

    // Add CSRF token for non-GET requests
    if (method.toUpperCase() !== 'GET' && API_CONFIG.csrfToken) {
        fetchOptions.headers['X-CSRFToken'] = API_CONFIG.csrfToken;
    }

    // Handle request data
    if (data) {
        if (options.contentType === 'application/json' || 
            (!options.contentType && typeof data === 'object')) {
            fetchOptions.headers['Content-Type'] = 'application/json';
            fetchOptions.body = JSON.stringify(data);
        } else if (data instanceof FormData) {
            fetchOptions.body = data;
        } else {
            fetchOptions.headers['Content-Type'] = 'application/x-www-form-urlencoded';
            fetchOptions.body = new URLSearchParams(data);
        }
    }

    return fetchOptions;
}

/**
 * Handle API response
 * @param {Response} response - Fetch response
 * @returns {Promise} Parsed response data
 */
async function handleResponse(response) {
    const contentType = response.headers.get('content-type');
    
    let data;
    if (contentType && contentType.includes('application/json')) {
        data = await response.json();
    } else {
        data = await response.text();
    }

    if (!response.ok) {
        const error = new Error(data.message || `HTTP ${response.status}: ${response.statusText}`);
        error.status = response.status;
        error.data = data;
        throw error;
    }

    return data;
}

/**
 * Make API request with retry logic
 * @param {string} url - Request URL
 * @param {Object} options - Fetch options
 * @param {number} attempt - Current attempt number
 * @returns {Promise} Response data
 */
async function makeRequestWithRetry(url, options, attempt = 1) {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeout);
        
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        return await handleResponse(response);
        
    } catch (error) {
        if (attempt < API_CONFIG.retryAttempts && 
            (error.name === 'AbortError' || error.status >= 500)) {
            
            await new Promise(resolve => 
                setTimeout(resolve, API_CONFIG.retryDelay * attempt)
            );
            
            return makeRequestWithRetry(url, options, attempt + 1);
        }
        
        throw error;
    }
}

/**
 * Generic API request function
 * @param {string} url - Request URL
 * @param {string} method - HTTP method
 * @param {Object} data - Request data
 * @param {Object} options - Additional options
 * @returns {Promise} Response data
 */
async function apiRequest(url, method = 'GET', data = null, options = {}) {
    const fetchOptions = createFetchOptions(method, data, options);
    return await makeRequestWithRetry(url, fetchOptions);
}

/**
 * GET request
 * @param {string} url - Request URL
 * @param {Object} params - URL parameters
 * @param {Object} options - Additional options
 * @returns {Promise} Response data
 */
async function apiGet(url, params = null, options = {}) {
    let requestUrl = url;
    if (params) {
        const urlParams = new URLSearchParams(params);
        requestUrl += (url.includes('?') ? '&' : '?') + urlParams.toString();
    }
    return await apiRequest(requestUrl, 'GET', null, options);
}

/**
 * POST request
 * @param {string} url - Request URL
 * @param {Object} data - Request data
 * @param {Object} options - Additional options
 * @returns {Promise} Response data
 */
async function apiPost(url, data = null, options = {}) {
    return await apiRequest(url, 'POST', data, options);
}

/**
 * PUT request
 * @param {string} url - Request URL
 * @param {Object} data - Request data
 * @param {Object} options - Additional options
 * @returns {Promise} Response data
 */
async function apiPut(url, data = null, options = {}) {
    return await apiRequest(url, 'PUT', data, options);
}

/**
 * DELETE request
 * @param {string} url - Request URL
 * @param {Object} data - Request data
 * @param {Object} options - Additional options
 * @returns {Promise} Response data
 */
async function apiDelete(url, data = null, options = {}) {
    return await apiRequest(url, 'DELETE', data, options);
}

/**
 * Handle form submission with API
 * @param {HTMLFormElement} form - Form element
 * @param {Object} options - Options (url, method, onSuccess, onError, etc.)
 */
async function handleFormSubmission(form, options = {}) {
    const {
        url = form.action,
        method = form.method || 'POST',
        onSuccess = null,
        onError = null,
        showSuccessAlert = true,
        showErrorAlert = true,
        loadingElement = null,
        resetForm = false
    } = options;

    try {
        if (loadingElement) {
            showLoading(loadingElement);
        }

        clearAlerts();

        const formData = new FormData(form);
        const response = await apiRequest(url, method, formData);

        if (showSuccessAlert && response.message) {
            showAlert('success', response.message);
        }

        if (resetForm) {
            form.reset();
        }

        if (onSuccess) {
            onSuccess(response);
        }

    } catch (error) {
        console.error('Form submission error:', error);

        let errorMessage = 'An error occurred. Please try again.';
        
        if (error.data && error.data.errors) {
            // Handle form validation errors
            displayFormErrors(form, error.data.errors);
        } else if (error.data && error.data.message) {
            errorMessage = error.data.message;
        } else if (error.message) {
            errorMessage = error.message;
        }

        if (showErrorAlert) {
            showAlert('error', errorMessage);
        }

        if (onError) {
            onError(error);
        }

    } finally {
        if (loadingElement) {
            hideLoading(loadingElement);
        }
    }
}

/**
 * Display form validation errors
 * @param {HTMLFormElement} form - Form element
 * @param {Object} errors - Validation errors
 */
function displayFormErrors(form, errors) {
    // Clear existing errors
    form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

    // Display new errors
    Object.keys(errors).forEach(fieldName => {
        const field = form.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.classList.add('is-invalid');
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback';
            errorDiv.textContent = Array.isArray(errors[fieldName]) 
                ? errors[fieldName][0] 
                : errors[fieldName];
            
            field.parentNode.appendChild(errorDiv);
        }
    });
}

/**
 * Clear form validation errors
 * @param {HTMLFormElement} form - Form element
 */
function clearFormErrors(form) {
    form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
}

/**
 * Load data into a table
 * @param {string} tableSelector - Table selector
 * @param {Array} data - Table data
 * @param {Object} options - Options (columns, emptyMessage, etc.)
 */
function loadTableData(tableSelector, data, options = {}) {
    const table = document.querySelector(tableSelector);
    if (!table) return;

    const tbody = table.querySelector('tbody');
    if (!tbody) return;

    const {
        columns = [],
        emptyMessage = 'No data available',
        rowClass = '',
        onRowClick = null
    } = options;

    if (!data || data.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="100%" class="text-center text-muted py-4">
                    ${emptyMessage}
                </td>
            </tr>
        `;
        return;
    }

    const rows = data.map(item => {
        const cells = columns.map(col => {
            let value = '';
            
            if (typeof col === 'string') {
                value = item[col] || '';
            } else if (typeof col === 'object') {
                if (col.key) {
                    value = item[col.key] || '';
                }
                
                if (col.formatter && typeof col.formatter === 'function') {
                    value = col.formatter(value, item);
                }
            }
            
            return `<td>${value}</td>`;
        }).join('');

        const clickHandler = onRowClick ? `onclick="(${onRowClick.toString()})(${JSON.stringify(item)})"` : '';
        
        return `<tr class="${rowClass}" ${clickHandler}>${cells}</tr>`;
    }).join('');

    tbody.innerHTML = rows;
}

/**
 * Setup automatic form handling
 * @param {string} formSelector - Form selector
 * @param {Object} options - Options for form handling
 */
function setupFormHandler(formSelector, options = {}) {
    const form = document.querySelector(formSelector);
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await handleFormSubmission(form, options);
    });

    // Clear errors on input
    form.addEventListener('input', (e) => {
        if (e.target.classList.contains('is-invalid')) {
            e.target.classList.remove('is-invalid');
            const feedback = e.target.parentNode.querySelector('.invalid-feedback');
            if (feedback) {
                feedback.remove();
            }
        }
    });
}

/**
 * Debounce function to limit function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Setup search functionality with debouncing
 * @param {string} inputSelector - Search input selector
 * @param {Function} searchFunction - Function to call for search
 * @param {number} delay - Debounce delay in milliseconds
 */
function setupSearch(inputSelector, searchFunction, delay = 300) {
    const input = document.querySelector(inputSelector);
    if (!input) return;

    const debouncedSearch = debounce(searchFunction, delay);
    
    input.addEventListener('input', (e) => {
        debouncedSearch(e.target.value);
    });
}

// Export functions for use in other scripts
window.APIUtils = {
    // Core API functions
    apiRequest,
    apiGet,
    apiPost,
    apiPut,
    apiDelete,
    
    // UI helpers
    showLoading,
    hideLoading,
    showAlert,
    clearAlerts,
    
    // Form helpers
    handleFormSubmission,
    displayFormErrors,
    clearFormErrors,
    setupFormHandler,
    
    // Table helpers
    loadTableData,
    
    // Utility functions
    debounce,
    setupSearch,
    
    // Configuration
    config: API_CONFIG
};

