/**
 * Dashboard Manager Module
 * Centralized dashboard functionality for loading data, updating stats, and managing charts
 * 
 * Usage:
 *   const dashboard = new DashboardManager({
 *       userType: 'teacher',
 *       apiEndpoint: '/api/dashboard-logs/',
 *       statCards: { ... },
 *       charts: { ... }
 *   });
 *   dashboard.load({ group: 'all', date_range: 'week' });
 */

class DashboardManager {
    constructor(config) {
        this.config = {
            userType: config.userType || 'student',
            apiEndpoint: config.apiEndpoint,
            statCards: config.statCards || {},
            charts: config.charts || {},
            onDataLoaded: config.onDataLoaded || null,
            onError: config.onError || null
        };
        
        this.currentData = null;
        this.controls = {};
        this.isLoading = false;
    }
    
    /**
     * Set up control elements (date pickers, selectors, etc.)
     */
    setupControls(controls) {
        this.controls = controls;
        
        // Setup date range control
        if (controls.dateRange) {
            const dateRangeEl = document.querySelector(controls.dateRange);
            if (dateRangeEl) {
                dateRangeEl.addEventListener('change', () => this.refresh());
            }
        }
        
        // Setup group selector
        if (controls.group) {
            const groupEl = document.querySelector(controls.group);
            if (groupEl) {
                groupEl.addEventListener('change', () => this.refresh());
            }
        }
        
        // Setup refresh button
        if (controls.refreshButton) {
            const refreshBtn = document.querySelector(controls.refreshButton);
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => this.refresh());
            }
        }
    }
    
    /**
     * Load dashboard data from API
     */
    async load(params = {}) {
        if (this.isLoading) return;
        
        this.isLoading = true;
        this.showLoadingState();
        
        try {
            const queryParams = new URLSearchParams(params);
            const response = await fetch(`${this.config.apiEndpoint}?${queryParams}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.currentData = data;
            
            // Update UI with data
            this.updateStatCards(data);
            this.updateCharts(data);
            
            // Call custom callback if provided
            if (this.config.onDataLoaded) {
                this.config.onDataLoaded(data);
            }
            
            this.hideLoadingState();
        } catch (error) {
            console.error('Dashboard load error:', error);
            this.handleError(error);
        } finally {
            this.isLoading = false;
        }
    }
    
    /**
     * Refresh dashboard with current control values
     */
    refresh() {
        const params = {};
        
        // Get date range
        if (this.controls.dateRange) {
            const dateRangeEl = document.querySelector(this.controls.dateRange);
            if (dateRangeEl) params.date_range = dateRangeEl.value;
        }
        
        // Get group/classroom
        if (this.controls.group) {
            const groupEl = document.querySelector(this.controls.group);
            if (groupEl) params.group = groupEl.value;
        }
        
        this.load(params);
    }
    
    /**
     * Update stat card values
     */
    updateStatCards(data) {
        Object.entries(this.config.statCards).forEach(([key, config]) => {
            const element = document.getElementById(config.id);
            if (!element) return;
            
            const value = this.getNestedValue(data, config.path);
            const formattedValue = this.formatValue(value, config.format);
            
            element.textContent = formattedValue;
            
            // Add animation
            element.classList.add('stat-updated');
            setTimeout(() => element.classList.remove('stat-updated'), 300);
        });
    }
    
    /**
     * Update dashboard charts
     */
    updateCharts(data) {
        Object.entries(this.config.charts).forEach(([key, config]) => {
            const chartData = this.getNestedValue(data, config.dataPath);
            if (!chartData) return;
            
            // Dispatch event for chart update (charts handle their own rendering)
            const event = new CustomEvent('dashboard-chart-update', {
                detail: {
                    chartId: config.id,
                    chartType: config.type,
                    data: chartData
                }
            });
            document.dispatchEvent(event);
        });
    }
    
    /**
     * Get nested value from object using dot notation
     */
    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => current?.[key], obj);
    }
    
    /**
     * Format value based on type
     */
    formatValue(value, format) {
        if (value === null || value === undefined) return '-';
        
        switch (format) {
            case 'number':
                return Number(value).toLocaleString();
            case 'percentage':
                return `${Number(value).toFixed(1)}%`;
            case 'currency':
                return `$${Number(value).toFixed(2)}`;
            case 'time':
                return this.formatMinutes(value);
            default:
                return String(value);
        }
    }
    
    /**
     * Format minutes to readable time
     */
    formatMinutes(minutes) {
        if (!minutes) return '0m';
        
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        
        if (hours > 0) {
            return `${hours}h ${mins}m`;
        }
        return `${mins}m`;
    }
    
    /**
     * Show loading state
     */
    showLoadingState() {
        // Add loading class to stat cards
        Object.values(this.config.statCards).forEach(config => {
            const element = document.getElementById(config.id);
            if (element) {
                element.textContent = '-';
                element.classList.add('loading');
            }
        });
        
        // Disable refresh button
        if (this.controls.refreshButton) {
            const btn = document.querySelector(this.controls.refreshButton);
            if (btn) btn.disabled = true;
        }
    }
    
    /**
     * Hide loading state
     */
    hideLoadingState() {
        // Remove loading class
        Object.values(this.config.statCards).forEach(config => {
            const element = document.getElementById(config.id);
            if (element) element.classList.remove('loading');
        });
        
        // Enable refresh button
        if (this.controls.refreshButton) {
            const btn = document.querySelector(this.controls.refreshButton);
            if (btn) btn.disabled = false;
        }
    }
    
    /**
     * Handle errors
     */
    handleError(error) {
        console.error('Dashboard error:', error);
        
        if (this.config.onError) {
            this.config.onError(error);
        } else {
            // Default error handling
            alert('Failed to load dashboard data. Please try again.');
        }
    }
    
    /**
     * Export current data as CSV
     */
    exportCSV(filename = 'dashboard-data.csv') {
        if (!this.currentData) {
            alert('No data to export');
            return;
        }
        
        // Convert data to CSV (basic implementation)
        const csv = this.convertToCSV(this.currentData);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        window.URL.revokeObjectURL(url);
    }
    
    /**
     * Convert object to CSV
     */
    convertToCSV(data) {
        // Simple CSV conversion (can be enhanced)
        const headers = Object.keys(data[0] || {});
        const rows = data.map(row => 
            headers.map(header => JSON.stringify(row[header] || '')).join(',')
        );
        
        return [headers.join(','), ...rows].join('\n');
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.DashboardManager = DashboardManager;
}

