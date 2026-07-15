# See LICENSE file for full copyright and licensing details.

from odoo import models


class TeacherMgmtReportXlsx(models.AbstractModel):
    _name = 'report.cl_class_mgmt_v16.teacher_mgmt_report_xlsx'
    _description = 'Reporte de Gestión Docente (XLSX)'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizards):
        sheet = workbook.add_worksheet('Gestión Docente')
        bold = workbook.add_format({'bold': True})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1})
        green_fmt = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        red_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        date_fmt = workbook.add_format({'num_format': 'dd/mm/yyyy'})

        sheet.write(0, 0, 'Fecha de emisión', bold)
        sheet.write(0, 1, data['fecha_emision'], date_fmt)

        headers = [
            'Teacher', 'Course', 'Section', 'Status',
            'Class days', 'Start - End / Month',
            'Groups Up to Date', 'Active Groups',
            'Student Cohort Size', 'Age Band',
        ]
        header_row = 2
        for col, header in enumerate(headers):
            sheet.write(header_row, col, header, header_fmt)

        row = header_row + 1
        for profesor in data['profesores']:
            for seccion in profesor['secciones']:
                status_fmt = green_fmt if seccion['status_color'] == 'green' else red_fmt
                sheet.write(row, 0, profesor['teacher_name'])
                sheet.write(row, 1, seccion['course'])
                sheet.write(row, 2, seccion['section'])
                sheet.write(row, 3, seccion['status_label'], status_fmt)
                sheet.write(row, 4, seccion['class_days'])
                sheet.write(row, 5, seccion['start_end'])
                sheet.write(row, 6, profesor['groups_up_to_date'])
                sheet.write(row, 7, profesor['active_groups'])
                sheet.write(row, 8, seccion['student_cohort_size'])
                sheet.write(row, 9, seccion['age_band'])
                row += 1

        sheet.set_column(0, 1, 26)
        sheet.set_column(2, 2, 16)
        sheet.set_column(3, 3, 16)
        sheet.set_column(4, 5, 28)
        sheet.set_column(6, 9, 16)
