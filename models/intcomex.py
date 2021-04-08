# -*- coding: utf-8 -*-

from odoo import api, fields, models

class IntcomexProteccionPrecio(models.Model):
    _name = "intcomex.proteccion_precio"
    _rec_name = "nombre"

    nombre = fields.Char('Nombre')
    producto_id = fields.Many2one('product.template','Producto')
    fecha_inicio = fields.Date('Fecha inicio')
    fecha_fin = fields.Date('Fecha fin')
    lote_id = fields.Many2one('stock.production.lot',string='Lote')
    tipo = fields.Selection([ ('proteccion','Price protection'), ('soi','Sell out incentive'), ('fondo','Fondos coop') ], 'Tipo')
    precio = fields.Float('Precio')
    