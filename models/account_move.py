from odoo import api, fields, models, tools, _
from odoo.modules import get_module_resource
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

    liquidacion_id = fields.Many2one('account_gt.liquidacion','Liquidacion', tracking=True)
    tipo_factura = fields.Selection([('venta','Venta'),('compra', 'Compra o Bien'),
    ('activo', 'Activo'), ('servicio', 'Servicio'),
    ('varios','Varios'), ('combustible', 'Combustible'),
    ('importacion', 'Importación'),('exportacion','Exportación'),
    ('factura_especial', 'Factura especial')],
        string="Tipo de factura")
    lugar_expedicion = fields.Char('Lugar de expedición')
    nombre_consignatario_destinatario = fields.Char('Nombre consignatario o destinatario')
    direccion_consignatario_destinatario = fields.Char('Dirección consignatario o destinatario')
    consignatario_destinatario_id = fields.Many2one('res.partner', string="Consignatario o Destinatario")
    codigo_consignatario_destinatario = fields.Char('Código consignatario o destinatario')
    comprador_id = fields.Many2one('res.partner', string="Comprador")
    exportador_id = fields.Many2one('res.partner', string="Exportador")
    nombre_comprador = fields.Char('Nombre comprador')
    direccion_comprador = fields.Char('Dirección comprador')
    codigo_comprador = fields.Char('Código comprador')
    otra_referencia = fields.Char('Otra referencia')
    incoterm_exp = fields.Selection([
            ('EXW', 'En fábrica'),
            ('FCA', 'Libre transportista'),
            ('FAS', 'Libre al costado del buque'),
            ('FOB', 'Libre a bordo'),
            ('CFR', 'Costo y flete'),
            ('CIF','Costo, seguro y flete'),
            ('CPT','Flete pagado hasta'),
            ('CIP','Flete y seguro pagado hasta'),
            ('DDP','Entregado en destino con derechos pagados'),
            ('DAP','Entregada en lugar'),
            ('DAT','Entregada en terminal'),
            ('ZZZ','Otros')
        ],string="Incoterm",default="EXW",
        help="Termino de entrega")  
    nombre_exportador = fields.Char('Nombre exportador')
    codigo_exportador = fields.Char('Código exportador')
    fel_serie = fields.Char('Serie', copy=False, tracking=True)
    fel_numero = fields.Char('Número', copy=False, tracking=True)
    
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
