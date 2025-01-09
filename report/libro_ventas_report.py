# -*- encoding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import UserError
import logging

class LibroVentas(models.AbstractModel):
    _name = 'report.account_gt.reporte_libro_ventas'


    def _get_conversion(self,move_id):
        conversion = {'impuesto': 0,'total':0 }
        total_sin_impuesto = 0
        total_total = 0


        amount_untaxed = 0
        amount_tax = 0
        amount_total = 0
        amount_residual = 0
        amount_untaxed_signed = 0
        amount_tax_signed = 0
        amount_total_signed = 0
        amount_residual_signed = 0


        for move in move_id:
            total_untaxed = 0.0
            total_untaxed_currency = 0.0
            total_tax = 0.0
            total_tax_currency = 0.0
            total_residual = 0.0
            total_residual_currency = 0.0
            total = 0.0
            total_currency = 0.0
            currencies = set()

            for line in move.line_ids:
                if line.currency_id:
                    currencies.add(line.currency_id)

                if move.is_invoice(include_receipts=True):
                    # === Invoices ===

                    if not line.exclude_from_invoice_tab:
                        # Untaxed amount.
                        total_untaxed += line.balance
                        total_untaxed_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.tax_line_id:
                        # Tax amount.
                        total_tax += line.balance
                        total_tax_currency += line.amount_currency
                        total += line.balance
                        total_currency += line.amount_currency
                    elif line.account_id.account_type.move_type in ('receivable', 'payable'):
                        # Residual amount.
                        total_residual += line.amount_residual
                        total_residual_currency += line.amount_residual_currency
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance
                        total_currency += line.amount_currency

            if move.move_type == 'entry' or move.is_outbound():
                sign = 1
            else:
                sign = -1

            # logging.warn(total_sin_impuesto)
            # logging.warn(total)




            amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            amount_total = sign * (total_currency if len(currencies) == 1 else total)
            amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            amount_untaxed_signed = -total_untaxed
            amount_tax_signed = -total_tax
            amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            amount_residual_signed = total_residual

            # logging.warn(move.name)
            logging.warn(amount_untaxed)
            logging.warn(amount_tax)
            logging.warn(amount_total)
            logging.warn(amount_residual)
            logging.warn(amount_untaxed_signed)
            logging.warn(amount_total_signed)
            logging.warn(amount_residual_signed)


            # total_sin_impuesto = -total_untaxed
            # total_total = sign * (total_currency if len(currencies) == 1 else total)
            if amount_residual_signed < 0:
                logging.warn('IF')
                logging.warn(amount_residual_signed)
                logging.warn(amount_tax_signed)
                conversion['impuesto'] = (amount_tax_signed *-1)
                conversion['total'] = amount_residual_signed * -1
            else:
                conversion['impuesto'] = (amount_tax_signed)
                conversion['total'] = amount_residual_signed
            logging.warn(move.name)
            logging.warn(conversion)

        return conversion


    def _get_impuesto_iva(self,tax_ids):
        impuesto_iva = False
        if len(tax_ids) > 0:
            for linea in tax_ids:
                if 'IVA' in linea.name:
                    impuesto_iva = True
                    logging.warn('si hay iva')
        return impuesto_iva

    def _get_ventas(self,datos):
        compras_lista = []
        gastos_no_lista = []
        logging.warning('Funcion get ventas libro diario')
        logging.warning(self.env.company)
        logging.warning(datos)
        estados = ['cancel', 'posted']
        compra_ids = self.env['account.move'].search([('company_id','=',self.env.company.id), ('journal_id', 'in', datos['diarios_ids']), ('invoice_date','<=',datos['fecha_fin']),('invoice_date','>=',datos['fecha_inicio']),
('state','in', estados),
        ('move_type','in',['out_invoice','out_refund'])],order='invoice_date asc, name asc')

        total = {'compra':0,'compra_exento':0,'servicio':0,'servicio_exento':0,'importacion':0,'pequenio':0,'iva':0,'total':0,'reten_iva': 0}
        logging.warning(compra_ids)
        logging.warning('')
        logging.warning('')
        total_gastos_no = 0
        documentos_operados = 0
        if compra_ids:

                for compra in compra_ids :
                    logging.warning('Varias veces')
                    logging.warning(compra.move_type)
                    if 'RECIB' not in compra.journal_id.code:
                        logging.warning('Ingreso ::::')
                        correlativo_interno = 0
                        nombre_proveedor = 'ANULADA'
                        rectificativa = False
                        # logging.warn('TIPO CAMBIO')
                        # logging.warn(self._get_conversion(compra))
                        formato_fecha = compra.date.strftime('%d/%m/%Y')
                        documentos_operados += 1
                        if compra.state != 'cancel':
                            correlativo_interno = compra.id
                            nombre_proveedor = 'Publicada'
                        if compra.move_type == 'out_refund':
                            rectificativa = True
                        fel_serie = ''
                        fel_numero = ''
                        if self.env['account.move'].fields_get('fel_serie'):
                            fel_serie = compra.fel_serie if compra.fel_serie else False
                        if self.env['account.move'].fields_get('fel_numero'):
                            fel_numero = compra.fel_numero if compra.fel_numero else False
                        if fel_serie == False and fel_numero == False:
                            if compra.payment_reference:
                                if '-' in compra.payment_reference:
                                    fel_serie = compra.payment_reference.split('-')[0]
                                    fel_numero = compra.payment_reference.split('-')[1]
                                elif '/' in compra.payment_reference:
                                    fel_serie = compra.payment_reference.split('/')[0]
                                    fel_numero = compra.payment_reference.split('/')[1]
                                elif ' ' in compra.payment_reference:
                                    fel_serie = compra.payment_reference.split(' ')[0]
                                    fel_numero = compra.payment_reference.split(' ')[1]
                                else:
                                    fel_serie = ""
                                    fel_numero = ""
                        dic = {
                            'id': compra.id,
                            'fecha': formato_fecha,
                            'documento': compra.ref if compra.ref else compra.name,
                            'serie': fel_serie,
                            'numero_factura': fel_numero,
                            'tipo_doc': compra.journal_id.tipo_factura if compra.journal_id.tipo_factura else '',
                            'proveedor': compra.partner_id.name,
                            'estado_factura': nombre_proveedor,
                            'nit': compra.partner_id.vat if compra.partner_id.vat else '',
                            'compra': 0,
                            'compra_exento':0,
                            'servicio': 0,
                            'servicio_exento': 0,
                            'importacion': 0,
                            'pequenio': 0,
                            'iva': 0,
                            'bruto': 0,
                            'total': 0,
                            'reten_iva': 0,
                            'correlativo_interno': correlativo_interno,
                            'pais_destino': compra.company_id.country_id.name,
                            'observaciones': compra.name,
                            'rectificativa': rectificativa
                        }

                        reten_iva = self.env['account.move'].search([('ref','=', str(compra.name))])
                        if reten_iva and compra.state != 'cancel':
                            for linea in reten_iva.line_ids:
                                logging.warn(linea.account_id.account_type.name)
                                if linea.account_id.account_type.name == 'Activos Circulantes':
                                    dic['reten_iva'] += linea.debit
                                    total['reten_iva'] += linea.debit

                        for linea in compra.invoice_line_ids:
                            impuesto_iva = False
                            impuesto_iva = self._get_impuesto_iva(linea.tax_ids)
                            if compra.currency_id.id != compra.company_id.currency_id.id and compra.state != 'cancel':
                                if ((linea.product_id) and (('COMISION POR SERVICIOS' not in linea.product_id.name) or ('COMISIONES BANCARIAS' not in linea.product_id.name) or ('Servicios y Comisiones' not in linea.product_id.name))):
                                    if len(linea.tax_ids) > 0:

                                        precio_unitario = linea.price_unit
                                        if linea.discount > 0:
                                            precio_unitario = linea.price_unit - (linea.price_unit*(linea.discount/100))

                                        monto_convertir_precio = compra.currency_id.with_context(date=compra.invoice_date).compute(precio_unitario, compra.company_id.currency_id)

                                        r = linea.tax_ids.compute_all(monto_convertir_precio, currency=compra.currency_id, quantity=linea.quantity, product=linea.product_id, partner=compra.partner_id)

                                        for i in r['taxes']:
                                            if 'IVA' in i['name']:
                                                dic['iva'] += i['amount']
                                            logging.warn(i)

                                        monto_convertir = compra.currency_id.with_context(date=compra.invoice_date).compute(linea.price_subtotal, compra.company_id.currency_id)

                                        if compra.tipo_factura == 'varios':
                                            if linea.product_id.type == 'product':
                                                dic['compra'] += monto_convertir
                                            if linea.product_id.type != 'product':
                                                dic['servicio'] +=  monto_convertir
                                        elif compra.tipo_factura == 'exportacion' or self.env.company.id != compra.currency_id.id :
                                            dic['importacion'] += monto_convertir

                                        else:
                                            if linea.product_id.type == 'product':
                                                dic['compra'] += monto_convertir
                                            if linea.product_id.type != 'product':
                                                dic['servicio'] +=  monto_convertir

                                    else:
                                        monto_convertir = compra.currency_id.with_context(date=compra.invoice_date).compute(linea.price_total, compra.company_id.currency_id)

                                        if compra.tipo_factura == 'varios':
                                            if linea.product_id.type == 'product':
                                                dic['compra'] += monto_convertir
                                            if linea.product_id.type != 'product':
                                                dic['servicio'] +=  monto_convertir
                                        elif compra.tipo_factura == 'exportacion' or self.env.company.id != compra.currency_id.id:
                                            dic['importacion'] += monto_convertir

                                        else:
                                            if linea.product_id.type == 'product':
                                                dic['compra_exento'] += monto_convertir
                                            if linea.product_id.type != 'product':
                                                dic['servicio_exento'] +=  monto_convertir


                            else:

                                if ((linea.product_id) and (('COMISION POR SERVICIOS' not in linea.product_id.name) or ('COMISIONES BANCARIAS' not in linea.product_id.name) or ('Servicios y Comisiones' not in linea.product_id.name)) and compra.state != 'cancel'):
                                    if len(linea.tax_ids) > 0:

                                        precio_unitario = linea.price_unit
                                        if linea.discount > 0:
                                            precio_unitario = linea.price_unit - (linea.price_unit*(linea.discount/100))

                                        r = linea.tax_ids.compute_all(precio_unitario, currency=compra.currency_id, quantity=linea.quantity, product=linea.product_id, partner=compra.partner_id)

                                        for i in r['taxes']:
                                            if 'IVA' in i['name']:
                                                logging.warning('')
                                                logging.warning('')
                                                logging.warning(compra.name)
                                                logging.warning('La parte del IVA')
                                                logging.warning(i['amount'])
                                                dic['iva'] += i['amount']
                                            logging.warning('')
                                            logging.warning('')
                                            logging.warning('Lo que es I')
                                            logging.warning(i)

                                        if compra.tipo_factura == 'varios':
                                            if linea.product_id.type == 'product':
                                                dic['compra'] += linea.price_subtotal
                                            if linea.product_id.type != 'product':
                                                dic['servicio'] +=  linea.price_subtotal
                                        elif compra.tipo_factura == 'importacion':
                                            dic['importacion'] += linea.price_subtotal
                                        else:
                                            if linea.product_id.type == 'product':
                                                dic['compra'] += linea.price_subtotal
                                            if linea.product_id.type != 'product':
                                                dic['servicio'] +=  linea.price_subtotal


                                    else:
                                        if linea.product_id.type == 'product':
                                            dic['compra_exento'] += linea.price_total
                                        if linea.product_id.type != 'product':
                                            dic['servicio_exento'] +=  linea.price_total


                        dic['total'] = dic['compra'] + dic['servicio'] + dic['compra_exento'] + dic['servicio_exento'] + dic['importacion'] + dic['iva'] + dic['pequenio']

                        if compra.move_type in ['out_refund']:
                            dic['compra']  = dic['compra'] * -1
                            dic['compra_exento'] = dic['compra_exento'] * -1
                            dic['servicio'] =  dic['servicio'] * -1
                            dic['servicio_exento'] = dic['servicio_exento'] * -1
                            dic['importacion'] = dic['importacion'] * -1
                            dic['pequenio'] = dic['pequenio'] * -1
                            dic['iva'] = dic['iva'] * -1
                            dic['total'] = dic['total'] * -1

                        total['compra'] += dic['compra']
                        total['compra_exento'] += dic['compra_exento']
                        total['servicio'] += dic['servicio']
                        total['servicio_exento'] += dic['servicio_exento']
                        total['importacion'] += dic['importacion']
                        total['pequenio'] += dic['pequenio']
                        total['iva'] += dic['iva']
                        total['total'] += dic['total']


                        compras_lista.append(dic)
                    else:
                        # GASTOS NO DEDUCIBLES
                        dic = {
                            'id': compra.id,
                            'fecha': compra.date,
                            'documento': compra.name,
                            'proveedor': compra.partner_id.name if compra.partner_id else '',
                            'nit': compra.partner_id.vat if compra.partner_id.vat else '',
                            'total': compra.amount_total
                        }
                        total_gastos_no += compra.amount_total
                        gastos_no_lista.append(dic)

        logging.warning('')
        logging.warning('')
        logging.warning('Compra lista')
        logging.warning(compras_lista)
        return {'compras_lista': compras_lista,'total': total,'documentos_operados':documentos_operados,'gastos_no': gastos_no_lista,'total_gastos_no': total_gastos_no}

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            '_get_ventas': self._get_ventas,
            'company_id': self.env.company,

        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
