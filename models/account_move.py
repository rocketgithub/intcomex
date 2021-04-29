# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging

class AccountMove(models.Model):
    _inherit = "account.move"

    partida_intcomex = fields.Boolean(string='Partida intcomex', default=False)
    tipo_nota = fields.Selection(selection=[
            ('proteccion','Price protection'),
            ('soi','Sell out incentive'),
            ('fondo','Fondos coop'),
        ], string='Tipo de nota')

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    def obtener_lotes(self):
        # Se busca la venta perteneciente a la linea factura y el numero de serie en caso lo contenga
        lote_ids = []
        ventas_ids = self.mapped('sale_line_ids.order_id')
        # logging.warn(ventas_ids)
        if ventas_ids:
            stock_move_line_ids = ventas_ids.mapped('picking_ids.move_line_ids_without_package')
            if stock_move_line_ids:
                for move_line in stock_move_line_ids:
                    if move_line.product_id == self.product_id:
                        lote_ids.append(move_line.lot_id)

        if self.move_id.pos_order_ids:
            for orden in self.move_id.pos_order_ids:
                for linea_orden in orden.lines:
                    if linea_orden.product_id == self.product_id:
                        if linea_orden.pack_lot_ids:
                            for linea_lote in linea_orden.pack_lot_ids:
                                lote_id = self.env['stock.production.lot'].search([('name','=',linea_lote.lot_name),('product_id','=',linea_orden.product_id.id)], limit=1)
                                lote_ids.append(lote_id)

        return lote_ids

    # Retorna un diccionario separado por los tipos de proteccion con su respectivo valor
    def obtener_proteccion(self):
        # Se busca protección de precios perteneciente al producto de la linea y fecha facturada
        res = []
        if self.move_id and self.move_id.invoice_date:
            proteccion_precio_ids = self.env['intcomex.proteccion_precio'].search([('producto_id','=',self.product_id.product_tmpl_id.id),('fecha_inicio','<=', self.move_id.invoice_date), ('fecha_fin', '>=', self.move_id.invoice_date)])
            logging.warn(proteccion_precio_ids)
            if proteccion_precio_ids:
                lote_ids = self.obtener_lotes()
                if lote_ids:
                    for lote in lote_ids:
                        precios = {'numero_serie': lote.name, 'proteccion_precio': 0, 'soi': 0, 'fondoscop': 0}
                        # Buscamos si existe alguna linea con numero de serie de tipo proteccion de precio o fondoscop para hacer las validaciones
                        for linea_proteccion in proteccion_precio_ids:
                            if linea_proteccion.lote_id:
                                if lote.id == linea_proteccion.lote_id.id and linea_proteccion.tipo == 'proteccion':
                                    precios['proteccion_precio'] += linea_proteccion.precio
                                elif lote.id == linea_proteccion.lote_id.id and linea_proteccion.tipo == 'fondo':
                                    precios['fondoscop'] += linea_proteccion.precio
                                else:
                                    continue
                            else:
                                if linea_proteccion.tipo == 'proteccion':
                                    precios['proteccion_precio'] += linea_proteccion.precio
                                elif linea_proteccion.tipo == 'fondo':
                                    precios['fondoscop'] += linea_proteccion.precio
                                else:
                                    continue

                        for linea_proteccion in proteccion_precio_ids:
                            if  lote.id == linea_proteccion.lote_id.id and (linea_proteccion.tipo == 'soi' and (precios['proteccion_precio'] > 0 or precios['fondoscop'] > 0)):
                                continue
                            elif lote.id == linea_proteccion.lote_id.id and (linea_proteccion.tipo == 'soi' and (precios['proteccion_precio'] == 0 or precios['fondoscop'] == 0)):
                                precios['soi'] += linea_proteccion.precio
                            elif len(linea_proteccion.lote_id) == 0 and (linea_proteccion.tipo == 'soi' and (precios['proteccion_precio'] == 0 or precios['fondoscop'] == 0)):
                                precios['soi'] += linea_proteccion.precio
                            else:
                                continue
                        res.append(precios)
                else:
                    precios = {'numero_serie': '', 'proteccion_precio': 0, 'soi': 0, 'fondoscop': 0}
                    # Buscamos si existe alguna linea sin numero de serie de tipo proteccion de precio o fondoscop para hacer las validaciones
                    for linea_proteccion in proteccion_precio_ids:
                        if linea_proteccion.tipo == 'proteccion':
                            precios['proteccion_precio'] += linea_proteccion.precio
                        elif linea_proteccion.tipo == 'fondo':
                            precios['fondoscop'] += linea_proteccion.precio
                        else:
                            continue
                    for linea_proteccion in proteccion_precio_ids:
                        if  (linea_proteccion.tipo == 'soi' and (precios['proteccion_precio'] > 0 or precios['fondoscop'] > 0)):
                            continue
                        elif (linea_proteccion.tipo == 'soi' and (precios['proteccion_precio'] == 0 or precios['fondoscop'] == 0)):
                            precios['soi'] += linea_proteccion.precio
                        else:
                            continue
                    res.append(precios)
        return res
