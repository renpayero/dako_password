/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

// A revealed password goes back to the mask after this delay.
export const HIDE_DELAY = 30000;

/**
 * Keeps the passwords revealed in the web client. The server only sends a password
 * through `dako_reveal`, which logs the access, so every reveal and copy is a request.
 */
export const passwordRevealService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        const state = reactive({ values: {} });
        const timers = {};

        function hide(resIds) {
            for (const resId of resIds) {
                browser.clearTimeout(timers[resId]);
                delete timers[resId];
                delete state.values[resId];
            }
        }

        function hideAll() {
            hide(Object.keys(state.values));
        }

        function show(values) {
            for (const [resId, value] of Object.entries(values)) {
                state.values[resId] = value;
                browser.clearTimeout(timers[resId]);
                timers[resId] = browser.setTimeout(() => hide([resId]), HIDE_DELAY);
            }
        }

        function fetchPasswords(resIds, action) {
            return orm.call("dako.password", "dako_reveal", [resIds], { action });
        }

        browser.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "hidden") {
                hideAll();
            }
        });

        return {
            state,
            hide,
            hideAll,
            async reveal(resIds) {
                show(await fetchPasswords(resIds, "reveal"));
            },
            /**
             * Copy a stored password to the clipboard. The clipboard write starts inside
             * the click handler, before awaiting the request, so that browsers that
             * require a user gesture (Safari) accept it.
             *
             * @returns {Promise<boolean>} false when the browser refused the clipboard:
             *   the password is then revealed so it can be copied by hand.
             */
            async copy(resId) {
                const valuePromise = fetchPasswords([resId], "copy").then((values) => values[resId]);
                const clipboard = browser.navigator.clipboard;
                try {
                    if (window.ClipboardItem && clipboard?.write) {
                        const blobPromise = valuePromise.then(
                            (value) => new Blob([value], { type: "text/plain" })
                        );
                        await clipboard.write([new window.ClipboardItem({ "text/plain": blobPromise })]);
                    } else {
                        await clipboard.writeText(await valuePromise);
                    }
                    return true;
                } catch {
                    // Request errors must reach the user: awaiting rethrows them.
                    const value = await valuePromise;
                    try {
                        await clipboard.writeText(value);
                        return true;
                    } catch {
                        show({ [resId]: value });
                        return false;
                    }
                }
            },
        };
    },
};

registry.category("services").add("dako_password.reveal", passwordRevealService);
