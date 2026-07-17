# -*- coding: utf-8 -*-
{
    'name'       : "Class Reports V1.0",
    'summary'    : "Class odooClass V1.0",
    'description': """
                        Reports OdooClassV1.0
                   """,
    'author': "IT Soluciones WEB",
    'category': 'Uncategori Vzed',
    'version': '16.1',
    'website': "https://www.itsolucionesweb.com",

    'depends': [
        'base',
        'school',
        'report_xlsx',
        'sign', # <-- Firma digital
    ],

    'license': 'AGPL-3',

    'data': [
        'data/paper_format.xml',

        'report/report.xml',
        'report/report_record_template.xml',
        'report/report_invoice_recibo.xml',
        'report/report_record_ce_template.xml',
        'report/report_record_fi_template.xml',
        'report/report_record_pr_template.xml',

        'report/report_inasistencias.xml',
        
        'report/report_informe_ina.xml',
        'report/report_informe_inscrip.xml',
        'report/report_informe_cam.xml',

        'report/report_invoice_student.xml',
        'report/report_invoice_student_inscripcion.xml',

        'views/admin_view.xml',

        'security/ir.model.access.csv',

        'wizard/wizard.xml',
        'wizard/wizard_ce.xml',
        'wizard/wizard_fi.xml',
        'wizard/wizard_pr.xml',
        'wizard/wizard_as.xml',
        'wizard/wizard_in.xml',
        'wizard/wizard_ca.xml',

        'views/cei_signer_views.xml', # <- Firmante
    ],

    'images': [
        'static/description/icon.jpg'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}