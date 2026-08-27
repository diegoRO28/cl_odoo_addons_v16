# -*- coding: utf-8 -*-

from email.policy import default
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import calendar, datetime

class Wizard(models.TransientModel):
    _name        = 'report.wizard_ca'
    _description = 'Report Wizard Inasistencias'

    date_today   = fields.Date('Fecha Informe', default=fields.Date.today )
    date_start   = fields.Date('Fecha Inicio', required=True, default=fields.Date.today )
    date_end     = fields.Date('Fecha Fin', required=True, default=fields.Date.today)
    
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
    def action_search_salida(self):
        form_data = self.read()[0]

        asi    = []
     
        no_cam      = 0
        j           = 1

        cam_obj = self.env['student.cambio'].search([] , order ='cambio_date asc')
     
        #raise ValidationError("no_student:" + str(no_ina))
        if cam_obj: 
           
           line_cam = cam_obj.filtered(lambda x: x.cambio_date >= self.date_start and x.cambio_date <= self.date_end and x.state == 'terminate')
           
           no_cam   = len(line_cam)
           #raise ValidationError("no_student:" + str(no_ina))
           j       = 1
           while j <= no_cam:
                        
               codeStu      = line_cam[j-1].student_id.student_code
               nombreStu    = line_cam[j-1].student_id.name

               nombreSec    = line_cam[j-1].standard_id.code + "/" + line_cam[j-1].standard_id.subject_id.nombre
               nombreCam    = line_cam[j-1].standard_id.school_id.name

               nombreCamDes = line_cam[j-1].standard_des_id.school_id.name
               nombreSecDes = line_cam[j-1].standard_des_id.code + "/" + line_cam[j-1].standard_des_id.subject_id.nombre

               fechaCam     = line_cam[j-1].cambio_date

               asi.append({       
                            'codeStu'      : codeStu,
                            'nombreStu'    : nombreStu,
                            'nombreSec'    : nombreSec, 
                            'nombreCam'    : nombreCam, 
                            'nombreSecDes' : nombreSecDes, 
                            'nombreCamDes' : nombreCamDes,
                            'fechaCam'     : fechaCam, 
                                    
                            #'company': self.env.user.company_id
                          })
                        
               j = j + 1
        
        data = {
            'form_data': form_data,
            'asi'   : asi,
        }

        return self.env.ref('report_class.action_report_informe_cam').report_action(self, data=data)