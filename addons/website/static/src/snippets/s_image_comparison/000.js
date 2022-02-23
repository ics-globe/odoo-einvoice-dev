/** @odoo-module */

import publicWidget from 'web.public.widget';
import {qweb} from 'web.core';

const ImageComparisonWidget = publicWidget.Widget.extend({
    selector: '.s_image_comparison',
    xmlDependencies: ['/website/static/src/snippets/s_image_comparison/000.xml'],
    disabledInEditableMode: false,
    events: {
        'input input[type="range"]': '_onSliderInput',
    },
    read_events: {
        'click .o_enlarge_button': '_onEnlargeButtonClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onEnlargeButtonClick(ev) {
        const images = Array.from(this.$target[0].querySelectorAll('.o_media_right, .o_media_left'))
            .map(img => img.src);
        const descriptions = Array.from(this.$target[0].querySelectorAll('.o_description'))
            .map(el => el.innerText);
        const $modal = $(qweb.render('website.image.comparison.modal', {
            images,
            descriptions,
        }));
        $modal.modal();
        $modal.one('shown.bs.modal', () => {
            this.trigger_up('widgets_start_request', {
                editableMode: false,
                $target: $modal.find('.s_image_comparison'),
            });
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSliderInput(ev) {
        // In edit mode, do not consider the slide as a history step.
        if (this.editableMode) {
            this.options.wysiwyg.odooEditor.observerUnactive();
        }
        const slideValue = this.$target[0].querySelector('input[type="range"]').value;
        this.$target[0].querySelector('.o_media_left').style.clipPath =
            `polygon(0 0, ${slideValue}% 0, ${slideValue}% 100%, 0 100%)`;
        if (this.editableMode) {
            this.options.wysiwyg.odooEditor.observerActive();
        }
    },
});
publicWidget.registry.s_image_comparison = ImageComparisonWidget;
export default ImageComparisonWidget;
