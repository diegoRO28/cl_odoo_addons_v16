# -*- coding: utf-8 -*-

from odoo import models
import logging

_logger = logging.getLogger(__name__)


class TeacherMgmtXlsx(models.AbstractModel):
    _name = 'report.school_teacher_mgmt_report.teacher_mgmt_xlsx'
    _description = 'Reporte de Gestión Docente (XLSX)'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wizards):
        # El controlador de report_xlsx descarta el 'data' de generate_report()
        # cuando la URL de descarga incluye docids (caso "generic report"), por
        # lo que hay que recalcular los datos a partir del wizard ya persistido
        # en vez de confiar en 'data'.
        wizard = wizards[:1]
        wizard_data = wizard._get_report_data() if wizard else {}
        teachers_data = wizard_data.get('teachers_data', [])
        current_date = wizard_data.get('current_date') or ''
        if current_date and not isinstance(current_date, str):
            current_date = current_date.strftime('%d/%m/%Y')
        filters = wizard_data.get('filters', {})

        _logger.info('Generando XLSX: %d profesores', len(teachers_data))

        # ── Formatos ──────────────────────────────────────────────────────────
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 16,
            'align': 'center', 'valign': 'vcenter',
        })
        bold_fmt = workbook.add_format({'bold': True})
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#2c3e50', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter',
            'border': 1, 'text_wrap': True,
        })
        teacher_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#ecf0f1', 'font_size': 12,
            'align': 'left', 'valign': 'vcenter', 'border': 1,
        })
        cell_fmt = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter',
            'font_size': 10, 'text_wrap': True,
        })
        cell_center_fmt = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 10,
        })
        cell_right_fmt = workbook.add_format({
            'border': 1, 'align': 'right', 'valign': 'vcenter', 'font_size': 10,
        })
        status_red_fmt = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter',
            'font_size': 10, 'font_color': 'white', 'bg_color': '#e74c3c',
        })
        status_green_fmt = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter',
            'font_size': 10, 'font_color': 'white', 'bg_color': '#27ae60',
        })
        totals_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#2c3e50', 'font_color': 'white',
            'align': 'center', 'valign': 'vcenter',
        })

        # ── Hoja ──────────────────────────────────────────────────────────────
        sheet = workbook.add_worksheet('Gestión Docente')

        # Título
        sheet.merge_range('A1:J1', 'REPORTE DE GESTIÓN DOCENTE', title_fmt)

        # Metadatos
        sheet.write(2, 0, 'FECHA DE EMISIÓN:', bold_fmt)
        sheet.write(2, 1, current_date)
        sheet.write(3, 0, 'PROFESOR:', bold_fmt)
        sheet.write(3, 1, filters.get('teacher', 'Todos'))
        sheet.write(4, 0, 'CÓDIGO DE SECCIÓN:', bold_fmt)
        sheet.write(4, 1, filters.get('section_code', 'Todas'))

        # Encabezados
        headers = [
            'Teacher', 'Course', 'Section', 'Status',
            'Class days', 'Start - End / Month',
            'Groups Up to Date', 'Active Groups',
            'Student Cohort Size', 'Age Band',
        ]
        header_row = 6
        for col, header in enumerate(headers):
            sheet.write(header_row, col, header, header_fmt)

        # ── Datos ─────────────────────────────────────────────────────────────
        total_active_groups = 0
        total_up_to_date = 0
        total_students = 0
        current_row = header_row + 1

        for teacher_data in teachers_data:
            teacher_name = teacher_data.get('teacher_name', '')
            sections = teacher_data.get('sections', [])
            active_groups = teacher_data.get('active_groups', 0)
            groups_up_to_date = teacher_data.get('groups_up_to_date', 0)
            num_sections = len(sections)

            if not num_sections:
                continue

            # Columna A — nombre del profesor (celda combinada si hay varias secciones)
            if num_sections > 1:
                sheet.merge_range(
                    current_row, 0,
                    current_row + num_sections - 1, 0,
                    teacher_name, teacher_fmt,
                )
                sheet.merge_range(
                    current_row, 6,
                    current_row + num_sections - 1, 6,
                    float(groups_up_to_date), cell_center_fmt,
                )
                sheet.merge_range(
                    current_row, 7,
                    current_row + num_sections - 1, 7,
                    float(active_groups), cell_center_fmt,
                )
            else:
                sheet.write(current_row, 0, teacher_name, teacher_fmt)
                sheet.write(current_row, 6, float(groups_up_to_date), cell_center_fmt)
                sheet.write(current_row, 7, float(active_groups), cell_center_fmt)

            for section_data in sections:
                sheet.write(current_row, 1, section_data.get('course', ''), cell_fmt)
                sheet.write(current_row, 2, section_data.get('code', ''), cell_fmt)

                status = section_data.get('status', '')
                is_up_to_date = section_data.get('is_up_to_date', False)
                if status == 'READY TO BE FILED':
                    sheet.write(current_row, 3, status, status_red_fmt)
                elif is_up_to_date:
                    sheet.write(current_row, 3, status, status_green_fmt)
                else:
                    sheet.write(current_row, 3, status, cell_fmt)

                class_days = section_data.get('class_days', '') or 'N/A'
                sheet.write(current_row, 4, class_days, cell_fmt)

                sheet.write(current_row, 5, section_data.get('date_range', ''), cell_fmt)

                students = section_data.get('total_students', 0)
                if students:
                    sheet.write(current_row, 8, float(students), cell_right_fmt)
                else:
                    sheet.write(current_row, 8, 'NO DATA', cell_fmt)
                total_students += students

                sheet.write(current_row, 9, section_data.get('age_band', ''), cell_fmt)

                current_row += 1

            total_active_groups += active_groups
            total_up_to_date += groups_up_to_date

        # ── Totales ───────────────────────────────────────────────────────────
        total_row = current_row + 1
        sheet.merge_range(total_row, 0, total_row, 5, 'TOTALES:', totals_fmt)
        sheet.write(total_row, 6, float(total_up_to_date), cell_center_fmt)
        sheet.write(total_row, 7, float(total_active_groups), cell_center_fmt)
        sheet.write(total_row, 8, float(total_students), cell_right_fmt)

        # ── Ancho de columnas ─────────────────────────────────────────────────
        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 35)
        sheet.set_column('C:C', 22)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:E', 35)
        sheet.set_column('F:F', 30)
        sheet.set_column('G:G', 18)
        sheet.set_column('H:H', 18)
        sheet.set_column('I:I', 22)
        sheet.set_column('J:J', 30)

        _logger.info('XLSX generado: %d profesores, %d secciones, %d estudiantes',
                     len(teachers_data), sum(len(t.get('sections', [])) for t in teachers_data),
                     total_students)