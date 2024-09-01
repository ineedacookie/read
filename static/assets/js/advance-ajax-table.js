const advanceAjaxTableInit = () => {
    const togglePaginationButtonDisable = (button, disabled) => {
        const updatedButton = button;
        updatedButton.disabled = disabled;
        updatedButton.classList[disabled ? 'add' : 'remove']('disabled');
    };

    // Selectors
    const table = document.getElementById('advanceAjaxTable');

    if (table) {
        const options = {
            valueNames: ['id', 'first_name', 'last_initial', 'email'],
            page: 10,
            pagination: {
                item: "<li><button class='page' type='button'></button></li>"
            },
            item: values => {
                const { first_name, last_initial, email, id } = values;
                return `
                    <tr class="btn-reveal-trigger">
                        <td class="order py-2 align-middle white-space-nowrap">
                            <strong>${first_name} ${last_initial}.</strong>
                        </td>
                        <td class="py-2 align-middle">
                            ${email}
                        </td>
                        <td class="py-2 align-middle white-space-nowrap text-end">
                            <div class="dropstart font-sans-serif position-static d-inline-block">
                                <button class="btn btn-link text-600 btn-sm dropdown-toggle btn-reveal"
                                    type='button'
                                    id="order-dropdown-${id}"
                                    data-bs-toggle="dropdown"
                                    data-boundary="window"
                                    aria-haspopup="true"
                                    aria-expanded="false"
                                    data-bs-reference="parent">
                                    <span class="fas fa-ellipsis-h fs-10"></span>
                                </button>
                                <div class="dropdown-menu dropdown-menu-end border py-2"
                                    aria-labelledby="order-dropdown-${id}">
                                    <a href="#!" class="dropdown-item">View</a>
                                    <a href="#!" class="dropdown-item">Edit</a>
                                    <a href="#!" class="dropdown-item">Delete</a>
                                </div>
                            </div>
                        </td>
                    </tr>
                `;
            }
        };

        const paginationButtonNext = table.querySelector('[data-list-pagination="next"]');
        const paginationButtonPrev = table.querySelector('[data-list-pagination="prev"]');
        const viewAll = table.querySelector('[data-list-view="*"]');
        const viewLess = table.querySelector('[data-list-view="less"]');
        const listInfo = table.querySelector('[data-list-info]');
        const listFilter = document.querySelector('[data-list-filter]');

        // Initialize List.js instance with options
        var orderList = new window.List(table, options);

        // Fallback
        orderList.on('updated', item => {
            const fallback = table.querySelector('.fallback') || document.getElementById(options.fallback);

            if (fallback) {
                if (item.matchingItems.length === 0) {
                    fallback.classList.remove('d-none');
                } else {
                    fallback.classList.add('d-none');
                }
            }
        });

        const totalItem = orderList.items.length;
        const itemsPerPage = orderList.page;
        const btnDropdownClose = orderList.listContainer.querySelector('.btn-close');
        let pageQuantity = Math.ceil(totalItem / itemsPerPage);
        let numberOfcurrentItems = orderList.visibleItems.length;
        let pageCount = 1;

        btnDropdownClose &&
            btnDropdownClose.addEventListener('search.close', () => orderList.fuzzySearch(''));

        const updateListControls = () => {
            listInfo &&
                (listInfo.innerHTML = `${orderList.i} to ${numberOfcurrentItems} of ${totalItem}`);
            paginationButtonPrev && togglePaginationButtonDisable(paginationButtonPrev, pageCount === 1);
            if (paginationButtonNext) {
                togglePaginationButtonDisable(paginationButtonNext, pageCount === pageQuantity);
            }

            if (pageCount > 1 && pageCount < pageQuantity) {
                togglePaginationButtonDisable(paginationButtonNext, false);
                togglePaginationButtonDisable(paginationButtonPrev, false);
            }
        };

        updateListControls();

        if (paginationButtonNext) {
            paginationButtonNext.addEventListener('click', e => {
                e.preventDefault();
                pageCount += 1;
                const nextInitialIndex = orderList.i + itemsPerPage;
                if (nextInitialIndex <= totalItem) {
                    orderList.show(nextInitialIndex, itemsPerPage);
                    updateListControls();
                } else {
                    pageCount -= 1;
                }
            });
        }

        if (paginationButtonPrev) {
            paginationButtonPrev.addEventListener('click', e => {
                e.preventDefault();
                pageCount -= 1;
                const prevInitialIndex = orderList.i - itemsPerPage;
                if (prevInitialIndex >= 0) {
                    orderList.show(prevInitialIndex, itemsPerPage);
                    updateListControls();
                } else {
                    pageCount += 1;
                }
            });
        }

        // Sorting functionality
        document.querySelectorAll('[data-sort]').forEach(header => {
            header.addEventListener('click', function () {
                const sortField = this.getAttribute('data-sort');
                let order = this.getAttribute('data-order') || 'asc';
                order = order === 'asc' ? 'desc' : 'asc';
                this.setAttribute('data-order', order);

                // Sort list items
                orderList.sort(sortField, { order });
            });
        });
    }
};

document.addEventListener('DOMContentLoaded', advanceAjaxTableInit);