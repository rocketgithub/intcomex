# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging


#from odoo.exceptions import UserError, ValidationError
import time
import xlsxwriter
import base64
import io
from dateutil.relativedelta import relativedelta

class ProductosProvistos(models.TransientModel):
    _name = 'intcomex.reporte_productos_provistos'

    fecha_desde = fields.Date(string="Fecha Inicial", required=True, default=lambda self: time.strftime('%Y-%m-%d'))
    fecha_hasta = fields.Date(string="Fecha Final", required=True, default=lambda self: time.strftime('%Y-%m-%d'))
 
    name = fields.Char('Nombre archivo')
    archivo = fields.Binary('Archivo')
    
    def print_report_excel(self):
        for w in self:
            dict = {}
            dict['fecha_hasta'] = w['fecha_hasta']
            dict['fecha_desde'] = w['fecha_desde']

            f = io.BytesIO()
            libro = xlsxwriter.Workbook(f)
            hoja = libro.add_worksheet('Reporte')
            bold = libro.add_format({'bold': True})
            date_format = libro.add_format({'num_format': 'dd/mm/yy'}) 
            merge_format = libro.add_format({
                'align': 'center',
                'valign': 'vcenter'
            })
            
            hoja.write(0, 0, 'SKU', bold)
            hoja.write(0, 1, 'Tienda', bold)
            hoja.write(0, 2, 'Fecha', bold)
            hoja.write(0, 3, 'Descripción', bold)
            hoja.write(0, 4, 'Marca', bold)
            hoja.write(0, 5, 'Serie', bold)
            hoja.write(0, 6, 'Costo de compra', bold)
            hoja.write(0, 7, 'SOI', bold)
            hoja.write(0, 8, 'Price Protection', bold)
            hoja.write(0, 9, 'Fondos Coop', bold)
                
            y = 0       
            facturas = self.env['account.move'].search([('type', 'in', ['out_invoice']), ('state', '=', 'posted'), ('date', '>=', w['fecha_desde']), ('date', '<=', w['fecha_hasta'])])
            
            datos = {}
            datos['totales'] = {}
            datos['notas_credito'] = {}
            
            datos['totales']['costo_compra'] = 0
            datos['totales']['proteccion_precio'] = 0
            datos['totales']['soi'] = 0
            datos['totales']['fondoscop'] = 0
            
            datos['notas_credito']['proteccion_precio'] = 0
            datos['notas_credito']['soi'] = 0
            datos['notas_credito']['fondoscop'] = 0
            
            for factura in facturas:
                for linea in factura.invoice_line_ids:
                    lote_linea = ''
                    if linea.sale_line_ids and linea.sale_line_ids.move_ids[0] and linea.sale_line_ids.move_ids[0].move_line_ids[0].lot_id:
                        lote_linea = linea.sale_line_ids.move_ids[0].move_line_ids[0].lot_id.name
                        
                    if factura.pos_order_ids:
                        for pos_line in factura.pos_order_ids[0].lines:
                            if pos_line.pack_lot_ids and pos_line.product_id.id == linea.product_id.id and pos_line.qty == linea.quantity and pos_line.price_unit == linea.price_unit:
                                lote_linea = pos_line.pack_lot_ids[0].lot_name
                    
                    protecciones = linea.obtener_proteccion()
                    soi = 0
                    pp = 0
                    fondos = 0
                    if protecciones:
                        for proteccion in protecciones:
                            if proteccion['numero_serie'] == lote_linea:
                                soi = proteccion['soi']
                                pp = proteccion['proteccion_precio']
                                fondos = proteccion['fondoscop']
                            
                    costo_compra = 0
                    stock_move_line_id = self.env['stock.move.line'].search([('lot_id', '=', lote_linea), ('move_id.picking_id.purchase_id', '!=', None), ('move_id.product_id', '=', linea.product_id.id)])
                    if stock_move_line_id:
                        linea_compra = self.env['purchase.order.line'].search([('order_id.id', '=', stock_move_line_id[0].move_id.picking_id.purchase_id.id), ('product_id', '=', linea.product_id.id)])
                        if linea_compra:
                            costo_compra = linea_compra[0].price_unit

                    y += 1
                    hoja.write(y, 0, linea.product_id.default_code)
                    hoja.write(y, 1, stock_move_line_id[0].move_id.warehouse_id.name if stock_move_line_id else '')
                    hoja.write(y, 2, factura.invoice_date, date_format)
                    hoja.write(y, 3, linea.product_id.name)
                    hoja.write(y, 4, linea.product_id.marca)
                    hoja.write(y, 5, lote_linea)
                    hoja.write(y, 6, costo_compra)

                    hoja.write(y, 7, soi)
                    hoja.write(y, 8, pp)
                    hoja.write(y, 9, fondos)

                    datos['totales']['costo_compra'] += costo_compra
                    datos['totales']['proteccion_precio'] += pp
                    datos['totales']['soi'] += soi
                    datos['totales']['fondoscop'] += fondos

            y += 1
            hoja.write(y, 5, 'Subtotal', bold)
            hoja.write(y, 6, datos['totales']['costo_compra'])
            hoja.write(y, 7, datos['totales']['soi'])
            hoja.write(y, 8, datos['totales']['proteccion_precio'])
            hoja.write(y, 9, datos['totales']['fondoscop'])

            dias_restar = relativedelta(days=7)
            dia_desde = w['fecha_desde'] - dias_restar
            notas_credito = self.env['account.move'].search([('type', 'in', ['out_refund']), ('state', '=', 'posted'), ('date', '>=', dia_desde), ('date', '<', w['fecha_desde'])]) 
            for nota in notas_credito:
                if nota.tipo_nota:
                    if nota.tipo_nota == 'proteccion':
                        datos['notas_credito']['proteccion_precio'] += nota.amount_total
                    elif nota.tipo_nota == 'soi':
                        datos['notas_credito']['soi'] += nota.amount_total
                    else:
                        datos['notas_credito']['fondoscop'] += nota.amount_total

            y += 2
            hoja.merge_range(y, 2, y+2, 2, "Notas de credito ingresadas \na Odoo por estos motivos \nla semana anterior", merge_format)
            hoja.write(y, 3, 'SOI')
            hoja.write(y, 4, datos['notas_credito']['soi'])
            
            y += 1
            hoja.write(y, 3, 'Price Protection')
            hoja.write(y, 4, datos['notas_credito']['proteccion_precio'])
            
            y += 1
            hoja.write(y, 3, 'Fondos Coop')
            hoja.write(y, 4, datos['notas_credito']['fondoscop'])
            
            y += 2
            hoja.write(y, 3, 'TOTAL', bold)
            hoja.write(y, 4, datos['totales']['costo_compra'] - datos['notas_credito']['soi'] - datos['notas_credito']['proteccion_precio'] - datos['notas_credito']['fondoscop'], bold)
            
            libro.close()
            datos = base64.b64encode(f.getvalue())
            self.write({'archivo':datos, 'name':'reporte_productos_provistos.xlsx'})

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'intcomex.reporte_productos_provistos',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }