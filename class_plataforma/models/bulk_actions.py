# See LICENSE file for full copyright and licensing details.

import logging

from odoo import models
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class MoodleBulkMixin(models.AbstractModel):
    """Lógica común de las acciones masivas hacia la Plataforma.

    Recorre los registros seleccionados en una lista, ejecuta el método de
    sincronización de cada uno y arma un resumen. Un error en un registro
    NO detiene a los demás: se marca en ese registro (igual que en los
    botones individuales) y se sigue con el siguiente.

    Todo es síncrono (no hay cola): por eso cada ejecución procesa como
    máximo _MOODLE_BULK_LIMIT registros. Los que sobren quedan pendientes
    y se procesan volviendo a lanzar la acción.
    """

    _name = 'moodle.bulk.mixin'
    _description = 'Acciones masivas hacia la Plataforma'

    # Una inscripción cuesta 6-8 peticiones a Moodle; 15 inscripciones son
    # ~100 peticiones. Más que eso arriesga el tiempo máximo del worker.
    _MOODLE_BULK_LIMIT = 15

    def _moodle_bulk_run(self, sync_method, pending, skipped_reason):
        """Ejecuta `sync_method` sobre `pending` (subconjunto de self).

        :param sync_method: nombre del método a llamar en cada registro.
        :param pending: registros de self que sí corresponde procesar.
        :param skipped_reason: texto que explica por qué se omite el resto.
        :return: acción 'display_notification' con el resumen.
        """
        todo = pending[:self._MOODLE_BULK_LIMIT]
        left = len(pending) - len(todo)
        skipped = len(self) - len(pending)

        ok = 0
        failed = []
        for rec in todo:
            try:
                getattr(rec, sync_method)()
                ok += 1
            except Exception as e:
                msg = str(e)
                # No se usa savepoint a propósito: revertirlo borraría
                # también las filas de moodle.sync.log, que son la
                # evidencia del error.
                rec.moodle_sync_error = True
                rec.moodle_error_message = msg
                rec.message_post(
                    body=_("Error al sincronizar con la Plataforma: %s") % msg
                )
                failed.append((rec.display_name, msg))
                _logger.exception(
                    "Error en acción masiva (%s) para %s",
                    sync_method, rec.display_name,
                )

        parts = []
        if ok:
            parts.append(_("%s sincronizados") % ok)
        if failed:
            parts.append(_("%s con error") % len(failed))
        if skipped:
            parts.append(_("%s omitidos (%s)") % (skipped, skipped_reason))
        if left:
            parts.append(_(
                "%s quedaron pendientes: vuelva a ejecutar la acción"
            ) % left)
        message = ', '.join(parts) if parts else _("Nada que sincronizar.")

        if failed:
            detail = '; '.join(
                '%s (%s)' % (name, msg[:80]) for name, msg in failed[:5]
            )
            if len(failed) > 5:
                detail += '…'
            message = "%s. %s %s" % (message, _("Errores:"), detail)

        if failed and not ok:
            notif_type = 'danger'
        elif failed or left or not ok:
            notif_type = 'warning'
        else:
            notif_type = 'success'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sincronización masiva con la Plataforma'),
                'message': message,
                'type': notif_type,
                'sticky': bool(failed or left),
            },
        }


class StudentInscripcionBulk(models.Model):
    """Acción masiva "Inscribir en Plataforma" sobre student.inscripcion."""

    # _name explícito: con varios _inherit y sin _name, Odoo crearía un
    # modelo nuevo en vez de extender student.inscripcion.
    _name = 'student.inscripcion'
    _inherit = ['student.inscripcion', 'moodle.bulk.mixin']

    def action_bulk_sync_plataforma(self):
        pending = self.filtered(
            lambda r: r.state == 'done' and not r.moodle_enrolled
        )
        return self._moodle_bulk_run(
            'action_sync_moodle', pending,
            _("no están confirmadas o ya están en la Plataforma"),
        )


class StudentStudentBulk(models.Model):
    """Acción masiva "Sincronizar con Plataforma" sobre student.student."""

    # _name explícito: ver nota en StudentInscripcionBulk.
    _name = 'student.student'
    _inherit = ['student.student', 'moodle.bulk.mixin']

    def action_bulk_sync_plataforma(self):
        pending = self.filtered(
            lambda r: r.student_code and not r.moodle_synced
        )
        return self._moodle_bulk_run(
            'action_sync_moodle_estudiante', pending,
            _("sin código o ya sincronizados"),
        )
