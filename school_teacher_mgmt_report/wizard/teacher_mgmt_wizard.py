# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
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

    def _get_domain(self):
        domain = [('state', '!=', 'cancel')]
        if self.teacher_id:
            domain.append(('user_id', '=', self.teacher_id.id))
        if self.section_code:
            domain.append(('code', '=', self.section_code.upper()))
        if self.env.user.company_id:
            domain.append(('company_id', '=', self.env.user.company_id.id))
        return domain

    def _get_section_status(self, section):
        if section.state == 'terminate':
            return 'READY TO BE FILED'
        if section.registroeva_ids:
            last_eva = section.registroeva_ids.sorted(
                key=lambda r: r.date_start, reverse=True)[0]
            if last_eva.date_start:
                return last_eva.date_start.strftime('%d/%m/%Y')
        if section.asistencia_ids:
            last_asi = section.asistencia_ids.sorted(
                key=lambda r: r.date_start, reverse=True)[0]
            if last_asi.date_start:
                return last_asi.date_start.strftime('%d/%m/%Y')
        if section.state == 'done':
            return section.start_date.strftime('%d/%m/%Y') if section.start_date else 'ACTIVE'
        return 'PENDING'

    def _get_age_band(self, section):
        level_name = section.standard_id.name.lower() if section.standard_id else ''
        if any(k in level_name for k in ['kids', 'niño', 'infantil', '8 a 10', '8-10']):
            return 'Edades entre 8 y 10 años'
        if any(k in level_name for k in ['teens', 'adolescente', '11 a 14', '11-14']):
            return 'Edades entre 11 y 14 años'
        return 'Adolescentes y Adultos'

    def _get_report_data(self):
        domain = self._get_domain()
        sections = self.env['school.standard'].search(domain)

        teachers_dict = {}
        order = []

        for section in sections:
            teacher = section.user_id
            if not teacher:
                continue

            if teacher.id not in teachers_dict:
                teachers_dict[teacher.id] = {
                    'teacher_name': teacher.name or '',
                    'sections': [],
                    'active_groups': 0,
                    'groups_up_to_date': 0,
                }
                order.append(teacher.id)

            is_up_to_date = section.state in ['done', 'terminate']

            start_date = section.start_date.strftime('%d/%m/%Y') if section.start_date else ''
            end_date = section.end_date.strftime('%d/%m/%Y') if section.end_date else ''
            if start_date and end_date:
                date_range = '{} - {}'.format(start_date, end_date)
            elif start_date:
                date_range = start_date
            else:
                date_range = ''

            teachers_dict[teacher.id]['sections'].append({
                'course': section.subject_id.nombre or section.subject_id.name or '',
                'code': section.code or '',
                'status': self._get_section_status(section),
                'class_days': section.note or '',
                'date_range': date_range,
                'total_students': section.total_students or 0,
                'age_band': self._get_age_band(section),
                'is_up_to_date': is_up_to_date,
            })

            teachers_dict[teacher.id]['active_groups'] += 1
            if is_up_to_date:
                teachers_dict[teacher.id]['groups_up_to_date'] += 1

        teachers_data = [teachers_dict[tid] for tid in order]

        current_date = self.date_today or fields.Date.today()

        return {
            'teachers_data': teachers_data,
            'current_date': current_date.strftime('%d/%m/%Y'),
            'filters': {
                'teacher': self.teacher_id.name if self.teacher_id else 'Todos',
                'section_code': self.section_code if self.section_code else 'Todas',
            },
            'total_teachers': len(teachers_data),
            'total_sections': sum(len(t['sections']) for t in teachers_data),
        }

    def generate_report(self):
        self.ensure_one()
        data = self._get_report_data()

        if not data['teachers_data']:
            raise ValidationError(_(
                'No se encontraron secciones con los filtros seleccionados.'
            ))

        return self.env.ref(
            'school_teacher_mgmt_report.report_teacher_mgmt_xlsx_action'
        ).report_action(self, data=data)