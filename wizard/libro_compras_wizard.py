# -*- coding: utf-8 -*-

from odoo import models, fields, api
import xlsxwriter
import base64
import io
import logging

class LibroComprasWizard(models.TransientModel):
    _name = 'account_gt.libro_compras.wizard'
    _description = "Wizard para libro de compras"

    fecha_inicio = fields.Date('Fecha inicio')
    fecha_fin = fields.Date('Fecha fin')
    name = fields.Char('Nombre archivo', size=32)
    archivo = fields.Binary('Archivo', filters='.xls')

    def print_report(self):
        data = {
             'ids': [],
             'model': 'account_gt.libro_compras.wizard',
             'form': self.read()[0]
        }
        return self.env.ref('account_gt.action_libro_compras').report_action([], data=data)


    def print_report_excel(self):
        for w in self:
            dict = {}
            dict['fecha_inicio'] = w.fecha_inicio
            dict['fecha_fin'] = w.fecha_fin
            # dict['impuesto_id'] = [w.impuesto_id.id, w.impuesto_id.name]
            # dict['diarios_id'] =[x.id for x in w.diarios_id]

            res = self.env['report.account_gt.reporte_libro_compras']._get_compras(dict)

            f = io.BytesIO()
            libro = xlsxwriter.Workbook(f)
            hoja = libro.add_worksheet('Reporte compras')

            hoja.write(0, 0, 'LIBRO DE COMPRAS Y SERVICIOS')
            hoja.write(2, 0, 'NUMERO DE IDENTIFICACION TRIBUTARIA')
            hoja.write(2, 1, self.env.company.vat)
            hoja.write(3, 0, 'NOMBRE COMERCIAL')
            hoja.write(3, 1,  self.env.company.name)
#             hoja.write(2, 3, 'DOMICILIO FISCAL')
#             hoja.write(2, 4,  self.env.company.street)
            hoja.write(3, 3, 'REGISTRO DEL')
            formato_fecha_inicio = w.fecha_inicio.strftime('%d/%m/%Y')
            formato_fecha_fin = w.fecha_fin.strftime('%d/%m/%Y')
            hoja.write(3, 4, formato_fecha_inicio + ' al ' + formato_fecha_fin)



            hoja.write(5, 0, 'Fecha')
            hoja.write(5, 1, 'Serie')
            hoja.write(5, 2, 'Factura')
            hoja.write(5, 3, 'Documento')
            hoja.write(5, 4, 'NIT')
            hoja.write(5, 5, 'Proveedor')
            hoja.write(5, 6, 'Combustible')
            hoja.write(5, 7, 'Compras')
            hoja.write(5, 8, 'Exentos')
            hoja.write(5, 9, 'Servicios')
            hoja.write(5, 10, 'Servicios exentos')
            hoja.write(5, 11, 'Importacion')
            hoja.write(5, 12, 'Pequeño contribuyente')
            hoja.write(5, 13, 'Activos')
            hoja.write(5, 14, 'IVA')
            hoja.write(5, 15, 'Total')

            fila = 6
            iva_proveedor=0
            iva_combustible=0
            iva_compra=0
            iva_servicios=0
            iva_pequenio=0
            iva_importaciones=0
            iva_exento=0
            iva_activo=0
            for compra in res['compras_lista']:
                hoja.write(fila, 0, compra['fecha'])
                hoja.write(fila, 1, compra['serie'])
                hoja.write(fila, 2, compra['factura'])
                hoja.write(fila, 3, compra['documento'])
                hoja.write(fila, 4, compra['nit'])
                hoja.write(fila, 5, compra['proveedor'])

                if compra['combustible']:
                    iva_combustible+=compra['iva']
#                 if compra['combustible']<0:
#                     compra['combustible'] = compra['combustible'] * -1
                hoja.write(fila, 6, compra['combustible'])

                if compra['compra']:
                    iva_compra+=compra['iva']
