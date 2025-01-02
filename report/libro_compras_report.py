# -*- encoding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import UserError
import logging
from datetime import datetime
import json


class LibroCompras(models.AbstractModel):
    _name = 'report.account_gt.reporte_libro_compras'


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
                    elif line.account_id.user_type_id.move_type in ('receivable', 'payable'):
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


            amount_untaxed = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
            amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
            amount_total = sign * (total_currency if len(currencies) == 1 else total)
            amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
            amount_untaxed_signed = -total_untaxed
            amount_tax_signed = -total_tax
            amount_total_signed = abs(total) if move.move_type == 'entry' else -total
            amount_residual_signed = total_residual


            if amount_residual_signed < 0:
                conversion['impuesto'] = (amount_tax_signed *-1)
                conversion['total'] = amount_residual_signed * -1
            else:
                conversion['impuesto'] = (amount_tax_signed)
                conversion['total'] = amount_residual_signed


        return conversion


    def _get_impuesto_iva(self,tax_ids):
        impuesto_iva = False
        if len(tax_ids) > 0:
            for linea in tax_ids:
                if 'IVA' in linea.name:
                    impuesto_iva = True

        return impuesto_iva

    def _get_compras(self,datos):
        compras_lista = []
        gastos_no_lista = []
        logging.warning('Bienvenido a la funcion de libro compras')
        compra_ids = self.env['account.move'].search([
        ('company_id','=',self.env.company.id),
        ('date','<=',datos['fecha_fin']),
        ('date','>=',datos['fecha_inicio']),
        ('state','=','posted'),
        ('move_type','in',['in_invoice','in_refund'])] ,order='invoice_date asc')
        total = {'compra':0,'compra_exento':0,'servicio':0,'servicio_exento':0,'importacion':0,'pequenio':0, 'combustible':0, 'activo':0,'iva':0,'total':0}
        total_gastos_no = 0
        documentos_operados = 0
        if compra_ids:
                for compra in compra_ids:
                    if compra.journal_id.tipo_factura != False and compra.journal_id.tipo_factura != "RECI":
                        formato_fecha = compra.invoice_date.strftime('%d/%m/%Y')
                        rectificativa=False
                        factura = ''
                        documento = ''
                        doc_ref = ''
                        if compra.ref:
                            if '-' in compra.ref:
                                factura = compra.ref.split('-')[0]
                                documento = compra.ref.split('-')[1]
                            elif '/' in compra.ref:
                                factura = compra.ref.split('/')[0]
                                documento = compra.ref.split('/')[1]
                            else:
                                modulo_fel = self.env['ir.module.module'].search([('name', '=', 'infilefel')])
                                if modulo_fel and modulo_fel.state == 'installed':
                                    factura = compra.fel_serie
                                    documento = compra.fel_numero
                                else:
                                    factura = ''
                                    documento = ''
                        if documento == '' and compra.journal_id.tipo_factura == 'FESP' and compra.fel_numero:
                                documento = compra.fel_numero
                            
                        documentos_operados += 1
                        if compra.journal_id:
                            doc_ref = compra.journal_id.tipo_factura
                        if compra.move_type == 'in_refund':
                            rectificativa=True

                        dic = {
                            'id': compra.id,
                            'fecha': formato_fecha,
                            'serie': factura,
                            'factura': documento,
                            'documento': doc_ref,
                            'proveedor': compra.partner_id.name if compra.partner_id else '',
                            'nit': compra.partner_id.vat if compra.partner_id.vat else '',
                            'compra': 0,
                            'compra_exento':0,
                            'servicio': 0,
                            'servicio_exento': 0,
                            'importacion': 0,
                            'pequenio': 0,
                            'combustible':0,
                            'activo':0,
                            'iva': 0,
                            'total': 0,
                            'rectificativa':rectificativa
                        }

#        Si la factura es nota de credito si es consumible y activo es igual a false

                        if dic['rectificativa']:
                            producto_compra = 0
                            producto_servicio = 0
                            producto_activo = 0
                            iva_general = 0
                            for linea in compra.invoice_line_ids:
                                if linea.product_id.type == 'consu' and linea.product_id.es_activo == False:
                                    producto_compra += linea.price_subtotal
                                    iva_general += linea.price_total - linea.price_subtotal
                                if linea.product_id.type == 'service' and linea.product_id.es_activo == False:
                                    producto_servicio += linea.price_subtotal
                                    iva_general += linea.price_total - linea.price_subtotal
                                if linea.product_id.type == 'consu' and linea.product_id.es_activo:
                                    producto_activo += linea.price_subtotal
                                    iva_general += linea.price_total - linea.price_subtotal

                            dic['compra']=producto_compra
                            dic['activo']=producto_activo
                            dic['servicio']=producto_servicio
                            dic['iva']=iva_general

