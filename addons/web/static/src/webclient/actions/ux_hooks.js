/** @odoo-module **/

import { useEffect } from "@web/core/effect_hook";
const { useComponent } = owl.hooks;

/**
 * Hook used to enrich html and provide automatic links to action.
 * Dom elements must have those attrs [res-id][res-model][view-type]
 * Each element with those attrs will become a link to the specified resource.
 * Works with Iframes.
 *
 * @param {owl reference} owlRef Owl ref to the element to enrich
 * @param {string} [selector] Selector to apply to the element resolved by the ref.
 */
export function useEnrichWithActionLinks(owlRef, selector = null) {
    const comp = useComponent();
    let tangibleRefEl; // use effect dependency

    useEffect(
        () => {
            let nodeFromRef = owlRef.el;
            tangibleRefEl = owlRef.el;

            // If we get an iframe, we need to wait until everything is loaded
            if (nodeFromRef.matches("iframe")) {
                nodeFromRef.onload = () => enrich(comp, nodeFromRef, selector, true);
            } else {
                enrich(comp, nodeFromRef, selector);
            }
        },
        () => [tangibleRefEl]
    );
}

function enrich(component, targetElement, selector, isIFrame = false) {
    let doc = window.document;

    // If we are in an iframe, we need to take the right document
    // both for the element and the doc
    if (isIFrame) {
        targetElement = targetElement.contentDocument;
        doc = targetElement;
    }

    // If there are selector, we may have multiple blocks of code to enrich
    const targets = [];
    if (selector) {
        targets.push(...targetElement.querySelectorAll(selector));
    } else {
        targets.push(targetElement);
    }

    // Search the elements with the selector, update them and bind an action.
    for (const currentTarget of targets) {
        const elementsToWrap = currentTarget.querySelectorAll("[res-id][res-model][view-type]");
        for (const element of elementsToWrap.values()) {
            const wrapper = doc.createElement("a");
            wrapper.setAttribute("href", "#");
            wrapper.addEventListener("click", (ev) => {
                ev.preventDefault();
                component.env.services.action.doAction({
                    type: "ir.actions.act_window",
                    view_mode: element.getAttribute("view-type"),
                    res_id: Number(element.getAttribute("res-id")),
                    res_model: element.getAttribute("res-model"),
                    views: [[element.getAttribute("view-id"), element.getAttribute("view-type")]],
                });
            });
            element.parentNode.insertBefore(wrapper, element);
            wrapper.appendChild(element);
        }
    }
}
