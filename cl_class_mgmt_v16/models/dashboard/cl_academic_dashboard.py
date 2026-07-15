# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ClAcademicDashboard(models.Model):
    _name = 'cl.academic.dashboard'
    _description = 'Dashboard Académica'
    _inherit = 'cl.dashboard.config'

    standard_ids = fields.Many2many('standard.standard', string='Niveles')
    subject_ids = fields.Many2many('subject.subject', string='Cursos')
    section_state = fields.Selection([
        ('all', 'Todas'),
        ('done', 'En curso'),
        ('terminate', 'Culminadas'),
    ], default='done', string='Estado de sección')
    group_by = fields.Selection([
        ('none', 'Sin agrupación'),
        ('campus', 'Campus'),
        ('standard', 'Nivel'),
        ('subject', 'Curso'),
    ], default='none', string='Agrupar por')

    @api.model
    def _get_or_create_mine(self):
        """Cada usuario tiene su propia configuración persistente (filtros
        recordados entre visitas), de ahí que este modelo sea un Model
        normal y no un wizard transaccional."""
        rec = self.search([('user_id', '=', self.env.uid)], limit=1)
        if not rec:
            rec = self.create({})
        return rec

    def _aplicar_filtros(self, filters):
        """Escribe (y por lo tanto persiste) los filtros recibidos desde el
        componente OWL. Solo toca los campos presentes en 'filters'."""
        self.ensure_one()
        vals = {}
        if 'campus_ids' in filters:
            vals['campus_ids'] = [(6, 0, filters['campus_ids'] or [])]
        if 'standard_ids' in filters:
            vals['standard_ids'] = [(6, 0, filters['standard_ids'] or [])]
        if 'subject_ids' in filters:
            vals['subject_ids'] = [(6, 0, filters['subject_ids'] or [])]
        if 'section_state' in filters:
            vals['section_state'] = filters['section_state']
        if 'group_by' in filters:
            vals['group_by'] = filters['group_by']
        if vals:
            self.write(vals)

    def _domain_secciones(self):
        """Filtros aplicados a school.standard. NOTA: period_mode/date_from/
        date_to (heredados de cl.dashboard.config) no se aplican todavía
        aquí -- filtrar por start_date de la sección con un preset de
        'este mes/trimestre/año' dejaría la mayoría de las secciones en
        curso fuera (empezaron antes), vaciando el panel. Queda el campo
        para uso futuro (ej. en KPIs que sí sean sensibles a fecha)."""
        self.ensure_one()
        if self.section_state == 'all':
            domain = [('state', 'in', ('done', 'terminate'))]
        else:
            domain = [('state', '=', self.section_state)]
        if self.campus_ids:
            domain.append(('school_id', 'in', self.campus_ids.ids))
        if self.standard_ids:
            domain.append(('standard_id', 'in', self.standard_ids.ids))
        if self.subject_ids:
            domain.append(('subject_id', 'in', self.subject_ids.ids))
        return domain

    def _compute_recent_sections(self, wizard):
        """Últimas secciones creadas (independiente del filtro de estado,
        para que una sección recién creada -- todavía en 'draft' -- se
        pueda ver acá aunque el filtro de Estado esté en 'En curso').
        Respeta campus/nivel/curso porque sigue siendo útil filtrar el
        contexto, pero no el estado."""
        self.ensure_one()
        domain = []
        if self.campus_ids:
            domain.append(('school_id', 'in', self.campus_ids.ids))
        if self.standard_ids:
            domain.append(('standard_id', 'in', self.standard_ids.ids))
        if self.subject_ids:
            domain.append(('subject_id', 'in', self.subject_ids.ids))
        recientes = self.env['school.standard'].search(domain, order='create_date desc', limit=8)
        return [{
            'id': r.id,
            'section': r.code or '',
            'course': r.subject_id.nombre or '',
            'teacher': r.user_id.name or 'Sin profesor',
            'campus': r.school_id.name or '',
            'estado': r.get_estado(r.state),
            'created': wizard._formatear_fecha(r.create_date.date()) if r.create_date else '',
        } for r in recientes]

    def _compute_alertas(self, secciones, secciones_por_id):
        """3 categorías de alerta académica (reemplaza a las alertas de
        'vencidos sin registrar' -- a pedido del usuario, 2026-07-15):
          1. Secciones con más de 1/4 de sus estudiantes reprobados
             (student.inscripcion.state_eva == 'aplazado').
          2. Secciones con al menos un estudiante con más de 1/4 de
             inasistencias (subject.asistencias.is_attended == False).
          3. Estudiantes con más de 3 inasistencias CONSECUTIVAS (racha),
             sin importar el % total.
        """
        self.ensure_one()
        alertas = []
        if not secciones:
            return alertas

        # --- 1. Reprobados por sección ---
        inscripciones = self.env['student.inscripcion'].search(
            [('standard_id', 'in', secciones.ids), ('state', '=', 'done')])
        total_por_seccion, aplazados_por_seccion = {}, {}
        for insc in inscripciones:
            sid = insc.standard_id.id
            total_por_seccion[sid] = total_por_seccion.get(sid, 0) + 1
            if insc.state_eva == 'aplazado':
                aplazados_por_seccion[sid] = aplazados_por_seccion.get(sid, 0) + 1

        for sid, total in total_por_seccion.items():
            aplazados = aplazados_por_seccion.get(sid, 0)
            if total and (aplazados / total) > 0.25:
                standard = secciones_por_id.get(sid)
                if not standard:
                    continue
                alertas.append({
                    'id': standard.id,
                    'tipo': 'Reprobados',
                    'section': standard.code or '',
                    'course': standard.subject_id.nombre or '',
                    'target': 'Toda la sección',
                    'detalle': '%s de %s estudiantes reprobados (%s%%)' % (
                        aplazados, total, round(aplazados * 100 / total)),
                })

        # --- 2 y 3. Inasistencias (altas y consecutivas) por estudiante ---
        filas = self.env['subject.asistencias'].search_read(
            [('standard_id', 'in', secciones.ids)],
            ['student_id', 'standard_id', 'is_attended', 'date_start'])

        por_estudiante = {}
        for fila in filas:
            if not fila['student_id'] or not fila['standard_id']:
                continue
            key = (fila['standard_id'][0], fila['student_id'][0])
            info = por_estudiante.setdefault(key, {
                'student': fila['student_id'][1], 'total': 0, 'ausencias': 0, 'fechas': [],
            })
            info['total'] += 1
            if not fila['is_attended']:
                info['ausencias'] += 1
            info['fechas'].append((fila['date_start'], fila['is_attended']))

        for (sid, _stid), info in por_estudiante.items():
            standard = secciones_por_id.get(sid)
            if not standard or not info['total']:
                continue

            if (info['ausencias'] / info['total']) > 0.25:
                alertas.append({
                    'id': standard.id,
                    'tipo': 'Inasistencia alta',
                    'section': standard.code or '',
                    'course': standard.subject_id.nombre or '',
                    'target': info['student'],
                    'detalle': '%s de %s encuentros (%s%%)' % (
                        info['ausencias'], info['total'], round(info['ausencias'] * 100 / info['total'])),
                })

            racha = max_racha = 0
            for _fecha, asistio in sorted(info['fechas'], key=lambda x: x[0]):
                racha = 0 if asistio else racha + 1
                max_racha = max(max_racha, racha)
            if max_racha > 3:
                alertas.append({
                    'id': standard.id,
                    'tipo': 'Inasistencia consecutiva',
                    'section': standard.code or '',
                    'course': standard.subject_id.nombre or '',
                    'target': info['student'],
                    'detalle': '%s inasistencias consecutivas' % max_racha,
                })

        return alertas

    def _compute_dashboard_data(self):
        self.ensure_one()
        wizard = self.env['teacher.mgmt.wizard']
        hoy = fields.Date.today()
        company = self.env.company

        secciones = self.env['school.standard'].search(self._domain_secciones())
        secciones_por_id = {s.id: s for s in secciones}

        total_estudiantes = sum(secciones.mapped('total_students'))
        total_activas = len(secciones.filtered(lambda s: s.state == 'done'))

        asis_activas = eval_activas = asis_ok = eval_ok = 0
        por_campus, por_nivel = {}, {}
        progreso_encuentros = []
        progreso_evaluaciones = []
        rows = []
        notas_por_seccion = {}

        for s in secciones:
            campus_name = s.school_id.name or 'Sin campus'
            nivel_name = s.standard_id.name or 'Sin nivel'
            por_campus[campus_name] = por_campus.get(campus_name, 0) + 1
            por_nivel[nivel_name] = por_nivel.get(nivel_name, 0) + s.total_students

            # Promedio de notas por SECCIÓN (no por curso): se calcula
            # siempre, sin importar si la sección sigue en curso o ya
            # culminó, para poder identificar qué sección concreta tiene
            # mejor rendimiento.
            evaluadas = s.registroeva_ids.filtered(lambda e: e.average > 0)
            if evaluadas:
                notas_por_seccion[s.id] = {
                    'id': s.id,
                    'section': s.code or '',
                    'course': s.subject_id.nombre or '',
                    'average': round(sum(evaluadas.mapped('average')) / len(evaluadas), 1),
                }

            en_curso = s.state == 'done'
            asis_up, asis_fecha = True, False
            eval_up, eval_fecha = True, False

            if en_curso:
                pendientes_asis = s.asistencia_ids.filtered(lambda a: a.state == 'draft')
                asis_up, asis_fecha = wizard._status_from_pendientes(pendientes_asis, hoy)
                asis_activas += 1
                if asis_up:
                    asis_ok += 1

                pendientes_eval = s.registroeva_ids.filtered(lambda e: e.state == 'draft')
                eval_up, eval_fecha = wizard._status_from_pendientes(pendientes_eval, hoy)
                eval_activas += 1
                if eval_up:
                    eval_ok += 1

                total_encuentros = len(s.asistencia_ids)
                dictados = len(s.asistencia_ids.filtered(lambda a: a.state == 'terminate'))
                pct_enc = 100 if not total_encuentros else round(dictados * 100 / total_encuentros)
                progreso_encuentros.append({
                    'id': s.id, 'section': s.code or '', 'course': s.subject_id.nombre or '',
                    'pct': pct_enc, 'dictados': dictados, 'total': total_encuentros,
                })

                total_evas = len(s.registroeva_ids)
                evas_terminadas = len(s.registroeva_ids.filtered(lambda e: e.state == 'terminate'))
                pct_eva = 100 if not total_evas else round(evas_terminadas * 100 / total_evas)
                progreso_evaluaciones.append({
                    'id': s.id, 'section': s.code or '', 'course': s.subject_id.nombre or '',
                    'pct': pct_eva, 'dictados': evas_terminadas, 'total': total_evas,
                })

            rows.append({
                'id': s.id,
                'section': s.code or '',
                'course': s.subject_id.nombre or '',
                'teacher': s.user_id.name or 'Sin profesor',
                'campus': campus_name,
                'standard': nivel_name,
                'average': round(s.average, 1) if s.average else 0,
                'average_label': ('%.1f' % s.average) if s.average else 'Sin datos',
                # Estado real de la sección (draft/done/terminate/cancel),
                # independiente del estado de asistencia/evaluación de
                # arriba -- por iniciar / iniciado / culminado.
                'section_status_label': s.get_estado(s.state).upper(),
                'section_status_color': {'draft': 'gray', 'done': 'green', 'terminate': 'gray'}.get(s.state, 'gray'),
                'status_label': 'CULMINADO' if not en_curso else (
                    wizard._formatear_fecha(asis_fecha) if asis_fecha else 'AL DÍA'),
                'status_color': 'gray' if not en_curso else ('green' if asis_up else 'red'),
                'eval_status_label': 'CULMINADO' if not en_curso else (
                    wizard._formatear_fecha(eval_fecha) if eval_fecha else 'AL DÍA'),
                'eval_status_color': 'gray' if not en_curso else ('green' if eval_up else 'red'),
                'total_students': s.total_students,
            })

        pct_asis = 100 if not asis_activas else round(asis_ok * 100 / asis_activas)
        pct_eval = 100 if not eval_activas else round(eval_ok * 100 / eval_activas)

        campus_series = sorted(
            ({'label': k, 'value': v} for k, v in por_campus.items()),
            key=lambda x: -x['value'])
        nivel_series = sorted(
            ({'label': k, 'value': v} for k, v in por_nivel.items()),
            key=lambda x: -x['value'])
        # De mayor a menor por defecto (a pedido del usuario, 2026-07-15) --
        # el componente OWL permite luego reordenar en cualquier sentido.
        progreso_encuentros_ordenado = sorted(progreso_encuentros, key=lambda p: -p['pct'])
        progreso_evaluaciones_ordenado = sorted(progreso_evaluaciones, key=lambda p: -p['pct'])
        top_secciones = sorted(notas_por_seccion.values(), key=lambda x: -x['average'])[:8]

        alertas = self._compute_alertas(secciones, secciones_por_id)
        recent_sections = self._compute_recent_sections(wizard)

        groups = None
        if self.group_by != 'none':
            key_map = {'campus': 'campus', 'standard': 'standard', 'subject': 'course'}
            group_key = key_map[self.group_by]
            buckets = {}
            orden = []
            for row in rows:
                label = row[group_key]
                if label not in buckets:
                    buckets[label] = []
                    orden.append(label)
                buckets[label].append(row)
            groups = [{'label': label, 'rows': buckets[label]} for label in orden]

        kpis = [
            # NOTA: allow_viz solo incluye 'bar'/'donut' cuando el KPI tiene
            # un desglose real (series) detrás. Un conteo único (secciones
            # activas, estudiantes totales) no tiene un desglose que
            # mostrar en barra/donut sin inventar datos, así que se deja
            # solo en 'number' (ver claude.md, "Es un chart? -> single
            # current value -> stat tile"). Los porcentajes (asistencias/
            # evaluaciones al día) sí soportan bar/donut, pero como
            # "medidor" (el % lleno, sin desglose) en vez de una serie.
            {'key': 'total_secciones_activas', 'label': 'Secciones activas',
             'value': total_activas, 'value_formatted': str(total_activas),
             'delta': None, 'delta_label': '', 'viz': 'number',
             'allow_viz': ['number'], 'color': 'blue', 'series': None},
            {'key': 'total_estudiantes', 'label': 'Estudiantes matriculados',
             'value': total_estudiantes, 'value_formatted': str(total_estudiantes),
             'delta': None, 'delta_label': '', 'viz': 'number',
             'allow_viz': ['number'], 'color': 'blue', 'series': None},
            {'key': 'pct_asistencias_al_dia', 'label': 'Asistencias al día',
             'value': pct_asis, 'value_formatted': '%s%%' % pct_asis,
             'delta': None, 'delta_label': '', 'viz': 'donut',
             'allow_viz': ['number', 'bar', 'donut'], 'color': 'teal', 'series': None},
            {'key': 'pct_evaluaciones_al_dia', 'label': 'Evaluaciones al día',
             'value': pct_eval, 'value_formatted': '%s%%' % pct_eval,
             'delta': None, 'delta_label': '', 'viz': 'donut',
             'allow_viz': ['number', 'bar', 'donut'], 'color': 'teal', 'series': None},
            {'key': 'secciones_por_campus', 'label': 'Secciones por campus',
             'value': len(campus_series), 'value_formatted': str(len(campus_series)),
             'delta': None, 'delta_label': '', 'viz': 'donut',
             'allow_viz': ['bar', 'donut'], 'color': 'blue', 'series': campus_series},
            {'key': 'estudiantes_por_nivel', 'label': 'Estudiantes por nivel',
             'value': total_estudiantes, 'value_formatted': str(total_estudiantes),
             'delta': None, 'delta_label': '', 'viz': 'donut',
             'allow_viz': ['bar', 'donut'], 'color': 'purple', 'series': nivel_series},
            {'key': 'progreso_encuentros', 'label': 'Progreso de encuentros',
             'value': len(progreso_encuentros_ordenado), 'value_formatted': str(len(progreso_encuentros_ordenado)),
             'delta': None, 'delta_label': '', 'viz': 'bar',
             'allow_viz': ['bar', 'table'], 'color': 'amber',
             'series': [{'id': p['id'], 'label': p['section'], 'value': p['pct']} for p in progreso_encuentros_ordenado[:8]]},
            {'key': 'progreso_evaluaciones', 'label': 'Progreso de evaluaciones',
             'value': len(progreso_evaluaciones_ordenado), 'value_formatted': str(len(progreso_evaluaciones_ordenado)),
             'delta': None, 'delta_label': '', 'viz': 'bar',
             'allow_viz': ['bar', 'table'], 'color': 'amber',
             'series': [{'id': p['id'], 'label': p['section'], 'value': p['pct']} for p in progreso_evaluaciones_ordenado[:8]]},
            {'key': 'mejores_secciones_promedio', 'label': 'Secciones con mejor promedio',
             'value': top_secciones[0]['average'] if top_secciones else 0,
             'value_formatted': ('%s pts' % top_secciones[0]['average']) if top_secciones else 'Sin datos',
             'delta': None, 'delta_label': '', 'viz': 'bar',
             'allow_viz': ['bar', 'table'], 'color': 'purple',
             # No es un desglose de un todo (cada sección tiene su propio
             # promedio, no suman 100%) -- por eso 'bar', nunca 'donut'
             # (mismo criterio que el ranking docente).
             'series': [{'id': t['id'], 'label': '%s (%s)' % (t['section'], t['course']), 'value': t['average']}
                        for t in top_secciones]},
            # 'Alertas académicas' NO se repite acá como tarjeta -- ya se ve
            # el conteo en el badge de la pestaña Alertas (evita duplicar
            # el mismo número dos veces en pantalla).
        ]

        return {
            'company_name': company.name,
            'company_logo': wizard._imagen_base64(company, 'logo_web'),
            'generated_at': wizard._formatear_fecha(hoy),
            'filters_applied': {
                'campus_ids': self.campus_ids.ids,
                'standard_ids': self.standard_ids.ids,
                'subject_ids': self.subject_ids.ids,
                'section_state': self.section_state,
                'group_by': self.group_by,
            },
            'campus_options': [{'id': c.id, 'name': c.name} for c in self.env['school.campus'].search([])],
            'standard_options': [{'id': s.id, 'name': s.name} for s in self.env['standard.standard'].search([])],
            'subject_options': [{'id': s.id, 'name': s.nombre} for s in self.env['subject.subject'].search([])],
            'kpis': kpis,
            'rows': rows,
            'groups': groups,
            'alerts': alertas,
            'progress_meetings': progreso_encuentros_ordenado,
            'progress_evaluations': progreso_evaluaciones_ordenado,
            'recent_sections': recent_sections,
        }

    @api.model
    def get_dashboard_data(self, filters=None):
        rec = self._get_or_create_mine()
        if filters:
            rec._aplicar_filtros(filters)
        return rec._compute_dashboard_data()

    @api.model
    def get_kpi_data(self, kpi_key, filters=None):
        rec = self._get_or_create_mine()
        if filters:
            rec._aplicar_filtros(filters)
        data = rec._compute_dashboard_data()
        for kpi in data['kpis']:
            if kpi['key'] == kpi_key:
                return kpi
        return None
