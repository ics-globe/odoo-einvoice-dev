/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import useUpdate from '@mail/component_hooks/use_update/use_update';
import PartnerImStatusIcon from '@mail/components/partner_im_status_icon/partner_im_status_icon';
import { link } from '@mail/model/model_field_command';

const { Component } = owl;

const components = { PartnerImStatusIcon };

class ComposerSuggestion extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const composer = this.env.models['mail.composer'].get(this.props.composerLocalId);
            const record = this.env.models[props.modelName].get(props.recordLocalId);
            return {
                composerHasToScrollToActiveSuggestion: composer && composer.hasToScrollToActiveSuggestion,
                record: record ? record.__state : undefined,
            };
        });
        useUpdate({ func: () => this._update() });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.composer}
     */
    get composer() {
        return this.env.models['mail.composer'].get(this.props.composerLocalId);
    }

    get isCannedResponse() {
        return this.props.modelName === "mail.canned_response";
    }

    get isChannel() {
        return this.props.modelName === "mail.thread";
    }

    get isCommand() {
        return this.props.modelName === "mail.channel_command";
    }

    get isPartner() {
        return this.props.modelName === "mail.partner";
    }

    get record() {
        return this.env.models[this.props.modelName].get(this.props.recordLocalId);
    }

    /**
     * Returns a descriptive title for this suggestion. Useful to be able to
     * read both parts when they are overflowing the UI.
     *
     * @returns {string}
     */
    title() {
        if (this.isCannedResponse) {
            return _.str.sprintf("%s: %s", this.record.source, this.record.substitution);
        }
        if (this.isChannel) {
            return this.record.name;
        }
        if (this.isCommand) {
            return _.str.sprintf("%s: %s", this.record.name, this.record.help);
        }
        if (this.isPartner) {
            if (this.record.email) {
                return _.str.sprintf("%s (%s)", this.record.nameOrDisplayName, this.record.email);
            }
            return this.record.nameOrDisplayName;
        }
        return "";
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (
            this.composer &&
            this.composer.hasToScrollToActiveSuggestion &&
            this.props.isActive
        ) {
            this.el.scrollIntoView({
                block: 'center',
            });
            this.composer.update({ hasToScrollToActiveSuggestion: false });
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClick(ev) {
        ev.preventDefault();
        this.composer.composerSuggestionList.update({ activeSuggestedRecord: link(this.record) });
        this.composer.insertSuggestion();
        this.composer.composerSuggestionList.closeSuggestions();
        this.trigger('o-composer-suggestion-clicked');
    }

}

Object.assign(ComposerSuggestion, {
    components,
    defaultProps: {
        isActive: false,
    },
    props: {
        composerLocalId: String,
        isActive: Boolean,
        modelName: String,
        recordLocalId: String,
    },
    template: 'mail.ComposerSuggestion',
});

export default ComposerSuggestion;