#                 if compra['compra']<0:
#                     compra['compra']= compra['compra'] * -1
                hoja.write(fila, 7, compra['compra'])

                if compra['compra_exento']:
                    iva_exento+=compra['iva']
#                 if compra['compra_exento']<0:
#                     compra['compra_exento'] = compra['compra_exento'] * -1
                hoja.write(fila, 8, compra['compra_exento'])

                if compra['servicio']:
                    iva_servicios+=compra['iva']
#                 if compra['servicio']<0:
#                     compra['servicio'] = compra['servicio'] * -1
                hoja.write(fila, 9, compra['servicio'])

#                 if compra['servicio_exento']<0:
#                     compra['servicio_exento'] = compra['servicio_exento'] * -1
                hoja.write(fila, 10, compra['servicio_exento'])

                if compra['importacion']:
                    iva_importaciones+=compra['iva']
#                 if compra['importacion']<0:
#                     compra['importacion'] = compra['importacion'] * -1
                hoja.write(fila, 11, compra['importacion'])

                if compra['pequenio']:
                    iva_pequenio+=compra['iva']
#                 if compra['pequenio'] < 0:
#                     compra['pequenio'] = compra['pequenio'] * -1
                hoja.write(fila, 12, compra['pequenio'])


                if compra['activo']:
                    iva_activo+=compra['iva']
#                 if compra['activo'] < 0:
#                     compra['activo'] = compra['activo'] * -1
                hoja.write(fila,13, compra['activo'])

#                 if compra['iva']<0:
#                     compra['iva'] = compra['iva'] * -1
                hoja.write(fila, 14, compra['iva'])

