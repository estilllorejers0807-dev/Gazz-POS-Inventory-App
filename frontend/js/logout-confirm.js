/*
 * Gazz POS - Global Logout Confirmation
 *
 * Add this before </body> on every page:
 *
 * <script src="{{ url_for('static', filename='js/logout-confirm.js') }}"></script>
 */

(function () {

    "use strict";


    // =========================================================
    // CREATE CSS
    // =========================================================

    function injectStyles() {

        if (
            document.getElementById(
                "gazz-logout-confirm-styles"
            )
        ) {
            return;
        }


        const style =
            document.createElement("style");


        style.id =
            "gazz-logout-confirm-styles";


        style.textContent = `

            .gazz-logout-overlay {

                position: fixed;

                inset: 0;

                background:
                    rgba(
                        15,
                        23,
                        42,
                        0.45
                    );

                display: none;

                align-items: center;

                justify-content: center;

                z-index: 99999;

            }


            .gazz-logout-overlay.show {

                display: flex;

            }


            .gazz-logout-dialog {

                width: 100%;

                max-width: 430px;

                margin: 20px;

                background: #ffffff;

                border: 1px solid #e5e7eb;

                border-radius: 14px;

                box-shadow:
                    0 20px 50px
                    rgba(
                        15,
                        23,
                        42,
                        0.20
                    );

                overflow: hidden;

                animation:
                    gazzLogoutDialogIn
                    0.18s ease;

            }


            @keyframes gazzLogoutDialogIn {

                from {

                    opacity: 0;

                    transform:
                        translateY(-10px)
                        scale(0.98);

                }


                to {

                    opacity: 1;

                    transform:
                        translateY(0)
                        scale(1);

                }

            }


            .gazz-logout-dialog-header {

                display: flex;

                align-items: center;

                justify-content: space-between;

                padding: 17px 20px;

                border-bottom:
                    1px solid #e5e7eb;

                background: #f8fafc;

            }


            .gazz-logout-dialog-brand {

                color: #dc2626;

                font-size: 12px;

                font-weight: 800;

                letter-spacing: 1.5px;

            }


            .gazz-logout-dialog-close {

                width: 32px;

                height: 32px;

                display: flex;

                align-items: center;

                justify-content: center;

                border: none;

                background: transparent;

                color: #64748b;

                border-radius: 7px;

                font-size: 22px;

                cursor: pointer;

                transition: 0.2s ease;

            }


            .gazz-logout-dialog-close:hover {

                background: #e5e7eb;

                color: #1f2937;

            }


            .gazz-logout-dialog-body {

                padding: 24px 22px 20px;

            }


            .gazz-logout-dialog-title {

                margin: 0 0 9px;

                color: #1f2937;

                font-size: 19px;

                font-weight: 800;

            }


            .gazz-logout-dialog-message {

                margin: 0;

                color: #64748b;

                font-size: 13px;

                line-height: 1.6;

            }


            .gazz-logout-dialog-actions {

                display: flex;

                justify-content: flex-end;

                gap: 10px;

                padding:
                    16px 22px 20px;

                border-top:
                    1px solid #f1f5f9;

            }


            .gazz-logout-dialog-button {

                min-width: 95px;

                height: 42px;

                padding: 0 17px;

                border: none;

                border-radius: 7px;

                font-family:
                    "Poppins",
                    sans-serif;

                font-size: 13px;

                font-weight: 700;

                cursor: pointer;

                transition: 0.2s ease;

            }


            .gazz-logout-dialog-cancel {

                background: #f1f5f9;

                color: #374151;

            }


            .gazz-logout-dialog-cancel:hover {

                background: #e2e8f0;

            }


            .gazz-logout-dialog-confirm {

                background: #dc2626;

                color: #ffffff;

            }


            .gazz-logout-dialog-confirm:hover {

                background: #b91c1c;

            }


            @media (max-width: 480px) {

                .gazz-logout-dialog {

                    max-width: 100%;

                }


                .gazz-logout-dialog-actions {

                    flex-direction:
                        column-reverse;

                }


                .gazz-logout-dialog-button {

                    width: 100%;

                }

            }

        `;


        document.head.appendChild(style);

    }


    // =========================================================
    // CREATE CONFIRMATION DIALOG
    // =========================================================

    function createDialog() {

        if (
            document.getElementById(
                "gazz-logout-overlay"
            )
        ) {
            return;
        }


        const overlay =
            document.createElement("div");


        overlay.id =
            "gazz-logout-overlay";


        overlay.className =
            "gazz-logout-overlay";


        overlay.innerHTML = `

            <div
                class="gazz-logout-dialog"
                onclick="event.stopPropagation()"
            >

                <div
                    class="gazz-logout-dialog-header"
                >

                    <span
                        class="gazz-logout-dialog-brand"
                    >
                        GAZZ POS INVENTORY
                    </span>


                    <button
                        type="button"
                        class="gazz-logout-dialog-close"
                        id="gazz-logout-close"
                        aria-label="Close"
                    >
                        ×
                    </button>

                </div>


                <div
                    class="gazz-logout-dialog-body"
                >

                    <h3
                        class="gazz-logout-dialog-title"
                    >
                        Log Out
                    </h3>


                    <p
                        class="gazz-logout-dialog-message"
                    >
                        Are you sure you want to
                        log out of your account?
                    </p>

                </div>


                <div
                    class="gazz-logout-dialog-actions"
                >

                    <button
                        type="button"
                        class="
                            gazz-logout-dialog-button
                            gazz-logout-dialog-cancel
                        "
                        id="gazz-logout-cancel"
                    >
                        Cancel
                    </button>


                    <button
                        type="button"
                        class="
                            gazz-logout-dialog-button
                            gazz-logout-dialog-confirm
                        "
                        id="gazz-logout-confirm"
                    >
                        Log Out
                    </button>

                </div>

            </div>

        `;


        document.body.appendChild(overlay);


        const closeButton =
            document.getElementById(
                "gazz-logout-close"
            );


        const cancelButton =
            document.getElementById(
                "gazz-logout-cancel"
            );


        const confirmButton =
            document.getElementById(
                "gazz-logout-confirm"
            );


        // =====================================================
        // CLOSE DIALOG
        // =====================================================

        function closeDialog() {

            overlay.classList.remove(
                "show"
            );


            document.body.style.overflow =
                "";


            overlay.dataset.logoutUrl =
                "";

        }


        // =====================================================
        // CLOSE BUTTON
        // =====================================================

        closeButton.addEventListener(
            "click",
            closeDialog
        );


        // =====================================================
        // CANCEL BUTTON
        // =====================================================

        cancelButton.addEventListener(
            "click",
            closeDialog
        );


        // =====================================================
        // CLICK OUTSIDE DIALOG
        // =====================================================

        overlay.addEventListener(
            "click",
            function (event) {

                if (
                    event.target ===
                    overlay
                ) {

                    closeDialog();

                }

            }
        );


        // =====================================================
        // CONFIRM LOGOUT
        // =====================================================

        confirmButton.addEventListener(
            "click",
            function () {

                const logoutUrl =
                    overlay.dataset.logoutUrl;


                if (logoutUrl) {

                    window.location.href =
                        logoutUrl;

                }

            }
        );


        // =====================================================
        // ESCAPE KEY
        // =====================================================

        document.addEventListener(
            "keydown",
            function (event) {

                if (
                    event.key === "Escape" &&
                    overlay.classList.contains(
                        "show"
                    )
                ) {

                    closeDialog();

                }

            }
        );

    }


    // =========================================================
    // DETECT LOGOUT LINKS
    // =========================================================

    function isLogoutLink(link) {

        if (
            !link ||
            link.tagName !== "A"
        ) {

            return false;

        }


        const href =
            link.getAttribute("href") ||
            "";


        // Flask logout URL

        if (
            href === "/logout" ||
            href.endsWith("/logout") ||
            href.includes("/logout?")
        ) {

            return true;

        }


        // Also detect links whose text says Log out

        const text =
            link.textContent
                .trim()
                .toLowerCase();


        return (
            text === "log out" ||
            text === "logout"
        );

    }


    // =========================================================
    // SETUP LOGOUT LINKS
    // =========================================================

    function setupLogoutLinks() {

        const links =
            document.querySelectorAll(
                "a"
            );


        links.forEach(
            function (link) {

                if (
                    !isLogoutLink(link)
                ) {

                    return;

                }


                // Prevent duplicate listeners

                if (
                    link.dataset
                        .logoutConfirmationReady
                    === "1"
                ) {

                    return;

                }


                link.dataset
                    .logoutConfirmationReady =
                    "1";


                link.addEventListener(
                    "click",
                    function (event) {

                        event.preventDefault();


                        const overlay =
                            document.getElementById(
                                "gazz-logout-overlay"
                            );


                        if (!overlay) {

                            return;

                        }


                        overlay.dataset
                            .logoutUrl =
                            link.href;


                        overlay.classList.add(
                            "show"
                        );


                        document.body.style.overflow =
                            "hidden";

                    }
                );

            }
        );

    }


    // =========================================================
    // INITIALIZE
    // =========================================================

    function initialize() {

        injectStyles();

        createDialog();

        setupLogoutLinks();

    }


    if (
        document.readyState ===
        "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            initialize
        );

    } else {

        initialize();

    }


})();