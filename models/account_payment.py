from odoo import api, fields, models, tools, _

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    liquidacion_id = fields.Many2one('account_gt.liquidacion','Liquidacion')
    descripcion = fields.Char(string='Descripción')
