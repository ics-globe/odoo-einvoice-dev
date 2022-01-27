(function () {
    const { Component, useComponent, onWillDestroy } = owl;
    const capitalize = (s) => (s ? s[0].toUpperCase() + s.slice(1) : "");
    const oldLifecycleMethods = [
        "mounted",
        "willStart",
        "willUnmount",
        "willPatch",
        "patched",
        "willUpdateProps",
    ];

    const hasOwnProperty = Object.prototype.hasOwnProperty;

    /**
     * Get all root HTMLElement from a given bdom (owl blockdom)
     * It is recursive
     * @param  {owl.VNode} bdom
     * @return {HTMLElement[]}
     */
    function getNodes(bdom) {
        const nodes = new Set();
        if (!bdom) {
            return nodes;
        }
        if (hasOwnProperty.call(bdom, "component")) {
            const el = bdom.component.el;
            if (el) {
                nodes.add(el);
            } else {
                nodes.add(...getNodes(bdom.bdom));
            }
        } else if (bdom.el) {
            nodes.add(bdom.el);
        } else if (hasOwnProperty.call(bdom, "children")) {
            for (const bnode of bdom.children) {
                nodes.add(...getNodes(bnode));
            }
        } else if (hasOwnProperty.call(bdom, "child")) {
            nodes.add(...getNodes(bdom.child));
        }
        return nodes;
    }

    owl.Component = class extends Component {
        constructor(...args) {
            super(...args);
            for (const methodName of oldLifecycleMethods) {
                const hookName = "on" + capitalize(methodName);
                const method = this[methodName];
                if (typeof method === "function") {
                    owl[hookName](method.bind(this));
                }
            }
            if (this.catchError) {
                owl.onError((error) => {
                    this.catchError(error);
                });
            }
            onWillDestroy(this.destroy.bind(this));
        }

        destroy() {}

        static get current() {
            return useComponent();
        }

        get el() {
            return Array.from(getNodes(this.__owl__.bdom)).filter((el) => el instanceof HTMLElement)[0];
        }

        /**
         * Emit a custom event of type 'eventType' with the given 'payload' on the
         * component's el, if it exists. However, note that the event will only bubble
         * up to the parent DOM nodes. Thus, it must be called between mounted() and
         * willUnmount().
         */
        trigger(eventType, payload) {
            this.__trigger(eventType, payload);
        }
        /**
         * Private trigger method, allows to choose the component which triggered
         * the event in the first place
         */
        __trigger(eventType, payload) {
            if (this.el) {
                const ev = new CustomEvent(eventType, {
                    bubbles: true,
                    cancelable: true,
                    detail: payload,
                });
                this.el.dispatchEvent(ev);
            }
        }
    };
    owl.Component.env = {};
    owl.Component.__getNodes__ = getNodes;

    Object.defineProperty(owl.Component, "components", {
        get() {
            return this._components;
        },
        set(val) {
            this._components = new Proxy(val, {
                get(target, key) {
                    return target[key] || owl.Component._components[key];
                },
            });
        },
    });
    owl.Component._components = {};
})();
