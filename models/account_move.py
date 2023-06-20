from odoo import api, fields, models, tools, _
from odoo.modules import get_module_resource
from odoo.release import version_info
import logging

class AccountMove(models.Model):
    _inherit = 'account.move'

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
    nombre_consignatario_destinatario = fields.Char('Nombre consignatario o destinatario')
    direccion_consignatario_destinatario = fields.Char('Dirección consignatario o destinatario')
    codigo_consignatario_destinatario = fields.Char('Código consignatario o destinatario')
    nombre_comprador = fields.Char('Nombre comprador')
    direccion_comprador = fields.Char('Dirección comprador')
    codigo_comprador = fields.Char('Código comprador')
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
    
class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    conciliacion_bancaria = fields.Boolean("Conciliacion bancaria")
    fecha_conciliacion_bancaria = fields.Date("Fecha conciliacion")

class ResCompany(models.Model):
    _inherit = "res.company"

    anulado_libro_compras = fields.Boolean('Anulado libro compras')
