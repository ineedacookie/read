/**
 * UI utility functions to reduce code duplication in interface components
 * Provides common UI patterns, modal handling, and interactive elements
 */

/**
 * Modal utility functions
 */
const ModalUtils = {
    /**
     * Show a confirmation modal
     * @param {string} title - Modal title
     * @param {string} message - Modal message
     * @param {Function} onConfirm - Callback for confirm action
     * @param {Object} options - Additional options
     */
    showConfirmation(title, message, onConfirm, options = {}) {
        const {
            confirmText = 'Confirm',
            cancelText = 'Cancel',
            confirmClass = 'btn-danger',
            size = '',
            onCancel = null
        } = options;

        const modalId = 'confirmationModal';
        let modal = document.getElementById(modalId);
        
        if (!modal) {
            modal = this.createConfirmationModal(modalId);
            document.body.appendChild(modal);
        }

        // Update modal content
        modal.querySelector('.modal-title').textContent = title;
        modal.querySelector('.modal-body').innerHTML = message;
        modal.querySelector('.btn-confirm').textContent = confirmText;
        modal.querySelector('.btn-confirm').className = `btn ${confirmClass}`;
        modal.querySelector('.btn-cancel').textContent = cancelText;

        // Update size
        const modalDialog = modal.querySelector('.modal-dialog');
        modalDialog.className = `modal-dialog ${size}`;

        // Set up event handlers
        const confirmBtn = modal.querySelector('.btn-confirm');
        const cancelBtn = modal.querySelector('.btn-cancel');

        // Remove existing listeners
        confirmBtn.replaceWith(confirmBtn.cloneNode(true));
        cancelBtn.replaceWith(cancelBtn.cloneNode(true));

        // Add new listeners
        modal.querySelector('.btn-confirm').addEventListener('click', () => {
            if (onConfirm) onConfirm();
            bootstrap.Modal.getInstance(modal).hide();
        });

        modal.querySelector('.btn-cancel').addEventListener('click', () => {
            if (onCancel) onCancel();
            bootstrap.Modal.getInstance(modal).hide();
        });

        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    /**
     * Create confirmation modal HTML
     * @param {string} modalId - Modal ID
     * @returns {HTMLElement} Modal element
     */
    createConfirmationModal(modalId) {
        const modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title"></h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body"></div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary btn-cancel" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-danger btn-confirm">Confirm</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        const container = document.createElement('div');
        container.innerHTML = modalHTML;
        return container.firstElementChild;
    },

    /**
     * Show a general modal with custom content
     * @param {string} title - Modal title
     * @param {string} content - Modal content (HTML)
     * @param {Object} options - Modal options
     */
    showModal(title, content, options = {}) {
        const {
            size = '',
            footer = null,
            onShow = null,
            onHide = null
        } = options;

        const modalId = 'generalModal';
        let modal = document.getElementById(modalId);
        
        if (!modal) {
            modal = this.createGeneralModal(modalId);
            document.body.appendChild(modal);
        }

        // Update modal content
        modal.querySelector('.modal-title').textContent = title;
        modal.querySelector('.modal-body').innerHTML = content;

        // Update size
        const modalDialog = modal.querySelector('.modal-dialog');
        modalDialog.className = `modal-dialog ${size}`;

        // Update footer
        const footerElement = modal.querySelector('.modal-footer');
        if (footer) {
            footerElement.innerHTML = footer;
            footerElement.style.display = 'block';
        } else {
            footerElement.style.display = 'none';
        }

        // Set up event handlers
        if (onShow) {
            modal.addEventListener('shown.bs.modal', onShow, { once: true });
        }
        if (onHide) {
            modal.addEventListener('hidden.bs.modal', onHide, { once: true });
        }

        // Show modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    /**
     * Create general modal HTML
     * @param {string} modalId - Modal ID
     * @returns {HTMLElement} Modal element
     */
    createGeneralModal(modalId) {
        const modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title"></h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body"></div>
                        <div class="modal-footer"></div>
                    </div>
                </div>
            </div>
        `;
        
        const container = document.createElement('div');
        container.innerHTML = modalHTML;
        return container.firstElementChild;
    }
};

/**
 * Loading state utilities
 */
const LoadingUtils = {
    /**
     * Create a loading spinner element
     * @param {string} text - Loading text
     * @param {string} size - Spinner size (sm, md, lg)
     * @returns {string} HTML string
     */
    createSpinner(text = 'Loading...', size = 'sm') {
        const sizeClass = size === 'sm' ? 'spinner-border-sm' : '';
        return `
            <div class="d-flex align-items-center">
                <div class="spinner-border ${sizeClass} me-2" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                ${text}
            </div>
        `;
    },

    /**
     * Show loading overlay on an element
     * @param {HTMLElement|string} element - Element or selector
     * @param {string} text - Loading text
     */
    showOverlay(element, text = 'Loading...') {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        if (!el) return;

        // Remove existing overlay
        this.hideOverlay(el);

        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center';
        overlay.style.backgroundColor = 'rgba(255, 255, 255, 0.8)';
        overlay.style.zIndex = '1000';
        overlay.innerHTML = this.createSpinner(text, 'md');

        // Add to element
        el.style.position = 'relative';
        el.appendChild(overlay);
    },

    /**
     * Hide loading overlay from an element
     * @param {HTMLElement|string} element - Element or selector
     */
    hideOverlay(element) {
        const el = typeof element === 'string' ? document.querySelector(element) : element;
        if (!el) return;

        const overlay = el.querySelector('.loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
};

/**
 * Form utilities
 */
const FormUtils = {
    /**
     * Serialize form data to object
     * @param {HTMLFormElement} form - Form element
     * @returns {Object} Form data object
     */
    serializeToObject(form) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            if (data[key]) {
                // Handle multiple values (checkboxes, multi-select)
                if (Array.isArray(data[key])) {
                    data[key].push(value);
                } else {
                    data[key] = [data[key], value];
                }
            } else {
                data[key] = value;
            }
        }
        
        return data;
    },

    /**
     * Populate form with data
     * @param {HTMLFormElement} form - Form element
     * @param {Object} data - Data to populate
     */
    populateForm(form, data) {
        Object.keys(data).forEach(key => {
            const field = form.querySelector(`[name="${key}"]`);
            if (field) {
                if (field.type === 'checkbox' || field.type === 'radio') {
                    field.checked = Boolean(data[key]);
                } else if (field.tagName === 'SELECT') {
                    field.value = data[key];
                } else {
                    field.value = data[key] || '';
                }
            }
        });
    },

    /**
     * Reset form validation states
     * @param {HTMLFormElement} form - Form element
     */
    resetValidation(form) {
        form.classList.remove('was-validated');
        form.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
            el.classList.remove('is-valid', 'is-invalid');
        });
        form.querySelectorAll('.valid-feedback, .invalid-feedback').forEach(el => {
            el.remove();
        });
    },

    /**
     * Enable/disable form fields
     * @param {HTMLFormElement} form - Form element
     * @param {boolean} enabled - Whether to enable or disable
     */
    setFormEnabled(form, enabled) {
        const fields = form.querySelectorAll('input, select, textarea, button');
        fields.forEach(field => {
            field.disabled = !enabled;
        });
    }
};

/**
 * Table utilities
 */
const TableUtils = {
    /**
     * Sort table by column
     * @param {HTMLTableElement} table - Table element
     * @param {number} columnIndex - Column index to sort by
     * @param {string} direction - Sort direction ('asc' or 'desc')
     */
    sortByColumn(table, columnIndex, direction = 'asc') {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aText = a.cells[columnIndex]?.textContent.trim() || '';
            const bText = b.cells[columnIndex]?.textContent.trim() || '';
            
            // Try to parse as numbers
            const aNum = parseFloat(aText);
            const bNum = parseFloat(bText);
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return direction === 'asc' ? aNum - bNum : bNum - aNum;
            } else {
                return direction === 'asc' 
                    ? aText.localeCompare(bText)
                    : bText.localeCompare(aText);
            }
        });

        // Re-append sorted rows
        rows.forEach(row => tbody.appendChild(row));
    },

    /**
     * Setup sortable table headers
     * @param {HTMLTableElement} table - Table element
     */
    makeSortable(table) {
        const headers = table.querySelectorAll('thead th[data-sortable]');
        
        headers.forEach((header, index) => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {
                const currentDirection = header.dataset.sortDirection || 'asc';
                const newDirection = currentDirection === 'asc' ? 'desc' : 'asc';
                
                // Reset other headers
                headers.forEach(h => {
                    h.dataset.sortDirection = '';
                    h.classList.remove('sort-asc', 'sort-desc');
                });
                
                // Set current header
                header.dataset.sortDirection = newDirection;
                header.classList.add(`sort-${newDirection}`);
                
                this.sortByColumn(table, index, newDirection);
            });
        });
    },

    /**
     * Filter table rows
     * @param {HTMLTableElement} table - Table element
     * @param {string} searchText - Text to search for
     * @param {Array} columnIndexes - Columns to search in (default: all)
     */
    filterRows(table, searchText, columnIndexes = null) {
        const tbody = table.querySelector('tbody');
        if (!tbody) return;

        const rows = tbody.querySelectorAll('tr');
        const search = searchText.toLowerCase();

        rows.forEach(row => {
            let visible = false;
            
            if (!search) {
                visible = true;
            } else {
                const cells = columnIndexes 
                    ? columnIndexes.map(i => row.cells[i]).filter(Boolean)
                    : Array.from(row.cells);
                
                visible = cells.some(cell => 
                    cell.textContent.toLowerCase().includes(search)
                );
            }
            
            row.style.display = visible ? '' : 'none';
        });
    }
};

/**
 * Date utilities
 */
const DateUtils = {
    /**
     * Format date for display
     * @param {Date|string} date - Date to format
     * @param {string} format - Format type (short, long, datetime)
     * @returns {string} Formatted date
     */
    formatDate(date, format = 'short') {
        const d = new Date(date);
        
        switch (format) {
            case 'short':
                return d.toLocaleDateString();
            case 'long':
                return d.toLocaleDateString(undefined, { 
                    weekday: 'long', 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                });
            case 'datetime':
                return d.toLocaleString();
            default:
                return d.toLocaleDateString();
        }
    },

    /**
     * Get relative time string
     * @param {Date|string} date - Date to compare
     * @returns {string} Relative time string
     */
    getRelativeTime(date) {
        const now = new Date();
        const then = new Date(date);
        const diffMs = now - then;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
        if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
        return `${Math.floor(diffDays / 365)} years ago`;
    }
};

/**
 * Number utilities
 */
const NumberUtils = {
    /**
     * Format number with commas
     * @param {number} num - Number to format
     * @returns {string} Formatted number
     */
    addCommas(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },

    /**
     * Format bytes to human readable
     * @param {number} bytes - Bytes to format
     * @returns {string} Formatted size
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
};

/**
 * Setup common UI behaviors
 */
function setupCommonBehaviors() {
    // Setup tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Setup popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            if (bsAlert) {
                setTimeout(() => bsAlert.close(), 5000);
            }
        });
    }, 100);
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', setupCommonBehaviors);

// Export utilities
window.UIUtils = {
    Modal: ModalUtils,
    Loading: LoadingUtils,
    Form: FormUtils,
    Table: TableUtils,
    Date: DateUtils,
    Number: NumberUtils,
    setupCommonBehaviors
};

