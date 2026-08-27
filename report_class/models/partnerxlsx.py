from odoo import models
class PartnerXlsx(models.AbstractModel):

    _name    = 'report.report_class.partner_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, partners):
        row  = 1
        col  = 0
        tira = ""
        city     = "Acarigua"
        country  = "VE"
        lang     = "en"
        password = "1234"
        rol      = "student"
        status   = "0"
        period   = "150"
        last_name     = ""
        # Create a workbook and add a worksheet.
        
        worksheet = workbook.add_worksheet('HOJA MOODLE')
        bold  = workbook.add_format({'bold': True})

        tira = "username,password,firstname,lastname,email,city,country,lang,course1,role1,enrolperiod1,enrolstatus1"
        worksheet.write(0, col, tira, bold)

        for obj in partners:

            code        = obj.student_id.student_code
            if not code:
                code = "CODE STUDENT VACIO"

            email       = obj.student_id.email
            if not email:
                email = "EMAIL VACIO"

            first_name  = obj.student_id.name
            if not first_name:
                first_name = "FIRSTNAME VACIO"

            code_moodle = obj.standard_id.code_moodle
            if not code_moodle:
                code_moodle = "CODE MOODLE VACIO"

            curse       = obj.standard_id.subject_id.name
            if not curse:
                curse = "CURSE VACIO"

            partner_xlsx = obj.name

            tira = code + "," + password + "," + first_name + "," + last_name + "," + email + "," + city + "," + country + "," + lang + "," + code_moodle + "," + rol + "," + period + "," + status  

            worksheet.write(row, col, tira, bold)
            
            row+=1