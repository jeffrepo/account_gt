# -*- encoding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import UserError
import logging

class LibroBancos(models.AbstractModel):
    _name = 'report.account_gt.reporte_libro_bancos'


    def saldo_inicial(self, datos):
        account_move_line_ids = self.env['account.move.line'].search([('account_id','=',datos['cuenta_id'][0]), ('date','<',datos['fecha_inicio'])], order='date')
        saldo = 0
        if account_move_line_ids:
            for movimiento in account_move_line_ids:
                saldo += movimiento.debit - movimiento.credit
        return saldo

    def moneda_cuenta(self, datos):
        moneda = False
        account_account = self.env['account.account'].search([('id','=',datos['cuenta_id'][0])])
        moneda = account_account.currency_id if account_account.currency_id else account_account.company_id.currency_id
        return moneda

    def movimientos(self, datos):
        moves = []
        account_move_line_ids = self.env['account.move.line'].search([('account_id','=',datos['cuenta_id'][0]), ('date','>=',datos['fecha_inicio']), ('date','<=',datos['fecha_fin']), ('parent_state','=','posted')], order='date')
        for movimiento in account_move_line_ids:
            debito = 0
            credito = 0
            if movimiento.amount_currency > 0:
                debito = movimiento.amount_currency
            else:
                credito = movimiento.amount_currency * -1
            mov = {
                'fecha': movimiento.date,
                'transaccion': movimiento.move_id.journal_id.name,
                'numero_cheque': movimiento.move_id.payment_ids[0].check_number if movimiento.move_id.payment_ids else '',
                # 'documento': movimiento.move_id.name if movimiento.move_id else '',
                'nombre': movimiento.partner_id.name if movimiento.partner_id else '',
                'descripcion': (movimiento.ref if movimiento.ref else ''),
                'debito': debito,
                'credito': credito,
                'moneda': movimiento.currency_id if movimiento.currency_id else movimiento.company_id.currency_id,
                'saldo': 0,
            }
            moves.append(mov)

        saldo_inicial = self.saldo_inicial(datos)
        saldo = saldo_inicial
        for m in moves:
            saldo = saldo + m['debito'] - m['credito']
            m['saldo'] = saldo
        return moves



    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'movimientos': self.movimientos,
            'saldo_inicial': self.saldo_inicial,
            'moneda_cuenta': self.moneda_cuenta,
            # 'direccion': diario.direccion and diario.direccion.street,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
