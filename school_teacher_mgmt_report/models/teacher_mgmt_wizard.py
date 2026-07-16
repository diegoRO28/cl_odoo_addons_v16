# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class TeacherMgmtWizard(models.TransientModel):
    _name = 'teacher.mgmt.wizard'
    _description = 'Wizard para generar reporte de Gestión Docente'

    # --- Filtros del Wizard ---
    teacher_id = fields.Many2one(
        'school.teacher',
        string='Profesor',
        help='Filtrar el reporte por un profesor específico.'
    )
    
    subject_id = fields.Many2one(
        'subject.subject',
        string='Curso',
        help='Filtrar el reporte por un curso específico.'
    )
    
    section_id = fields.Many2one(
        'school.standard',
        string='Sección',
        help='Filtrar el reporte por una sección específica.'
    )
    
    date_today = fields.Date(
        'Fecha de Emisión',
        default=fields.Date.today,
        readonly=True
    )

    # --- ONCHANGE para filtrar dinámicamente ---
    
    @api.onchange('teacher_id')
    def _onchange_teacher_id(self):
        """
        Cuando se selecciona un profesor:
        1. Limpiar curso y sección
        2. Actualizar el dominio del curso para mostrar solo los del profesor
        """
        self.subject_id = False
        self.section_id = False
        
        if self.teacher_id:
            # Obtener los cursos del profesor
            subject_ids = self.teacher_id.subject_id.ids
            domain = [('id', 'in', subject_ids)] if subject_ids else [('id', '=', False)]
            return {'domain': {'subject_id': domain}}
        else:
            return {'domain': {'subject_id': []}}
        
    @api.onchange('subject_id')
    def _onchange_subject_id(self):
        """
        Cuando se selecciona un curso:
        1. Limpiar la sección
        2. Actualizar el dominio de la sección para mostrar solo las del curso
        """
        self.section_id = False
        
        if self.subject_id:
            domain = [('subject_id', '=', self.subject_id.id), ('state', '!=', 'cancel')]
            return {'domain': {'section_id': domain}}
        else:
            return {'domain': {'section_id': [('state', '!=', 'cancel')]}}

    # --- MÉTODOS PRINCIPALES ---

    def _get_domain(self):
        """
        Construye el dominio para filtrar los registros de school.standard.
        """
        domain = []
        # Excluir secciones canceladas
        domain.append(('state', '!=', 'cancel'))

        if self.teacher_id:
            domain.append(('user_id', '=', self.teacher_id.id))
        
        if self.subject_id:
            domain.append(('subject_id', '=', self.subject_id.id))
            
        if self.section_id:
            domain.append(('id', '=', self.section_id.id))

        # Filtrar por compañía actual
        if self.env.user.company_id:
            domain.append(('company_id', '=', self.env.user.company_id.id))

        return domain

    def _get_section_status(self, section):
        """
        Determina el estado de una sección.
        """
        # Si la sección está terminada
        if section.state == 'terminate':
            return 'READY TO BE FILED'
        
        # Buscar la última fecha de actividad
        latest_date = None
        
        # Buscar en registros de evaluación
        if section.registroeva_ids:
            try:
                last_eva = section.registroeva_ids.sorted(
                    key=lambda r: r.date_start or fields.Date.today(), 
                    reverse=True
                )[0]
                if last_eva.date_start:
                    latest_date = last_eva.date_start
            except:
                pass
        
        # Buscar en registros de asistencia (si no se encontró fecha)
        if not latest_date and section.asistencia_ids:
            try:
                last_asi = section.asistencia_ids.sorted(
                    key=lambda r: r.date_start or fields.Date.today(), 
                    reverse=True
                )[0]
                if last_asi.date_start:
                    latest_date = last_asi.date_start
            except:
                pass
        
        # Si hay fecha, devolverla formateada
        if latest_date:
            try:
                if isinstance(latest_date, str):
                    for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y']:
                        try:
                            dt = datetime.strptime(latest_date, fmt)
                            return dt.strftime('%d/%m/%Y')
                        except:
                            continue
                    return latest_date
                else:
                    return latest_date.strftime('%d/%m/%Y')
            except:
                return str(latest_date)
        
        # Si la sección está activa pero sin registros
        if section.state == 'done':
            if section.start_date:
                try:
                    return section.start_date.strftime('%d/%m/%Y')
                except:
                    return str(section.start_date)
            return 'ACTIVE'
        
        return 'PENDING'

    def _get_age_band(self, section):
        """
        Determina la banda de edad basada en el nivel.
        """
        level_name = section.standard_id.name.lower() if section.standard_id else ''
        
        kids_keywords = ['kids', 'niño', 'infantil', '8 a 10', '8-10']
        if any(keyword in level_name for keyword in kids_keywords):
            return 'Edades entre 8 y 10 años'
        
        teens_keywords = ['teens', 'adolescente', '11 a 14', '11-14']
        if any(keyword in level_name for keyword in teens_keywords):
            return 'Edades entre 11 y 14 años'
        
        return 'Adolescentes y Adultos'

    def _get_class_days(self, section):
        """
        Obtiene los días de clase del campo 'note' del modelo school.standard.
        """
        if section.note:
            # Si el campo note está vacío o contiene solo espacios, retornar el valor por defecto
            note = section.note.strip()
            if note:
                return note
        return 'ATTENDANCE RECORDS FINALISED'

    def _format_date_range(self, section):
        """
        Formatea el rango de fechas start_date y end_date.
        """
        start_date = section.start_date
        end_date = section.end_date
        
        if start_date and end_date:
            try:
                start_str = start_date.strftime('%b %dst')
                end_str = end_date.strftime('%b %dst %Y')
                return f"{start_str} - {end_str}"
            except:
                return f"{start_date} - {end_date}"
        elif start_date:
            try:
                return start_date.strftime('%b %dst %Y')
            except:
                return str(start_date)
        elif end_date:
            try:
                return end_date.strftime('%b %dst %Y')
            except:
                return str(end_date)
        return ''

    def _get_report_data(self):
        """
        Obtiene los datos agrupados por profesor para el reporte.
        Estructura exacta para el Excel:
        
        Teacher | Course | Section | Status | Class days | Start - End / Month | Groups Up to Date | Active Groups | Student Cohort Size | Age Band
        """
        domain = self._get_domain()
        sections = self.env['school.standard'].search(domain)
        _logger.info(f"Se encontraron {len(sections)} secciones para el reporte.")

        # Agrupar por profesor
        teachers_data = {}
        
        for section in sections:
            teacher = section.user_id
            if not teacher:
                continue
                
            if teacher.id not in teachers_data:
                teachers_data[teacher.id] = {
                    'teacher': teacher,
                    'teacher_name': teacher.name or '',
                    'sections': [],
                    'active_groups': 0,
                    'groups_up_to_date': 0,
                }
            
            # Determinar si está al día (up to date)
            # Una sección está "al día" si su estado es 'done' o 'terminate'
            is_up_to_date = section.state in ['done', 'terminate']
            
            # Obtener el nombre del curso
            course_name = section.subject_id.nombre or section.subject_id.name or ''
            
            # Formatear fechas
            start_date_str = ''
            end_date_str = ''
            if section.start_date:
                try:
                    start_date_str = section.start_date.strftime('%b %dst')
                except:
                    start_date_str = str(section.start_date)
            if section.end_date:
                try:
                    end_date_str = section.end_date.strftime('%b %dst %Y')
                except:
                    end_date_str = str(section.end_date)
            
            teachers_data[teacher.id]['sections'].append({
                'section': section,
                # Columna B: Course (nombre del curso)
                'course': course_name,
                # Columna C: Section (código de la sección)
                'code': section.code or '',
                # Columna D: Status
                'status': self._get_section_status(section),
                # Columna E: Class days
                'class_days': self._get_class_days(section),
                # Columna F: Start - End / Month
                'date_range': self._format_date_range(section),
                'start_date': start_date_str,
                'end_date': end_date_str,
                # Columna I: Student Cohort Size
                'total_students': section.total_students or 0,
                # Columna J: Age Band
                'age_band': self._get_age_band(section),
                'is_up_to_date': is_up_to_date,
            })
            
            # Contar grupos activos (todas las secciones del profesor)
            teachers_data[teacher.id]['active_groups'] += 1
            # Contar grupos al día
            if is_up_to_date:
                teachers_data[teacher.id]['groups_up_to_date'] += 1
        
        result = list(teachers_data.values())
        
        # Ordenar por nombre de profesor
        result.sort(key=lambda x: x['teacher'].name or '')
        
        # Calcular totales
        total_teachers = len(result)
        total_sections = sum(len(t['sections']) for t in result)
        total_groups_up_to_date = sum(t['groups_up_to_date'] for t in result)
        total_active_groups = sum(t['active_groups'] for t in result)
        total_students = sum(sum(s['total_students'] for s in t['sections']) for t in result)
        
        return {
            'teachers_data': result,
            'current_date': self.date_today or fields.Date.today(),
            'filters': {
                'teacher': self.teacher_id.name if self.teacher_id else 'Todos',
                'subject': self.subject_id.nombre if self.subject_id else 'Todos',
                'section': self.section_id.code if self.section_id else 'Todas',
            },
            'total_teachers': total_teachers,
            'total_sections': total_sections,
            'total_groups_up_to_date': total_groups_up_to_date,
            'total_active_groups': total_active_groups,
            'total_students': total_students,
            'company': self.env.user.company_id,
        }

    def generate_report(self):
        """
        Acción para generar y descargar el reporte en formato XLSX.
        """
        self.ensure_one()
        data = self._get_report_data()

        if not data['teachers_data']:
            raise ValidationError(_('No se encontraron profesores con secciones activas con los filtros seleccionados.'))

        # Generar reporte XLSX
        return self.env.ref('school_teacher_mgmt_report.report_teacher_mgmt_xlsx_action').report_action(self, data=data)