import base64
import io
import re
import xlwt

from odoo import fields, models


class Generate2307Wizard(models.TransientModel):
    _name = "l10n_ph_2307.wizard"
    _description = "Exports 2307 data to a XLS file."

    moves_to_export = fields.Many2many(
        "account.move",
        string="Joural To Include",
    )
    generate_xls_file = fields.Binary(
        "Generated file",
        help="Technical field used to temporarily hold the generated XLS file before its downloaded."
    )

    def _write_single_row(self, worksheet, cursor, values):
        worksheet.write(cursor, 0, label=values['invoice_date'])
        worksheet.write(cursor, 1, label=values['vat'])
        worksheet.write(cursor, 2, label=values['branch_code'])
        worksheet.write(cursor, 3, label=values['company_name'])
        worksheet.write(cursor, 4, label=values['first_name'])
        worksheet.write(cursor, 5, label=values['middle_name'])
        worksheet.write(cursor, 6, label=values['last_name'])
        worksheet.write(cursor, 7, label=values['address'])
        worksheet.write(cursor, 8, label=values['product_name'])
        worksheet.write(cursor, 9, label=values['atc'])
        worksheet.write(cursor, 10, label=values['price_subtotal'])
        worksheet.write(cursor, 11, label=values['amount'])
        worksheet.write(cursor, 12, label=values['tax_amount'])

    def _write_rows(self, worksheet, moves):
        cursor = 0
        for move in moves:
            cursor += 1
            partner = move.partner_id
            values = {}
            values['invoice_date'] = move.invoice_date.strftime("%m/%d/%Y") if move.invoice_date else ''
            values['vat'] = re.sub(r'\-', '', partner.vat)[:9] if partner.vat else ''
            values['branch_code'] = partner.branch_code or '000'
            values['company_name'] = partner.commercial_partner_id.name
            values['first_name'] = partner.first_name or ''
            values['middle_name'] = partner.middle_name or ''
            values['last_name'] = partner.last_name or ''
            values['address'] = ", ".join(filter(None, [partner.street, partner.street2, partner.city, partner.state_id, partner.country_id.name]))
            for invoice_line in move.invoice_line_ids:
                for tax in invoice_line.tax_ids.filtered_domain([('l10n_ph_atc', '!=', False)]):
                    values['product_name'] = re.sub(r'[\(\)]', '', invoice_line.product_id.name)
                    values['atc'] = tax.l10n_ph_atc
                    values['price_subtotal'] = invoice_line.price_subtotal
                    values['amount'] = tax.amount
                    values['tax_amount'] = tax._compute_amount(invoice_line.price_subtotal, invoice_line.price_unit)
                    self._write_single_row(worksheet, cursor, values)
                    cursor += 1

    def action_generate(self):
        """ Generate a xls format file for importing to
        https://bir-excel-uploader.com/excel-file-to-bir-dat-format/#bir-form-2307-settings.
        This website will then generate a BIR 2307 format excel file for uploading to the
        PH government.
        """
        self.ensure_one()

        file_data = io.BytesIO()
        workbook = xlwt.Workbook(encoding='utf-8')
        worksheet = workbook.add_sheet('Form2307')

        col_headers = ["Reporting_Month", "Vendor_TIN", "branchCode", "companyName", "surName", "firstName", "middleName", "address", "nature", "ATC", "income_payment", "ewt_rate", "tax_amount"]
        for index, col_header in enumerate(col_headers):
            worksheet.write(0, index, label=col_header)

        self._write_rows(worksheet, self.moves_to_export)

        workbook.save(file_data)
        file_data.seek(0)
        data = file_data.read()

        self.generate_xls_file = base64.b64encode(data)

        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "/web/content?model=l10n_ph_2307.wizard&download=true&field=generate_xls_file&filename=Form_2307.xls&id={}".format(self.id),
        }
