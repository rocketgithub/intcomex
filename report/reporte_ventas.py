# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging


#from odoo.exceptions import UserError, ValidationError
import time
import xlsxwriter
import base64
import io
from dateutil.relativedelta import relativedelta

class ReporteVentas(models.TransientModel):
    _name = 'intcomex.reporte_ventas'

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
            porcentaje = libro.add_format({'num_format': '0%'})
            merge_format = libro.add_format({
                'align': 'center',
                'valign': 'vcenter'
            })
            
            hoja.write(0, 0, 'SKU', bold)
            hoja.write(0, 1, 'Descripción', bold)
            hoja.write(0, 2, 'Tienda', bold)
            hoja.write(0, 3, 'Cantidad', bold)
            hoja.write(0, 4, 'Fecha de venta', bold)
            hoja.write(0, 5, 'Firma FEL', bold)
            hoja.write(0, 6, 'Marca', bold)
            hoja.write(0, 7, 'Categoría', bold)
            hoja.write(0, 8, 'Serie / Imei', bold)
            hoja.write(0, 9, 'Costo', bold)
            hoja.write(0, 10, 'Precio de Venta', bold)
            hoja.write(0, 11, 'Margen Actual', bold)
            hoja.write(0, 12, 'Price Protection', bold)
                
            y = 0       
            facturas = self.env['account.move'].search([('type', 'in', ['out_invoice', 'out_refund']), ('state', '=', 'posted'), ('date', '>=', w['fecha_desde']), ('date', '<=', w['fecha_hasta'])])
            
            for factura in facturas:
                for linea in factura.invoice_line_ids:
                    y += 1
                    lote_linea = ''
                    tienda = ''
                    if linea.sale_line_ids and linea.sale_line_ids.move_ids[0]:
                        tienda = linea.sale_line_ids.move_ids[0].warehouse_id.name
                        if linea.sale_line_ids.move_ids[0].move_line_ids[0].lot_id:
                            lote_linea = linea.sale_line_ids.move_ids[0].move_line_ids[0].lot_id.name
                        
                    if factura.pos_order_ids:
                        tienda = factura.pos_order_ids[0].config_id.name
                        for pos_line in factura.pos_order_ids[0].lines:
                            if pos_line.pack_lot_ids and pos_line.product_id.id == linea.product_id.id and pos_line.qty == linea.quantity and pos_line.price_unit == linea.price_unit:
                                lote_linea = pos_line.pack_lot_ids[0].lot_name
                          
                    protecciones = linea.obtener_proteccion()
                    price_protection = 0
                    if protecciones:
                        for proteccion in protecciones:
                            if proteccion['numero_serie'] == lote_linea:
                                price_protection =  proteccion['soi'] + proteccion['proteccion_precio'] + proteccion['fondoscop']
                            
                    costo_compra = 0
                    stock_move_line_id = self.env['stock.move.line'].search([('lot_id', '=', lote_linea), ('move_id.picking_id.purchase_id', '!=', None), ('move_id.product_id', '=', linea.product_id.id)])
                    if stock_move_line_id:
                        linea_compra = self.env['purchase.order.line'].search([('order_id.id', '=', stock_move_line_id[0].move_id.picking_id.purchase_id.id), ('product_id', '=', linea.product_id.id)])
                        if linea_compra:
                            costo_compra = linea_compra[0].price_unit
                            
                    hoja.write(y, 0, linea.product_id.default_code)
                    hoja.write(y, 1, linea.product_id.name)
                    hoja.write(y, 2, tienda)
                    hoja.write(y, 3, linea.quantity)
                    hoja.write(y, 4, factura.invoice_date, date_format)
                    hoja.write(y, 5, factura.firma_fel)
                    hoja.write(y, 6, linea.product_id.marca)
                    hoja.write(y, 7, linea.product_id.categ_id.name)
                    hoja.write(y, 8, lote_linea)
                    hoja.write(y, 9, costo_compra)
                    hoja.write(y, 10, linea.price_unit)
                    hoja.write(y, 11, (linea.price_unit - costo_compra) / (linea.price_unit or 1), porcentaje)
                    hoja.write(y, 12, price_protection)             
                    
            libro.close()
            datos = base64.b64encode(f.getvalue())
            self.write({'archivo':datos, 'name':'reporte_ventas.xlsx'})

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'intcomex.reporte_ventas',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }