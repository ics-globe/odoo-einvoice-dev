# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': "Spain - FACe EDI",
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'website': 'https://www.facturae.gob.es/face/Paginas/FACE.aspx',
    'description': """
    This module create the file require to send the invoices information to the General State Administrations.
    
    for more informations, see https://www.facturae.gob.es/face/Paginas/FACE.aspx
    """,
    'depends': [
        'account_edi',
        'l10n_es',
        'uom',
    ],
    'data': [
        "data/uom_data.xml",
        "data/account_tax_data.xml",
        "data/facturae_templates.xml",
        "data/account_edi_data.xml",
        "data/certificate_template.xml",

        "security/ir.model.access.csv",

        "views/l10n_es_edi_face_views.xml",
        "views/res_company_views.xml",
        "views/res_partner_views.xml",
        "views/account_tax_views.xml",
        "views/account_menuitem.xml",
    ],
    'demo': [
        "demo/res_company_demo.xml",
        "demo/res_partner_demo.xml",
        "demo/l10n_es_edi_face_demo.xml",
    ],
    "external_dependencies": {"python": ["xades"]},
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
