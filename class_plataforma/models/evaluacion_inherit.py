# See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class StandardEvaluacionMoodle(models.Model):
    """Integración con Moodle sobre standard.evaluacion (Registro de
    Evaluaciones), pestaña 'Plataforma'.

    A diferencia de las actividades normales ('school.libroact', que el
    profesor define y pondera manualmente), aquí las actividades y su
    finalización vienen directamente de la Plataforma ('activity
    completion' de Moodle): esta extensión solo pide, por estudiante,
    cuántas actividades tiene SU unidad correspondiente y cuántas completó.

    Cada 'standard.evaluacion' es UNA evaluación (una de las N que tiene
    el libro de evaluación de la sección). Se relaciona con UNA O MÁS
    unidades de Moodle (de las M secciones del curso, sin contar la
    sección 0 'General') por POSICIÓN y AGRUPACIÓN: si M es múltiplo de
    N, cada evaluación se relaciona con un bloque de M/N unidades
    consecutivas (si M == N, el bloque es de 1 unidad: el caso de
    siempre). Si M no es múltiplo de N, no hay forma confiable de
    agrupar y se avisa en vez de inventar la relación.

    La estructura de unidades del curso ('core_course_get_contents') se
    cachea por MATERIA (subject.subject), no por sección ni por
    evaluación: todas las secciones de una misma materia comparten el
    mismo curso en la Plataforma, así que sincronizar varias evaluaciones
    cuesta como máximo una sola llamada a esa función en total.
    """

    _inherit = 'standard.evaluacion'

    moodle_actividad_ids = fields.One2many(
        'moodle.actividad.plataforma', 'evaluacion_id',
        string='Actividades en la Plataforma', readonly=True,
    )
    moodle_actividades_last_sync = fields.Datetime(
        string='Última sincronización de actividades',
        readonly=True, copy=False,
    )
    moodle_actividades_sync_error = fields.Boolean(
        string='Error al sincronizar actividades',
        default=False, copy=False,
    )
    moodle_actividades_error_message = fields.Text(
        string='Detalle de error (actividades)',
        readonly=True, copy=False,
    )
    moodle_unidad_nombre = fields.Char(
        string='Unidad en la Plataforma', readonly=True, copy=False,
        help="Unidad (sección) del curso en la Plataforma con la que "
             "quedó relacionada esta evaluación, según la última sincronización.",
    )
    moodle_sync_log_ids = fields.One2many(
        'moodle.sync.log', 'evaluacion_id',
        string='Log de sincronización',
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Paso 1: ubicar el curso en la Plataforma (reutiliza la caché de
    # la Sección si ya fue sincronizada; si no, la resuelve y la guarda
    # ahí, igual que hace school.standard al iniciar la sección).
    # ------------------------------------------------------------------
    def _moodle_resolve_course_id(self, client, config):
        self.ensure_one()
        standard = self.standard_id
        if standard.moodle_course_id:
            return standard.moodle_course_id

        code_moodle = self.subject_id.code_moodle
        if not code_moodle:
            raise UserError(_(
                "El curso '%s' no tiene configurado un 'Código Moodle'. "
                "Configure el código en el catálogo de Cursos."
            ) % self.subject_id.name)

        course = client.search_course_by_shortname(
            code_moodle, config=config, related_record=self
        )
        if not course:
            raise UserError(_(
                "No se encontró en la Plataforma un curso con el código '%s'."
            ) % code_moodle)

        course_id = course.get('id')
        standard.write({
            'moodle_course_id': course_id,
            'moodle_course_name': course.get('fullname') or course.get('shortname') or code_moodle,
        })
        return course_id

    # ------------------------------------------------------------------
    # Paso 2: relacionar ESTA evaluación con SU unidad en la Plataforma,
    # por cantidad y posición.
    # ------------------------------------------------------------------
    def _moodle_resolve_unidad(self, client, config, course_id):
        """Devuelve (orden, section_id, section_name, cmids) del bloque de
        unidades de Moodle que le corresponde a esta evaluación. 'cmids'
        es la UNIÓN de las actividades de todas las unidades del bloque
        (normalmente una sola, salvo que la evaluación abarque varias).

        Cuenta las evaluaciones del libro (N) y las unidades reales del
        curso en la Plataforma (M, excluyendo la sección 0 'General',
        usando la caché por materia). Si M es múltiplo de N, agrupa
        unidades consecutivas en bloques de M/N y usa la posición de esta
        evaluación dentro del libro para ubicar el bloque que le toca. Si
        no es múltiplo, no se puede agrupar de forma confiable: se
        informa el detalle en vez de inventar la relación.
        """
        self.ensure_one()

        libro = self.libroevas_id.libro_id
        evaluaciones = libro.evaluacion_ids
        if self.libroevas_id.id not in evaluaciones.ids:
            raise UserError(_(
                "La evaluación '%s' no aparece entre las evaluaciones del "
                "libro '%s'; revise la configuración del libro de evaluación."
            ) % (self.libroevas_id.nombre or self.libroevas_id.name, libro.nombre))
        indice = evaluaciones.ids.index(self.libroevas_id.id)
        total_evaluaciones = len(evaluaciones)

        unidades = self.subject_id._moodle_get_unidades(
            client, config, course_id, related_record=self
        )
        total_unidades = len(unidades)

        if not total_evaluaciones or not total_unidades:
            raise UserError(_(
                "No se puede relacionar automáticamente la evaluación con "
                "una unidad de la Plataforma: el libro de evaluación '%s' "
                "tiene %s evaluación(es) y el curso en la Plataforma tiene "
                "%s unidad(es) (sin contar 'General')."
            ) % (libro.nombre, total_evaluaciones, total_unidades))

        if total_unidades % total_evaluaciones != 0:
            # La caché por materia puede estar desactualizada (se habrán
            # agregado o quitado unidades en la Plataforma desde la última
            # lectura): se relee una sola vez antes de rendirse.
            unidades = self.subject_id._moodle_get_unidades(
                client, config, course_id, related_record=self, force=True
            )
            total_unidades = len(unidades)

        if total_unidades % total_evaluaciones != 0:
            raise UserError(_(
                "No se puede relacionar automáticamente la evaluación con "
                "una o más unidades de la Plataforma: el libro de "
                "evaluación '%s' tiene %s evaluación(es), pero el curso en "
                "la Plataforma tiene %s unidad(es) (sin contar 'General'), "
                "que no es múltiplo de la cantidad de evaluaciones. Ajuste "
                "cualquiera de las dos cantidades para que una sea múltiplo "
                "exacto de la otra y vuelva a sincronizar."
            ) % (libro.nombre, total_evaluaciones, total_unidades))

        tamano_bloque = total_unidades // total_evaluaciones
        inicio = indice * tamano_bloque
        bloque = unidades[inicio:inicio + tamano_bloque]

        nombres = [u['name'] for u in bloque]
        section_name = nombres[0] if len(nombres) == 1 else ' + '.join(nombres)
        section_id = bloque[0]['id'] if bloque else 0
        cmids = set()
        for u in bloque:
            cmids |= u['cmids']
        return indice, section_id, section_name, cmids

    # ------------------------------------------------------------------
    # Orquestación: por cada estudiante inscrito, pide su avance de
    # 'activity completion' y lo filtra a la unidad relacionada.
    # ------------------------------------------------------------------
    def action_sync_moodle_actividades(self):
        self.ensure_one()
        client = self.env['moodle.client']
        config = self.env['moodle.config'].get_active_config()

        course_id = self._moodle_resolve_course_id(client, config)
        indice, section_id, section_name, cmids = self._moodle_resolve_unidad(
            client, config, course_id
        )

        registros = self.evaluacion_ids  # standard.evaluaciones: 1 por estudiante
        errores = []
        nuevos_vals = []

        for registro in registros:
            student = registro.student_id
            uid = student.moodle_user_id
            if not uid:
                errores.append(_(
                    "%s: no tiene usuario vinculado en la Plataforma todavía."
                ) % student.display_name)
                registro.moodle_realizado = False
                continue

            try:
                statuses = client.get_activities_completion(
                    course_id, uid, config=config,
                    related_record=self, student_code=student.student_code,
                )
            except UserError as e:
                errores.append(_("%s: %s") % (student.display_name, e))
                registro.moodle_realizado = False
                continue

            de_la_unidad = [s for s in statuses if s.get('cmid') in cmids]
            total = len(de_la_unidad)
            completadas = sum(1 for s in de_la_unidad if s.get('state') in (1, 2))

            nuevos_vals.append({
                'evaluacion_id': self.id,
                'student_id': student.id,
                'unidad_orden': indice,
                'unidad_moodle_id': section_id,
                'unidad_nombre': section_name,
                'total_actividades': total,
                'actividades_completadas': completadas,
            })
            # "¿Realizó Plataforma?": solo si completó TODAS las
            # actividades trackeadas del bloque de unidades relacionado.
            registro.moodle_realizado = bool(total) and completadas == total

        # Reemplaza el detalle anterior por el recién consultado.
        self.moodle_actividad_ids.unlink()
        if nuevos_vals:
            self.env['moodle.actividad.plataforma'].create(nuevos_vals)

        self.write({
            'moodle_unidad_nombre': section_name,
            'moodle_actividades_last_sync': fields.Datetime.now(),
            'moodle_actividades_sync_error': bool(errores),
            'moodle_actividades_error_message': "\n".join(errores) if errores else False,
        })
        _logger.info(
            "Sincronización de actividades (Plataforma) para %s: relacionada "
            "con la unidad '%s'; %s estudiante(s) procesados, %s con error.",
            self.display_name, section_name, len(registros) - len(errores), len(errores),
        )
        return True

    # ------------------------------------------------------------------
    # Botón: ejecución manual desde el formulario de la evaluación
    # ------------------------------------------------------------------
    def action_retry_sync_moodle_actividades(self):
        self.ensure_one()
        try:
            self.action_sync_moodle_actividades()
        except Exception as e:
            self.moodle_actividades_sync_error = True
            self.moodle_actividades_error_message = str(e)
            self.message_post(
                body=_("Error al sincronizar actividades con la Plataforma: %s") % e
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error al sincronizar actividades'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                },
            }
        if self.moodle_actividades_sync_error:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sincronización con errores'),
                    'message': self.moodle_actividades_error_message,
                    'type': 'warning',
                    'sticky': True,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sincronización exitosa'),
                'message': _(
                    "Se actualizó el avance de actividades desde la Plataforma "
                    "(unidad relacionada: %s)."
                ) % self.moodle_unidad_nombre,
                'type': 'success',
                'sticky': False,
            },
        }


class StandardEvaluacionesMoodle(models.Model):
    """Integración con Moodle sobre standard.evaluaciones (la fila de
    detalle por estudiante dentro de una evaluación)."""

    _inherit = 'standard.evaluaciones'

    moodle_realizado = fields.Boolean(
        string='¿Realizó Plataforma?',
        default=False, copy=False, readonly=True,
        help="Se marca automáticamente, en cada sincronización de "
             "actividades, cuando el estudiante completó TODAS las "
             "actividades de la Plataforma (con seguimiento de "
             "finalización activado) correspondientes a esta evaluación.",
    )
