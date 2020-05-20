# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import datetime
import logging

class IntcomexGenerarProteccionPreciosWizard(models.TransientModel):
    _name = "intcomex.generar_proteccion_precios.wizard"

    account_id = fields.Many2one("account.account", string="Cuenta contable", required=True)
    journal_id = fields.Many2one("account.journal", string="Diario", required=True)
    fecha_inicio = fields.Date(string='Fecha inicio', required=True)
    fecha_fin = fields.Date(string='Fecha fin', required=True)

    def crear_partida_contable(self):
        facturas = self.env['account.move'].search([('type', 'in', ['out_invoice', 'out_refund']), ('state', '=', 'posted'), ('date', '>=', self.fecha_inicio), ('date', '<=', self.fecha_fin), ('partida_intcomex', '!=', True)])
        cuenta_inventario_ids = {}
        #En este ciclo se crea un diccionario con todas las cuentas de inventario que serán utilizadas para crear la partida contable, y su respectiva sumatoria del monto.
        for factura in facturas:
            logging.warn(factura)
            factura.partida_intcomex = True
            for linea in factura.invoice_line_ids:
                if not linea.product_id.categ_id:
                    raise UserError("El producto '" + linea.product_id.name + "' no tiene definida una categoría.")
                if not linea.product_id.categ_id.property_stock_valuation_account_id:
                    raise UserError("La categoría de producto '" + linea.product_id.categ_id.name + "' no tiene definida una cuenta contable de inventario.")

                monto_proteccion = linea.obtener_proteccion(self.fecha_inicio,self.fecha_fin)
                if monto_proteccion > 0:
                    if factura.type == 'out_refund':
                        monto_proteccion *= -1

                    if linea.product_id.categ_id.property_stock_valuation_account_id.id not in cuenta_inventario_ids:
                        cuenta_inventario_ids[linea.product_id.categ_id.property_stock_valuation_account_id.id] = 0
                    cuenta_inventario_ids[linea.product_id.categ_id.property_stock_valuation_account_id.id] += monto_proteccion

        lineas_partida = []
        total = 0
        for account_id in cuenta_inventario_ids:
            if cuenta_inventario_ids[account_id] != 0:
                total += cuenta_inventario_ids[account_id]
                lineas_partida.append((0, 0, {
                    'name': '/',
                    'journal_id': self.journal_id.id,
                    'account_id': account_id,
                    'credit': cuenta_inventario_ids[account_id],
                    'debit': 0,
                    'parent_state': 'draft',
                }))

        if lineas_partida:
            lineas_partida.append((0, 0, {
                'name': '/',
                'journal_id': self.journal_id.id,
                'account_id': self.account_id.id,
                'credit': 0,
                'debit': total,
                'parent_state': 'draft',
            }))

            dict = {}
            dict['date'] = fields.Datetime.now()
            dict['name'] = 'Intcomex ' + str(fields.Datetime.now())
            dict['ref'] = datetime.datetime.strftime(self.fecha_inicio, '%d/%m/%Y')  + ' - ' + datetime.datetime.strftime(self.fecha_fin, '%d/%m/%Y')
            dict['journal_id'] = self.journal_id.id
            dict['amount_total'] = total
            dict['state'] = 'draft'

            dict['line_ids'] = lineas_partida

            move = self.env['account.move'].create(dict)
            move.post()

        return {'type': 'ir.actions.act_window_close'}