#                         if compra.tipo_factura == 'combustible':
#                             dic['combustible']+=(compra.amount_untaxed_signed*-1)
#                             iva = (compra.amount_total_signed*-1)+ compra.amount_untaxed_signed
#                             dic['iva']+= iva

                        if compra.tipo_factura == 'activo' and compra.journal_id.tipo_factura != 'FESP':
                            dic['activo']+=(compra.amount_untaxed_signed*-1)
                            iva = (compra.amount_total_signed*-1)+ compra.amount_untaxed_signed
                            dic['iva']+= iva


                        if compra.journal_id.tipo_factura == 'DUCA':
                            servicio_duca=0
                            iva_duca=0
                            duca_exentos=0
                            for linea_duca in compra.invoice_line_ids:
                                if linea_duca.tax_ids:
                                    if linea_duca.product_id.type == 'service' or linea_duca.product_id.type == 'consu':
                                        servicio_duca += linea_duca.price_subtotal
                                        iva_duca += linea_duca.price_total - linea_duca.price_subtotal
                                elif 'DAI' in linea_duca.product_id.name:
                                    duca_exentos += linea_duca.price_total
                            dic['importacion']=servicio_duca
                            dic['compra_exento']=duca_exentos
                            dic['iva']= iva_duca




                        total_factura_especial=0
                        total_servicio=0
                        fctura_distinta = False
                        total_exento=0
                        iva_fe = 0
                        if compra.journal_id.tipo_factura == 'FESP':
                            logging.warning('Hiiiiiii')
                            logging.warning(compra.name)
                            logging.warning(compra.id)
                            logging.warning(compra.fel_serie)
                            logging.warning(compra.tax_totals_json)
                            logging.warning(dic)
                            logging.warning('')
                            if compra.id == dic['id']:
                                if self.env['account.move'].fields_get('fel_serie'):
                                    dic['serie']=compra.fel_serie
                            fctura_distina = False
                            iva=0
                            total_fe=0
                            subtotal_fe=0
                            for lineas in compra.invoice_line_ids:
                                r = lineas.tax_ids.compute_all(lineas.price_unit, currency=compra.currency_id, quantity=lineas.quantity, product=lineas.product_id, partner=compra.partner_id)
                                if compra.id == 6435:
                                    logging.warning('R-----------------')
                                    logging.warning(r)
                                total_fe += lineas.quantity * lineas.price_unit
                                if lineas.product_id.es_activo and lineas.product_id.type == 'consu' or lineas.product_id.es_activo == False and lineas.product_id.type == 'consu':

                                    total_exento += lineas.price_subtotal
                                    subtotal_fe = total_exento
                                if (lineas.product_id.type in ['service','product']) and lineas.product_id.es_activo == False:

                                    total_servicio += lineas.price_subtotal
                                    subtotal_fe = total_servicio
                            
                            iva_fe = total_fe - subtotal_fe

                            dic['compra_exento'] = total_exento
                            dic['servicio'] = total_servicio
                            dic['iva'] = iva_fe
