/** @odoo-module alias=web.bootstrap.extensions **/

/**
 * The bootstrap library extensions and fixes should be done here to avoid
 * patching in place.
 */

/**
 * Review Bootstrap Sanitization: leave it enabled by default but extend it to
 * accept more common tag names like tables and buttons, and common attributes
 * such as style or data-. If a specific tooltip or popover must accept custom
 * tags or attributes, they must be supplied through the whitelist BS
 * parameter explicitely.
 *
 * We cannot disable sanitization because bootstrap uses tooltip/popover
 * DOM attributes in an "unsafe" way.
 */
let bsSanitizeAllowList = Tooltip.Default.allowList;

bsSanitizeAllowList['*'].push('title', 'style', /^data-[\w-]+/);

bsSanitizeAllowList.header = [];
bsSanitizeAllowList.main = [];
bsSanitizeAllowList.footer = [];

bsSanitizeAllowList.caption = [];
bsSanitizeAllowList.col = ['span'];
bsSanitizeAllowList.colgroup = ['span'];
bsSanitizeAllowList.table = [];
bsSanitizeAllowList.thead = [];
bsSanitizeAllowList.tbody = [];
bsSanitizeAllowList.tfooter = [];
bsSanitizeAllowList.tr = [];
bsSanitizeAllowList.th = ['colspan', 'rowspan'];
bsSanitizeAllowList.td = ['colspan', 'rowspan'];

bsSanitizeAllowList.address = [];
bsSanitizeAllowList.article = [];
bsSanitizeAllowList.aside = [];
bsSanitizeAllowList.blockquote = [];
bsSanitizeAllowList.section = [];

bsSanitizeAllowList.button = ['type'];
bsSanitizeAllowList.del = [];

/**
 * Returns an extended version of bootstrap default whitelist for sanitization,
 * i.e. a version where, for each key, the original value is concatened with the
 * received version's value and where the received version's extra key/values
 * are added.
 *
 * Note: the returned version
 *
 * @param {Object} extensions
 * @returns {Object} /!\ the returned whitelist is made from a *shallow* copy of
 *      the default whitelist, extended with given whitelist.
 */
export function makeExtendedSanitizeWhiteList(extensions) {
    let allowList = Object.assign({}, Tooltip.Default.allowList);
    Object.keys(extensions).forEach(key => {
        allowList[key] = (allowList[key] || []).concat(extensions[key]);
    });
    return allowList;
}

/* Bootstrap tooltip defaults overwrite */
Tooltip.Default.placement = 'auto';
Tooltip.Default.fallbackPlacement = ['bottom', 'right', 'left', 'top'];
Tooltip.Default.html = true;
Tooltip.Default.trigger = 'hover';
Tooltip.Default.container = 'body';
Tooltip.Default.boundary = 'window';
Tooltip.Default.delay = { show: 1000, hide: 0 };

const bootstrapShowFunction = Tooltip.prototype.show;
Tooltip.prototype.show = function () {
    // Overwrite bootstrap tooltip method to prevent showing 2 tooltip at the
    // same time
    $('.tooltip').remove();
    const errorsToIgnore = ["Please use show on visible elements"];
    try {
        return bootstrapShowFunction.call(this);
    } catch (error) {
        if (errorsToIgnore.includes(error.message)) {
            return 0;
        }
        throw error;
    }
};

/* Bootstrap scrollspy fix for non-body to spy */

const bootstrapSpyRefreshFunction = ScrollSpy.prototype.refresh;
ScrollSpy.prototype.refresh = function () {
    bootstrapSpyRefreshFunction.apply(this, arguments);
    if (this._scrollElement === window || this._config.method !== 'offset') {
        return;
    }
    const baseScrollTop = this._getScrollTop();
    for (let i = 0; i < this._offsets.length; i++) {
        this._offsets[i] += baseScrollTop;
    }
};

/**
 * In some cases, we need to keep the first element of navbars selected.
 */
const bootstrapSpyProcessFunction = ScrollSpy.prototype._process;
ScrollSpy.prototype._process = function () {
    bootstrapSpyProcessFunction.apply(this, arguments);
    if (this._activeTarget === null && this._config.alwaysKeepFirstActive) {
        this._activate(this._targets[0]);
    }
};

/* Bootstrap modal scrollbar compensation on non-body */
/*
// Commented as not found equivalent function name in BS5
const bsSetScrollbarFunction = $.fn.modal.Constructor.prototype._setScrollbar;
$.fn.modal.Constructor.prototype._setScrollbar = function () {
    const $scrollable = $().getScrollingElement();
    if (document.body.contains($scrollable[0])) {
        $scrollable.compensateScrollbar(true);
    }
    return bsSetScrollbarFunction.apply(this, arguments);
};
const bsResetScrollbarFunction = $.fn.modal.Constructor.prototype._resetScrollbar;
$.fn.modal.Constructor.prototype._resetScrollbar = function () {
    const $scrollable = $().getScrollingElement();
    if (document.body.contains($scrollable[0])) {
        $scrollable.compensateScrollbar(false);
    }
    return bsResetScrollbarFunction.apply(this, arguments);
};
**/
