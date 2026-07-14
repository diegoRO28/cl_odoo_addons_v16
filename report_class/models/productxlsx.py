from odoo import models
class ProductXlsx(models.AbstractModel):

    _name    = 'report.report_class.product_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, product):
        row  = 1
        col  = 0
        tira = ""
        # Create a workbook and add a worksheet.
        
        worksheet = workbook.add_worksheet('HOJA NUEVOS PRECIOS')
        bold  = workbook.add_format({'bold': True})

        tira = "name"
        worksheet.write(0, col, "id", bold)
        worksheet.write(0, col+1, "name", bold)
        worksheet.write(0, col+2, "list_price", bold)
        worksheet.write(0, col+3, "company_id", bold)

        for obj in product:
            
            product_xlsx = obj.name

            aux_id         = obj.id 
            aux_name       = obj.name
            aux_list_price = obj.list_price
            aux_company_id = obj.company_id.partner_id.name

            worksheet.write(row, col, aux_id, bold)
            worksheet.write(row, col+1, aux_name, bold)
            worksheet.write(row, col+2, aux_list_price, bold)
            worksheet.write(row, col+3, aux_company_id, bold)
            
            row+=1