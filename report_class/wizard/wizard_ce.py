# -*- coding: utf-8 -*-

from email.policy import default
from odoo import api, fields, models
from odoo.exceptions import UserError
import calendar, datetime

class Wizard(models.TransientModel):
    _name = 'report.wizard_ce'
    _description = 'Report Wizard / Constancia de Estudios'

    date_start      = fields.Date('Fecha Inicio', required=True, default=fields.Date.today )
    date_end        = fields.Date('Fecha Fin', required=True, default=fields.Date.today)
    student_id      = fields.Many2one('student.student', string="Estudiante", required=True)
    inscripcion_id  = fields.Many2one('student.inscripcion', 'Sección', help='Selecione la secciòn', required=True)
    signer_id       = fields.Many2one('cei.signer', string='Firmante')
    
    def primer_dia_mes(self):
        now = datetime.datetime.now()
        year = now.year
        month = now.month

        return datetime.date(year,month,1)

    def ultimo_dia_mes(self):
        now = datetime.datetime.now()
        year = now.year
        month = now.month
        last_day = calendar.monthrange(year, month)[1] ## último día

        return datetime.date(year,month,last_day)
    
#-----------------------------------------------------------------------#
    def get_escala(self):
        '''Method to compute la escala minima.'''

        califica_vals = {'minimo': 0, 'maximo': 0 , 'aprobado': 0 }
  
        escalaObj = self.env['grade.line'].sudo().search([('sequence', '=', '1')], limit=1)

        if escalaObj:
           califica_vals = {'minimo': escalaObj.from_mark, 
                            'maximo': escalaObj.to_mark,
                            'aprobado': escalaObj.pass_mark
                           }
        
        return califica_vals

#-----------------------------------------------------------------------#
    def extraer_nivel_curso(self, nombre_curso):
        '''Método para extraer el nombre del nivel del curso de manera inteligente'''
        
        if not nombre_curso:
            return ''
        
        # Diccionario de patrones conocidos para cada tipo de curso
        # Formato: 'palabra_clave': 'nivel_a_retornar'
        niveles_kids = {
            'NIVEL 1': 'NIVEL 1',
            'NIVEL 2': 'NIVEL 2',
            'NIVEL 3': 'NIVEL 3',
            'NIVEL 4': 'NIVEL 4',
            'NIVEL 5': 'NIVEL 5',
            'NIVEL 6': 'NIVEL 6',
        }
        
        niveles_teens = {
            'NIVEL 1': 'NIVEL 1',
            'NIVEL 2': 'NIVEL 2',
            'NIVEL 3': 'NIVEL 3',
        }
        
        niveles_general = {
            'BEGINNER': 'BEGINNER',
            'ELEMENTARY': 'ELEMENTARY',
            'PRE-INTERMEDIATE': 'PRE-INTERMEDIATE',
            'PRE - INTERMEDIATE': 'PRE-INTERMEDIATE',
            'INTERMEDIATE': 'INTERMEDIATE',
            'ADVANCED PLUS': 'ADVANCED PLUS',
            'ADVANCED': 'ADVANCED',
            'UPPER ADVANCED': 'UPPER ADVANCED',
            'MASTER ADVANCED': 'MASTER ADVANCED',
        }
        
        niveles_robotica = {
            'KIDS - NIVEL 1': 'KIDS - NIVEL 1',
            'KIDS - NIVEL 2': 'KIDS - NIVEL 2',
            'MAKERS 2.0': 'MAKERS 2.0',
            'TEENS - NIVEL 1': 'TEENS - NIVEL 1',
            'TEENS - NIVEL 2': 'TEENS - NIVEL 2',
            'CAPACITACIÓN DOCENTE': 'CAPACITACIÓN DOCENTE',
        }
        
        nombre_upper = nombre_curso.upper()
        
        # Verificar si es curso KIDS
        if 'CLEVELAND KIDS' in nombre_upper:
            for patron, nivel in niveles_kids.items():
                if patron in nombre_upper:
                    return nivel
        
        # Verificar si es curso TEENS
        elif 'CLEVELAND TEENS' in nombre_upper:
            for patron, nivel in niveles_teens.items():
                if patron in nombre_upper:
                    return nivel
        
        # Verificar si es curso de ROBOTICA
        elif 'ROBOTICA' in nombre_upper:
            for patron, nivel in niveles_robotica.items():
                if patron in nombre_upper:
                    return nivel
        
        # Verificar cursos GENERAL ENGLISH
        else:
            # Buscar en orden de más específico a menos específico
            if 'ADVANCED PLUS' in nombre_upper:
                return 'ADVANCED PLUS'
            elif 'UPPER ADVANCED' in nombre_upper:
                return 'UPPER ADVANCED'
            elif 'MASTER ADVANCED' in nombre_upper:
                return 'MASTER ADVANCED'
            elif 'PRE-INTERMEDIATE' in nombre_upper or 'PRE - INTERMEDIATE' in nombre_upper:
                return 'PRE-INTERMEDIATE'
            elif 'INTERMEDIATE' in nombre_upper:
                return 'INTERMEDIATE'
            elif 'ELEMENTARY' in nombre_upper:
                return 'ELEMENTARY'
            elif 'BEGINNER' in nombre_upper:
                return 'BEGINNER'
            elif 'ADVANCED' in nombre_upper:
                return 'ADVANCED'
        
        # Si no coincide con ningún patrón, devolver el nombre completo
        return nombre_curso

