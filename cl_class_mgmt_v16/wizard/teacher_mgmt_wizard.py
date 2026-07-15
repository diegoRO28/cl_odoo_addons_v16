# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

MESES_ABBR = {
    1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic',
}


class TeacherMgmtWizard(models.TransientModel):
    _name = 'teacher.mgmt.wizard'
    _description = 'Reporte de Gestión Docente'

    fecha_emision = fields.Date(
        string='Fecha de emisión', default=fields.Date.today, readonly=True)

    teacher_ids = fields.Many2many(
        'school.teacher', string='Profesores',
        help='Si no selecciona ninguno, se incluyen todos los profesores.')
    standard_ids = fields.Many2many(
        'school.standard', string='Secciones',
        help='Si no selecciona ninguna, se incluyen todas las secciones.')
    subject_ids = fields.Many2many(
        'subject.subject', string='Cursos',
        help='Si no selecciona ninguno, se incluyen todos los cursos.')

    report_type = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
    ], string='Formato', required=True, default='pdf')

    def _secciones_en_curso(self, excluir=()):
        """school.standard en curso (state='done'), restringidas por los
        filtros YA seleccionados en el wizard, excepto los campos listados
        en 'excluir' (para no restringir un filtro por su propia
        selección)."""
        domain = [('state', '=', 'done')]
        if 'teacher_ids' not in excluir and self.teacher_ids:
            domain.append(('user_id', 'in', self.teacher_ids.ids))
        if 'subject_ids' not in excluir and self.subject_ids:
            domain.append(('subject_id', 'in', self.subject_ids.ids))
        if 'standard_ids' not in excluir and self.standard_ids:
            domain.append(('id', 'in', self.standard_ids.ids))
        return self.env['school.standard'].search(domain)

    @api.onchange('teacher_ids', 'subject_ids', 'standard_ids')
    def _onchange_filtros(self):
        """Los 3 filtros se complementan entre sí: elegir uno restringe las
        opciones disponibles de los otros dos a lo que realmente comparten
        las secciones en curso (mismo profesor/curso/sección)."""
        secciones_teacher = self._secciones_en_curso(excluir=('teacher_ids',))
        secciones_subject = self._secciones_en_curso(excluir=('subject_ids',))
        secciones_standard = self._secciones_en_curso(excluir=('standard_ids',))
        return {'domain': {
            'teacher_ids': [('id', 'in', secciones_teacher.mapped('user_id').ids)],
            'subject_ids': [('id', 'in', secciones_subject.mapped('subject_id').ids)],
            'standard_ids': [('id', 'in', secciones_standard.ids)],
        }}

    def _get_secciones(self):
        """Secciones EN CURSO (state='done') que entran en el reporte,
        según los filtros de profesor/sección/curso seleccionados."""
        self.ensure_one()
        return self._secciones_en_curso().sorted(
            key=lambda s: (s.user_id.name or '', s.id))

    @staticmethod
    def _status_from_pendientes(pendientes, fecha_referencia):
        """(up_to_date: bool, fecha: Date|False). Rojo (up_to_date=False) si
        hay un elemento vencido (date_start <= fecha de referencia) sin
        registrar; se muestra la fecha del más antiguo vencido. Si no hay
        ninguno vencido, verde; se muestra la fecha del próximo elemento
        pendiente, o False (nada pendiente) si no queda ninguno."""
        pendientes = pendientes.sorted('date_start')
        vencidos = pendientes.filtered(
            lambda a: a.date_start and a.date_start <= fecha_referencia)
        if vencidos:
            return False, vencidos[0].date_start
        if pendientes:
            return True, pendientes[0].date_start
        return True, False

    def _status_info(self, standard, fecha_referencia=None):
        """Estado de asistencia (encuentros) de la sección. Ver
        _status_from_pendientes."""
        fecha_referencia = fecha_referencia or self.fecha_emision
        pendientes = standard.asistencia_ids.filtered(lambda a: a.state == 'draft')
        return self._status_from_pendientes(pendientes, fecha_referencia)

    def _eval_status_info(self, standard, fecha_referencia):
        """Estado de evaluaciones de la sección. Ver
        _status_from_pendientes."""
        pendientes = standard.registroeva_ids.filtered(lambda e: e.state == 'draft')
        return self._status_from_pendientes(pendientes, fecha_referencia)

    @staticmethod
    def _imagen_base64(record, field_name):
        """Data URI de un campo binario (imagen) de 'record', o False si no
        tiene una cargada."""
        valor = record and record[field_name]
        if not valor:
            return False
        return 'data:image/png;base64,' + valor.decode('utf-8')

    def _foto_profesor(self, teacher):
        return self._imagen_base64(teacher, 'image_128')

    @staticmethod
    def _class_days(standard):
        """dias_clase_ids (días estructurados) si existen; si no, el texto
        libre 'Horario de Clases' (note)."""
        if standard.dias_clase_ids:
            return ', '.join(standard.dias_clase_ids.sorted('sequence').mapped('name'))
        return standard.note or ''

    @staticmethod
    def _formatear_fecha(fecha):
        if not fecha:
            return ''
        return '%d %s %s' % (fecha.day, MESES_ABBR.get(fecha.month, ''), fecha.year)

    def _start_end(self, standard):
        return '%s - %s' % (
            self._formatear_fecha(standard.start_date),
            self._formatear_fecha(standard.end_date),
        )

    def _ultimo_encuentro_info(self, standard):
        """Último encuentro (asistencia) ya cargado -- fecha de la clase y
        cuándo se cargó. No existe un campo explícito de 'fecha de carga',
        así que se usa write_date (última modificación del registro, que
        coincide con el momento en que el profesor marca asistencia) como
        aproximación razonable."""
        ultimo = standard.asistencia_ids.filtered(
            lambda a: a.state == 'terminate').sorted('date_start', reverse=True)[:1]
        if not ultimo:
            return None
        return {
            'fecha': self._formatear_fecha(ultimo.date_start),
            'cargado_el': self._formatear_fecha(ultimo.write_date.date()) if ultimo.write_date else '',
        }

    def _actividades_progreso(self, evaluacion):
        """Progreso de carga de notas por actividad (school.libroact),
        agregando los standard.actividades (uno por estudiante) de todos
        los standard.evaluaciones (uno por estudiante) de esta
        standard.evaluacion. 'completa' = todos los estudiantes ya tienen
        nota cargada (nota > 0) para esa actividad."""
        actividades = self.env['standard.actividades'].search(
            [('evaluacion_id', 'in', evaluacion.evaluacion_ids.ids)])
        por_actividad = {}
        orden = []
        for act in actividades:
            aid = act.actividad_id.id
            if aid not in por_actividad:
                por_actividad[aid] = {'nombre': act.nombre or '', 'total': 0, 'cargadas': 0}
                orden.append(aid)
            por_actividad[aid]['total'] += 1
            if act.nota:
                por_actividad[aid]['cargadas'] += 1
        return [{
            'nombre': por_actividad[aid]['nombre'],
            'cargadas': por_actividad[aid]['cargadas'],
            'total': por_actividad[aid]['total'],
            'completa': por_actividad[aid]['total'] > 0 and por_actividad[aid]['cargadas'] == por_actividad[aid]['total'],
        } for aid in orden]

    def _ultima_evaluacion_info(self, standard):
        """Última evaluación ya cargada (done o terminate) -- nombre, fecha,
        cuándo se cargó y, si sigue 'abierta' (state='done', todavía
        recibiendo notas), el progreso de carga por actividad."""
        ultima = standard.registroeva_ids.filtered(
            lambda e: e.state in ('done', 'terminate')).sorted('date_start', reverse=True)[:1]
        if not ultima:
            return None
        abierta = ultima.state == 'done'
        return {
            'nombre': ultima.libroevas_id.name or '',
            'fecha': self._formatear_fecha(ultima.date_start),
            'cargado_el': self._formatear_fecha(ultima.write_date.date()) if ultima.write_date else '',
            'abierta': abierta,
            'actividades': self._actividades_progreso(ultima) if abierta else [],
        }

    def _compute_report_data(self):
        """Arma la estructura de datos del reporte, agrupada por profesor,
        reutilizada tanto por el reporte PDF como por el XLSX."""
        self.ensure_one()
        secciones = self._get_secciones()

        profesores = []
        por_profesor = {}
        orden_profesores = []
        for standard in secciones:
            teacher = standard.user_id
            if teacher.id not in por_profesor:
                por_profesor[teacher.id] = {
                    'teacher_name': teacher.name or '',
                    'active_groups': 0,
                    'groups_up_to_date': 0,
                    'secciones': [],
                }
                orden_profesores.append(teacher.id)

            up_to_date, fecha_status = self._status_info(standard)
            info = por_profesor[teacher.id]
            info['active_groups'] += 1
            if up_to_date:
                info['groups_up_to_date'] += 1

            info['secciones'].append({
                'course': standard.subject_id.nombre or '',
                'section': standard.code or '',
                'status_label': self._formatear_fecha(fecha_status) if fecha_status else 'READY TO BE FILED',
                'status_color': 'green' if up_to_date else 'red',
                'class_days': self._class_days(standard),
                'start_end': self._start_end(standard),
                'student_cohort_size': standard.total_students,
                'age_band': standard.standard_id.name or '',
            })

        for teacher_id in orden_profesores:
            profesores.append(por_profesor[teacher_id])

        return {
            'fecha_emision': self.fecha_emision,
            'profesores': profesores,
        }

    @api.model
    def get_dashboard_data(self):
        """Datos en vivo para el dashboard OWL (cl_class_mgmt_v16). A
        diferencia del reporte PDF/XLSX (solo secciones EN CURSO), acá se
        incluyen también las CULMINADAS para poder mostrar el conteo de
        'grupos completados' por profesor, tal como en el prototipo
        (index.html)."""
        hoy = fields.Date.today()
        company = self.env.company
        secciones = self.env['school.standard'].search(
            [('state', 'in', ('done', 'terminate'))])

        por_profesor = {}
        orden_profesores = []
        demo = {'kids': 0, 'teens': 0, 'online': 0,
                'adults14': 0, 'adults56': 0, 'adults78': 0, 'scholarship': 0}
        total_students = 0
        global_active = 0
        global_up_to_date = 0
        global_eval_active = 0
        global_eval_up_to_date = 0
        cursos_set, niveles_set, campus_set = set(), set(), set()

        for standard in secciones.sorted(key=lambda s: (s.user_id.name or '', s.id)):
            teacher = standard.user_id
            tid = teacher.id or 0
            if tid not in por_profesor:
                por_profesor[tid] = {
                    'id': tid,
                    'name': teacher.name or 'Sin profesor',
                    'photo': self._foto_profesor(teacher),
                    'secciones': [],
                }
                orden_profesores.append(tid)

            is_closed = standard.state == 'terminate'
            up_to_date, fecha_status = True, False
            eval_up_to_date, eval_fecha_status = True, False
            if not is_closed:
                up_to_date, fecha_status = self._status_info(standard, fecha_referencia=hoy)
                global_active += 1
                if up_to_date:
                    global_up_to_date += 1

                eval_up_to_date, eval_fecha_status = self._eval_status_info(standard, hoy)
                global_eval_active += 1
                if eval_up_to_date:
                    global_eval_up_to_date += 1

            size = standard.total_students
            course_name = standard.subject_id.nombre or ''
            age_band = standard.standard_id.name or ''
            campus_name = standard.school_id.name or ''

            if not is_closed:
                total_students += size
                cursos_set.add(course_name)
                niveles_set.add(age_band)
                campus_set.add(campus_name)
                low = course_name.lower()
                if 'scholarship' in low:
                    demo['scholarship'] += size
                elif age_band == 'KIDS':
                    demo['kids'] += size
                elif age_band == 'TEENS':
                    demo['teens'] += size
                elif age_band == 'ONLINE':
                    demo['online'] += size
                elif 'upper' in low or 'master' in low:
                    demo['adults78'] += size
                elif 'advanced' in low:
                    demo['adults56'] += size
                else:
                    demo['adults14'] += size

            por_profesor[tid]['secciones'].append({
                'id': standard.id,
                'course': course_name,
                'section': standard.code or '',
                'campus': campus_name,
                'status_label': 'CULMINADO' if is_closed else (
                    self._formatear_fecha(fecha_status) if fecha_status else 'READY TO BE FILED'),
                'status_color': 'gray' if is_closed else ('green' if up_to_date else 'red'),
                'eval_status_label': 'CULMINADO' if is_closed else (
                    self._formatear_fecha(eval_fecha_status) if eval_fecha_status else 'READY TO BE FILED'),
                'eval_status_color': 'gray' if is_closed else ('green' if eval_up_to_date else 'red'),
                'is_closed': is_closed,
                'class_days': self._class_days(standard),
                'start_end': self._start_end(standard),
                'student_cohort_size': size,
                'age_band': age_band,
                'ultimo_encuentro': None if is_closed else self._ultimo_encuentro_info(standard),
                'ultima_evaluacion': None if is_closed else self._ultima_evaluacion_info(standard),
            })

        global_percentage = 100 if global_active == 0 else round(
            global_up_to_date * 100 / global_active)
        global_eval_percentage = 100 if global_eval_active == 0 else round(
            global_eval_up_to_date * 100 / global_eval_active)

        # Deja un snapshot de hoy cada vez que se abre el panel (además del
        # cron diario, que garantiza que quede uno aunque nadie lo abra) --
        # así el punto de "hoy" en el histórico refleja el valor más
        # reciente del día.
        self.env['cl.teacher.kpi.snapshot']._get_or_create_today(global_percentage, global_eval_percentage)

        profesores = []
        for tid in orden_profesores:
            info = por_profesor[tid]
            secciones_prof = info['secciones']
            active = [s for s in secciones_prof if not s['is_closed']]
            completed = [s for s in secciones_prof if s['is_closed']]
            ok = [s for s in active if s['status_color'] == 'green']
            eval_ok = [s for s in active if s['eval_status_color'] == 'green']
            percent = 100 if not active else round(len(ok) * 100 / len(active))
            eval_percent = 100 if not active else round(len(eval_ok) * 100 / len(active))
            profesores.append({
                'id': info['id'],
                'name': info['name'],
                'photo': info['photo'],
                'active_groups': len(active),
                'completed_groups': len(completed),
                'ok_groups': len(ok),
                'percent': percent,
                'eval_ok_groups': len(eval_ok),
                'eval_percent': eval_percent,
                'score': round((percent + eval_percent) / 2),
                'secciones': secciones_prof,
            })

        ranking = sorted(
            (p for p in profesores if p['active_groups'] > 0),
            key=lambda p: (-p['score'], -p['percent'], p['name']),
        )

        return {
            'fecha_emision': self._formatear_fecha(hoy),
            'company_name': company.name,
            'company_logo': self._imagen_base64(company, 'logo_web'),
            'global_percentage': global_percentage,
            'global_eval_percentage': global_eval_percentage,
            'total_students': total_students,
            'ranking': ranking,
            'demographics': demo,
            'profesores': profesores,
            'course_options': sorted(cursos_set),
            'nivel_options': sorted(niveles_set),
            'campus_options': sorted(campus_set),
        }

    def action_generar_reporte(self):
        self.ensure_one()
        data = self._compute_report_data()
        if self.report_type == 'xlsx':
            return self.env.ref(
                'cl_class_mgmt_v16.action_teacher_mgmt_report_xlsx').report_action(self, data=data)
        return self.env.ref(
            'cl_class_mgmt_v16.action_teacher_mgmt_report_pdf').report_action(self, data=data)
