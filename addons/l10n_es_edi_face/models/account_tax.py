from odoo import _, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'
    l10n_es_edi_face_tax_type = fields.Selection([
        ('01', _('Value-Added Tax')),
        ('02', _('Taxes on production, services and imports in Ceuta and Melilla')),
        ('03', _('IGIC: Canaries General Indirect Tax')),
        ('04', _('IRPF: Personal Income Tax')),
        ('05', _('Other')),
        ('06', _('ITPAJD: Tax on wealth transfers and stamp duty')),
        ('07', _('IE: Excise duties and consumption taxes')),
        ('08', _('RA: Customs duties')),
        ('09', _('IGTECM: Sales tax in Ceuta and Melilla')),
        ('10', _('IECDPCAC: Excise duties on oil derivates in Canaries')),
        ('11', _('IIIMAB: Tax on premises that affect the environment in the Balearic Islands')),
        ('12', _('ICIO: Tax on construction, installation and works')),
        ('13', _('IMVDN: Local tax on unoccupied homes in Navarre')),
        ('14', _('IMSN: Local tax on building plots in Navarre')),
        ('15', _('IMGSN: Local sumptuary tax in Navarre')),
        ('16', _('IMPN: Local tax on advertising in Navarre')),
        ('17', _('REIVA: Special VAT for travel agencies')),
        ('18', _('REIGIC: Special IGIC: for travel agencies')),
        ('19', _('REIPSI: Special IPSI for travel agencies')),
        ('20', _('IPS: Insurance premiums Tax')),
        ('21', _('SWUA: Surcharge for Winding Up Activity')),
        ('22', _('IVPEE: Tax on the value of electricity generation')),
        ('23',
         _('Tax on the production of spent nuclear fuel and radioactive waste from the generation of nuclear electric '
           'power')),
        ('24', _('Tax on the storage of spent nuclear energy and radioactive waste in centralised facilities')),
        ('25', _('IDEC: Tax on bank deposits')),
        ('26', _('Excise duty applied to manufactured tobacco in Canaries')),
        ('27', _('IGFEI: Tax on Fluorinated Greenhouse Gases')),
        ('28', _('IRNR: Non-resident Income Tax')),
        ('29', _('Corporation Tax')),
    ],
            string='Spanish FACe EDI Tax Type', required=True, default='01',
    )


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'
    l10n_es_edi_face_tax_type = fields.Selection([
        ('01', _('Value-Added Tax')),
        ('02', _('Taxes on production, services and imports in Ceuta and Melilla')),
        ('03', _('IGIC: Canaries General Indirect Tax')),
        ('04', _('IRPF: Personal Income Tax')),
        ('05', _('Other')),
        ('06', _('ITPAJD: Tax on wealth transfers and stamp duty')),
        ('07', _('IE: Excise duties and consumption taxes')),
        ('08', _('RA: Customs duties')),
        ('09', _('IGTECM: Sales tax in Ceuta and Melilla')),
        ('10', _('IECDPCAC: Excise duties on oil derivates in Canaries')),
        ('11', _('IIIMAB: Tax on premises that affect the environment in the Balearic Islands')),
        ('12', _('ICIO: Tax on construction, installation and works')),
        ('13', _('IMVDN: Local tax on unoccupied homes in Navarre')),
        ('14', _('IMSN: Local tax on building plots in Navarre')),
        ('15', _('IMGSN: Local sumptuary tax in Navarre')),
        ('16', _('IMPN: Local tax on advertising in Navarre')),
        ('17', _('REIVA: Special VAT for travel agencies')),
        ('18', _('REIGIC: Special IGIC: for travel agencies')),
        ('19', _('REIPSI: Special IPSI for travel agencies')),
        ('20', _('IPS: Insurance premiums Tax')),
        ('21', _('SWUA: Surcharge for Winding Up Activity')),
        ('22', _('IVPEE: Tax on the value of electricity generation')),
        ('23',
         _('Tax on the production of spent nuclear fuel and radioactive waste from the generation of nuclear electric '
           'power')),
        ('24', _('Tax on the storage of spent nuclear energy and radioactive waste in centralised facilities')),
        ('25', _('IDEC: Tax on bank deposits')),
        ('26', _('Excise duty applied to manufactured tobacco in Canaries')),
        ('27', _('IGFEI: Tax on Fluorinated Greenhouse Gases')),
        ('28', _('IRNR: Non-resident Income Tax')),
        ('29', _('Corporation Tax')),
    ],
            string='Spanish FACe EDI Tax Type', required=True, default='01',
    )
