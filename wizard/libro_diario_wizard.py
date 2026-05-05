# -*- coding: utf-8 -*-

from odoo import models, fields, api
import xlsxwriter
import base64
import io
import logging

class LibroDiarioWizard(models.TransientModel):
    _name ="account_gt.libro_diario.wizard"
    _description ="Wizard creado para libro diario"

    fecha_inicio = fields.Date('Fecha inicio: ')
    fecha_fin = fields.Date('Fecha final: ')
    diario_ids = fields.Many2many('account.journal',string="Diarios")
    consolidado = fields.Boolean('Consolidado')
    name = fields.Char('Nombre archivo: ', size=32)
    archivo = fields.Binary('Archivo ', filters='.xls')
    movimientos_destino = fields.Selection([('posted', 'Todos los asientos validados'),
                                ('all', 'Todos los asientos'),
                                ], string='Movimientos destino', required=True, default='posted')
    
    def _xlsx_value(self, value):
        if isinstance(value, dict):
            return (
                value.get('es_GT')
                or value.get('en_US')
                or next(iter(value.values()), '')
            )
        return value or ''
    
    def print_report(self):
        data = {
            'ids':[],
            'model': 'account_gt.libro_diario.wizard',
            'form': self.read()[0]
        }
        return self.env.ref('account_gt.action_libro_diario').report_action([], data=data)


    def print_report_excel(self):
        for w in self:
            dict = {}
            dict['fecha_inicio'] = w.fecha_inicio
            dict['fecha_fin'] = w.fecha_fin

            reporte_data = self.env['report.account_gt.reporte_libro_diario']._get_data(w.fecha_inicio, w.fecha_fin, w.diario_ids.ids, w.consolidado, w.movimientos_destino)
            reporte_data_consolidado = self.env['report.account_gt.reporte_libro_diario']._get_data_consolidado(w.fecha_inicio, w.fecha_fin, w.diario_ids.ids, w.consolidado, w.movimientos_destino)   
            
            f = io.BytesIO()
            libro = xlsxwriter.Workbook(f)
            hoja = libro.add_worksheet('Reporte libro diario')


            formato_moneda = libro.add_format(
            {'num_format': '[$Q-100A]#,##0.00;[RED]([$Q-100A]#,##0.00)'}
            )

            if reporte_data:
                hoja.write(0, 3, self.env.company.name)
                hoja.write(1, 3, 'NIT: ' + str(self.env.company.vat))
                hoja.write(2, 3, 'Libro Diario')
                hoja.write(3, 3, 'Periodo del ' + str(w.fecha_inicio) + ' AL ' + str(w.fecha_fin))
                hoja.write(4, 3, 'CIFRAS EXPRESADAS EN QUETZALES')

                
                hoja.set_column("A:G", 24)
                hoja.write(6, 0, 'Asiento')
                hoja.write(6, 1, 'Fecha')
                hoja.write(6, 2, 'Codigo')
                hoja.write(6, 3, 'Cuenta')
                hoja.write(6, 4, 'Descripción')
                hoja.write(6, 5, 'Debe')
                hoja.write(6, 6, 'Haber')

                fila = 7
                for diario in reporte_data:
                    hoja.write(fila, 0, reporte_data[diario]['diario']['es_GT'])
                    fila += 1
                    for asiento in reporte_data[diario]['asientos']:
                        for m in reporte_data[diario]['asientos'][asiento]['movimientos']:
                            if m['debe'] > 0:
                                hoja.write(fila, 0, m['nombre_movimiento'])
                                hoja.write(fila, 1, m['fecha'])
                            else:
                                hoja.write(fila, 0, '')
                                hoja.write(fila, 1, '')

                            hoja.write(fila, 2, self._xlsx_value(m['codigo']))
                            hoja.write(fila, 3, m['nombre_cuenta']["es_GT"])
                            hoja.write(fila, 4, m['descripcion'])
                            hoja.write(fila, 5, m['debe'], formato_moneda)
                            hoja.write(fila, 6, m['haber'], formato_moneda)
                            fila += 1
                            
                    hoja.write(fila, 4, 'TOTAL')
                    hoja.write(fila, 5, str(reporte_data[diario]['asientos'][asiento]['total_debe']), formato_moneda)
                    hoja.write(fila, 6, str(reporte_data[diario]['asientos'][asiento]['total_haber']), formato_moneda)
                    fila += 1
                    hoja.write(fila, 4, 'TOTAL DIARIO')
                    hoja.write(fila, 5, str(reporte_data[diario]['total_debe']), formato_moneda)
                    hoja.write(fila, 6, str(reporte_data[diario]['total_haber']), formato_moneda)
                    fila += 1

            
            if reporte_data_consolidado:
                hoja.write(0, 2, self.env.company.name)
                hoja.write(1, 2, 'NIT: ' + str(self.env.company.vat))
                hoja.write(2, 2, 'Libro Diario')
                hoja.write(3, 2, 'Periodo del ' + str(w.fecha_inicio) + ' AL ' + str(w.fecha_fin))
                hoja.write(4, 2, 'CIFRAS EXPRESADAS EN QUETZALES')

                
                hoja.set_column("A:D", 24)
                hoja.write(6, 0, 'Codigo')
                hoja.write(6, 1, 'Cuenta')
                hoja.write(6, 2, 'Debe')
                hoja.write(6, 3, 'Haber')

                fila = 7
                for llave_mes in reporte_data_consolidado:
                    if llave_mes != 'total_debe':
                        if llave_mes != 'total_haber':
                            hoja.write(fila, 0, reporte_data_consolidado[llave_mes]['nombre_mes'])
                            fila += 1
                            for llave_diario in reporte_data_consolidado[llave_mes]:
                                if llave_diario != 'nombre_mes':
                                    if llave_diario != 'total_debe':
                                        if llave_diario != 'total_haber':
                                            hoja.write(fila, 0, self._xlsx_value(reporte_data_consolidado[llave_mes][llave_diario]['diario']))
                                            fila += 1
                                            for m_a in reporte_data_consolidado[llave_mes][llave_diario]['movimientos_agrupados']:
                                                mov = reporte_data_consolidado[llave_mes][llave_diario]['movimientos_agrupados'][m_a]
                                                hoja.write(fila, 0, self._xlsx_value(mov['codigo']))
                                                hoja.write(fila, 1, self._xlsx_value(mov['nombre_cuenta']))
                                                hoja.write(fila, 2, reporte_data_consolidado[llave_mes][llave_diario]['movimientos_agrupados'][m_a]['debe'], formato_moneda)
                                                hoja.write(fila, 3, reporte_data_consolidado[llave_mes][llave_diario]['movimientos_agrupados'][m_a]['haber'], formato_moneda)
                                                fila += 1

                                            hoja.write(fila, 0, '')
                                            hoja.write(fila, 1, 'Total diario')
                                            hoja.write(fila, 2, reporte_data_consolidado[llave_mes][llave_diario]['total_debe'], formato_moneda)
                                            hoja.write(fila, 3, reporte_data_consolidado[llave_mes][llave_diario]['total_haber'], formato_moneda)

                                            fila += 1

                            
                            hoja.write(fila, 0, '')
                            hoja.write(fila, 1, 'Total de '+ reporte_data_consolidado[llave_mes]['nombre_mes'])
                            hoja.write(fila, 2, reporte_data_consolidado[llave_mes]['total_debe'], formato_moneda)
                            hoja.write(fila, 3, reporte_data_consolidado[llave_mes]['total_haber'], formato_moneda)
                            fila += 1

                hoja.write(fila, 0, '')
                hoja.write(fila, 1, 'Total general')
                hoja.write(fila, 2, reporte_data_consolidado['total_debe'], formato_moneda)
                hoja.write(fila, 3, reporte_data_consolidado['total_haber'], formato_moneda)
                            
                                            

            
            libro.close()
            datos = base64.b64encode(f.getvalue())
            self.write({'archivo':datos, 'name':'libro_diario.xlsx'})

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account_gt.libro_diario.wizard',
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
