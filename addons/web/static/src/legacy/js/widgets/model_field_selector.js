odoo.define("web.ModelFieldSelector", function (require) {
"use strict";

var core = require("web.core");
var Widget = require("web.Widget");
var ModelFieldSelectorPopOver = require("web.ModelFieldSelectorPopover");

    /**
 * The ModelFieldSelector widget can be used to display/select a particular
 * field chain from a given model.
 */
var ModelFieldSelector = Widget.extend({
    template: "ModelFieldSelector",
    events: {},
    editionEvents: {
        // Handle popover opening and closing
        "focusin": "_onFocusIn",
        "focusout": "_onFocusOut",
    },
    /**
     * @constructor
     * The ModelFieldSelector requires a model and a field chain to work with.
     *
     * @param parent
     * @param {string} model - the model name (e.g. "res.partner")
     * @param {string[]} chain - list of the initial field chain parts
     * @param {Object} [options] - some key-value options
     * @param {string} [options.order='string']
     *                 an ordering key for displayed fields
     * @param {boolean} [options.readonly=true] - true if should be readonly
     * @param {function} [options.filter]
     *                 a function to filter the fetched fields
     * @param {Object} [options.filters]
     *                 some key-value options to filter the fetched fields
     * @param {boolean} [options.filters.searchable=true]
     *                  true if only the searchable fields have to be used
     * @param {Object[]} [options.fields=null]
     *                   the list of fields info to use when no relation has
     *                   been followed (null indicates the widget has to request
     *                   the fields itself)
     * @param {boolean|function} [options.followRelations=true]
     *                  true if can follow relation when building the chain
     * @param {boolean} [options.showSearchInput=true]
     *                  false to hide a search input to filter displayed fields
     * @param {boolean} [options.needDefaultValue=false]
     *                  true if a default value can be entered after the selected chain
     * @param {boolean} [options.cancelOnEscape=false]
     *                  true if a the chain selected should be ignored when the user hit ESC
     * @param {boolean} [options.debugMode=false]
     *                  true if the widget is in debug mode, false otherwise
     */
    init: function (parent, model, chain, options) {
        this._super.apply(this, arguments);

        this.model = model;
        this.popOver = {'chain': chain, 'pages': []};
        this.options = _.extend({
            order: 'string',
            readonly: true,
            fields: null,
            debugMode: false
        }, options || {});

        this.dirty = false;
        this.popOver = new ModelFieldSelectorPopOver(parent, model, chain, options);

        if (!this.options.readonly) {
            _.extend(this.events, this.editionEvents);
            this.popOver.appendTo($("<div/>"));
            this.popOver.on("field_selector_render", undefined, this._render.bind(this));
            this.popOver.on("field_selector_started", undefined, () => {
                this.$el.append(this.popOver.$el);
                this.$popover = this.$(".o_field_selector_popover");
            });
        }
    },
    /**
     * @see Widget.willStart()
     * @returns {Promise}
     */
    willStart: function () {
        return this._super.apply(this, arguments);
    },
    /**
     * @see Widget.start
     * @returns {Promise}
     */
    start: function () {
        this.$value = this.$(".o_field_selector_value");
        this.$valid = this.$(".o_field_selector_warning");

        if (this.options.readonly) {
            this.popOver._prefill().then(this._render.bind(this));
        }

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * Returns the field information selected by the field chain.
     *
     * @returns {Object}
     */
    getSelectedField: function () {
        return this.popOver.getSelectedField();
    },
    /**
     * Indicates if the field chain is valid. If the field chain has not been
     * processed yet (the widget is not ready), this method will return
     * undefined.
     *
     * @returns {boolean}
     */
    isValid: function () {
        return this.popOver.valid;
    },
    /**
     * Saves a new field chain (array) and re-render.
     *
     * @param {string[]} chain - the new field chain
     * @returns {Promise} resolved once the re-rendering is finished
     */
    setChain: function (chain) {
        return this.popOver.setChain(chain);
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Updates the rendering of the value (the serie of tags separated by
     * arrows).
     *
     * @private
     */
    _render: function () {
        // Render the chain value
        this.$value.html(core.qweb.render(this.template + ".value", {
            chain: this.popOver.chain,
            pages: this.popOver.pages,
        }));

        // Toggle the warning message
        this.$valid.toggleClass('d-none', !!this.isValid());
    },
    /**
     * Called when the widget is focused -> opens the popover
     */
    _onFocusIn: function () {
        this.popOver._onFocusIn();
    },
    /**
     * Called when the widget is blurred -> closes the popover
     */
    _onFocusOut: function () {
        this.popOver._onFocusOut();
    },
});

return ModelFieldSelector;
});