#                         compra.tipo_factura = 'combustible' and
                            
                        if compra.journal_id.tipo_factura != 'FESP' and compra.journal_id.tipo_factura == 'FACT':
                            for linea in compra.invoice_line_ids:
                                impuesto_iva = False
                                impuesto_iva = self._get_impuesto_iva(linea.tax_ids)
                                if compra.currency_id.id != compra.company_id.currency_id.id:
                                    if ((linea.product_id) and (('COMISION POR SERVICIOS' not in linea.product_id.name) or ('COMISIONES BANCARIAS' not in linea.product_id.name) or ('Servicios y Comisiones' not in linea.product_id.name))):
                                        if len(linea.tax_ids) > 0:

                                            monto_convertir_precio = compra.currency_id.with_context(date=compra.invoice_date).compute(linea.price_unit, compra.company_id.currency_id)

                                            r = linea.tax_ids.compute_all(monto_convertir_precio, currency=compra.currency_id, quantity=linea.quantity, product=linea.product_id, partner=compra.partner_id)
                                            if compra.id == 7167:
                                                logging.warning('Que es r?')
                                                logging.warning(r)
                                            for i in r['taxes']:
                                                if 'IVA' in i['name']:
                                                    dic['iva'] += i['amount']

                                            monto_convertir = compra.currency_id.with_context(date=compra.invoice_date).compute(linea.price_subtotal, compra.company_id.currency_id)

                                            if compra.tipo_factura == 'varios':
                                                if linea.product_id.type == 'product':
                                                    dic['compra'] += monto_convertir
                                                if linea.product_id.type != 'product':
                                                    dic['servicio'] +=  monto_convertir
                                            elif compra.tipo_factura == 'importacion':
                                                dic['importacion'] += monto_convertir

                                            else:
                                                if linea.product_id.type == 'product':
                                                    dic['compra'] += monto_convertir
                                                if linea.product_id.type != 'product':
                                                    dic['servicio'] +=  monto_convertir



                                            if compra.partner_id.pequenio_contribuyente:
                                                dic['compra'] = 0
                                                dic['servicio'] = 0
                                                dic['importacion'] = 0
                                                dic['pequenio'] += monto_convertir

                                            # dic['total']
                                            
                                        else:
                                            monto_convertir = compra.currency_id.with_context(date=compra.invoice_date).compute(linea.price_total, compra.company_id.currency_id)

                                            if compra.tipo_factura == 'varios':
                                                if linea.product_id.type == 'product':
                                                    dic['compra'] += monto_convertir
                                                if linea.product_id.type != 'product':
                                                    dic['servicio'] +=  monto_convertir
                                            elif compra.tipo_factura == 'importacion':
                                                dic['importacion'] += monto_convertir

                                            else:
                                                if linea.product_id.type == 'product':
                                                    dic['compra_exento'] += monto_convertir
                                                if linea.product_id.type != 'product':
                                                    dic['servicio_exento'] +=  monto_convertir



                                            if compra.partner_id.pequenio_contribuyente:
                                                dic['compra'] = 0
                                                dic['servicio'] = 0
                                                dic['importacion'] = 0
                                                dic['compra_exento'] = 0
                                                dic['servicio_exento'] = 0
                                                dic['pequenio'] += monto_convertir

                                else:
                                    total_act=0

                                    if linea.product_id:
                                        if len(linea.tax_ids) > 0:

                                            r = linea.tax_ids.compute_all(linea.price_unit, currency=compra.currency_id, quantity=linea.quantity, product=linea.product_id, partner=compra.partner_id)

                                            for i in r['taxes']:
                                                if 'IVA' in i['name']:
                                                    dic['iva'] += i['amount']
                                            logging.warning('Tal vez else')
                                            if compra.id == 6435:
                                                logging.warning('Factura buscada')
                                                logging.warning(r)
                                            if compra.tipo_factura == 'varios':

                                                if linea.product_id.type == 'product':
                                                    dic['compra'] += linea.price_subtotal
                                                if linea.product_id.type != 'product':
                                                    dic['servicio'] +=  linea.price_subtotal
                                            elif compra.tipo_factura == 'importacion':

                                                dic['importacion'] += linea.price_subtotal
#                                               if compra.tipo_factura == 'combustible':
                                            elif compra.tipo_factura == 'combustible' and linea.product_id.type == 'consu':
                                                
                                                #crea un diccionario 
                                                datos_json = json.loads(compra.tax_totals_json)
                                                if 'amount_untaxed' in datos_json:
                                                    dic['combustible']=datos_json['amount_untaxed']
                                                
                                                for linea_contable in compra.line_ids:
                                                    if 5 in linea_contable.account_id.user_type_id.get_external_id():
                                                        logging.warning('Ingresando en alguna parteeeee')    
                                                        dic['iva'] = linea_contable.debit
                                                        x = datos_json['amount_total'] - dic['iva']
                                                        dic['compra_exento'] = x - dic['combustible']
                                                    
