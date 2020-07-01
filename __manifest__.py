# -*- coding: utf-8 -*-
{
    'name': "Intcomex",

    'summary': """ Módulo para intcomex """,

    'description': """
        Módulo para intcomex
    """,

    'author': "Aquih",
    'website': "http://www.aquih.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['sale','product'],

    'data': [
        'views/account_move_views.xml',
        'views/product_template_views.xml',
        'views/intcomex_views.xml',
        'wizard/generar_proteccion_precios_views.xml',
        'wizard/reportes_views.xml',
        'security/ir.model.access.csv',
    ],
}
