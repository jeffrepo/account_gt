from odoo import api, fields, models, tools, _
from odoo.release import version_info
import logging

class AccountMove(models.Model):
    _inherit = 'account.move'

    def write(self, vals):
        for move in self:
            if vals and move.move_type == "entry" and'liquidacion_id' in vals and vals['liquidacion_id']:
                vals['liquidacion_id'] = False            
        res = super(AccountMove, self).write(vals)
        return res
    
    if version_info[0] == 13:
        @api.onchange('journal_id')
        def onchange_tipo_factura(self):
            tipo = False
            if self.type in ['in_invoice','in_refund']:
                tipo = 'compra'
            if self.type in ['out_invoice','out_refund']:
                tipo = 'venta'
            logging.warn(tipo)
            self.tipo_factura = tipo
    else:
        @api.onchange('journal_id')
        def onchange_tipo_factura(self):
            tipo = False
            if self.move_type in ['in_invoice','in_refund']:
                tipo = 'compra'
            if self.move_type in ['out_invoice','out_refund']:
                tipo = 'venta'
            logging.warn(tipo)
            self.tipo_factura = tipo

    liquidacion_id = fields.Many2one('account_gt.liquidacion','Liquidacion')
    tipo_factura = fields.Selection([('venta','Venta'),('compra', 'Compra o Bien'),
    ('activo', 'Activo'), ('servicio', 'Servicio'),
    ('varios','Varios'), ('combustible', 'Combustible'),
    ('importacion', 'Importación'),('exportacion','Exportación'),
    ('factura_especial', 'Factura especial')],
        string="Tipo de factura")
    lugar_expedicion = fields.Char('Lugar de expedición')
    consignatario_destinatario_id = fields.Many2one('res.partner', string="Consignatario o Destinatario")
    codigo_consignatario_destinatario = fields.Char('Código consignatario o destinatario')
    comprador_id = fields.Many2one('res.partner', string="Comprador")
    exportador_id = fields.Many2one('res.partner', string="Exportador")
    direccion_comprador = fields.Char('Dirección comprador')
    otra_referencia = fields.Char('Otra referencia')
    incoterm_exp = fields.Selection([('EXW','EXW'),('FCA', 'FCA'),
    ('FAS', 'FAS'), ('FOB', 'FOB'),
    ('CFR','CFR'), ('CIF', 'CIF'),
    ('CPT', 'CPT'),('CIP','CIP'),
    ('DDP','DDP'),('DAP','DAP'),
    ('DPU','DPU'),('ZZZ','ZZZ')],
        string="Intocerm exportación")
    nombre_exportador = fields.Char('Nombre exportador')
    codigo_exportador = fields.Char('Código exportador')

    @api.onchange('consignatario_destinatario_id')
    def _onchange_consignatario_destinatario_id(self):
        if self.consignatario_destinatario_id:
            self.comprador_id = self.partner_id.id
            self.exportador_id = self.partner_id.id

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    conciliacion_bancaria = fields.Boolean("Conciliacion bancaria")
    fecha_conciliacion_bancaria = fields.Date("Fecha conciliacion")

class ResCompany(models.Model):
    _inherit = "res.company"

    anulado_libro_compras = fields.Boolean('Anulado libro compras')