#                 if compra['total'] < 0:
#                     compra['total'] = compra['total'] * -1
                hoja.write(fila, 15, compra['total'])

                fila += 1

            hoja.write(fila, 5, 'TOTAL')
            hoja.write(fila, 6, res['total']['combustible'])
            hoja.write(fila, 7, res['total']['compra'])
            hoja.write(fila, 8, res['total']['compra_exento'])
            hoja.write(fila, 9, res['total']['servicio'])
            hoja.write(fila, 10, res['total']['servicio_exento'])
            hoja.write(fila, 11, res['total']['importacion'])
            hoja.write(fila, 12, res['total']['pequenio'])
            hoja.write(fila, 13, res['total']['activo'])
            hoja.write(fila, 14, res['total']['iva'])
            hoja.write(fila, 15, res['total']['total'])

            fila += 1


            hoja.write(fila, 14, 'Documentos operados:')
            hoja.write(fila, 15, res['documentos_operados'])

            fila += 1

            if len(res['gastos_no']) > 0:

                hoja.write(fila,0,'Gastos no deducibles')

                fila += 1

                hoja.write(fila,0,'Fecha')
                hoja.write(fila,1,'Documento')
                hoja.write(fila,2,'NIT')
                hoja.write(fila,3,'Proveedor')
                hoja.write(fila,4,'Total')

                fila += 1

                for gasto in res['gastos_no']:
                    hoja.write(fila,0,gasto['fecha'])
                    hoja.write(fila,1,gasto['documento'])
                    hoja.write(fila,2,gasto['nit'])
                    hoja.write(fila,3,gasto['proveedor'])
                    hoja.write(fila,4,gasto['total'])

                    fila += 1


                hoja.write(fila,3,'Total gastos no deducibles')
                hoja.write(fila,4,res['total_gastos_no'])

            fila+=2
            hoja.write(fila,3,'Resumen')
            hoja.write(fila,4,'Base')
            hoja.write(fila,5,'IVA')
            hoja.write(fila,6,'Total')

            fila+=1
            hoja.write(fila,3,'Total de combustibles: ')
            hoja.write(fila,4,res['total']['combustible'])
            hoja.write(fila,5,iva_combustible)
            total_combustible=iva_combustible+res['total']['combustible']
            hoja.write(fila,6,total_combustible)
            fila+=1
            hoja.write(fila,3,'Total de compras: ')
            hoja.write(fila,4,res['total']['compra'])
            hoja.write(fila,5,iva_compra)
            total_compra=res['total']['compra']+iva_compra
            hoja.write(fila,6,total_compra)
            fila+=1
            hoja.write(fila,3,'Total de servicios: ')
            hoja.write(fila,4,res['total']['servicio'])
            hoja.write(fila,5,iva_servicios)
            total_servicios=res['total']['servicio']+iva_servicios
            hoja.write(fila,6,total_servicios)
            fila+=1
            hoja.write(fila,3,'Pequeños contribuyentes: ')
            hoja.write(fila,4,res['total']['pequenio'])
            hoja.write(fila,5,iva_pequenio)
            total_pequenio=res['total']['pequenio']+iva_pequenio
            hoja.write(fila,6,total_pequenio)
            fila+=1
            hoja.write(fila,3,'Total de importaciones: ')
            hoja.write(fila,4,res['total']['importacion'])
            hoja.write(fila,5,iva_importaciones)
            total_importaciones=res['total']['importacion']+iva_importaciones
            hoja.write(fila,6,total_importaciones)
            fila+=1
            hoja.write(fila,3,'Vehículos: ')
            hoja.write(fila,4,res['total']['activo'])
            hoja.write(fila,5,iva_activo)
            total_activo = res['total']['activo']+iva_activo
            hoja.write(fila,6,total_activo)

            fila+=1
            hoja.write(fila,3,'Total exento: ')
            hoja.write(fila,4,res['total']['compra_exento'])
            hoja.write(fila,5,iva_exento)
            total_exento=res['total']['compra_exento']+iva_exento
            hoja.write(fila,6,total_exento)



            fila+=1
            base=0
            hoja.write(fila,3,'Total General: ')
            if res['total']['total'] > res['total']['iva']:
                base = res['total']['total']-res['total']['iva']
            hoja.write(fila,4, base)
            hoja.write(fila,5, res['total']['iva'])
            hoja.write(fila,6, res['total']['total'])
            fila+=1
            hoja.write(fila,3,'Total documentos operados: ')
            hoja.write(fila,4,res['documentos_operados'])


            fila+=3
            hoja.write(fila, 0, 'Resumen de 10 proveedores')
            fila+=1
            hoja.write(fila, 0, 'Proveedor')
            hoja.write(fila, 1, 'Base')
            hoja.write(fila, 2, 'IVA')
            hoja.write(fila, 3, 'Total')

            proveedores = self.env['account.move'].search([('invoice_date', '>=', w.fecha_inicio), ('invoice_date', '<=', w.fecha_fin), ('move_type', '=', 'in_invoice'), ('state', '=', 'posted')])
            dicc_proveedores={}
            contador = 0
            positivo = 0
            positivo_base = 0
            total_base = 0
            iva_linea = 0
            for proveedor in proveedores:
                if proveedor.journal_id.tipo_factura != False:
                    if proveedor.partner_id.id not in dicc_proveedores:
                        dicc_proveedores[proveedor.partner_id.id]={
                        'nombre_proveedor': proveedor.partner_id.name,
                        'base':0,
                        'iva':0,
                        'total':0
                        }
                        contador+=1

                    iva = 0
                    if proveedor.partner_id.id in dicc_proveedores and proveedor.journal_id.tipo_factura != 'FESP':

                        positivo = proveedor.amount_total_signed * -1

                        positivo_base = proveedor.amount_untaxed_signed * -1

                        dicc_proveedores[proveedor.partner_id.id]['base']+=positivo_base
                        dicc_proveedores[proveedor.partner_id.id]['total']+=positivo
