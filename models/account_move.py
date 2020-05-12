# -*- coding: utf-8 -*-

from odoo import api, fields, models

class AccountMove(models.Model):
    _inherit = "account.move"

    partida_intcomex = fields.Boolean(string='Partida intcomex', default=False)
