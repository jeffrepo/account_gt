# -*- coding: utf-8 -*-

from odoo import models, fields, api

class LibroConciliacionBancariaWizard(models.TransientModel):
    _name = 'account_gt.libro_conciliacion_bancaria.wizard'
    _description = "Wizard para libro conciliacion bancaria"

    fecha_inicio = fields.Date('Fecha inicio')
    fecha_fin = fields.Date('Fecha fin')
    cuenta_id = fields.Many2one(
        'account.account', string='Cuenta',
        domain=lambda self: [('company_ids', 'parent_of', self.env.company.id)],
    )
    currency_id = fields.Many2one(
        'res.currency', string='Moneda', compute='_compute_currency_id',
    )
    saldo = fields.Monetary(
        'Saldo de cuenta', currency_field='currency_id',
        help='Ingrese el saldo en la moneda indicada: la de la cuenta, '
             'o la de la compañía si la cuenta no tiene moneda configurada.',
    )

    @api.depends('cuenta_id.currency_id')
    @api.depends_context('company')
    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = wizard.cuenta_id.currency_id or self.env.company.currency_id

    def print_report(self):
        data = {
             'ids': [],
             'model': 'account_gt.libro_conciliacion_bancaria.wizard',
             'form': self.read()[0]
        }
        return self.env.ref('account_gt.action_libro_conciliacion_bancaria').report_action([], data=data)
