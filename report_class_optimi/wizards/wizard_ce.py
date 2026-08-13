# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
import calendar
import datetime


class WizardCeOptimized(models.TransientModel):
    """
    Hereda de report.wizard_ce y mejora la obtención de datos
    para incluir secciones archivadas.
    """
    _name = 'report.wizard_ce'
    _inherit = 'report.wizard_ce'  # Hereda del wizard original

    def action_search_salida(self):
        """
        Sobrescribe el método original para incluir secciones archivadas.
        """
        form_data = self.read()[0]

        helper = self.env['report.helper.optimized']

        # Obtener estudiante e inscripción (incluye archivados)
        student = helper.get_student(self.student_id.id)
        inscripcion = helper.get_inscripcion(self.inscripcion_id.id)
        standard = helper.get_standard(inscripcion)

        # Obtener firmante
        signer = False
        if self.signer_id:
            signer = self.env['cei.signer'].sudo().with_context(active_test=False).browse(self.signer_id.id)

        # Preparar datos del estudiante
        est = [{
            'cedula': student.student_ci or '',
            'codigo': student.student_code or '',
            'nombre': student.name or '',
            'seccion': standard.code if standard else '',
            'curso': self.extraer_nivel_curso(standard.subject_id.nombre) if standard and standard.subject_id else '',
            'schedule': standard.note if standard else '',
            'signature': standard.company_id.director_signature if standard and standard.company_id else False,
            'director': standard.company_id.director_name if standard and standard.company_id else '',
            'director_id': standard.company_id.director_id if standard and standard.company_id else '',
            'director_job': standard.company_id.director_job if standard and standard.company_id else '',
            'empresa': standard.company_id.name if standard and standard.company_id else '',
            'programa': standard.subject_id.programa_id.name if standard and standard.subject_id and standard.subject_id.programa_id else '',
            'estado': self.get_estado(inscripcion.state),
            'date': self.get_date(),
        }]

        data = {
            'form_data': form_data,
            'est': est,
            'signer': signer.id if signer else False,
        }

        return self.env.ref('report_class.action_report_record_ce') \
            .with_context(active_test=False) \
            .report_action(self, data=data)

    def get_date(self):
        """Obtiene la fecha en formato texto."""
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        dias = ['ero', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete',
                'ocho', 'nueve', 'diez', 'once', 'doce', 'trece', 'catorce',
                'quince', 'dieciséis', 'diecisiete', 'dieciocho', 'diecinueve',
                'veinte', 'veintiuno', 'veintidós', 'veintitres', 'veinticuatro',
                'veinticinco', 'veintiséis', 'veintisiete', 'veintiocho',
                'veintinueve', 'treinta', 'treinta y uno']

        fecha = datetime.datetime.now()
        year = fecha.year
        month = fecha.strftime("%m")
        day = fecha.strftime("%e")
        mes = meses[int(month) - 1]
        dia = dias[int(day) - 1]
        tiraAno = self.numero_to_letras(year)
        tira_fecha = "a los " + dia + " días del mes de " + mes + " de " + tiraAno.lower()
        return tira_fecha

    def numero_to_letras(self, numero):
        """Convierte un número a letras."""
        indicador = [("", ""), ("MIL", "MIL"), ("MILLON", "MILLONES"), ("MIL", "MIL"), ("BILLON", "BILLONES")]
        entero = int(numero)
        contador = 0
        numero_letras = ""
        while entero > 0:
            a = entero % 1000
            if contador == 0:
                en_letras = self.convierte_cifra(a, 1).strip()
            else:
                en_letras = self.convierte_cifra(a, 0).strip()
            if a == 0:
                numero_letras = en_letras + " " + numero_letras
            elif a == 1:
                if contador in (1, 3):
                    numero_letras = indicador[contador][0] + " " + numero_letras
                else:
                    numero_letras = en_letras + " " + indicador[contador][0] + " " + numero_letras
            else:
                numero_letras = en_letras + " " + indicador[contador][1] + " " + numero_letras
            numero_letras = numero_letras.strip()
            contador = contador + 1
            entero = int(entero / 1000)
        return numero_letras

    def convierte_cifra(self, numero, sw):
        """Convierte una cifra a letras."""
        lista_centana = ["", ("CIEN", "CIENTO"), "DOSCIENTOS", "TRESCIENTOS",
                         "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS",
                         "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]
        lista_decena = ["", ("DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE",
                             "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"),
                        ("VEINTE", "VEINTI"), ("TREINTA", "TREINTA Y "),
                        ("CUARENTA", "CUARENTA Y "), ("CINCUENTA", "CINCUENTA Y "),
                        ("SESENTA", "SESENTA Y "), ("SETENTA", "SETENTA Y "),
                        ("OCHENTA", "OCHENTA Y "), ("NOVENTA", "NOVENTA Y ")]
        lista_unidad = ["", ("UN", "UNO"), "DOS", "TRES", "CUATRO", "CINCO",
                        "SEIS", "SIETE", "OCHO", "NUEVE"]
        centena = int(numero / 100)
        decena = int((numero - (centena * 100)) / 10)
        unidad = int(numero - (centena * 100 + decena * 10))

        texto_centena = lista_centana[centena]
        if centena == 1:
            if (decena + unidad) != 0:
                texto_centena = texto_centena[1]
            else:
                texto_centena = texto_centena[0]

        texto_decena = lista_decena[decena]
        if decena == 1:
            texto_decena = texto_decena[unidad]
        elif decena > 1:
            if unidad != 0:
                texto_decena = texto_decena[1]
            else:
                texto_decena = texto_decena[0]

        if decena != 1:
            texto_unidad = lista_unidad[unidad]
            if unidad == 1:
                texto_unidad = texto_unidad[sw]
        else:
            texto_unidad = ""

        return "%s %s %s" % (texto_centena, texto_decena, texto_unidad)

    def extraer_nivel_curso(self, nombre_curso):
        """Extrae el nivel del curso."""
        if not nombre_curso:
            return ''

        nombre_upper = nombre_curso.upper()

        # Definir niveles
        niveles_kids = ['NIVEL 1', 'NIVEL 2', 'NIVEL 3', 'NIVEL 4', 'NIVEL 5', 'NIVEL 6']
        niveles_teens = ['NIVEL 1', 'NIVEL 2', 'NIVEL 3']
        niveles_general = ['BEGINNER', 'ELEMENTARY', 'PRE-INTERMEDIATE', 'INTERMEDIATE',
                          'ADVANCED', 'ADVANCED PLUS', 'UPPER ADVANCED', 'MASTER ADVANCED']

        # Buscar en Kids
        if 'CLEVELAND KIDS' in nombre_upper:
            for nivel in niveles_kids:
                if nivel in nombre_upper:
                    return nivel

        # Buscar en Teens
        if 'CLEVELAND TEENS' in nombre_upper:
            for nivel in niveles_teens:
                if nivel in nombre_upper:
                    return nivel

        # Buscar en general
        for nivel in niveles_general:
            if nivel in nombre_upper:
                return nivel

        return nombre_curso

    def get_estado(self, sta):
        """Mapeo de estados."""
        estados = {
            'draft': 'POR INICIAR',
            'done': 'INICIADO',
            'terminate': 'CULMINADO',
            'aprobado': 'APROBADO',
            'aplazado': 'APLAZADO',
        }
        return estados.get(sta, sta or '')