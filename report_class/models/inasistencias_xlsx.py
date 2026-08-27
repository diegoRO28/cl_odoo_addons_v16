from odoo import models
import xlsxwriter
import io

class InasistenciasXlsx(models.AbstractModel):
    _name = 'report.report_class.inasistencias_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, partners):
        sheet = workbook.add_worksheet('Inasistencias')
        bold = workbook.add_format({'bold': True})
        
        # Add report headers
        sheet.write(0, 0, 'FECHA', bold)
        sheet.write(0, 1, data['form_data']['date_today'])
        sheet.write(1, 0, 'DEL', bold)
        sheet.write(1, 1, data['form_data']['date_start'])
        sheet.write(1, 2, 'AL', bold)
        sheet.write(1, 3, data['form_data']['date_end'])

        # Add table headers
        headers = ['#', 'CÓDIGO', 'ESTUDIANTE', 'SECCION', 'ENCUENTRO', 'FECHA', 'CAMPUS', 'PROFESOR']
        for col_num, header in enumerate(headers):
            sheet.write(3, col_num, header, bold)
        
        # Add data rows
        for row_num, line in enumerate(data['asi'], start=4):
            sheet.write(row_num, 0, row_num-3)
            sheet.write(row_num, 1, line['codeStu'])
            sheet.write(row_num, 2, line['nombreStu'])
            sheet.write(row_num, 3, line['nombreSec'])
            sheet.write(row_num, 4, line['nombreEnc'])
            sheet.write(row_num, 5, line['fechaEnc'])
            sheet.write(row_num, 6, line['nombreCam'])
            sheet.write(row_num, 7, line['nombreDoc'])