#-----------------------------------------------------------------------#
    def numero_to_letras(self,numero):
        indicador = [("",""),("MIL","MIL"),("MILLON","MILLONES"),("MIL","MIL"),("BILLON","BILLONES")]
        entero = int(numero)
        decimal = int(round((numero - entero)*100))
        #print 'decimal : ',decimal 
        contador = 0
        numero_letras = ""
        while entero >0:
            a = entero % 1000
            if contador == 0:
                en_letras = self.convierte_cifra(a,1).strip()
            else :
                en_letras = self.convierte_cifra(a,0).strip()
            if a==0:
                numero_letras = en_letras+" "+numero_letras
            elif a==1:
                if contador in (1,3):
                    numero_letras = indicador[contador][0]+" "+numero_letras
                else:
                    numero_letras = en_letras+" "+indicador[contador][0]+" "+numero_letras
            else:
                numero_letras = en_letras+" "+indicador[contador][1]+" "+numero_letras
            numero_letras = numero_letras.strip()
            contador = contador + 1
            entero = int(entero / 1000)
        
        return numero_letras
 
    def convierte_cifra(self,numero,sw):
        lista_centana = ["",("CIEN","CIENTO"),"DOSCIENTOS","TRESCIENTOS","CUATROCIENTOS","QUINIENTOS","SEISCIENTOS","SETECIENTOS","OCHOCIENTOS","NOVECIENTOS"]
        lista_decena = ["",("DIEZ","ONCE","DOCE","TRECE","CATORCE","QUINCE","DIECISEIS","DIECISIETE","DIECIOCHO","DIECINUEVE"),
                        ("VEINTE","VEINTI"),("TREINTA","TREINTA Y "),("CUARENTA" , "CUARENTA Y "),
                        ("CINCUENTA" , "CINCUENTA Y "),("SESENTA" , "SESENTA Y "),
                        ("SETENTA" , "SETENTA Y "),("OCHENTA" , "OCHENTA Y "),
                        ("NOVENTA" , "NOVENTA Y ")
                    ]
        lista_unidad = ["",("UN" , "UNO"),"DOS","TRES","CUATRO","CINCO","SEIS","SIETE","OCHO","NUEVE"]
        centena = int (numero / 100)
        decena = int((numero -(centena * 100))/10)
        unidad = int(numero - (centena * 100 + decena * 10))
        #print "centena: ",centena, "decena: ",decena,'unidad: ',unidad
    
        texto_centena = ""
        texto_decena = ""
        texto_unidad = ""
    
        #Validad las centenas
        texto_centena = lista_centana[centena]
        if centena == 1:
            if (decena + unidad)!=0:
                texto_centena = texto_centena[1]
            else :
                texto_centena = texto_centena[0]
    
        #Valida las decenas
        texto_decena = lista_decena[decena]
        if decena == 1 :
            texto_decena = texto_decena[unidad]
        elif decena > 1 :
            if unidad != 0 :
                texto_decena = texto_decena[1]
            else:
                texto_decena = texto_decena[0]
        #Validar las unidades
        #print "texto_unidad: ",texto_unidad
        if decena != 1:
            texto_unidad = lista_unidad[unidad]
            if unidad == 1:
                texto_unidad = texto_unidad[sw]
    
        return "%s %s %s" %(texto_centena,texto_decena,texto_unidad)

