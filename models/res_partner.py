from odoo import api, fields, models, tools, _

class Partner(models.Model):
    _inherit = "res.partner"

    pequenio_contribuyente = fields.Boolean('Pequeño contribuyente')
    documento_personal_identificacion = fields.Char('DPI')
    numero_documento_extranjero = fields.Char("Número de Documento de Identificación del Extranjero")
    codigo_destinatario = fields.Char("Código destinatario")
