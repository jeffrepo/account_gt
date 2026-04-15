# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ConciliacionBancariaWizard(models.TransientModel):
    _name = 'account_gt.conciliacion_bancaria.wizard'
    _description = "Wizard para conciliar con banco"

    fecha = fields.Date('Fecha de conciliación')

    def conciliar_con_banco(self):
        for campo_wizard in self:
            if campo_wizard.fecha:
                movimientos_seleccionados = self.env['account.move.line'].browse(self.env.context.get('active_ids', []))
                for movimiento in movimientos_seleccionados:
                    # existe_conciliacion = self.env['account_gt.conciliacion_bancaria'].search([('move_id','=',movimiento.id)])
                    if movimiento.conciliacion_bancaria and movimiento.fecha_conciliacion_bancaria:
                        raise ValidationError("No se pudó conciliar, por que ya fue conciliado en otra fecha.")
                    else:
                        movimiento.write({'conciliacion_bancaria': True, 'fecha_conciliacion_bancaria': campo_wizard.fecha})
            else:
                raise ValidationError("Seleccione fecha")

        return {'type': 'ir.actions.act_window_close'}

    def desconciliar_con_banco(self):
        for campo_wizard in self:
            movimientos_seleccionados = self.env['account.move.line'].browse(self.env.context.get('active_ids', []))
            for move in movimientos_seleccionados:
                # conciliacion = self.env['account_gt.conciliacion_bancaria'].search([('move_id','=',move.id)])
                if move.fecha_conciliacion_bancaria and move.conciliacion_bancaria:
                    move.write({'conciliacion_bancaria': False , 'fecha_conciliacion_bancaria': False})
                else:
                    raise ValidationError("No se puede desconciliar un movimiento que no fué conciliado.")

        return {'type': 'ir.actions.act_window_close'}
