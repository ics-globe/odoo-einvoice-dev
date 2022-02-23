/** @odoo-module **/
import options from 'web_editor.snippets.options';
import {_t} from '@web/core/l10n/translation';

options.registry.ImageComparison = options.Class.extend({
    /**
     * @override
     */
    start() {
        this._super(...arguments);
        this.__onDivClick = this._onDivClick.bind(this);
        // This is needed because when the user clicks on the image comparison,
        // the input captures the event, so we have to manually activate the
        // image options.
        this.$target[0].querySelector('div').addEventListener('click', this.__onDivClick);
    },
    /**
     * @override
     */
    cleanForSave() {
        const slideValue = 50;
        this.$target[0].querySelector('input[type="range"]').value = slideValue;
        this.$target[0].querySelector('.o_media_left').style.clipPath =
            `polygon(0 0, ${slideValue}% 0, ${slideValue}% 100%, 0 100%)`;
        delete this.$target[0].closest('.s_image_comparison').dataset.editedMedia;
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.$target[0].querySelector('div').removeEventListener('click', this.__onDivClick);
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Creates or removes the captions.
     *
     * @see this.selectClass for parameters
     */
    showCaptions(previewMode, widgetValue, params) {
        const descriptionEls = this.$target[0].querySelectorAll('.o_description');
        if (widgetValue && !descriptionEls.length) {
            // Create the two caption elements.
            const inputEl = this.$target[0].querySelector('input[type="range"]');
            for (const side of ['left', 'right']) {
                const divEl = document.createElement('div');
                divEl.className = `o_description o_${side}_description o_not_editable`;
                divEl.setAttribute('contenteditable', 'false');
                const spanEl = document.createElement('span');
                spanEl.className = 'o_default_snippet_text';
                spanEl.setAttribute('contenteditable', 'true');
                spanEl.innerText = side === 'left' ? _t('BEFORE') : _t('AFTER');
                divEl.appendChild(spanEl);
                inputEl.after(divEl);
            }
        } else if (!widgetValue && descriptionEls.length) {
            for (const el of descriptionEls) {
                el.remove();
            }
        }
    },
    /**
     * Creates or removes the enlarge button.
     *
     * @see this.selectClass for parameters
     */
    showZoomButton(previewMode, widgetValue, params) {
        const buttonEl = this.$target[0].querySelector('.o_enlarge_button');
        if (widgetValue && !buttonEl) {
            // Create the button.
            const newButtonEl = document.createElement('button');
            newButtonEl.className = 'btn o_enlarge_button mr-1 mb-1 o_not_editable';
            newButtonEl.setAttribute('contenteditable', 'false');
            newButtonEl.setAttribute('title', _t('Enlarge Images'));
            const iconEl = document.createElement('i');
            iconEl.className = 'fa fa-expand';
            newButtonEl.appendChild(iconEl);
            this.$target[0].querySelector('figure').appendChild(newButtonEl);
        } else if (!widgetValue && buttonEl) {
            buttonEl.remove();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onDivClick(ev) {
        ev.stopPropagation();
        const selector = this.$target[0].dataset.editedMedia || '.o_media_left';
        this.trigger_up('activate_snippet', {
            $snippet: this.$target.find(selector),
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'showCaptions':
                return Boolean(this.$target[0].querySelector('.o_description'));
            case 'showZoomButton':
                return Boolean(this.$target[0].querySelector('.o_enlarge_button'));
        }
        return this._super(...arguments);
    },
});

options.registry.ImageComparisonImage = options.Class.extend({
    isTopOption: true,
    forceNoDeleteButton: true,
    /**
     * @override
     */
    start() {
        this._super(...arguments);
        const currentSide = this.$target[0].classList.contains('o_media_right') ? 'right' : 'left';
        let buttonText = currentSide === 'right' ? _t('Edit Left Media') : _t('Edit Right Media');
        this.$el[0].querySelector('[data-change-edited-media]').innerText = buttonText;

        const leftPanelEl = this.$overlay.data('$optionsSection')[0];
        const titleTextEl = leftPanelEl.querySelector('we-title > span');
        titleTextEl.innerText = currentSide === 'right' ? _t('RIGHT Media') : _t('LEFT Media');

    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the media to edit.
     *
     * @see this.selectClass for parameters
     */
    changeEditedMedia(previewMode, widgetValue, params) {
        const mediaToEdit = this.$target[0].classList.contains('o_media_right') ? 'left' : 'right';
        const selector = `.o_media_${mediaToEdit}`;
        this.$target[0].closest('.s_image_comparison').dataset.editedMedia = selector;
        const imageEl = this.$target[0].closest('.s_image_comparison').querySelector(selector);
        this.trigger_up('activate_snippet', {
            $snippet: $(imageEl),
        });
    },
});

export default {
    ImageComparisonImage: options.registry.ImageComparisonImage,
    ImageComparison: options.registry.ImageComparison,
};
