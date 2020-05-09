# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _, SUPERUSER_ID

class ProductTemplate(models.Model):
    _inherit = "product.template"

    proteccion_precio_ids = fields.One2many('intcomex.proteccion_precio','producto_id','Proteccion de precio')
