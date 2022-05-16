/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

const { useEffect, useRef } = owl;

/**
 * This hook will register/unregister the given registration
 * when the caller component will mount/unmount.
 *
 * @param {string} hotkey
 * @param {(context: { reference: HTMLElement, target: HTMLElement})=>void} callback
 * @param {Object} options additional options
 * @param {boolean} [options.allowRepeat=false]
 *  allow registration to perform multiple times when hotkey is held down
 * @param {boolean} [options.bypassEditableProtection=false]
 *  if true the hotkey service will call this registration
 *  even if an editable element is focused
 * @param {boolean} [options.global=false]
 *  allow registration to perform no matter the UI active element
 * @param {string} [options.reference="hotkey"]
 *  Reference HTML element of the registration.
 */
export function useHotkey(hotkey, callback, options = {}) {
    const hotkeyService = useService("hotkey");
    const hotkeyOptions = options.reference
        ? { ...options, reference: useRef(options.reference) }
        : options;
    useEffect(
        () => hotkeyService.add(hotkey, callback, hotkeyOptions),
        () => []
    );
}
