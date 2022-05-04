/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";

export class RewardButton extends PosComponent {
    setup() {
        super.setup()
        useListener('click', this.onClick);
    }

    hasClaimableRewards() {
        const order = this.env.pos.get_order();
        const rewards = order ? order.getClaimableRewards() : [];
        return rewards.length > 0;
    }

    /**
     * Applies the reward on the current order, if multiple products can be claimed opens a popup asking for which one.
     *
     * @param {Object} reward
     * @param {number} coupon_id
     */
    async _applyReward(reward, coupon_id) {
        const order = this.env.pos.get_order();

        // Enable reward if disabled.
        const indexDisabled = order.disabledRewards.findIndex(rewardId => rewardId === reward.id);
        if (indexDisabled > -1) {
            order.disabledRewards.splice(indexDisabled, 1);
        }

        if (reward.reward_type === 'product') {
            let selectedProduct;
            if (reward.multi_product) {
                const productsList = reward.reward_product_ids.map((product_id) => {
                    const product = this.env.pos.db.get_product_by_id(product_id);
                    return {
                        id: product_id,
                        label: product.display_name,
                        item: product,
                    }
                });
                const { confirmed, payload } = await this.showPopup('SelectionPopup', {
                    title: this.env._t('Please select a product for this reward'),
                    list: productsList,
                });
                if (!confirmed) {
                    return false;
                }
                selectedProduct = payload;
            } else {
                selectedProduct = this.env.pos.db.get_product_by_id(reward.reward_product_ids[0]);
            }
            this.env.pos.get_order().add_product(selectedProduct, { quantity: reward.reward_product_qty });
        } else {
            this.env.pos.get_order()._applyNonProductReward(reward, coupon_id, {});
            this.env.pos.get_order()._updateRewards();
        }
    }

    async onClick() {
        const order = this.env.pos.get_order();
        const rewards = order.getClaimableRewards();
        if (rewards.length === 0) {
            await this.showPopup('ErrorPopup', {
                title: this.env._t('No rewards available.'),
                body: this.env._t('There are no rewards claimable for this customer.')
            });
            return false;
        } else if (rewards.length === 1) {
            return this._applyReward(rewards[0].reward, rewards[0].coupon_id);
        } else {
            const rewardsList = rewards.map((reward) => ({
                id: reward.reward.id,
                label: reward.reward.description,
                item: reward,
            }));
            const { confirmed, payload: selectedReward } = await this.showPopup('SelectionPopup', {
                title: this.env._t('Please select a reward'),
                list: rewardsList,
            });
            if (confirmed) {
                return this._applyReward(selectedReward.reward, selectedReward.coupon_id);
            }
        }
        return false;
    }
}

RewardButton.template = 'RewardButton';

ProductScreen.addControlButton({
    component: RewardButton,
    condition: function() {
        return this.env.pos.config.use_coupon_programs || this.env.pos.config.loyalty_program_id || this.env.pos.config.use_gift_card;
    }
});

Registries.Component.add(RewardButton);
