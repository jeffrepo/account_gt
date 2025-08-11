from odoo import api, fields, models, tools, _
from odoo.modules import get_module_resource
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError, AccessError
import logging

class AccountACcount(models.Model):
    _inherit = "account.account"

    combustible = fields.Boolean('Combustible')
    retencion_iva = fields.Boolean('Iva retencion')
    uso = fields.Selection([('exento','Exento'),('compra_bien','Compra / bien'),('impuesto_petroleo','Impuesto de petroleo'),('combustible','Combustible'),('retencion_iva','Retencion IVA'),('iva','IVA')],'Uso')

class ResCompany(models.Model):
    _inherit = "res.company"

    columna_farmacia_exento_ventas = fields.Boolean('Columna farmacia exento')
    gastos_no_deducibles = fields.Boolean('Mostrar gastos no deducibles Libro compras')

class Liquidacion(models.Model):
    _name = "account_gt.liquidacion"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Liquidacion'
    _order = 'id desc'

    name = fields.Char('Nombre', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    descripcion = fields.Char('Descripcion',tracking=True)
    fecha = fields.Date('Fecha',tracking=True)
    factura_ids = fields.One2many('account_gt.liquidacion_factura','liquidacion_id','Facturas')
    pago_ids = fields.One2many('account_gt.liquidacion_pago','liquidacion_id','Pagos')
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency','Moneda',default=lambda self: self.env.company.currency_id.id)
    diario_id = fields.Many2one('account.journal', 'Diario', required=True,tracking=True)
    cuenta_id = fields.Many2one('account.account', 'Cuenta de desajuste',tracking=True)
    move_id = fields.Many2one('account.move', 'Movimiento',tracking=True)
    state = fields.Selection([
        ('borrador', 'Borrador'),
        ('conciliado', 'Conciliado'),
        ('cancelado', 'Cancelado'),], string='Estado', readonly=True, copy=False, index=True, tracking=3, default='borrador')
    factura_relacion_ids = fields.One2many('account.move','liquidacion_id','Facturas', tracking=True)
    pago_relacion_ids = fields.One2many('account.payment','liquidacion_id' ,'Pagos', tracking=True)
    total_factura = fields.Float('Total factura')

    def _sincronizar_facturas(self):
        liquidaciones = self.env['account_gt.liquidacion'].search([])
        if len(liquidaciones) > 0:
            total_factura = 0
            for liquidacion in liquidaciones:
                facturas_existentes  = []
                pagos_existentes = []
                for fe in liquidacion.factura_relacion_ids:
                    facturas_existentes.append(fe.id)
                    
                logging.warning(facturas_existentes)
                for fn in liquidacion.factura_ids:
                    logging.warning(fn.factura_id.id)
                    if fn.factura_id.id not in facturas_existentes:
                        logging.warning('no exsite')
                        logging.warning(fn.factura_id.id)
                        fn.factura_id.liquidacion_id = liquidacion.id

                if len(liquidacion.pago_relacion_ids):
                    for pe in liquidacion.pago_relacion_ids:
                        pagos_existentes.append(pe.id)

                    if len(liquidacion.pago_ids) > 0:
                        for pn in liquidacion.pago_ids:
                            if pn.pago_id not in pagos_existentes:
                                pn.pago_id.liquidacion_id = liquidacion.id

                for fe in liquidacion.factura_relacion_ids:
                    total_factura += fe.amount_total
                liquidacion.total_factura = total_factura
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code(
                    'account_gt.liquidacion', sequence_date=seq_date) or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('account_gt.liquidacion', sequence_date=seq_date) or _('New')

        result = super(Liquidacion, self).create(vals)
        return result


    def conciliar_liquidacion(self):
        move = False
        moneda_factura = False
        moneda_pago= False
        for dato in self:
            lineas = []

            total = 0
            if dato.factura_relacion_ids:
                moneda_factura = dato.factura_relacion_ids[0].currency_id
                for linea in dato.factura_relacion_ids:
                    # logging.warn(f.number)
                    # logging.warn(f.amount_total)
                    for l in linea.line_ids:
                        if l.account_id.user_type_id.name in ["Por pagar"]:
                            if not l.reconciled:
                                total += l.credit - l.debit
                                lineas.append(l)
                                logging.warning(l.credit - l.debit)
                            else:
                                raise UserError('La factura %s ya esta conciliada' % (linea.name))
            logging.warning('PASA FACTURA')
            logging.warning(lineas)

            if dato.pago_relacion_ids:
                moneda_pago = dato.pago_relacion_ids[0].currency_id
                for linea in dato.pago_relacion_ids:
                    # logging.warn(c.name)
                    # logging.warn(c.amount)
                    for l in linea.line_ids:
                        if l.account_id.reconcile and l.account_id.user_type_id.name in ["Por pagar",]:
                            if not l.reconciled :
                                total -= l.debit - l.credit
                                lineas.append(l)
                                logging.warning(l.debit - l.credit)
                            else:
                                raise UserError('El Pago %s ya esta conciliado' % (linea.name))

            logging.warning('PASA PAGO')
            for l in lineas:
                logging.warning(l.account_id.user_type_id.name)
                logging.warning(l.debit)
                logging.warning(l.credit)

            logging.warning(lineas)


            # if (moneda_pago.name=="GTQ" and moneda_factura.name=="GTQ") and moneda_factura.id == moneda_pago.id and round(total) != 0:
            #     logging.warning('TOTAL')
            #     logging.warning(total)
            #     break

            lineas_conciliares = []
            nuevas_lineas = []
            for linea in lineas:
                logging.warning('linea nuebvas')
                logging.warning(linea.credit)
                logging.warning(linea.debit)
                nuevas_lineas.append((0, 0, {
                    'name': linea.name,
                    'debit': linea.credit,
                    'credit': linea.debit,
                    'account_id': linea.account_id.id,
                    'partner_id': linea.partner_id.id,
                    'journal_id': dato.diario_id.id,
                    'date_maturity': dato.fecha,
                }))
            logging.warning('lineas')
            logging.warning(lineas)
            if total != 0 and moneda_factura.id != moneda_pago.id:
                nuevas_lineas.append((0, 0, {
                    'name': 'Diferencia de ' + dato.name,
                    'debit': -1 * total if total < 0 else 0,
                    'credit': total if total > 0 else 0,
                    'account_id': dato.cuenta_id.id,
                    'date_maturity': dato.fecha,
                }))

            if total != 0 and moneda_factura.name== 'USD' and moneda_pago.name=='USD':
                logging.warning('DOLAR')
                nuevas_lineas.append((0, 0, {
                    'name': 'Diferencia de ' + dato.name,
                    'debit': -1 * total if total < 0 else 0,
                    'credit': total if total > 0 else 0,
                    'account_id': dato.cuenta_id.id,
                    'date_maturity': dato.fecha,
                }))

            logging.warning('a crear move')
            move = self.env['account.move'].create({
                'line_ids': nuevas_lineas,
                'ref': dato.name,
                'date': dato.fecha,
                'journal_id': dato.diario_id.id,
            });

            move.action_post()
            #
            # move.write()
            if move and move.line_ids:
                indice = 0
                for linea in lineas:
                    lineas_conciliar = linea | move.line_ids[indice]
                    lineas_conciliar.reconcile()
                    indice += 1
            #

                self.write({'move_id': move.id})

        if move:
            # for linea in dato.factura_relacion_ids:
            #     linea.factura_id.write({'liquidacion_id': dato.id})
            # for linea in dato.pago_relacion_ids:
            #     linea.pago_id.write({'liquidacion_id': dato.id})
            self.write({'state': 'conciliado'})

        return True


    def cancelar_liquidacion(self):
        for dato in self:
            for l in dato.move_id.line_ids:
                if l.reconciled:
                    l.remove_move_reconcile()
            dato.move_id.button_draft()
            dato.move_id.button_cancel()
            # dato.move_id.unlink()

            if dato.move_id:
                for linea in dato.factura_ids:
                    linea.factura_id.write({'liquidacion_id': False})
                for linea in dato.pago_ids:
                    linea.pago_id.write({'liquidacion_id': False})
                self.write({'state': 'cancelado'})

        return True


    def cambiar_borrador(self):
        self.write({'state': 'borrador'})
        return True



class LiquidacionFactura(models.Model):
    _name = "account_gt.liquidacion_factura"
    _rec_name = "liquidacion_id"

    liquidacion_id = fields.Many2one('account_gt.liquidacion','Liquidacion')
    factura_id = fields.Many2one('account.move','Factura')
    currency_id = fields.Many2one('res.currency',string='moneda', related='factura_id.currency_id')
    total = fields.Monetary('Total',related='factura_id.amount_total')

class LiquidacionPago(models.Model):
    _name = "account_gt.liquidacion_pago"
    _rec_name = "liquidacion_id"

    liquidacion_id = fields.Many2one('account_gt.liquidacion','Liquidacion')
    pago_id = fields.Many2one('account.payment','Pago')
    currency_id = fields.Many2one('res.currency',string='moneda', related='pago_id.currency_id')
    total = fields.Monetary('Total',related='pago_id.amount')