#-----------------------------------------------------------------------#
    def get_date(self):
            meses = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
            dias  = ['ero','dos','tres','cuatro','cinco','seis','siete','ocho','nueve','diez','once','doce',
                     'trece','catorce','quince','dieciséis','diecisiete','dieciocho','diecinueve','veinte','veintiuno','veintidós','veintitres','veinticuatro',
                     'veinticinco','veintiséis','veintisiete','veintiocho','veintinueve','treinta','treinta y uno']
            
            fecha = datetime.datetime.now()
            now = datetime.datetime.now()
            year = now.year
            month = fecha.strftime("%m")

            day = fecha.strftime("%e")

            mes = meses[int(month)-1]
            dia = dias[int(day)-1]
            tiraAno = self.numero_to_letras(year)
            ano = " del año dos mil veintitrés"
            tira_fecha = "a los " + dia + " días del mes de " + mes + " de " + tiraAno.lower()

            return tira_fecha
    
#-----------------------------------------------------------------------#
    def get_estado(self , sta):
        '''Method to compute la escala minima.'''

        if sta == 'draft':
           return 'POR INICIAR'
        elif sta == 'done':
           return 'INICIADO' 
        elif sta == 'terminate':
           return 'CULMINADO'
        elif sta == 'aprobado':
           return 'APROBADO'
        elif sta == 'aplazado':
           return 'APLAZADO'
        else:
            return sta
        
        return sta
    
