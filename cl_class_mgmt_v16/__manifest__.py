# See LICENSE file for full copyright and licensing details.

{
    'name': 'CL Gestión Académica',
    'version': '16.0.1.0.0',
    'author': 'Ocarina Solutions',
    'category': 'Gestion Academica de Centros de Estudios',
    'license': 'AGPL-3',
    'summary': 'Extensiones de gestión académica sobre el módulo school',

    'depends': [
        'school',
        'school_mod',
        'school_optimize',
        'school_archive',
        'custom_libroeva_copy',
        'report_xlsx',
        'mail',
    ],

    'data': [
        'security/ir.model.access.csv',
        'security/dashboard_security.xml',
        'data/dia_semana_data.xml',
        'data/teacher_kpi_snapshot_cron.xml',
        'views/standard_view.xml',
        'views/subject_view.xml',
        'views/asistencia_view.xml',
        'views/registroeva_view.xml',
        'wizard/reprogramar_wizard_views.xml',
        'wizard/teacher_mgmt_wizard_views.xml',
        'wizard/teacher_mgmt_dashboard_views.xml',
        'report/teacher_mgmt_report_views.xml',
        'views/dashboard_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'cl_class_mgmt_v16/static/src/scss/teacher_mgmt_dashboard.scss',
            'cl_class_mgmt_v16/static/src/js/teacher_mgmt_dashboard.js',
            'cl_class_mgmt_v16/static/src/xml/teacher_mgmt_dashboard.xml',
            'cl_class_mgmt_v16/static/src/scss/academic_dashboard.scss',
            'cl_class_mgmt_v16/static/src/js/cl_chart_utils.js',
            'cl_class_mgmt_v16/static/src/js/academic_dashboard.js',
            'cl_class_mgmt_v16/static/src/xml/academic_dashboard.xml',
            'cl_class_mgmt_v16/static/src/scss/admin_dashboard.scss',
            'cl_class_mgmt_v16/static/src/js/admin_dashboard.js',
            'cl_class_mgmt_v16/static/src/xml/admin_dashboard.xml',
        ],
    },

    'installable': True,
    'application': False,
    'auto_install': False,
}
