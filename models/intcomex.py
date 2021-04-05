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

    
class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def write(self, vals):
        res = super(StockMoveLine, self).write(vals)
        for line in self:
            sale = self.env['sale.order'].search([('name', '=', line.move_id.picking_id.origin)])
            if sale:
                for sale_line in sale.order_line:
                    if sale_line.product_id.id == line.product_id.id:
                        sale_line.lot_id = line.lot_id
                        for invoice_line in sale_line.invoice_lines:
                            invoice_line.lot_id = line.lot_id
        return res
    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    lot_id = fields.Many2one('stock.production.lot', 'Lot')
        
    def _prepare_invoice_line(self):
        res = super(SaleOrderLine, self)._prepare_invoice_line()
        if self.lot_id:
            res['lot_id'] = self.lot_id.id
        return res