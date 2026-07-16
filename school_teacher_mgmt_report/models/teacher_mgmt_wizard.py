# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
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
    
    section_code = fields.Char(
        string='Código de Sección',
        help='Filtrar el reporte por el código de la sección.'
    )
    
    date_today = fields.Date(
        'Fecha de Emisión',
        default=fields.Date.today,
        readonly=True
    )

    def _get_domain(self):
        """
        Construye el dominio para filtrar los registros de school.standard.
        """
        domain = []
        # Excluir secciones que están en estado 'cancel'
        domain.append(('state', '!=', 'cancel'))

        if self.teacher_id:
            domain.append(('user_id', '=', self.teacher_id.id))
        
        if self.subject_id:
            domain.append(('subject_id', '=', self.subject_id.id))
            
        if self.section_code:
            domain.append(('code', '=', self.section_code.upper().strip()))

        # Agregar filtro por compañía actual
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
            last_eva = section.registroeva_ids.sorted(key=lambda r: r.date_start or fields.Date.today(), reverse=True)[0]
            if last_eva.date_start:
                latest_date = last_eva.date_start
        
        # Buscar en registros de asistencia (si no se encontró fecha)
        if not latest_date and section.asistencia_ids:
            last_asi = section.asistencia_ids.sorted(key=lambda r: r.date_start or fields.Date.today(), reverse=True)[0]
            if last_asi.date_start:
                latest_date = last_asi.date_start
        
        # Si hay fecha, devolverla formateada
        if latest_date:
            try:
                if isinstance(latest_date, str):
                    from datetime import datetime
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

    def _get_report_data(self):
        """
        Obtiene los datos agrupados por profesor para el reporte.
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
                    'sections': [],
                    'active_groups': 0,
                    'groups_up_to_date': 0,
                }
            
            # Determinar si está al día
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
                'course': course_name,
                'code': section.code or '',
                'status': self._get_section_status(section),
                'class_days': section.note or 'ATTENDANCE RECORDS FINALISED',
                'start_date': start_date_str,
                'end_date': end_date_str,
                'total_students': section.total_students or 0,
                'age_band': self._get_age_band(section),
                'is_up_to_date': is_up_to_date,
            })
            
            teachers_data[teacher.id]['active_groups'] += 1
            if is_up_to_date:
                teachers_data[teacher.id]['groups_up_to_date'] += 1
        
        result = list(teachers_data.values())
        
        # Ordenar por nombre de profesor
        result.sort(key=lambda x: x['teacher'].name or '')
        
        return {
            'teachers_data': result,
            'current_date': self.date_today or fields.Date.today(),
            'filters': {
                'teacher': self.teacher_id.name if self.teacher_id else 'Todos',
                'subject': self.subject_id.nombre if self.subject_id else 'Todos',
                'section_code': self.section_code if self.section_code else 'Todas',
            },
            'total_teachers': len(result),
            'total_sections': sum(len(t['sections']) for t in result),
            'total_groups_up_to_date': sum(t['groups_up_to_date'] for t in result),
            'total_active_groups': sum(t['active_groups'] for t in result),
            'total_students': sum(sum(s['total_students'] for s in t['sections']) for t in result),
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