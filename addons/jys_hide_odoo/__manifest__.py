# -*- coding: utf-8 -*-
{
    'name': 'JYS Hide Base for Odoo17',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Hide Base',
    'description': 'Hide Base for Odoo17',
    'author': 'Jova Software',
    'maintainer': 'Jova Software',
    'company': 'Jova Software',
    'website': 'https://www.jovasoftware.com',
    'depends': ['base','web','auth_signup'],
    'data' :[
        'views/favicon.xml',
        'views/login_templates.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'jys_hide_odoo/static/src/js/extended_user_menu.js',
            'jys_hide_odoo/static/src/js/favicon.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,    
}