#-----------------------------------------------------------------------#
    def action_search_salida(self):
        form_data = self.read()[0]

        est    = []
        eva    = []
        act    = []
        asi    = []
        pro    = []

        no_eva      = 0
        i           = 1
        j           = 1
        r           = 1

        acumOralStu = 0
        acumEscStu  = 0
        acumEva     = 0
        contaEva    = 0
        contaAsi    = 0
        contaAsiste = 0

        promeO      = 0
        promeE      = 0
        promeT      = 0
        promeA      = 0

        calificaVals = self.get_escala()

        # Incluir registros archivados
        stuObj = self.env['student.student'].with_context(active_test=False).search([('id','=', self.student_id.id)] , order ='name asc')

        riObj = self.env['student.inscripcion'].with_context(active_test=False).search([('id','=', self.inscripcion_id.id)] , order ='name asc')

        signer = self.env['cei.signer'].sudo().search([('id','=', self.signer_id.id)])

        if stuObj: 
            
             cedula     = stuObj.student_ci
             codigo     = stuObj.student_code
             nombre     = stuObj.name
             
             # FORZAR active_test=False para la sección
             standard_rec = riObj.standard_id.with_context(active_test=False) if riObj.standard_id else None
             
             seccion    = ''
             curso      = ''
             schedule   = ''
             signature  = False
             director   = ''
             director_id = ''
             director_job = ''
             empresa    = ''
             programa   = ''
             estado     = ''
             date       = self.get_date()
             
             if standard_rec:
                 seccion    = standard_rec.code + '-' + standard_rec.name if standard_rec.code and standard_rec.name else standard_rec.name or ''
                 # MODIFICACIÓN: Extraer solo el nivel del curso
                 curso_completo = standard_rec.subject_id.nombre if standard_rec.subject_id else ''
                 curso = self.extraer_nivel_curso(curso_completo)
                 schedule   = standard_rec.note if standard_rec.note else ''
                 signature  = standard_rec.company_id.director_signature if standard_rec.company_id else False
                 director   = standard_rec.company_id.director_name if standard_rec.company_id else ''
                 director_id = standard_rec.company_id.director_id if standard_rec.company_id else ''
                 director_job = standard_rec.company_id.director_job if standard_rec.company_id else ''
                 empresa    = standard_rec.company_id.name if standard_rec.company_id else ''
                 programa   = standard_rec.subject_id.programa_id.name if standard_rec.subject_id and standard_rec.subject_id.programa_id else ''
                 estado     = self.get_estado(riObj.state) if riObj else ''

             est.append({      
                            'cedula'        : cedula,  
                            'codigo'        : codigo, 
                            'nombre'        : nombre, 
                            'seccion'       : seccion,
                            'curso'         : curso,
                            'schedule'      : schedule,
                            'signature'     : signature,
                            'director'      : director,
                            'director_id'   : director_id,
                            'director_job'  : director_job,
                            'empresa'       : empresa,
                            'programa'      : programa,
                            'estado'        : estado,
                            'date'          : date,
                          })
             
             if standard_rec:
                 
                 seccion     = standard_rec.name
                 no_eva      = len(standard_rec.registroeva_ids)
                 no_asi      = len(standard_rec.asistencia_ids)

                #-----------------------------------------------------------------------#
                # CICLO EVALUACIONES DE LA SECCION                                      #
                #-----------------------------------------------------------------------#
                 j       = 1
                 while j <= no_eva:
                        
                    if standard_rec.registroeva_ids[j-1].state == 'terminate':
                        
                        # FORZAR active_test=False para detalles de evaluación
                        reObj = standard_rec.registroeva_ids[j-1].with_context(active_test=False).evaluacion_ids
                        no_evas = len(reObj)
                        
                        #-----------------------------------------------------------------------#
                        # CICLO DETALLES DE EVALUACIONES DE LA SECCION                          #
                        #-----------------------------------------------------------------------#

                        r = 1
                        nombreEva = ''
                        notaT = 0.0
                        nombreSta = ''
                        
                        while r <= no_evas:
                            if reObj[r-1].student_id.id == stuObj.id:

                                contaEva = contaEva + 1

                                nombreEva = reObj[r-1].evaluacion_id.nombre if reObj[r-1].evaluacion_id else ''
                                notaT     = reObj[r-1].nota if reObj[r-1].nota else 0.0
                                nombreSta = reObj[r-1].state if reObj[r-1].state else ''
                                acumEva  += notaT
                                
                                # FORZAR active_test=False para actividades
                                raObj = reObj[r-1].with_context(active_test=False).actividad_ids
                                no_act = len(raObj)
                                act = []
                                i = 1

                                while i <= no_act:
                                    nombreAct = raObj[i-1].nombre if raObj[i-1].nombre else ''
                                    nota      = raObj[i-1].nota if raObj[i-1].nota else 0.0
                                    nota_r    = raObj[i-1].nota_r if raObj[i-1].nota_r else 0.0
                                
                                    act.append({      
                                        'nombreAct' : nombreAct.upper(),       
                                        'nota'      : nota,
                                        'nota_r'    : nota_r,  
                                    })

                                    i = i + 1

                            
                            r = r + 1
                        
                        eva.append({      
                                    'nombreEva' : nombreEva.upper(),       
                                    'nota'      : notaT,
                                    'nombreSta' : nombreSta.upper(),  
                                    'noAct'     : no_act, 
                                    'listAct'   : act,
                                   })

                    j = j + 1
                        
                #-----------------------------------------------------------------------#
                # CICLO ASISTENCIA DE LA SECCION                                      #
                #-----------------------------------------------------------------------#
                 j       = 1
                 while j <= no_asi:
                        
                    if standard_rec.asistencia_ids[j-1].state == 'terminate':
                        
                        # FORZAR active_test=False para detalles de asistencia
                        raObj = standard_rec.asistencia_ids[j-1].with_context(active_test=False).asistencia_ids
                        no_detalle_asi = len(raObj)

                        #-----------------------------------------------------------------------#
                        # CICLO DETALLES DE ASISTENCIA DE LA SECCION                          #
                        #-----------------------------------------------------------------------#

                        r = 1
                        nombreAsi = ''
                        is_asistio = False
                        nombreSta = ''
                        
                        while r <= no_detalle_asi:
                            if raObj[r-1].student_id.id == stuObj.id:
                                contaAsi = contaAsi + 1
                                nombreAsi = raObj.asistencia_id.name if raObj.asistencia_id else ''
                                nombreSta = self.get_estado(raObj.asistencia_id.state) if raObj.asistencia_id else ''
                                
                                if raObj[r-1].is_attended:
                                    contaAsiste = contaAsiste + 1
                                    is_asistio = 'ASISTENTE'
                                else:
                                    is_asistio = 'INASISTENTE'
                             
                            r = r + 1
                       
                        asi.append({      
                                    'nombreAsi' : nombreAsi, 
                                    'nombreSta' : nombreSta, 
                                    'is_asistio': is_asistio, 
                                   })
                        
                    j = j + 1
                        
        nombreSta = ''
        if contaEva != 0:
                promeT = acumEva / contaEva

                if promeT >= calificaVals['aprobado']:
                        nombreSta = "APROBADO"
                else:
                        nombreSta = "APLAZADO"
                
        if contaAsi != 0:
            promeA = (contaAsiste/contaAsi)*100


        pro.append({      
                    'promeT'    : promeT,
                    'promeA'    : promeA,
                    'nombreSta' : nombreSta,
                   })
        
        data = {
            'form_data': form_data,
            'est'   : est,
            'eva'   : eva,
            'act'   : act,
            'asi'   : asi,
            'pro'   : pro,
            'signer': signer.id if signer else False,
        }

        return self.env.ref('report_class.action_report_record_ce').report_action(self, data=data)