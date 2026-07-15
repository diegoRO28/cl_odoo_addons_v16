# See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

MESES_ES = [
    'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
    'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
]

# Mapas estáticos en vez de introspección de record._fields['x'].selection:
# ese campo puede ser un método/callable en vez de una lista de tuplas
# según cómo termine resuelto el related (crash real encontrado en
# producción, 'function' object is not iterable, al haber filas reales que
# ejercitaran ese código -- con el período por defecto vacío nunca se
# había disparado). Mismo criterio que get_estado() en este módulo: mapear
# a mano en vez de confiar en introspección frágil del ORM.
INVOICE_STATE_LABELS = {'draft': 'Borrador', 'posted': 'Publicada', 'cancel': 'Cancelada'}
PAYMENT_STATE_LABELS = {
    'not_paid': 'Sin pagar', 'in_payment': 'En proceso de pago', 'paid': 'Pagada',
    'partial': 'Pago parcial', 'reversed': 'Revertida', 'invoicing_legacy': 'Legado',
}


class ClAdminDashboard(models.Model):
    _name = 'cl.admin.dashboard'
    _description = 'Dashboard Administrativa'
    _inherit = 'cl.dashboard.config'

    inscripcion_state = fields.Selection([
        ('active', 'Activos'),
        ('retirado', 'Retirados'),
        ('all', 'Todos'),
    ], default='active', string='Estado de inscripción')
    show_financials = fields.Boolean(
        default=False, string='Mostrar facturación',
        help="Solo tiene efecto si el usuario tiene acceso a account.move "
             "(grupo account.group_account_user); controla si se calculan "
             "los KPIs de facturación/morosidad (evita el costo de esas "
             "consultas cuando el usuario no las necesita).")
    billing_group_by = fields.Selection([
        ('none', 'Sin agrupación'),
        ('curso', 'Curso'),
        ('seccion', 'Sección'),
        ('mes', 'Mes'),
    ], default='none', string='Agrupar facturación por')

    @api.model
    def _get_or_create_mine(self):
        rec = self.search([('user_id', '=', self.env.uid)], limit=1)
        if not rec:
            rec = self.create({})
        return rec

    def _aplicar_filtros(self, filters):
        self.ensure_one()
        vals = {}
        if 'campus_ids' in filters:
            vals['campus_ids'] = [(6, 0, filters['campus_ids'] or [])]
        if 'period_mode' in filters:
            vals['period_mode'] = filters['period_mode']
        if 'date_from' in filters:
            vals['date_from'] = filters['date_from']
        if 'date_to' in filters:
            vals['date_to'] = filters['date_to']
        if 'inscripcion_state' in filters:
            vals['inscripcion_state'] = filters['inscripcion_state']
        if 'show_financials' in filters:
            vals['show_financials'] = filters['show_financials']
        if 'billing_group_by' in filters:
            vals['billing_group_by'] = filters['billing_group_by']
        if vals:
            self.write(vals)

    def _resolver_periodo(self):
        """Resuelve date_from/date_to efectivos según period_mode. A
        diferencia del dashboard Académico (donde el período queda
        declarado pero sin aplicar -- ver cl_academic_dashboard.py), acá sí
        se usa: las inscripciones/retiros/cambios/facturas SON eventos
        puntuales con fecha propia (a diferencia de una sección que puede
        seguir 'en curso' desde antes del período), así que filtrar por
        período no vacía el panel sin motivo.

        'Último mes/trimestre/semestre' son ventanas MÓVILES de 1/3/6
        meses hacia atrás desde hoy (relativedelta), NO 'mes/trimestre/
        semestre calendario en curso' -- bug real reportado por el usuario
        (2026-07-15): con el cálculo anterior (inicio del trimestre/
        semestre calendario), como hoy cae justo al comienzo tanto del
        Q3 (trimestre Jul-Sep) como del segundo semestre (Jul-Dic), los 3
        filtros 'Este mes'/'Último trimestre'/'Último semestre' colapsaban
        a la MISMA ventana angosta (1-15 de julio), viéndose vacíos por
        igual mientras 'Todo el año' sí mostraba datos. Con ventanas
        móviles, 'Último trimestre' siempre cubre efectivamente 3 meses
        atrás sin importar en qué día del trimestre calendario caiga hoy.
        'Todo el año' se mantiene como año-a-la-fecha (1 de enero -> hoy),
        a propósito distinto de un 'últimos 12 meses' móvil -- es la
        lectura literal de 'todo el año' que pidió el usuario."""
        self.ensure_one()
        hoy = fields.Date.context_today(self)
        if self.period_mode == 'custom':
            return (self.date_from or hoy.replace(day=1)), (self.date_to or hoy)
        if self.period_mode == 'quarter':
            return hoy - relativedelta(months=3), hoy
        if self.period_mode == 'semester':
            return hoy - relativedelta(months=6), hoy
        if self.period_mode == 'year':
            return hoy.replace(month=1, day=1), hoy
        return hoy - relativedelta(months=1), hoy  # 'month'

    def _domain_company(self, field='company_id'):
        """Restringe a las compañías que el usuario actual tiene permitidas
        (self.env.companies) -- evita traer registros de OTRA compañía que
        el usuario no puede ver. IMPORTANTE (bug real encontrado en
        producción, 2026-07-15): student.retiro/student.cambio NO tienen
        un ir.rule propio basado en company_id (a diferencia de
        student.student, que sí lo tiene) -- sin este filtro, el .search()
        devuelve registros de compañías ajenas sin error, pero acceder
        DESPUÉS a 'student_id.name' en Python sí dispara AccessError (esa
        lectura cruza a student.student, que rechaza la compañía ajena),
        tumbando el dashboard COMPLETO con una sola excepción no capturada.
        Filtrar por compañía en el domain de búsqueda es la solución
        correcta (se resuelve por SQL/join, no dispara el rule del modelo
        relacionado) -- NO se usa sudo() acá a propósito: bypassear
        ir.rule ocultaría un problema real de aislamiento multi-compañía
        en vez de respetarlo."""
        return [(field, 'in', self.env.companies.ids)]

    def _domain_inscripciones(self, date_from, date_to):
        self.ensure_one()
        domain = [('inscription_date', '>=', date_from), ('inscription_date', '<=', date_to)] + self._domain_company()
        if self.inscripcion_state == 'active':
            domain.append(('state', '=', 'done'))
        elif self.inscripcion_state == 'retirado':
            domain.append(('state', '=', 'cancel'))
        if self.campus_ids:
            domain.append(('school_id', 'in', self.campus_ids.ids))
        return domain

    def _domain_retiros(self, date_from, date_to):
        self.ensure_one()
        domain = [('retiro_date', '>=', date_from), ('retiro_date', '<=', date_to)] + self._domain_company()
        if self.campus_ids:
            domain.append(('ri_id.school_id', 'in', self.campus_ids.ids))
        return domain

    def _domain_cambios(self, date_from, date_to):
        """Filtra por CAMPUS DE ORIGEN (ri_id.school_id, igual que retiros) --
        un cambio de sección 'pertenece' al campus del que sale el
        estudiante a efectos de este ranking. Compañía vía ri_id.company_id
        (student.cambio no tiene un company_id propio, solo company_des_id
        del lado destino -- ver claude.md)."""
        self.ensure_one()
        domain = [('cambio_date', '>=', date_from), ('cambio_date', '<=', date_to)] + self._domain_company('ri_id.company_id')
        if self.campus_ids:
            domain.append(('ri_id.school_id', 'in', self.campus_ids.ids))
        return domain

    def _domain_secciones_activas(self):
        self.ensure_one()
        domain = [('state', '=', 'done')] + self._domain_company()
        if self.campus_ids:
            domain.append(('school_id', 'in', self.campus_ids.ids))
        return domain

    def _domain_estudiantes_activos(self):
        """Snapshot de inscripciones actualmente activas -- a propósito SIN
        filtro de período: un estudiante inscrito hace 3 meses en un curso
        que sigue en curso hoy sigue siendo un 'estudiante activo', aunque
        su inscription_date caiga fuera del período seleccionado (mismo
        criterio que ya se evitó en el dashboard Académico para las
        secciones 'en curso' -- ver _domain_secciones() ahí)."""
        self.ensure_one()
        domain = [('state', '=', 'done')] + self._domain_company()
        if self.campus_ids:
            domain.append(('school_id', 'in', self.campus_ids.ids))
        return domain

    def _domain_facturas_inscripcion(self):
        self.ensure_one()
        domain = [('is_inscripcion', '=', True), ('state', '=', 'posted')] + self._domain_company()
        if self.campus_ids:
            domain.append(('inscripcion_id.school_id', 'in', self.campus_ids.ids))
        return domain

    def _has_billing_access(self):
        return self.env.user.has_group('account.group_account_user')

    def _top_secciones(self, records, section_field, limit=8):
        """Cuenta ocurrencias de `records` agrupadas por la sección
        (school.standard) referenciada en `section_field`, ordenado de
        mayor a menor. Usado para responder 'cuáles grupos tienen más
        retiros/cambios/inscripciones' (a pedido del usuario, 2026-07-15)."""
        agg, labels = {}, {}
        for r in records:
            sec = r[section_field]
            if not sec:
                continue
            agg[sec.id] = agg.get(sec.id, 0) + 1
            labels[sec.id] = sec.code or ''
        series = sorted(({'id': k, 'label': labels[k], 'value': v} for k, v in agg.items()), key=lambda x: -x['value'])
        return series[:limit]

    def _compute_capacidad(self):
        """Semáforo por sección activa (verde >70% ocupación, ámbar 40-70%,
        rojo <40% -- ver claude.md sección 9: rojo indica riesgo de sección
        poco rentable, no un problema de sobrecupo)."""
        self.ensure_one()
        secciones = self.env['school.standard'].search(self._domain_secciones_activas())
        rows = []
        pcts = []
        for s in secciones:
            if not s.capacity:
                continue
            pct = round(s.total_students * 100 / s.capacity)
            pcts.append(pct)
            color = 'green' if pct > 70 else ('amber' if pct >= 40 else 'red')
            rows.append({
                'id': s.id,
                'section': s.code or '',
                'course': s.subject_id.nombre or '',
                'campus': s.school_id.name or '',
                'capacity': s.capacity,
                'total_students': s.total_students,
                'remaining_seats': s.remaining_seats,
                'pct': pct,
                'color': color,
            })
        rows.sort(key=lambda r: r['pct'])
        pct_promedio = round(sum(pcts) / len(pcts)) if pcts else 0
        return rows, pct_promedio

    def _compute_retiros(self, date_from, date_to):
        self.ensure_one()
        retiros = self.env['student.retiro'].search(self._domain_retiros(date_from, date_to))

        rows = [{
            'id': r.id,
            'student': r.student_id.name or '',
            'section': r.standard_id.code or '',
            'course': r.subject_id.nombre or '',
            'campus': r.school_id.name or '',
            'motivo': r.tiporetiro_id.name or 'Sin motivo',
            'date': r.retiro_date.strftime('%d/%m/%Y') if r.retiro_date else '',
        } for r in retiros]

        por_motivo = {}
        for r in retiros:
            key = r.tiporetiro_id.name or 'Sin motivo'
            por_motivo[key] = por_motivo.get(key, 0) + 1
        motivo_series = sorted(
            ({'label': k, 'value': v} for k, v in por_motivo.items()), key=lambda x: -x['value'])

        por_mes = {}
        for r in retiros:
            if not r.retiro_date:
                continue
            key = (r.retiro_date.year, r.retiro_date.month)
            por_mes[key] = por_mes.get(key, 0) + 1
        meses_ordenados = sorted(por_mes.keys())
        by_month = [{'label': '%s %s' % (MESES_ES[m - 1], y), 'value': por_mes[(y, m)]} for y, m in meses_ordenados]

        top_secciones = self._top_secciones(retiros, 'standard_id')
        return len(retiros), rows, motivo_series, by_month, top_secciones

    def _compute_cambios(self, date_from, date_to):
        self.ensure_one()
        cambios = self.env['student.cambio'].search(self._domain_cambios(date_from, date_to))

        rows = [{
            'id': c.id,
            'student': c.student_id.name or '',
            'section_origen': c.standard_id.code or '',
            'course_origen': c.standard_id.subject_id.nombre or '',
            'campus_origen': c.school_id.name or '',
            'section_destino': c.standard_des_id.code or '',
            'course_destino': c.subject_des_id.nombre or '',
            'campus_destino': c.school_des_id.name or '',
            'motivo': c.tipocambio_id.name or 'Sin motivo',
            'date': c.cambio_date.strftime('%d/%m/%Y') if c.cambio_date else '',
        } for c in cambios]

        # Ranking por sección de ORIGEN -- 'de qué grupo salen más
        # estudiantes por cambio', simétrico al criterio de retiros.
        top_secciones = self._top_secciones(cambios, 'standard_id')
        return len(cambios), rows, top_secciones

    def _compute_inscripciones_por_mes(self, date_from, date_to):
        """Serie mensual de inscripciones -- a propósito NO respeta el chip
        'Estado de inscripción' (mide altas nuevas en el período, sin
        importar si luego se retiraron), solo período + campus, mismo
        criterio que 'últimas secciones creadas' en el dashboard Académico
        (una serie de tendencia se distorsiona si se filtra por estado
        actual)."""
        self.ensure_one()
        domain = [('inscription_date', '>=', date_from), ('inscription_date', '<=', date_to)] + self._domain_company()
        if self.campus_ids:
            domain.append(('school_id', 'in', self.campus_ids.ids))
        inscripciones = self.env['student.inscripcion'].search(domain)
        por_mes = {}
        for i in inscripciones:
            if not i.inscription_date:
                continue
            key = (i.inscription_date.year, i.inscription_date.month)
            por_mes[key] = por_mes.get(key, 0) + 1
        meses_ordenados = sorted(por_mes.keys())
        return [{'label': '%s %s' % (MESES_ES[m - 1], y), 'value': por_mes[(y, m)]} for y, m in meses_ordenados]

    def _compute_morosidad(self):
        """Snapshot (SIN filtro de período, mismo criterio que
        _domain_estudiantes_activos): una deuda de hace 2 meses sigue
        pendiente HOY aunque su invoice_date caiga fuera del período
        seleccionado. Agrupa por curso/sección/profesor para responder
        'cuáles son los grupos con mayor morosidad' (a pedido del
        usuario)."""
        self.ensure_one()
        moves = self.env['account.move'].search(
            self._domain_facturas_inscripcion() + [('payment_state', 'in', ('not_paid', 'partial'))])
        hoy = fields.Date.context_today(self)
        por_curso, por_seccion, por_profesor, seccion_labels = {}, {}, {}, {}
        rows = []
        for m in moves:
            insc = m.inscripcion_id
            residual = m.amount_residual
            if not insc or residual <= 0:
                continue
            seccion = insc.standard_id
            curso = seccion.subject_id.nombre or 'Sin curso'
            seccion_label = seccion.code or ''
            profesor = seccion.user_id.name or 'Sin profesor'
            por_curso[curso] = por_curso.get(curso, 0) + residual
            por_seccion[seccion.id] = por_seccion.get(seccion.id, 0) + residual
            seccion_labels[seccion.id] = seccion_label
            por_profesor[profesor] = por_profesor.get(profesor, 0) + residual
            dias_atraso = (hoy - m.invoice_date_due).days if m.invoice_date_due and m.invoice_date_due < hoy else 0
            rows.append({
                'id': insc.id,
                'invoice': m.name or '',
                'student': insc.student_id.name or '',
                'section': seccion_label,
                'course': curso,
                'teacher': profesor,
                'campus': insc.school_id.name or '',
                'amount_residual': round(residual, 2),
                'amount_total': round(m.amount_total, 2),
                'due_date': m.invoice_date_due.strftime('%d/%m/%Y') if m.invoice_date_due else 'Sin vencimiento',
                'dias_atraso': dias_atraso,
            })
        rows.sort(key=lambda r: -r['amount_residual'])

        curso_series = sorted(({'label': k, 'value': round(v, 2)} for k, v in por_curso.items()), key=lambda x: -x['value'])
        seccion_series = sorted(
            ({'id': k, 'label': seccion_labels[k], 'value': round(v, 2)} for k, v in por_seccion.items()),
            key=lambda x: -x['value'])[:8]
        profesor_series = sorted(({'label': k, 'value': round(v, 2)} for k, v in por_profesor.items()), key=lambda x: -x['value'])[:8]

        total_morosidad = sum(r['amount_residual'] for r in rows)
        vencidas = [r for r in rows if r['dias_atraso'] > 0]
        total_vencido = sum(r['amount_residual'] for r in vencidas)
        return {
            'rows': rows,
            'por_curso': curso_series,
            'por_seccion': seccion_series,
            'por_profesor': profesor_series,
            'total_morosidad': round(total_morosidad, 2),
            'total_vencido': round(total_vencido, 2),
            'cantidad_vencidas': len(vencidas),
            'cantidad_facturas': len(rows),
        }

    def _compute_cobrado(self, moves, date_from, date_to):
        """Dinero EFECTIVAMENTE recibido en el período, vía account.payment
        -- a propósito NO se deriva de 'amount_total - amount_residual' de
        la factura, porque eso mezclaría la fecha de la FACTURA con la
        fecha real del COBRO (un pago de hoy puede corresponder a una
        factura de hace meses, y viceversa). A pedido explícito del
        usuario: facturado (account.move) != cobrado (account.payment) !=
        pendiente (account.move.amount_residual), son 3 conceptos
        distintos que no deben mezclarse en un solo número.

        account.payment.reconciled_invoice_ids es un campo COMPUTADO sin
        store/search (confirmado en el código fuente de Odoo 16,
        addons/account/models/account_payment.py) -- no se puede usar en
        un domain de búsqueda. Por eso acá se buscan los pagos de cliente
        posteados en el rango de fechas y se filtra, en Python, cuáles
        reconcilian contra alguna factura del conjunto `moves` ya conocido
        (ya filtrado por campus/is_inscripcion). Simplificación aceptada:
        si un mismo pago reconciliara PARCIALMENTE contra facturas fuera
        de `moves` además de una factura de `moves`, se cuenta el monto
        completo del pago (no solo la porción reconciliada contra esa
        factura) -- caso de borde poco probable en este negocio (un pago
        de un padre normalmente cubre solo facturas de inscripción de su
        propio hijo)."""
        self.ensure_one()
        if not moves:
            return 0.0
        move_ids = set(moves.ids)
        payments = self.env['account.payment'].search([
            ('date', '>=', date_from), ('date', '<=', date_to),
            ('payment_type', '=', 'inbound'), ('partner_type', '=', 'customer'),
            ('state', '=', 'posted'),
        ] + self._domain_company())
        total = sum(p.amount for p in payments if set(p.reconciled_invoice_ids.ids) & move_ids)
        return round(total, 2)

    def _compute_facturacion(self, date_from, date_to, morosidad):
        """Solo se calcula si el usuario tiene acceso a account.move Y
        show_financials está activo (evita el costo de estas consultas
        cuando no hacen falta). 'Facturado' y 'Cobrado' SÍ respetan el
        período (son eventos con fecha propia); 'Pendiente'/'Vencido' son
        el snapshot ya calculado por _compute_morosidad (sin período, ver
        ahí el porqué)."""
        self.ensure_one()
        domain_periodo = self._domain_facturas_inscripcion() + [
            ('invoice_date', '>=', date_from), ('invoice_date', '<=', date_to)]
        moves_periodo = self.env['account.move'].search(domain_periodo)
        total_facturado = sum(moves_periodo.mapped('amount_total'))

        todas_facturas = self.env['account.move'].search(self._domain_facturas_inscripcion())
        total_cobrado = self._compute_cobrado(todas_facturas, date_from, date_to)

        breakdown = []
        if self.billing_group_by == 'curso':
            agg = {}
            for m in moves_periodo:
                key = (m.inscripcion_id.standard_id.subject_id.nombre or 'Sin curso') if m.inscripcion_id else 'Sin curso'
                agg[key] = agg.get(key, 0) + m.amount_total
            breakdown = sorted(({'label': k, 'value': round(v, 2)} for k, v in agg.items()), key=lambda x: -x['value'])
        elif self.billing_group_by == 'seccion':
            agg, labels = {}, {}
            for m in moves_periodo:
                insc = m.inscripcion_id
                if not insc:
                    continue
                sec = insc.standard_id
                agg[sec.id] = agg.get(sec.id, 0) + m.amount_total
                labels[sec.id] = sec.code or ''
            breakdown = sorted(
                ({'id': k, 'label': labels[k], 'value': round(v, 2)} for k, v in agg.items()),
                key=lambda x: -x['value'])[:8]
        elif self.billing_group_by == 'mes':
            agg = {}
            for m in moves_periodo:
                if not m.invoice_date:
                    continue
                key = (m.invoice_date.year, m.invoice_date.month)
                agg[key] = agg.get(key, 0) + m.amount_total
            meses_ordenados = sorted(agg.keys())
            breakdown = [{'label': '%s %s' % (MESES_ES[mm - 1], yy), 'value': round(agg[(yy, mm)], 2)} for yy, mm in meses_ordenados]

        return {
            'total_facturado': round(total_facturado, 2),
            'total_cobrado': total_cobrado,
            'total_pendiente': morosidad['total_morosidad'],
            'total_vencido': morosidad['total_vencido'],
            'cantidad_facturas': len(moves_periodo),
            'breakdown': breakdown,
            'breakdown_dim': self.billing_group_by,
        }

    def _compute_alertas_cupo(self):
        """Secciones activas con cupo agotado o casi lleno (>=90%) --
        relevante para Administrativa (gestión de capacidad), no requiere
        acceso a facturación."""
        self.ensure_one()
        secciones = self.env['school.standard'].search(self._domain_secciones_activas())
        alertas = []
        for s in secciones:
            if not s.capacity:
                continue
            pct = round(s.total_students * 100 / s.capacity)
            if pct >= 90:
                alertas.append({
                    'id': s.id,
                    'tipo': 'Cupo agotado' if s.remaining_seats <= 0 else 'Cupo casi lleno',
                    'section': s.code or '',
                    'course': s.subject_id.nombre or '',
                    'target': s.school_id.name or '',
                    'detalle': '%s de %s cupos ocupados (%s%%)' % (s.total_students, s.capacity, pct),
                })
        return alertas

    def _compute_dashboard_data(self):
        self.ensure_one()
        wizard = self.env['teacher.mgmt.wizard']
        hoy = fields.Date.today()
        company = self.env.company
        date_from, date_to = self._resolver_periodo()

        inscripciones = self.env['student.inscripcion'].search(self._domain_inscripciones(date_from, date_to))
        total_estudiantes_activos = self.env['student.inscripcion'].search_count(self._domain_estudiantes_activos())

        rows = [{
            'id': i.id,
            'student': i.student_id.name or '',
            'section': i.standard_id.code or '',
            'course': i.subject_id.nombre or '',
            'campus': i.school_id.name or '',
            'date': i.inscription_date.strftime('%d/%m/%Y') if i.inscription_date else '',
            'state_label': i.get_estado(i.state).upper(),
            'state_color': {'draft': 'gray', 'done': 'green', 'terminate': 'gray', 'cancel': 'red'}.get(i.state, 'gray'),
            'invoice_state': INVOICE_STATE_LABELS.get(i.state_invoice, 'Sin factura') if i.state_invoice else 'Sin factura',
            'payment_state': PAYMENT_STATE_LABELS.get(i.payment_state, '') if i.payment_state else '',
        } for i in inscripciones]
        inscripciones_por_seccion = self._top_secciones(inscripciones, 'standard_id')

        cant_retiros, retiros_rows, retiros_por_motivo, retiros_by_month, retiros_por_seccion = self._compute_retiros(date_from, date_to)
        cant_cambios, cambios_rows, cambios_por_seccion = self._compute_cambios(date_from, date_to)
        inscripciones_por_mes = self._compute_inscripciones_por_mes(date_from, date_to)
        capacidad_rows, pct_ocupacion_promedio = self._compute_capacidad()
        alertas = self._compute_alertas_cupo()

        has_billing_access = self._has_billing_access()
        morosidad = None
        billing_summary = None
        if has_billing_access and self.show_financials:
            morosidad = self._compute_morosidad()
            billing_summary = self._compute_facturacion(date_from, date_to, morosidad)

        kpis = [
            # NOTA: sin histórico persistido todavía (ver claude.md sección
            # 12, "Snapshots históricos" descartado para esta fase), así que
            # 'total_estudiantes_activos' queda en 'number' puro -- una
            # 'line' de tendencia requeriría guardar un valor por día, que
            # no existe. Mismo criterio de ajuste aplicado en el dashboard
            # Académico para KPIs sin desglose real.
            {'key': 'total_estudiantes_activos', 'label': 'Estudiantes activos',
             'value': total_estudiantes_activos, 'value_formatted': str(total_estudiantes_activos),
             'delta': None, 'delta_label': '', 'viz': 'number',
             'allow_viz': ['number'], 'color': 'blue', 'series': None},
            {'key': 'retiros_periodo', 'label': 'Retiros del período',
             'value': cant_retiros, 'value_formatted': str(cant_retiros),
             'delta': None, 'delta_label': '', 'viz': 'bar',
             'allow_viz': ['number', 'bar', 'donut'], 'color': 'coral', 'series': retiros_por_motivo},
            {'key': 'pct_ocupacion_promedio', 'label': 'Ocupación promedio',
             'value': pct_ocupacion_promedio, 'value_formatted': '%s%%' % pct_ocupacion_promedio,
             'delta': None, 'delta_label': '', 'viz': 'donut',
             'allow_viz': ['number', 'bar', 'donut'], 'color': 'teal', 'series': None},
            {'key': 'inscripciones_por_mes', 'label': 'Inscripciones por mes',
             'value': sum(p['value'] for p in inscripciones_por_mes), 'value_formatted': str(sum(p['value'] for p in inscripciones_por_mes)),
             'delta': None, 'delta_label': '', 'viz': 'bar',
             'allow_viz': ['bar', 'table'], 'color': 'blue', 'series': inscripciones_por_mes},
            {'key': 'retiros_por_motivo', 'label': 'Retiros por motivo',
             'value': cant_retiros, 'value_formatted': str(cant_retiros),
             'delta': None, 'delta_label': '', 'viz': 'donut',
             'allow_viz': ['bar', 'donut'], 'color': 'coral', 'series': retiros_por_motivo},
            {'key': 'capacidad_por_seccion', 'label': 'Capacidad por sección',
             'value': len(capacidad_rows), 'value_formatted': str(len(capacidad_rows)),
             'delta': None, 'delta_label': '', 'viz': 'bar',
             'allow_viz': ['bar', 'table'], 'color': 'purple',
             'series': [{'id': r['id'], 'label': r['section'], 'value': r['pct'], 'color':
                         {'green': '#1baf7a', 'amber': '#eda100', 'red': '#e34948'}[r['color']]}
                        for r in capacidad_rows[:8]]},
            {'key': 'retiros_por_seccion', 'label': 'Grupos con más retiros',
             'value': len(retiros_por_seccion), 'value_formatted': str(len(retiros_por_seccion)),
             'delta': None, 'delta_label': '', 'viz': 'bar',
             'allow_viz': ['bar', 'table'], 'color': 'coral', 'series': retiros_por_seccion},
            {'key': 'cambios_por_seccion', 'label': 'Grupos con más cambios de sección',
             'value': len(cambios_por_seccion), 'value_formatted': str(len(cambios_por_seccion)),
             'delta': None, 'delta_label': '', 'viz': 'bar',
             'allow_viz': ['bar', 'table'], 'color': 'amber', 'series': cambios_por_seccion},
            {'key': 'inscripciones_por_seccion', 'label': 'Grupos con más inscripciones',
             'value': len(inscripciones_por_seccion), 'value_formatted': str(len(inscripciones_por_seccion)),
             'delta': None, 'delta_label': '', 'viz': 'bar',
             'allow_viz': ['bar', 'table'], 'color': 'blue', 'series': inscripciones_por_seccion},
        ]
        if has_billing_access:
            kpis.append({
                'key': 'facturacion_periodo', 'label': 'Facturado (período)',
                'value': billing_summary['total_facturado'] if billing_summary else 0,
                'value_formatted': ('%.2f' % billing_summary['total_facturado']) if billing_summary else 'Sin cargar',
                'delta': None, 'delta_label': '', 'viz': 'number',
                'allow_viz': ['number'], 'color': 'amber', 'series': None})
            kpis.append({
                'key': 'cobrado_periodo', 'label': 'Cobrado (período)',
                'value': billing_summary['total_cobrado'] if billing_summary else 0,
                'value_formatted': ('%.2f' % billing_summary['total_cobrado']) if billing_summary else 'Sin cargar',
                'delta': None, 'delta_label': '', 'viz': 'number',
                'allow_viz': ['number'], 'color': 'teal', 'series': None})
            kpis.append({
                'key': 'facturacion_pendiente', 'label': 'Pendiente por cobrar (total)',
                'value': morosidad['total_morosidad'] if morosidad else 0,
                'value_formatted': ('%.2f' % morosidad['total_morosidad']) if morosidad else 'Sin cargar',
                'delta': None, 'delta_label': '', 'viz': 'number',
                'allow_viz': ['number'], 'color': 'coral', 'series': None})
            kpis.append({
                'key': 'morosidad_por_seccion', 'label': 'Grupos con mayor morosidad',
                'value': len(morosidad['por_seccion']) if morosidad else 0,
                'value_formatted': (str(len(morosidad['por_seccion']))) if morosidad else 'Sin cargar',
                'delta': None, 'delta_label': '', 'viz': 'bar',
                'allow_viz': ['bar', 'table'], 'color': 'coral',
                'series': morosidad['por_seccion'] if morosidad else None})

        return {
            'company_name': company.name,
            'company_logo': wizard._imagen_base64(company, 'logo_web'),
            'generated_at': wizard._formatear_fecha(hoy),
            'filters_applied': {
                'campus_ids': self.campus_ids.ids,
                'period_mode': self.period_mode,
                'date_from': fields.Date.to_string(date_from),
                'date_to': fields.Date.to_string(date_to),
                'inscripcion_state': self.inscripcion_state,
                'show_financials': self.show_financials,
                'billing_group_by': self.billing_group_by,
            },
            'campus_options': [{'id': c.id, 'name': c.name} for c in self.env['school.campus'].search(self._domain_company())],
            'has_billing_access': has_billing_access,
            'kpis': kpis,
            'rows': rows,
            'groups': None,
            'alerts': alertas,
            'retiros_rows': retiros_rows,
            'retiros_by_month': retiros_by_month,
            'cambios_rows': cambios_rows,
            'capacity_rows': capacidad_rows,
            'billing_summary': billing_summary,
            'morosidad': morosidad,
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
