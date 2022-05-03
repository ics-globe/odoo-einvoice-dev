from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, res_ids=None, data=None, run_script=None):
        account_move = self.env[self.model].browse(res_ids)
        if account_move.company_id.country_id.code != 'PT':
            return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
        run_script = """
            // Constants for A4 paper size
            const tableWidth = "17.65cm";
            const firstPageEnd = 3050;
            const bodyHeight = 580;

            // Force the HTML and the PDF table (and its columns) to have the same width across all pages
            // (because the table header will be copied for each of the future tables)
            // This is necessary to correctly determine which row belongs to which page
            document.querySelector("table").style.width = tableWidth;
            const ths = document.querySelectorAll("th");
            for (var i = 0; i < ths.length; i++) {
                ths[i].style.width = ths[i].getBoundingClientRect().width + "px";
            }
            
            // Parse main table informations into a list of dicts representing the smaller tables (one per page)
            const rows = document.querySelectorAll("tr");
            const amounts = document.querySelectorAll("span.oe_currency_value");
            var tables = [{
                rows: [],
                carrying: 0.0,
            }]
            for (var i = 1; i < rows.length; i++) {
                if (amounts[i - 1] === undefined)   // i-1 because offset with header which has no amount,
                    continue                        // might be undefined if the row is a total row
                
                tables[tables.length-1].carrying += parseFloat(amounts[i - 1].innerText.split(",").join(""));
                tables[tables.length-1].rows.push(i);
                
                if (rows[i].getBoundingClientRect().bottom > firstPageEnd + (tables.length-1) * bodyHeight) {
                    tables.push({
                        rows: [],
                        carrying: tables[tables.length-1].carrying,
                    })
                }
            }
            
            // Delete the old unique table (but remember its header to reuse later)
            const theadElement = document.querySelector("thead");
            const tableElement = document.querySelector("table");
            tableElement.parentNode.removeChild(tableElement);
            
            // Function to create the div containing the carry over in the beggining/end of the page
            function carryValueElement(amount) {
                return "<table class='table-sm' style='margin-left: auto; margin-right: 0; border-top: 1px solid; border-bottom: 1px solid'>"+
                            "<tr>" +
                                "<td><strong>Valor acumulado</strong></td>" +
                                "<td class='text-right'>" +
                                    "<strong>" + amount.toLocaleString('pt-PT') + "&euro;</strong>" +
                                "</td>" +
                            "</tr>" +
                        "</table>" 
            }
            
            // Create the new tables
            for (var i = 0; i < tables.length; i++){
                var html = "";
                if (i != 0) 
                    html += carryValueElement(tables[i-1].carrying);
                if (tables[i].rows.length > 0){
                    html += "<table class='table table-sm o_main_table' name='invoice_line_table' style='width: " + tableWidth + "'>";
                    html +=     theadElement.outerHTML;
                    html += "   <tobdy>";
                    for (var j = 0; j < tables[i].rows.length; j++){
                        const row = rows[tables[i].rows[j]];
                        html += row.outerHTML;
                    }
                    html += "   </tbody>";
                    html += "</table>";
                }
                if (i != tables.length - 1) {
                    html += carryValueElement(tables[i].carrying);
                    html += "<div style='page-break-after: always;'/>";
                }
                document.getElementById("total").parentNode.insertAdjacentHTML("beforebegin", html);
            }
        """
        return super()._render_qweb_pdf(res_ids=res_ids, data=data, run_script=run_script)
