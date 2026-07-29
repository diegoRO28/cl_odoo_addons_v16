# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError

class StandardEvaluacion(models.Model):
    _inherit = "standard.evaluacion"

    # OVERRIDE:
    def get_no_students(self):
        '''Method to compute subjects.'''
        contador = 0
        for rec in self:
            #nombre = rec.standard_id.student_ids[0].student_code
            # Filtrando los estudiantes inscritos:
            contador = len(rec.standard_id.student_ids.filtered(lambda x: x.state_aux == 'inscrito'))

        return contador

    # OVERRIDE: 
    #-----------------------------------------------------------------------#
    def generate_record_evaluacion(self, no_students):
        """Generate registro de Evaluacion por seccion / Curso."""

        # # Especifica el campo
        # field = "nota1"
        
        #  # Especifica el nombre técnico de la vista
        # view_ref = "school.view_standard_evaluacion_form"

        #     # Carga la vista XML como un objeto
        # view = self.env.ref(view_ref)
        # if not view:
        #         raise ValidationError("La vista {} no existe.".format(view_ref))

        #     # Convierte el campo arch de la vista a un objeto lxml.etree.Element
        # arch_tree = etree.fromstring(view.arch)
        #     # Encuentra el campo price_unit en la vista
        # xpath_expr = "//page/field/tree/field[@name='{}']".format(field)

        # lista_campos = arch_tree.xpath(xpath_expr)
        
        # for field in lista_campos:
        #     field.set("string", "Examen escrito")
        #    # Guarda los cambios en la vista
        # view.write({"arch": etree.tostring(arch_tree)})


        i = 1

        evaluacion_obj = self.env['standard.evaluaciones']
        actividad_obj  = self.env['standard.actividades']


        for rec in self:
            if no_students != 0:
               # UPDATE: Cambiando rec.standard_id.student_ids por rec.standard_id.student_ids.filtered(lambda x: x.state_aux == 'inscrito')
               # Nota: Es la única modificación hecha en éste método. El resto sigue igual.
               student_ids = rec.standard_id.student_ids.filtered(lambda x: x.state_aux == 'inscrito')
               while i <= no_students:                   
                   # Antes:
                   # stu_ri    = rec.standard_id.student_ids[i-1].id
                   # stu_id    = rec.standard_id.student_ids[i-1].student_id.id
                   # stu_state = rec.standard_id.student_ids[i-1].state
                   
                   # Después:
                   stu_ri    = student_ids[i-1].id
                   stu_id    = student_ids[i-1].student_id.id
                   stu_state = student_ids[i-1].state                   
                   eva_id    = rec.id


                   no_act    = len(rec.libroevas_id.actividad_ids)

                   if stu_state == 'done':

                        # raise ValidationError(_("Tira: " + stu_state.help))
                        
                        evalua_id = evaluacion_obj.create({
                                            'inscripcion_id': stu_ri,
                                            'evaluacion_id' : eva_id,
                                            'student_id'    : stu_id,
                                        })

                        r=1
                        while r <= no_act:
                            if r==1:
                               evalua_id.is_act1 = True
                               evalua_id.actividad1_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = "A1: " + evalua_id.actividad1_id.tipo_id.name + " , "
                               
                            elif r==2:
                               evalua_id.is_act2 = True
                               evalua_id.actividad2_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = rec.note_act + " A2: " + evalua_id.actividad2_id.tipo_id.name + " , "
                            elif r==3:
                               evalua_id.is_act3 = True
                               evalua_id.actividad3_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = rec.note_act + " A3: " + evalua_id.actividad3_id.tipo_id.name + " , "
                            elif r==4:
                               evalua_id.is_act4 = True
                               evalua_id.actividad4_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = rec.note_act + " A4: " + evalua_id.actividad4_id.tipo_id.name + " , "
                               
                            elif r==5:
                               evalua_id.is_act5 = True
                               evalua_id.actividad5_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = rec.note_act + " A5: " + evalua_id.actividad5_id.tipo_id.name + " , "
                            elif r==6:
                               evalua_id.is_act6 = True
                               evalua_id.actividad6_id = rec.libroevas_id.actividad_ids[r-1].id
                               rec.note_act = rec.note_act + " A6: " + evalua_id.actividad6_id.tipo_id.name

                            r = r + 1

                          #raise ValidationError("ID : " + str(evalua_id.id))
                  

                   if no_act != 0:

                        j = 1
                        while j <= no_act:
                                
                            act_id = rec.libroevas_id.actividad_ids[j-1].id
                            act_name = rec.libroevas_id.actividad_ids[j-1].nombre
                            #raise ValidationError("GENERANDO LAS EVALUACIONES: while :" + "NO_ACT:" + str(no_act) + "ACT_ID:" + str(act_id) + act_name)
                                #-----------------------------------------------------------------------#
                                # GENERA EL REGISTRO A LOS STUDENT DONE                                  #
                                #-----------------------------------------------------------------------#

                            if stu_state == 'done':
                                         actividad_obj.create({
                                             
                                             'evaluacion_id' : evalua_id.id,
                                             'actividad_id'  : act_id,
                                             'student_id'    : stu_id,
                                         })
                            #raise ValidationError("GENERANDO LAS EVALUACIONES: ..!" + "STU_ID:" + str(stu_id) + "EVA_ID:" + str(rec.id))
                            j = j + 1
                            #raise ValidationError("GENERANDO LAS EVALUACIONES: while :" + "NO_ACT:" + str(no_act) + "ACT_ID:" + str(act_id) + act_name)

                   else:
                        raise ValidationError("ERROR: No hay actividades para la evaluación " + "EVA_ID:" + str(eva_id))

                   i = i + 1

        #raise ValidationError(_("Note: " + rec.note))        