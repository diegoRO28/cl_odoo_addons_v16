from odoo import models
class FacturaXlsx(models.AbstractModel):

    _name    = 'report.report_class.factura_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, factura):
        row  = 1
        col  = 0
        tira = ""
        # Create a workbook and add a worksheet.
        
        worksheet = workbook.add_worksheet('FACTURAS POR INSCRIPCIÓN')
        bold  = workbook.add_format({'bold': True})

        tira = "name"
        worksheet.write(0, col, "Fecha", bold)
        worksheet.write(0, col+1, "Student code", bold)
        worksheet.write(0, col+2, "Student", bold)
        worksheet.write(0, col+3, "Factura", bold)
        worksheet.write(0, col+4, "company_id", bold)

        for obj in factura:
            
            factura_xlsx = obj.name

            aux_fecha         = obj.invoice_date
            aux_student_code  = obj.partner_id.student_code
            aux_student_id    = obj.partner_id.name
            aux_name          = obj.name
            
            worksheet.write(row, col,   aux_fecha)
            worksheet.write(row, col+1, aux_student_code)
            worksheet.write(row, col+2, aux_student_id, bold)
            worksheet.write(row, col+3, aux_name, bold)
           
            row+=1