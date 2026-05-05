# -*- encoding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import UserError
import logging

class LibroDiario(models.AbstractModel):
    _name = 'report.account_gt.reporte_libro_diario'
    
    def _get_data(self, fecha_inicio, fecha_fin, diario_ids, consolidado, movimientos_destino):
        if consolidado == False:
            data = {}
            estados = []
            if movimientos_destino == 'posted':
                estados = ("posted")
            else:
                estados = ('draft','posted','cancel')
            diario_str = ','.join([str(x) for x in diario_ids])
            if movimientos_destino == 'posted':
                self.env.cr.execute(
                    'SELECT am.move_id,am.date as fecha, am.move_name as nombre_movimiento, a.code_store as codigo, a.name as nombre_cuenta, aj.name as nombre_diario, am.journal_id as diario_id, am.name as descripcion,sum(debit) as debe, sum(credit) as haber' \
                        ' from account_move_line am join account_account a on(am.account_id = a.id) join account_journal aj on(aj.id = am.journal_id) join account_move m on (m.id = am.move_id)' \
                        ' where am.date >= %s and am.date <= %s and m.state = %s and am.journal_id in ('+ diario_str + ') '\
                        ' GROUP BY am.move_id, am.name, aj.name, a.code_store, a.name, am.date, am.move_name, am.journal_id ORDER BY aj.name, a.code_store, am.date', (fecha_inicio,fecha_fin, 'posted'))
            else:
                self.env.cr.execute(
                    'SELECT am.move_id,am.date as fecha, am.move_name as nombre_movimiento, a.code_store as codigo, a.name as nombre_cuenta, aj.name as nombre_diario, am.journal_id as diario_id, am.name as descripcion,sum(debit) as debe, sum(credit) as haber' \
                        ' from account_move_line am join account_account a on(am.account_id = a.id) join account_journal aj on(aj.id = am.journal_id) join account_move m on (m.id = am.move_id)' \
                        ' where am.date >= %s and am.date <= %s and m.state in %s and am.journal_id in ('+ diario_str + ') '\
                        ' GROUP BY am.move_id, am.name, aj.name, a.code_store, a.name, am.date, am.move_name, am.journal_id ORDER BY aj.name, a.code_store, am.date', (fecha_inicio,fecha_fin, estados))                
            for m in self.env.cr.dictfetchall():
                if m['diario_id'] not in data :
                    data[m['diario_id']] = {'diario': m['nombre_diario'], 'total_debe': 0, 'total_haber': 0 ,'asientos': {}}

                if m['move_id'] not in data[ m['diario_id']  ]['asientos']:
                    data[ m['diario_id']  ]['asientos'][ m['move_id'] ] = {'total_debe': 0, 'total_haber': 0, 'movimientos': []}

                if m['move_id'] in data[ m['diario_id']  ]['asientos']:
                    data[m['diario_id']]['total_debe'] += m['debe']
                    data[m['diario_id']]['total_haber'] += m['haber']
                    data[ m['diario_id']  ]['asientos'][ m['move_id']  ]['total_debe'] += m['debe']
                    data[ m['diario_id']  ]['asientos'][ m['move_id']  ]['total_haber'] += m['haber']
                    data[ m['diario_id']  ]['asientos'][ m['move_id']  ]['movimientos'].append({'fecha': m['fecha'], 'nombre_movimiento': m['nombre_movimiento'],'nombre_cuenta': m['nombre_cuenta'],'descripcion': m['descripcion'],'codigo': m['codigo'], 'nombre_cuenta': m['nombre_cuenta'], 'debe': m['debe'], 'haber': m['haber'] })

        else:
            data = False
        return data

    def _get_data_consolidado(self, fecha_inicio, fecha_fin, diario_ids, consolidado, movimientos_destino):

        if consolidado == True:
            data = {}
            estados = []
            if movimientos_destino == 'posted':
                estados = ("posted")
            else:
                estados = ('draft','posted','cancel')
                
            diario_str = ','.join([str(x) for x in diario_ids])
            estado_str = ','.join([str(x) for x in estados])
            if movimientos_destino == 'posted':
                self.env.cr.execute(
                    'SELECT am.account_id as cuenta_movimiento_id, am.move_id,am.date as fecha, am.move_name as nombre_movimiento, a.code_store as codigo, a.name as nombre_cuenta, aj.name as nombre_diario, am.journal_id as diario_id, am.name as descripcion,sum(debit) as debe, sum(credit) as haber' \
                        ' from account_move_line am join account_account a on(am.account_id = a.id) join account_journal aj on(aj.id = am.journal_id) join account_move m on (m.id = am.move_id)' \
                        ' where am.date >= %s and am.date <= %s and m.state = %s and am.journal_id in ('+ diario_str + ') '\
                        ' GROUP BY am.account_id, am.move_id, am.name, aj.name, a.code_store, a.name, am.date, am.move_name, am.journal_id ORDER BY aj.name, a.code_store, am.date', (fecha_inicio,fecha_fin, 'posted'))
            else:
                self.env.cr.execute(
                    'SELECT am.account_id as cuenta_movimiento_id, am.move_id,am.date as fecha, am.move_name as nombre_movimiento, a.code_store as codigo, a.name as nombre_cuenta, aj.name as nombre_diario, am.journal_id as diario_id, am.name as descripcion,sum(debit) as debe, sum(credit) as haber' \
                        ' from account_move_line am join account_account a on(am.account_id = a.id) join account_journal aj on(aj.id = am.journal_id) join account_move m on (m.id = am.move_id)' \
                        ' where am.date >= %s and am.date <= %s and m.state in %s and am.journal_id in ('+ diario_str + ') '\
                        ' GROUP BY am.account_id, am.move_id, am.name, aj.name, a.code_store, a.name, am.date, am.move_name, am.journal_id ORDER BY aj.name, a.code_store, am.date', (fecha_inicio,fecha_fin, estados))                
            for m in self.env.cr.dictfetchall():
                mes = m['fecha'].strftime('%m')
                nombre_mes = None
                nombre_meses = {
                    "01":'Enero',
                    "02":'Febrero',
                    "03":'Marzo',
                    "04":'Abril',
                    "05":'Mayo',
                    "06":'Junio',
                    "07":'Julio',
                    "08":'Agosto',
                    "09":'Septiembre',
                    "10":'Octubre',
                    "11":'Noviembre',
                    "12":'Diciembre'
                }

                if mes in nombre_meses:
                    nombre_mes = nombre_meses[mes]

                if mes not in data and consolidado == True:
                    data[mes]={
                    }
                if mes in data:
                    data[mes]['nombre_mes']=nombre_mes
                if consolidado == True and mes in data and m['diario_id'] not in data[mes]:
                    data[mes][m['diario_id']] = {'diario': m['nombre_diario'], 'total_debe': 0, 'total_haber': 0 ,'asientos': {}, 'movimientos_agrupados':{}}

                if mes in data and m['diario_id'] in data[mes] and m['move_id'] not in data[mes][m['diario_id']]['asientos']:
                    data[mes][m['diario_id']]['asientos'][m['move_id']]={'total_debe': 0, 'total_haber': 0, 'movimientos': {}}


                if consolidado == True and mes in data and m['diario_id'] in data[mes] and m['move_id'] in data[mes][m['diario_id']]['asientos']:
                    if m['cuenta_movimiento_id'] not in data[mes][m['diario_id']]['movimientos_agrupados']:
                        data[mes][m['diario_id']]['movimientos_agrupados'][m['cuenta_movimiento_id']]={
                        'codigo':m['codigo'],
                        'nombre_cuenta':m['nombre_cuenta'],
                        'debe':0,
                        'haber':0
                        }

                    data[mes][m['diario_id']]['movimientos_agrupados'][m['cuenta_movimiento_id']]['debe']+=round(m['debe'],2)
                    data[mes][m['diario_id']]['movimientos_agrupados'][m['cuenta_movimiento_id']]['haber']+=round(m['haber'],2)

            total_general_debe = 0
            total_general_haber = 0
            for x_mes in data:
                mes_debe = 0
                mes_haber = 0
                for x_diario in data[x_mes]:
                    if x_diario != 'nombre_mes':
                        mov_agrupado_debe = 0
                        mov_agrupado_haber = 0
                        for m_a in data[x_mes][x_diario]['movimientos_agrupados']:
                            mov_agrupado_debe+=round(data[x_mes][x_diario]['movimientos_agrupados'][m_a]['debe'],2)
                            mov_agrupado_haber+=round(data[x_mes][x_diario]['movimientos_agrupados'][m_a]['haber'],2)

                        data[x_mes][x_diario]['total_debe']=round(mov_agrupado_debe,2)
                        data[x_mes][x_diario]['total_haber']=round(mov_agrupado_haber,2)
                        mes_debe += data[x_mes][x_diario]['total_debe']
                        mes_haber += data[x_mes][x_diario]['total_haber']
                data[x_mes]['total_debe'] = mes_debe
                data[x_mes]['total_haber'] = mes_haber
                total_general_debe += data[x_mes]['total_debe']
                total_general_haber += data[x_mes]['total_haber']
            data['total_debe']=total_general_debe
            data['total_haber']=total_general_haber
        else:
            data = False

        return data

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_ids', []))

        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'company': self.env.company,
            'get_data': self._get_data,
            'get_data_consolidado': self._get_data_consolidado,
            'company': self.env.company,
        }

