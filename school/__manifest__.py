# See LICENSE file for full copyright and licensing details.

{
    'name': 'OdooClass',
    'version': '16.0.1.0.0',
    'author': 'IT Soluciones Web C.A.',
    'website': 'http://www.itsolucionesweb.com',
    'category': 'Gestion Academica de Centros de Estudios',
    'license': "AGPL-3",
    'complexity': 'easy',
    "summary": "Gestión Académica",
    'images': ['static/description/EMS.jpg'],

    #'depends': ['contacts','hr', 'crm', 'account'],

    'depends': [
        'account',
        'contacts',
        'stock',
        'sale',
        'hr',
    ],



    'data': ['security/school_security.xml',
             'security/ir.model.access.csv',
             'data/student_sequence.xml',
             'data/mail_template.xml',
             'wizard/terminate_reason_view.xml',
             
             'views/school_view.xml',
             'views/standard_view.xml',

             'views/teacher_view.xml',
             'views/parent_view.xml',
             'views/asistencia_view.xml',
             #'views/evaluacion_view.xml',
             
             'views/inscripcion_view.xml',
             

             'views/campus_view.xml',
             #'views/estudiante_view.xml',
             #'views/estudia_view.xml',
             'views/student_view.xml',
             'views/subject_view.xml',
             
             # 'views/res_partner_view_inherit.xml',

             #'wizard/assign_roll_no_wizard.xml',
             #'wizard/move_standards_view.xml',

             'report/report_view.xml',
             'report/identity_card.xml',
             "report/teacher_identity_card.xml",
             'report/identity_card_eva.xml',
             'report/identity_card_asi.xml',
             'report/identity_card_sec.xml',
             'report/identity_card_inc.xml',
             'report/identity_card_sub.xml',
             'report/identity_card_ret.xml',

             #----------------------------------------
             # V2
             #----------------------------------------
                'views/tipoeva_view.xml',
                'views/libroeva_view.xml',
                'views/registroeva_view.xml',
                'views/programa_view.xml',
                'views/tiporetiro_view.xml',
                'views/tipocambio_view.xml',
                'views/retiro_view.xml',
                'views/cambio_view.xml',

             ],
    'demo': ['demo/school_demo.xml'],
    'assets': {
        'web.assets_backend': [
            '/school/static/src/scss/schoolcss.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