#                         iva = dicc_proveedores[proveedor.partner_id.id]['total'] - dicc_proveedores[proveedor.partner_id.id]['base']

                        if len(proveedor.invoice_line_ids.tax_ids) > 0:
                            iva = positivo - positivo_base
                        dicc_proveedores[proveedor.partner_id.id]['iva']+=iva


                    if proveedor.partner_id.id in dicc_proveedores and proveedor.journal_id.tipo_factura == 'FESP':
                        total_base_linea=0
                        iva_linea=0
                        total_base = 0
                        total_fe = 0
                        iva_total = 0
                        for lineas_proveedor in proveedor.invoice_line_ids:
                            logging.warning('')
                            total_base += lineas_proveedor.price_subtotal
                            total_fe += lineas_proveedor.quantity * lineas_proveedor.price_unit
                        iva_total = total_fe - total_base
                        dicc_proveedores[proveedor.partner_id.id]['base']+= total_base
                        dicc_proveedores[proveedor.partner_id.id]['total']+=total_fe
                        dicc_proveedores[proveedor.partner_id.id]['iva']+=iva_total
#                             if lineas_proveedor.product_id.es_activo:
#                                 total_base_linea = lineas_proveedor.quantity * lineas_proveedor.price_unit;
#                                 iva_linea = total_base_linea - lineas_proveedor.price_subtotal
#                             if lineas_proveedor.product_id.type == 'service':
#                                 total_base_linea = lineas_proveedor.quantity * lineas_proveedor.price_unit;
#                                 iva_linea = total_base_linea - lineas_proveedor.price_subtotal
#                         dicc_proveedores[proveedor.partner_id.id]['base'] += total_base_linea;
#                         dicc_proveedores[proveedor.partner_id.id]['iva'] += iva_linea
# #                         total_base - (proveedor.amount_untaxed_signed*-1)
#                         dicc_proveedores[proveedor.partner_id.id]['total'] = dicc_proveedores[proveedor.partner_id.id]['base'] + dicc_proveedores[proveedor.partner_id.id]['iva']



            logging.warning('')
            logging.warning('')
            logging.warning('Diccionario proveedores')
            logging.warning(dicc_proveedores)
            logging.warning(len(dicc_proveedores))
            logging.warning('')
            logging.warning('')

            list_total = []
            posicion = 0
            reemplazo =0
            for id in dicc_proveedores:
                list_total.append(dicc_proveedores[id]['total'])

            for recorrido in range(1, len(list_total)):
                for posicion in range(len(list_total) - recorrido):
                    if list_total[posicion] < list_total[posicion + 1]:
                        temp = list_total[posicion]
                        list_total[posicion] = list_total[posicion+1]
                        list_total[posicion+1]= temp



            fila+=3
            contador = 0
            lista_id=[]
            for x_monto in list_total:
                if contador < 10:
                    for id in dicc_proveedores:
                        if x_monto == dicc_proveedores[id]['total'] and id not in lista_id:

                            hoja.write(fila, 0, dicc_proveedores[id]['nombre_proveedor'])
                            if dicc_proveedores[id]['base'] < 0:
                                dicc_proveedores[id]['base'] = dicc_proveedores[id]['base'] * -1
                                hoja.write(fila, 1, dicc_proveedores[id]['base'])
                            else:
                                hoja.write(fila, 1, dicc_proveedores[id]['base'])
                            if dicc_proveedores[id]['iva'] < 0:
                                dicc_proveedores[id]['iva'] = dicc_proveedores[id]['iva'] * -1
                                hoja.write(fila, 2, dicc_proveedores[id]['iva'])
                            else:
                                hoja.write(fila, 2, dicc_proveedores[id]['iva'])
                            if dicc_proveedores[id]['total'] < 0:
                                dicc_proveedores[id]['total'] = dicc_proveedores[id]['total'] * -1
                                hoja.write(fila, 3, dicc_proveedores[id]['total'])
                            else:
                                hoja.write(fila, 3, dicc_proveedores[id]['total'])
                            fila+=1
                            lista_id.append(id)
                contador+=1



            libro.close()
            datos = base64.b64encode(f.getvalue())
            self.write({'archivo':datos, 'name':'libro_compras.xlsx'})

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account_gt.libro_compras.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
