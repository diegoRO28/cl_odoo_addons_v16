# See LICENSE file for full copyright and licensing details.

from odoo import models


class TeacherMgmtReportXlsx(models.AbstractModel):
    _name = 'report.cl_class_mgmt_v16.teacher_mgmt_report_xlsx'
    _description = 'Reporte de Gestión Docente (XLSX)'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizards):
        # Desempaquetar correctamente — Odoo envuelve el dict en 'data'
        wizard_data = data.get('data', {})
        teachers_data = wizard_data.get('teachers_data', [])
        current_date = wizard_data.get('current_date')
        filters = wizard_data.get('filters', {})

        sheet = workbook.add_worksheet('Gestión Docente')

        # Formatos
        bold_fmt = workbook.add_format({'bold': True})
        date_fmt = workbook.add_format({'num_format': 'dd/mm/yyyy'})

        header_fmt = workbook.add_format({
            'bold': True,
            'bg_color': '#F2F2F2',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        cell_fmt = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
        })
        cell_center_fmt = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10,
        })
        cell_right_fmt = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 10,
        })
        green_fmt = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
            'bg_color': '#C6EFCE',
            'font_color': '#006100',
        })
        red_fmt = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
            'bg_color': '#FFC7CE',
            'font_color': '#9C0006',
        })
        teacher_fmt = workbook.add_format({
            'bold': True,
            'bg_color': '#ecf0f1',
            'font_size': 12,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
        })
        totals_fmt = workbook.add_format({
            'bold': True,
            'bg_color': '#2c3e50',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
        })

        # Cabecera del documento
        sheet.merge_range('A1:J1', 'REPORTE DE GESTIÓN DOCENTE', workbook.add_format({
            'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter',
        }))

        sheet.write(2, 0, 'FECHA DE EMISIÓN:', bold_fmt)
        if current_date:
            sheet.write(2, 1, current_date.strftime('%d/%m/%Y'))
        sheet.write(3, 0, 'PROFESOR:', bold_fmt)
        sheet.write(3, 1, filters.get('teacher', 'Todos'))
        sheet.write(4, 0, 'CÓDIGO DE SECCIÓN:', bold_fmt)
        sheet.write(4, 1, filters.get('section_code', 'Todas'))

        # Encabezados de columnas
        headers = [
            'Teacher', 'Course', 'Section', 'Status',
            'Class days', 'Start - End / Month',
            'Groups Up to Date', 'Active Groups',
            'Student Cohort Size', 'Age Band',
        ]
        header_row = 6
        for col, header in enumerate(headers):
            sheet.write(header_row, col, header, header_fmt)

        # Totales acumulados
        total_active_groups = 0
        total_up_to_date = 0
        total_students = 0
        current_row = header_row + 1

        for teacher_data in teachers_data:
            # El wizard guarda el recordset en 'teacher', no un string
            teacher = teacher_data['teacher']
            sections = teacher_data['sections']
            active_groups = teacher_data['active_groups']
            groups_up_to_date = teacher_data['groups_up_to_date']
            num_sections = len(sections)

            if num_sections == 0:
                continue

            # Nombre del profesor — celda combinada
            if num_sections > 1:
                sheet.merge_range(
                    current_row, 0,
                    current_row + num_sections - 1, 0,
                    teacher.name or '',
                    teacher_fmt,
                )
                # Groups Up to Date — celda combinada
                sheet.merge_range(
                    current_row, 6,
                    current_row + num_sections - 1, 6,
                    float(groups_up_to_date),
                    cell_center_fmt,
                )
                # Active Groups — celda combinada
                sheet.merge_range(
                    current_row, 7,
                    current_row + num_sections - 1, 7,
                    float(active_groups),
                    cell_center_fmt,
                )
            else:
                sheet.write(current_row, 0, teacher.name or '', teacher_fmt)
                sheet.write(current_row, 6, float(groups_up_to_date), cell_center_fmt)
                sheet.write(current_row, 7, float(active_groups), cell_center_fmt)

            for section_data in sections:
                # Course
                sheet.write(current_row, 1, section_data.get('course', ''), cell_fmt)

                # Section code
                sheet.write(current_row, 2, section_data.get('code', ''), cell_fmt)

                # Status — verde o rojo según is_up_to_date
                status = section_data.get('status', '')
                status_fmt = green_fmt if section_data.get('is_up_to_date') else red_fmt
                sheet.write(current_row, 3, status, status_fmt)

                # Class days
                sheet.write(current_row, 4, section_data.get('class_days', ''), cell_fmt)

                # Start - End (las fechas vienen como objetos date desde el wizard)
                start_date = section_data.get('start_date')
                end_date = section_data.get('end_date')
                if start_date and end_date:
                    date_range = '{} - {}'.format(
                        start_date.strftime('%d/%m/%Y'),
                        end_date.strftime('%d/%m/%Y'),
                    )
                elif start_date:
                    date_range = start_date.strftime('%d/%m/%Y')
                else:
                    date_range = ''
                sheet.write(current_row, 5, date_range, cell_fmt)

                # Student Cohort Size
                students = section_data.get('total_students', 0)
                sheet.write(current_row, 8, float(students), cell_right_fmt)
                total_students += students

                # Age Band
                sheet.write(current_row, 9, section_data.get('age_band', ''), cell_fmt)

                current_row += 1

            total_active_groups += active_groups
            total_up_to_date += groups_up_to_date

        # Fila de totales
        total_row = current_row + 1
        sheet.merge_range(total_row, 0, total_row, 5, 'TOTALES:', totals_fmt)
        sheet.write(total_row, 6, float(total_up_to_date), cell_center_fmt)
        sheet.write(total_row, 7, float(total_active_groups), cell_center_fmt)
        sheet.write(total_row, 8, float(total_students), cell_right_fmt)

        # Ancho de columnas
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 30)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:E', 30)
        sheet.set_column('F:F', 25)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 18)
        sheet.set_column('J:J', 25)