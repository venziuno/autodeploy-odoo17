# -*- coding: utf-8 -*-
{
    'name': 'Bestindo Custom Module',
    'version': '17.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Bestindo Persada Module',
    'description': 'Bestindo Custom',
    'author': 'Jova Software',
    'maintainer': 'Jova Software',
    'company': 'Jova Software',
    'website': 'https://www.jovasoftware.com',
    'depends': ['web','base', 'contacts', 'delivery', 'sale', 'product', 'sale_management', 'stock', 'all_in_one_sales_kit'],

    'data': [
        'data/data_roles.xml',
        'security/bp_group.xml',
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/res_users_views.xml',
        'views/res_partner_views.xml',
        'views/product_views.xml',
        'views/stock_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/multi_location_views.xml',
        'views/bp_deposit_views.xml',
        'views/bp_promotion_views.xml',
        'views/bp_users_roles_views.xml',

        'views/bp_menu_views.xml',    ],

    'license': 'Other proprietary',
    'installable': True,
}
