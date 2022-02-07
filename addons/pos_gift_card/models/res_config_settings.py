# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_gift_card_product_id = fields.Many2one('product.product', compute='_compute_pos_gift_card_product_id', store=True, readonly=False, pos='gift_card_product_id')
    pos_gift_card_settings = fields.Selection(related='pos_config_id.gift_card_settings', readonly=False)

    @api.depends('pos_module_pos_gift_card', 'pos_config_id')
    def _compute_pos_gift_card_product_id(self):
        for res_config in self:
            if res_config.pos_module_pos_gift_card:
                res_config.pos_gift_card_product_id = res_config.pos_config_id.gift_card_product_id or self.env.ref("gift_card.pay_with_gift_card_product", False)
            else:
                res_config.pos_gift_card_product_id = False
