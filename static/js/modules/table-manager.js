/**
 * Table Manager Module
 * Centralized table operations for sorting, filtering, and pagination
 * 
 * Usage:
 *   const tableManager = new TableManager('#myTable', {
 *       sortable: true,
 *       filterable: true,
 *       paginate: true
 *   });
 */

class TableManager {
    constructor(tableSelector, options = {}) {
        this.table = document.querySelector(tableSelector);
        if (!this.table) {
            console.error(`Table '${tableSelector}' not found`);
            return;
        }
        
        this.options = {
            sortable: options.sortable !== false,
            filterable: options.filterable !== false,
            paginate: options.paginate || false,
            rowsPerPage: options.rowsPerPage || 10,
            onRowClick: options.onRowClick || null
        };
        
        this.tbody = this.table.querySelector('tbody');
        this.currentSort = { column: null, direction: 'asc' };
        this.currentPage = 1;
        this.allRows = [];
        
        this.init();
    }
    
    init() {
        // Store all rows
        this.allRows = Array.from(this.tbody.querySelectorAll('tr'));
        
        // Setup sortable headers
        if (this.options.sortable) {
            this.setupSorting();
        }
        
        // Setup row click handlers
        if (this.options.onRowClick) {
            this.setupRowClick();
        }
        
        // Setup pagination
        if (this.options.paginate) {
            this.setupPagination();
        }
    }
    
    setupSorting() {
        const headers = this.table.querySelectorAll('th[data-sortable]');
        
        headers.forEach(header => {
            header.style.cursor = 'pointer';
            header.innerHTML += ' <i class="fas fa-sort ms-1"></i>';
            
            header.addEventListener('click', () => {
                const column = header.dataset.column || header.cellIndex;
                this.sort(column);
            });
        });
    }
    
    setupRowClick() {
        this.tbody.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            if (row && this.options.onRowClick) {
                this.options.onRowClick(row, e);
            }
        });
    }
    
    setupPagination() {
        const paginationContainer = document.createElement('div');
        paginationContainer.className = 'pagination-container mt-3';
        this.table.parentNode.appendChild(paginationContainer);
        
        this.updatePagination();
    }
    
    sort(column) {
        const direction = this.currentSort.column === column && this.currentSort.direction === 'asc' 
            ? 'desc' 
            : 'asc';
        
        this.currentSort = { column, direction };
        
        // Sort rows
        this.allRows.sort((a, b) => {
            const aValue = a.cells[column]?.textContent.trim() || '';
            const bValue = b.cells[column]?.textContent.trim() || '';
            
            // Try to sort as numbers if possible
            const aNum = parseFloat(aValue);
            const bNum = parseFloat(bValue);
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return direction === 'asc' ? aNum - bNum : bNum - aNum;
            }
            
            // Sort as strings
            return direction === 'asc' 
                ? aValue.localeCompare(bValue)
                : bValue.localeCompare(aValue);
        });
        
        // Update sort icons
        this.table.querySelectorAll('th i').forEach(icon => {
            icon.className = 'fas fa-sort ms-1';
        });
        
        const activeHeader = this.table.querySelector(`th[data-column="${column}"]`) 
            || this.table.querySelectorAll('th')[column];
        
        if (activeHeader) {
            const icon = activeHeader.querySelector('i');
            if (icon) {
                icon.className = `fas fa-sort-${direction === 'asc' ? 'up' : 'down'} ms-1`;
            }
        }
        
        this.render();
    }
    
    filter(searchTerm) {
        searchTerm = searchTerm.toLowerCase();
        
        this.allRows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        });
        
        if (this.options.paginate) {
            this.currentPage = 1;
            this.updatePagination();
        }
    }
    
    render() {
        // Clear tbody
        this.tbody.innerHTML = '';
        
        // Render rows
        const start = this.options.paginate ? (this.currentPage - 1) * this.options.rowsPerPage : 0;
        const end = this.options.paginate ? start + this.options.rowsPerPage : this.allRows.length;
        
        this.allRows.slice(start, end).forEach(row => {
            this.tbody.appendChild(row);
        });
        
        if (this.options.paginate) {
            this.updatePagination();
        }
    }
    
    updatePagination() {
        const container = this.table.parentNode.querySelector('.pagination-container');
        if (!container) return;
        
        const totalPages = Math.ceil(this.allRows.length / this.options.rowsPerPage);
        
        let html = '<nav><ul class="pagination">';
        
        // Previous button
        html += `<li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${this.currentPage - 1}">Previous</a>
        </li>`;
        
        // Page numbers
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                html += `<li class="page-item ${i === this.currentPage ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>`;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }
        
        // Next button
        html += `<li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" data-page="${this.currentPage + 1}">Next</a>
        </li>`;
        
        html += '</ul></nav>';
        
        container.innerHTML = html;
        
        // Add click handlers
        container.querySelectorAll('a[data-page]').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(link.dataset.page);
                if (page > 0 && page <= totalPages) {
                    this.currentPage = page;
                    this.render();
                }
            });
        });
    }
    
    refresh() {
        this.allRows = Array.from(this.tbody.querySelectorAll('tr'));
        this.render();
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.TableManager = TableManager;
}

