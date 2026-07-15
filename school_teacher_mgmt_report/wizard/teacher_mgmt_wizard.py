# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)


class TeacherMgmtWizard(models.TransientModel):
    _name = 'teacher.mgmt.wizard'
    _description = 'Wizard para generar reporte de Gestión Docente'

    teacher_id = fields.Many2one(
        'school.teacher',
        string='Profesor',
        help='Filtrar el reporte por un profesor específico.'
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

    # report_type = fields.Selection(
    #     [
    #         ('pdf', 'PDF'),
    #         ('xlsx', 'Excel (XLSX)'),
    #     ],
    #     string='Tipo de Reporte',
    #     default='xlsx',
    #     required=True,
    # )

    def _get_domain(self):
        domain = []
        domain.append(('state', '!=', 'cancel'))

        if self.teacher_id:
            domain.append(('user_id', '=', self.teacher_id.id))
        if self.section_code:
            domain.append(('code', '=', self.section_code.upper()))

        if self.env.user.company_id:
            domain.append(('company_id', '=', self.env.user.company_id.id))

        return domain

    def _get_report_data(self):
        domain = self._get_domain()
        sections = self.env['school.standard'].search(domain)
        
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
            
            is_up_to_date = section.state in ['done', 'terminate']
            status = self._get_section_status(section)
            age_band = self._get_age_band(section)
            
            teachers_data[teacher.id]['sections'].append({
                'section': section,
                'course': section.subject_id.nombre or section.subject_id.name,
                'code': section.code,
                'status': status,
                'class_days': section.note or '',
                'start_date': section.start_date,
                'end_date': section.end_date,
                'total_students': section.total_students,
                'age_band': age_band,
                'is_up_to_date': is_up_to_date,
            })
            
            teachers_data[teacher.id]['active_groups'] += 1
            if is_up_to_date:
                teachers_data[teacher.id]['groups_up_to_date'] += 1
        
        result = list(teachers_data.values())
        
        return {
            'teachers_data': result,
            'current_date': self.date_today or fields.Date.today(),
            'filters': {
                'teacher': self.teacher_id.name if self.teacher_id else 'Todos',
                'section_code': self.section_code if self.section_code else 'Todas',
            },
            'total_teachers': len(result),
            'total_sections': sum(len(t['sections']) for t in result),
            'company': self.env.user.company_id,
        }

    def _get_section_status(self, section):
        if section.state == 'terminate':
            return 'READY TO BE FILED'
        
        if section.registroeva_ids:
            last_eva = section.registroeva_ids.sorted(key=lambda r: r.date_start, reverse=True)[0]
            if last_eva.date_start:
                return fields.Date.to_string(last_eva.date_start)
        
        if section.asistencia_ids:
            last_asi = section.asistencia_ids.sorted(key=lambda r: r.date_start, reverse=True)[0]
            if last_asi.date_start:
                return fields.Date.to_string(last_asi.date_start)
        
        if section.state == 'done':
            return fields.Date.to_string(section.start_date) if section.start_date else 'ACTIVE'
        
        return 'PENDING'

    def _get_age_band(self, section):
        level_name = section.standard_id.name.lower() if section.standard_id else ''
        
        kids_keywords = ['kids', 'niño', 'infantil', '8 a 10', '8-10']
        if any(keyword in level_name for keyword in kids_keywords):
            return 'Edades entre 8 y 10 años'
        
        teens_keywords = ['teens', 'adolescente', '11 a 14', '11-14']
        if any(keyword in level_name for keyword in teens_keywords):
            return 'Edades entre 11 y 14 años'
        
        return 'Adolescentes y Adultos'

    def generate_report(self):
        self.ensure_one()
        data = self._get_report_data()

        if not data['teachers_data']:
            raise ValidationError(_('No se encontraron profesores con secciones activas con los filtros seleccionados.'))

        # FORZAR XLSX
        return self.env.ref('school_teacher_mgmt_report.report_teacher_mgmt_xlsx_action').report_action(self, data=data)