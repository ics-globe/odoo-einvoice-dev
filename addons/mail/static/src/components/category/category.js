/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import AutocompleteInput from '@mail/components/autocomplete_input/autocomplete_input';
import CategoryItem from '@mail/components/category_item/category_item';

const { Component } = owl;

const components = { AutocompleteInput, CategoryItem };

class Category extends Component {
    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const category = this.env.models['mail.category'].get(this.props.categoryLocalId);
            return {
                category: category ? category.__state : undefined,
            }
        })

        // bind since passed as props
        this._onAddItemAutocompleteSelect = this._onAddItemAutocompleteSelect.bind(this);
        this._onAddItemAutocompleteSource = this._onAddItemAutocompleteSource.bind(this);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.category}
     */
    get category() {
        return this.env.models['mail.category'].get(this.props.categoryLocalId);
    }

    /**
     * @returns {mail.category_item[]}
     */
    get categoryItems() {
        return this.category.categoryItems;
    }

    /**
     * @returns {string}
     */
    get COMMAND_ADD_TITLE() {
        switch(this.category.type) {
            case 'channel':
                return this.env._t("Add or join a channel");
            case 'chat':
                return this.env._t("Start a conversation");
        }
    }

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
    }

    get NEW_ITEM_PLACEHOLDER() {
        switch(this.category.type) {
            case 'channel':
                return this.env._t('Find or create a channel...');
            case 'chat':
                return this.env._t('Find or start a conversation...');
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     * @param {Object} ui
     * @param {Object} ui.item
     * @param {integer} ui.item.id
     */
    _onAddItemAutocompleteSelect(ev, ui){
        switch(this.category.type) {
            case 'channel':
                this.discuss.handleAddChannelAutocompleteSelect(ev, ui);
                break;
            case 'chat':
                this.discuss.handleAddChatAutocompleteSelect(ev, ui);
                break;
        }
    }

    /**
     * @private
     * @param {Object} req
     * @param {string} req.term
     * @param {function} res
     */
    _onAddItemAutocompleteSource(req, res) {
        switch(this.category.type) {
            case 'channel':
                this.discuss.handleAddChannelAutocompleteSource(req, res);
                break;
            case 'chat':
                this.discuss.handleAddChatAutocompleteSource(req, res);
                break;
        }
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickView(ev){
        ev.stopPropagation();
        return this.env.bus.trigger('do-action', {
            action: {
                name: this.env._t("Public Channels"),
                type: 'ir.actions.act_window',
                res_model: 'mail.channel',
                views: [[false, 'kanban'], [false, 'form']],
                domain: [['public', '!=', 'private']]
            },
        });
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAdd(ev) {
        ev.stopPropagation();
        switch(this.category.type) {
            case 'channel':
                this.discuss.update({ isAddingChannel: true });
                break;
            case 'chat':
                this.discuss.update({ isAddingChat: true });
                break;
        }
    }

    /**
     * @private
     * @param {CustomEvent} ev
     */
    _onHideAddingItem(ev){
        ev.stopPropagation();
        this.discuss.clearIsAddingItem();
    }

    /**
     * @private
     */
    _toggleCategoryOpen() {
        this.category.toggleIsOpen();
    }
}

Object.assign(Category, {
    components,
    props: {
        categoryLocalId: String,
    },
    template: 'mail.Category',
});

export default Category;
