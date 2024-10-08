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
    'depends': ['web','base', 'contacts', 'delivery', 'sale', 'product', 'sale_management', 'stock', 'stock_delivery', 'l10n_id_efaktur', 'payment_custom', 'all_in_one_sales_kit'],

    'data': [
        'security/bp_group.xml',
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/res_users_views.xml',
        'views/res_partner_views.xml',
        'views/product_views.xml',
        'views/stock_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/payment_provider_views.xml',
        'views/multi_location_views.xml',
        'views/bp_deposit_views.xml',
        'views/bp_member_point_views.xml',
        'views/bp_promotion_views.xml',
        'views/bp_users_roles_views.xml',
        'views/ir_action_server.xml',
        'views/delivery_carrier_views.xml',
        'views/bp_negotiation_views.xml',
        'views/bp_term_views.xml',
        'views/bp_cart_views.xml',

        'wizard/account_views.xml',
        'wizard/sale_report_analysis_views.xml',
        'wizard/invoice_report_pdf_views.xml',

        'views/bp_menu_views.xml',    
        'views/bp_assets.xml',
        'data/ir_sequence_data.xml',
        'data/data_roles.xml',

        'report/paperformat.xml',
        'report/report_invoice.xml'
    ],

    'license': 'Other proprietary',
    'installable': True,
}
