# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route

from odoo.addons.sale.controllers.portal import CustomerPortal


class SaleStockPortal(CustomerPortal):

    @route(['/my/orders/<int:order_id>/picking/<int:picking_id>'], type='http', auth="public", website=True)
    def portal_order_picking(self, order_id, picking_id, access_token=None):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if picking_id not in order_sudo.picking_ids.ids:
            # Picking doesn't exist, or is not linked to provided SO
            return request.redirect('/my')

        # breaks test_SO_and_DO_portal_acess
        # picking_sudo = order_sudo.env['stock.picking'].browse(picking_id)
        # if picking_sudo.picking_type_id.code != 'internal':
        #     # Internal picking are not expected to be exposed to portal users
        #     return request.redirect('/my')

        # print report as SUPERUSER, since it require access to product, taxes, payment term etc.. and portal does not have those access rights.
        pdf = request.env.ref('stock.action_report_delivery').with_user(SUPERUSER_ID)._render_qweb_pdf(
            [picking_id]
        )[0]

        return request.make_response(
            pdf,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf)),
            ]
        )
