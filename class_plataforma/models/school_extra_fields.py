# See LICENSE file for full copyright and licensing details.

import json
import logging

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

# Si cambia el código del curso en Moodle, la estructura de unidades
# guardada en caché deja de ser válida.
_MOODLE_UNIDADES_CACHE_KEYS = {'code_moodle'}


class SubjectSubjectMoodle(models.Model):
    """Agrega el código de curso en Moodle al catálogo de cursos de school,
    y cachea la estructura de unidades (secciones) de ese curso en la
    Plataforma.

    Todas las secciones (school.standard) que comparten una misma materia
    (subject.subject) comparten también el mismo curso en la Plataforma:
    por eso la estructura de unidades se cachea aquí (a nivel de materia) y
    no en cada evaluación o sección. Así, sincronizar varias evaluaciones
    -de la misma materia o de secciones distintas- cuesta como máximo UNA
    llamada a 'core_course_get_contents' en total, no una por evaluación.
    """

    _inherit = 'subject.subject'

    code_moodle = fields.Char(
        string='Código Moodle',
        help="Shortname del curso en Moodle. Debe coincidir exactamente "
             "con el 'Nombre corto del curso' configurado en Moodle.",
    )

    moodle_unidades_json = fields.Text(
        string='Caché de unidades en la Plataforma',
        readonly=True, copy=False,
        help="Caché interna (JSON) de la estructura de unidades (secciones, "
             "sin contar 'General') del curso en la Plataforma, usada por "
             "la sincronización de Evaluaciones para no repetir "
             "'core_course_get_contents' en cada evaluación. Se invalida "
             "automáticamente si cambia el 'Código Moodle'.",
    )
    moodle_unidades_last_sync = fields.Datetime(
        string='Última lectura de unidades en la Plataforma',
        readonly=True, copy=False,
    )

    # ------------------------------------------------------------------
    # Invalidar la caché si cambia el código del curso en Moodle
    # ------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if _MOODLE_UNIDADES_CACHE_KEYS.intersection(vals):
            super().write({
                'moodle_unidades_json': False,
                'moodle_unidades_last_sync': False,
            })
        return res

    # ------------------------------------------------------------------
    # Estructura de unidades (con caché)
    # ------------------------------------------------------------------
    def _moodle_get_unidades(self, client, config, course_id,
                               related_record=None, force=False):
        """Devuelve la lista ORDENADA de unidades del curso en la
        Plataforma: [{'orden': i, 'id': <section_id>, 'name': <str>,
        'cmids': <set>}, ...] (sin contar la sección 0 'General').

        Usa la caché guardada salvo que esté vacía o se pida force=True
        (p. ej. porque la cantidad de unidades dejó de coincidir con la
        cantidad de evaluaciones y puede haberse quedado desactualizada).
        """
        self.ensure_one()
        if not force and self.moodle_unidades_json:
            data = json.loads(self.moodle_unidades_json)
            return [{**u, 'cmids': set(u['cmids'])} for u in data]

        contents = client.get_course_contents(
            course_id, config=config, related_record=related_record or self
        ) or []
        secciones = sorted(
            (s for s in contents if (s.get('section') or 0) != 0),
            key=lambda s: s.get('section') or 0,
        )
        unidades = [
            {
                'orden': i,
                'id': s.get('id') or 0,
                'name': s.get('name') or _('Unidad %s') % (i + 1),
                'cmids': sorted({
                    m.get('id') for m in (s.get('modules') or []) if m.get('id')
                }),
            }
            for i, s in enumerate(secciones)
        ]
        self.write({
            'moodle_unidades_json': json.dumps(unidades),
            'moodle_unidades_last_sync': fields.Datetime.now(),
        })
        _logger.info(
            "Estructura de unidades actualizada desde la Plataforma para "
            "la materia '%s': %s unidad(es).", self.display_name, len(unidades),
        )
        return [{**u, 'cmids': set(u['cmids'])} for u in unidades]

    # ------------------------------------------------------------------
    # Botón manual: forzar relectura de la estructura (p. ej. si se
    # agregaron/quitaron unidades o actividades en la Plataforma)
    # ------------------------------------------------------------------
    def action_refresh_moodle_unidades(self):
        self.ensure_one()
        try:
            if not self.code_moodle:
                raise UserError(_(
                    "El curso '%s' no tiene configurado un 'Código Moodle'."
                ) % self.name)
            client = self.env['moodle.client']
            config = self.env['moodle.config'].get_active_config()
            course = client.search_course_by_shortname(
                self.code_moodle, config=config, related_record=self
            )
            if not course:
                raise UserError(_(
                    "No se encontró en la Plataforma un curso con el código '%s'."
                ) % self.code_moodle)
            unidades = self._moodle_get_unidades(
                client, config, course.get('id'),
                related_record=self, force=True,
            )
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error al actualizar la estructura'),
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Estructura actualizada'),
                'message': _(
                    "Se encontraron %s unidad(es) en el curso de la Plataforma."
                ) % len(unidades),
                'type': 'success',
            },
        }
