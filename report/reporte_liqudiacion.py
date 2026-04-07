# -*- coding: utf-8 -*-
from odoo import api, models, fields
import logging, datetime

class ReporteLiquidacion(models.AbstractModel):
    _name = 'report.account_gt.liquidacion'

    def a_letras(self,monto):
        letras = numero_a_moneda(monto)
        return letras
        
    def convertir_fecha_hora(self, fecha_hora):
    	fecha = datetime.datetime.strptime(str(fecha_hora), '%Y-%m-%d %H:%M:%S').date().strftime('%Y-%m-%d')
    	hora = datetime.datetime.strftime(fields.Datetime.context_timestamp(self, datetime.datetime.now()), "%H:%M:%S")
    	logging.warning("funcion")
    	informacion = {
    		'fecha': fecha,
    		'hora': hora,
    	}
    	return informacion
    	
    def convertir_fecha_hora_ms(self, fecha_hora):
    	fecha = datetime.datetime.strptime(str(fecha_hora), '%Y-%m-%d %H:%M:%S.%f').date().strftime('%Y-%m-%d')
    	hora = datetime.datetime.strftime(fields.Datetime.context_timestamp(self, datetime.datetime.now()), "%H:%M:%S")
    	logging.warning("funcion2")
    	informacion = {
    		'fecha': fecha,
    		'hora': hora,
    	}
    	return informacion
    	

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['account_gt.liquidacion'].browse(docids)

        return {
            'convertir_fecha_hora': self.convertir_fecha_hora,
            'convertir_fecha_hora_ms': self.convertir_fecha_hora_ms,
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': docs,
        }
        