#                                                 precio = ( linea.price_unit * (1-(linea.discount or 0.0)/100.0) )
#                                                 precios = linea.tax_ids.compute_all(precio, currency=compra.currency_id, quantity=linea.quantity, product=linea.product_id, partner=compra.partner_id)
#                                                 iva_cobrar = 0
#                                                 idp_super = 0
#                                                 for impuesto in precios['taxes']:
#                                                     if impuesto['name'] ==  'IVA por Cobrar':
#                                                         iva_cobrar += impuesto['amount']
#                                                     if impuesto['name'] ==  'IDP Super':
#                                                         idp_super += impuesto['amount']
#                                                 dic['combustible']+=(compra.amount_untaxed_signed*-1)
# #                                                 iva = (compra.amount_total_signed*-1)+ compra.amount_untaxed_signed
#                                                 dic['iva'] = iva_cobrar
#                                                 dic['compra_exento'] = idp_super
# #                                                 dic['iva']+= iva
                                            else:
                                                iva_prod=0
                                                if linea.product_id.es_activo:
                                                    dic['activo'] += linea.price_subtotal
                                                    total_act = linea.quantity * linea.price_unit
                                                    iva_prod += total_act - linea.price_subtotal
                                                    dic['iva'] = iva_prod
                                                else:
                                                    if linea.product_id.type == 'product' :
                                                        dic['compra'] += linea.price_subtotal
                                                    if linea.product_id.type != 'product' and linea.product_id.type != 'consu':
                                                        dic['servicio'] +=  linea.price_subtotal
                                                    if linea.product_id.type == 'consu' and linea.product_id.es_activo == False:

                                                        dic['compra'] +=  linea.price_subtotal

                                            if compra.partner_id.pequenio_contribuyente:
                                                dic['compra'] = 0
                                                dic['servicio'] = 0
                                                dic['importacion'] = 0
                                                dic['compra_exento'] = 0
                                                dic['servicio_exento'] = 0
                                                dic['pequenio'] += linea.price_total


                                        else:
                                            if linea.product_id.type == 'product':
                                                dic['compra_exento'] += linea.price_total
                                            if linea.product_id.type != 'product':
                                                dic['servicio_exento'] +=  linea.price_total


                                            if compra.partner_id.pequenio_contribuyente:
                                                dic['compra'] = 0
                                                dic['servicio'] = 0
                                                dic['importacion'] = 0
                                                dic['compra_exento'] = 0
                                                dic['servicio_exento'] = 0
                                                dic['pequenio'] += linea.price_total




                        if compra.move_type in ['in_refund']:
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
                        total['combustible'] += dic['combustible']
                        total['activo'] += dic['activo']
                        total['iva'] += dic['iva']
                        compras_lista.append(dic)
                        dic['total'] = dic['activo'] + dic['combustible'] + dic['compra'] + dic['servicio'] + dic['compra_exento'] + dic['servicio_exento'] + dic['importacion'] + dic['iva'] + dic['pequenio']
                        total['total'] += dic['total']

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
        
        dicc_resumen_total={
            0:{
                'total_iva_combustible':0,
                'total_combustible':0
                },
            1:{
                'total_iva_compras':0,
                'total_compras':0
            },
            2:{
                'total_iva_servicio':0,
                'total_servicio':0
            },
            3:{
                'total_iva_pequenio':0,
                'total_pequenio':0
            },
            4:{
                'total_iva_importaciones':0,
                'total_importaciones':0
            },
            5:{
                'total_iva_vehiculos':0,
                'total_vehiculos':0
            },
            6:{
                'total_iva_exento':0,
                'total_exento':0
            }
        }

        for lista in compras_lista:
            total_combustible=0
            total_compras=0
            total_servicio=0
            for id_compra in lista:
                if id_compra == 'combustible':
                    if lista['combustible']>0:
                        dicc_resumen_total[0]['total_iva_combustible']+=lista['iva']
                        dicc_resumen_total[0]['total_combustible']+=lista['total']
                if id_compra == 'compra':
                    if lista['compra']>0:
                        dicc_resumen_total[1]['total_iva_compras']+=lista['iva']
                        dicc_resumen_total[1]['total_compras']+=lista['total']
                if id_compra == 'servicio':
                    if lista['servicio']>0:
                        dicc_resumen_total[2]['total_iva_servicio']+=lista['iva']
                        dicc_resumen_total[2]['total_servicio']+=lista['total']
                if id_compra == 'pequenio':
                    if lista['pequenio']>0:
                        dicc_resumen_total[3]['total_iva_pequenio']+=lista['iva']
                        dicc_resumen_total[3]['total_pequenio']+=lista['total']
                if id_compra == 'importacion':
                    if lista['importacion']>0:
                        dicc_resumen_total[4]['total_iva_importaciones']+=lista['iva']
                        dicc_resumen_total[4]['total_importaciones']+=lista['total']
                if id_compra == 'activo':
                    if lista['activo']>0:
                        dicc_resumen_total[5]['total_iva_vehiculos']+=lista['iva']
                        dicc_resumen_total[5]['total_vehiculos']+=lista['total']
                if id_compra == 'compra_exento':
                    if lista['compra_exento']>0:
                        dicc_resumen_total[6]['total_iva_exento']+=lista['iva']
                        dicc_resumen_total[6]['total_exento']+=lista['total']

        if dic['id'] == 6435:
            logging.warning('Prestar atención ')
            logging.warning(dic)
        return {'compras_lista': compras_lista,'total': total,'documentos_operados':documentos_operados,'resumen_total':dicc_resumen_total,'gastos_no': gastos_no_lista,'total_gastos_no': total_gastos_no}

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            '_get_compras': self._get_compras,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
