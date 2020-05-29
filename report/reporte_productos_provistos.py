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
            merge_format = libro.add_format({
                'align': 'center',
                'valign': 'vcenter'
            })
            
            hoja.write(0, 0, 'SKU', bold)
            hoja.write(0, 1, 'Descripción', bold)
            hoja.write(0, 2, 'Marca', bold)
            hoja.write(0, 3, 'Serie', bold)
            hoja.write(0, 4, 'Costo de compra', bold)
            hoja.write(0, 5, 'SOI', bold)
            hoja.write(0, 6, 'Price Protection', bold)
            hoja.write(0, 7, 'Fondos Coop', bold)
                
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
                    proteccion = linea.obtener_proteccion(w['fecha_desde'], w['fecha_hasta'])
                    if proteccion:
                        if proteccion[0]['soi'] > 0 or proteccion[0]['proteccion_precio'] > 0 or proteccion[0]['fondoscop'] > 0:
                            #Se calcula costo de compra
                            costo_compra = 0
                            lote_id = self.env['stock.production.lot'].search([('name','=',proteccion[0]['numero_serie'])])
                            move_line =  self.env['stock.move.line'].search([('lot_id','=',lote_id.id)])
                            if move_line:
                                ml = []
                                for m in move_line:
                                    ml.append(m.move_id.id)
                                    if ml:
                                        move = self.env['stock.move'].search([('id','in',ml)])
                                        if move:
                                            for m in move:
                                                if m.price_unit > 0:
                                                    costo_compra = m.price_unit
                                                else:
                                                    costo_compra = linea.product_id.standard_price
                            
                            y += 1
                            hoja.write(y, 0, linea.product_id.default_code)
                            hoja.write(y, 1, linea.product_id.name)
                            hoja.write(y, 2, 'marca')
                            hoja.write(y, 3, proteccion[0]['numero_serie'])
                            hoja.write(y, 4, costo_compra)

                            hoja.write(y, 5, proteccion[0]['soi'])
                            hoja.write(y, 6, proteccion[0]['proteccion_precio'])
                            hoja.write(y, 7, proteccion[0]['fondoscop'])

                            datos['totales']['costo_compra'] += costo_compra
                            datos['totales']['proteccion_precio'] += proteccion[0]['proteccion_precio']
                            datos['totales']['soi'] += proteccion[0]['soi']
                            datos['totales']['fondoscop'] += proteccion[0]['fondoscop']
            
            y += 1
            hoja.write(y, 3, 'Subtotal', bold)
            hoja.write(y, 4, datos['totales']['costo_compra'])
            hoja.write(y, 5, datos['totales']['soi'])
            hoja.write(y, 6, datos['totales']['proteccion_precio'])
            hoja.write(y, 7, datos['totales']['fondoscop'])

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