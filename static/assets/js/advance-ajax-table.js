const advanceAjaxTableInit = () => {
    const togglePaginationButtonDisable = (button, disabled) => {
        const updatedButton = button;
        updatedButton.disabled = disabled;
        updatedButton.classList[disabled ? 'add' : 'remove']('disabled');
    };

    // Selectors
    const table = document.getElementById('advanceAjaxTable');

    if (table) {
        const rows = Array.from(table.querySelectorAll('tbody tr'));
        const viewAll = table.querySelector('[data-list-view="*"]');
        const viewLess = table.querySelector('[data-list-view="less"]');
        const listInfo = table.querySelector('[data-list-info]');
        const listFilter = document.querySelector('[data-list-filter]');

        let totalItem = rows.length;
        let itemsPerPage = 10;
        let pageCount = 1;
        let pageQuantity = Math.ceil(totalItem / itemsPerPage);
        
        const updateList = (page) => {
            const start = (page - 1) * itemsPerPage;
            const end = page * itemsPerPage;
            rows.forEach((row, index) => {
                row.style.display = index >= start && index < end ? '' : 'none';
            });
            updateListControls();
        };

        const updateListControls = () => {
            listInfo && (listInfo.innerHTML = `${(pageCount - 1) * itemsPerPage + 1} to ${Math.min(pageCount * itemsPerPage, totalItem)} of ${totalItem}`);
            paginationButtonPrev && togglePaginationButtonDisable(paginationButtonPrev, pageCount === 1);
            paginationButtonNext && togglePaginationButtonDisable(paginationButtonNext, pageCount === pageQuantity);
        };

        const paginationButtonNext = table.querySelector('[data-list-pagination="next"]');
        const paginationButtonPrev = table.querySelector('[data-list-pagination="prev"]');

        paginationButtonNext && paginationButtonNext.addEventListener('click', e => {
            e.preventDefault();
            if (pageCount < pageQuantity) {
                pageCount += 1;
                updateList(pageCount);
            }
        });

        paginationButtonPrev && paginationButtonPrev.addEventListener('click', e => {
            e.preventDefault();
            if (pageCount > 1) {
                pageCount -= 1;
                updateList(pageCount);
            }
        });

        updateList(pageCount);

        if (listFilter) {
            listFilter.addEventListener('input', e => {
                const filterValue = e.target.value.toLowerCase();
                rows.forEach(row => {
                    const rowText = row.textContent.toLowerCase();
                    row.style.display = rowText.includes(filterValue) ? '' : 'none';
                });
                totalItem = rows.filter(row => row.style.display === '').length;
                pageQuantity = Math.ceil(totalItem / itemsPerPage);
                pageCount = 1;
                updateList(pageCount);
            });
        }

        document.querySelectorAll('[data-sort]').forEach(header => {
            header.addEventListener('click', function () {
                const sortField = this.getAttribute('data-sort');
                const sortOrder = this.getAttribute('data-order') || 'asc';
                const newOrder = sortOrder === 'asc' ? 'desc' : 'asc';
                this.setAttribute('data-order', newOrder);

                rows.sort((a, b) => {
                    const aText = a.querySelector(`.${sortField}`).textContent.trim();
                    const bText = b.querySelector(`.${sortField}`).textContent.trim();
                    return newOrder === 'asc' ? aText.localeCompare(bText) : bText.localeCompare(aText);
                });

                rows.forEach(row => table.querySelector('tbody').appendChild(row));
                updateList(pageCount);
            });
        });
    }
};

document.addEventListener('DOMContentLoaded', advanceAjaxTableInit);