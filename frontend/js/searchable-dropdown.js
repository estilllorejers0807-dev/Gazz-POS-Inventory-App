document.addEventListener("DOMContentLoaded", function () {

    /*
     * =========================================================
     * SEARCHABLE DROPDOWN
     * =========================================================
     *
     * Any <select> with:
     *
     *     class="searchable-select"
     *
     * will automatically get a search box.
     */

    document.querySelectorAll(
        ".searchable-select"
    ).forEach(function (select) {

        createSearchableDropdown(select);

    });


    function createSearchableDropdown(select) {

        /*
         * Prevent duplicate initialization
         */
        if (
            select.dataset.searchInitialized === "true"
        ) {
            return;
        }

        select.dataset.searchInitialized = "true";


        /*
         * =====================================================
         * CREATE SEARCH INPUT
         * =====================================================
         */

        const wrapper = document.createElement("div");

        wrapper.className =
            "searchable-dropdown-wrapper";


        const searchInput =
            document.createElement("input");

        searchInput.type = "text";

        searchInput.className =
            "dropdown-search";

        searchInput.placeholder =
            "Search...";


        /*
         * Insert search box before select
         */

        select.parentNode.insertBefore(
            wrapper,
            select
        );


        wrapper.appendChild(
            searchInput
        );


        wrapper.appendChild(
            select
        );


        /*
         * =====================================================
         * SAVE ORIGINAL OPTIONS
         * =====================================================
         */

        const originalOptions =
            Array.from(select.options).map(
                function (option) {

                    return {

                        value: option.value,

                        text: option.textContent,

                        disabled: option.disabled,

                        selected: option.selected

                    };

                }
            );


        /*
         * =====================================================
         * SEARCH
         * =====================================================
         */

        searchInput.addEventListener(
            "input",
            function () {

                const search =
                    searchInput.value
                        .toLowerCase()
                        .trim();


                /*
                 * Remember current value
                 */

                const currentValue =
                    select.value;


                /*
                 * Remove current options
                 */

                select.innerHTML = "";


                /*
                 * Add matching options
                 */

                originalOptions.forEach(
                    function (item) {

                        const matches =
                            item.text
                                .toLowerCase()
                                .includes(search);


                        if (matches) {

                            const option =
                                document.createElement(
                                    "option"
                                );


                            option.value =
                                item.value;


                            option.textContent =
                                item.text;


                            option.disabled =
                                item.disabled;


                            /*
                             * Keep selected product
                             */

                            if (
                                item.value ===
                                currentValue
                            ) {

                                option.selected =
                                    true;

                            }


                            select.appendChild(
                                option
                            );

                        }

                    }
                );


                /*
                 * If only one product remains,
                 * don't automatically select it.
                 *
                 * The cashier must explicitly choose it.
                 */

            }
        );


        /*
         * =====================================================
         * CLEAR SEARCH WHEN SELECT CHANGES
         * =====================================================
         */

        select.addEventListener(
            "change",
            function () {

                searchInput.value = "";

                restoreOptions();

            }
        );


        /*
         * =====================================================
         * RESTORE OPTIONS
         * =====================================================
         */

        function restoreOptions() {

            const currentValue =
                select.value;


            select.innerHTML = "";


            originalOptions.forEach(
                function (item) {

                    const option =
                        document.createElement(
                            "option"
                        );


                    option.value =
                        item.value;


                    option.textContent =
                        item.text;


                    option.disabled =
                        item.disabled;


                    if (
                        item.value ===
                        currentValue
                    ) {

                        option.selected =
                            true;

                    }


                    select.appendChild(
                        option
                    );

                }
            );

        }

    }

});