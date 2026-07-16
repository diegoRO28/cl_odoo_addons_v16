# -*- coding: utf-8 -*-

from odoo import models
import logging

_logger = logging.getLogger(__name__)


class TeacherMgmtXlsx(models.AbstractModel):
    _name = 'report.school_teacher_mgmt_report.teacher_mgmt_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, partners):
        """
        Genera el reporte en formato XLSX con la estructura del modelo.
        """
        # Obtener los datos del wizard
        wizard_data = data.get('data', {})
        teachers_data = wizard_data.get('teachers_data', [])
        current_date = wizard_data.get('current_date')
        filters = wizard_data.get('filters', {})
        
        # Formato de fecha
        date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
        
        # Estilos
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter',
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#2c3e50',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'text_wrap': True,
        })
        
        teacher_format = workbook.add_format({
            'bold': True,
            'bg_color': '#ecf0f1',
            'font_size': 12,
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
            'text_wrap': True,
        })
        
        cell_center_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 10,
        })
        
        cell_right_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'font_size': 10,
        })
        
        status_red_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'font_size': 10,
            'font_color': 'white',
            'bg_color': '#e74c3c',
        })
        
        # Crear la hoja
        sheet = workbook.add_worksheet('Attendance')
        
        # Título
        sheet.merge_range('A1:K1', 'REPORTE DE GESTIÓN DOCENTE', title_format)
        
        # Fecha de emisión
        sheet.write(2, 0, 'FECHA DE EMISIÓN:', workbook.add_format({'bold': True}))
        if current_date:
            sheet.write(2, 1, current_date.strftime('%d/%m/%Y'), date_format)
        
        # Filtros
        sheet.write(3, 0, 'PROFESOR:', workbook.add_format({'bold': True}))
        sheet.write(3, 1, filters.get('teacher', 'Todos'))
        sheet.write(4, 0, 'CURSO:', workbook.add_format({'bold': True}))
        sheet.write(4, 1, filters.get('subject', 'Todos'))
        sheet.write(5, 0, 'SECCIÓN:', workbook.add_format({'bold': True}))
        sheet.write(5, 1, filters.get('section', 'Todas'))
        
        # Encabezados de columnas
        headers = [
            'Teacher', 'Course', 'Section', 'Status',
            'Class days', 'Start - End / Month', 'Groups Up to Date',
            'Active Groups', 'Student Cohort Size', 'Age Band'
        ]
        
        # Escribir encabezados
        row = 7
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)
        
        # Variables para totales
        total_active_groups = 0
        total_up_to_date = 0
        total_students = 0
        current_row = row + 1
        
        # Iterar por cada profesor
        for teacher_data in teachers_data:
            teacher = teacher_data['teacher']
            sections = teacher_data['sections']
            active_groups = teacher_data['active_groups']
            groups_up_to_date = teacher_data['groups_up_to_date']
            
            if not sections:
                continue
            
            # Escribir el nombre del profesor (fila de cabecera combinada)
            sheet.merge_range(
                current_row, 0,
                current_row + len(sections) - 1, 0,
                teacher.name or '',
                teacher_format
            )
            
            # Escribir Groups Up to Date (combinado)
            sheet.merge_range(
                current_row, 6,
                current_row + len(sections) - 1, 6,
                float(groups_up_to_date),
                cell_center_format
            )
            
            # Escribir Active Groups (combinado)
            sheet.merge_range(
                current_row, 7,
                current_row + len(sections) - 1, 7,
                float(active_groups),
                cell_center_format
            )
            
            # Iterar por las secciones del profesor
            for section_data in sections:
                # Course
                sheet.write(current_row, 1, section_data.get('course', ''), cell_format)
                
                # Section
                sheet.write(current_row, 2, section_data.get('code', ''), cell_format)
                
                # Status
                status = section_data.get('status', '')
                if status == 'READY TO BE FILED':
                    sheet.write(current_row, 3, status, status_red_format)
                else:
                    sheet.write(current_row, 3, status, cell_format)
                
                # Class days
                class_days = section_data.get('class_days', '')
                if not class_days or class_days == '':
                    class_days = 'ATTENDANCE RECORDS FINALISED'
                sheet.write(current_row, 4, class_days, cell_format)
                
                # Start - End / Month
                start_date = section_data.get('start_date', '')
                end_date = section_data.get('end_date', '')
                date_range = ''
                if start_date and end_date:
                    date_range = f"{start_date} - {end_date}"
                elif start_date:
                    date_range = start_date
                elif end_date:
                    date_range = end_date
                sheet.write(current_row, 5, date_range, cell_format)
                
                # Student Cohort Size
                total_students_section = section_data.get('total_students', 0)
                if total_students_section > 0:
                    sheet.write(current_row, 8, float(total_students_section), cell_right_format)
                else:
                    sheet.write(current_row, 8, 'NO DATA', cell_format)
                total_students += total_students_section
                
                # Age Band
                age_band = section_data.get('age_band', '')
                if not age_band and section_data.get('section'):
                    age_band = self._get_age_band(section_data['section'])
                sheet.write(current_row, 9, age_band, cell_format)
                
                current_row += 1
            
            # Acumular totales
            total_active_groups += active_groups
            total_up_to_date += groups_up_to_date
        
        # Fila de totales
        total_row = current_row + 1
        
        # Encabezado de totales
        sheet.merge_range(total_row, 0, total_row, 5, 'TOTALES:', workbook.add_format({
            'bold': True,
            'bg_color': '#2c3e50',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
        }))
        
        # Totales
        sheet.write(total_row, 6, float(total_up_to_date), cell_center_format)
        sheet.write(total_row, 7, float(total_active_groups), cell_center_format)
        sheet.write(total_row, 8, float(total_students), cell_right_format)
        
        # Autoajustar columnas
        sheet.set_column('A:A', 25)
        sheet.set_column('B:B', 35)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 25)
        sheet.set_column('E:E', 35)
        sheet.set_column('F:F', 30)
        sheet.set_column('G:G', 18)
        sheet.set_column('H:H', 18)
        sheet.set_column('I:I', 22)
        sheet.set_column('J:J', 30)
        
        _logger.info(f"Reporte XLSX generado con {len(teachers_data)} profesores")