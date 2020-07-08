# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging


#from odoo.exceptions import UserError, ValidationError
import time
import xlsxwriter
import base64
import io
from dateutil.relativedelta import relativedelta

class ReporteIngresos(models.TransientModel):
    _name = 'intcomex.reporte_ingresos'

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
            hoja.write(0, 1, 'Descripción', bold)
            hoja.write(0, 2, 'Tienda', bold)
            hoja.write(0, 3, 'Marca', bold)
            hoja.write(0, 4, 'Categoría', bold)
            hoja.write(0, 5, 'Fecha de ingreso', bold)
            hoja.write(0, 6, 'Costo', bold)
            hoja.write(0, 7, 'Serie / Imei', bold)
            hoja.write(0, 8, 'Documento de origen', bold)
                
            y = 0       
            facturas = self.env['account.move'].search([('type', 'in', ['in_invoice']), ('state', '=', 'posted'), ('date', '>=', w['fecha_desde']), ('date', '<=', w['fecha_hasta'])])
            
            for factura in facturas:
                for linea in factura.invoice_line_ids:
                    y += 1
                   
                    lote_ids = linea.obtener_lotes()
                    if lote_ids:
                        for lote in lote_ids:
                            lote_name = lote.name
                            
                    else:
                        lote_name = ""
                        
                    hoja.write(y, 0, linea.product_id.default_code)
                    hoja.write(y, 1, linea.product_id.name)
                    hoja.write(y, 2, 'tienda')
                    hoja.write(y, 3, linea.product_id.marca)
                    hoja.write(y, 4, linea.product_id.categ_id.name)
                    hoja.write(y, 5, factura.invoice_date, date_format)
                    hoja.write(y, 6, linea.price_unit)
                    hoja.write(y, 7, lote_name)
                    hoja.write(y, 8, factura.invoice_origin)
                    
            
            
            libro.close()
            datos = base64.b64encode(f.getvalue())
            self.write({'archivo':datos, 'name':'reporte_ingresos.xlsx'})

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'intcomex.reporte_ingresos',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }