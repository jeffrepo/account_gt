from odoo import api, fields, models, tools, _
import ast
import copy
import datetime
import io
import json
import logging
import markupsafe
from collections import defaultdict
from math import copysign, inf

from odoo.exceptions import ValidationError
from odoo.exceptions import UserError, AccessError
from odoo.addons.web.controllers.main import clean_action
from odoo.exceptions import RedirectWarning
from odoo.osv import expression
from odoo.tools import config, date_utils, get_lang
from odoo.tools.misc import formatLang, format_date
from odoo.tools.misc import xlsxwriter

import logging

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    def get_xlsx(self, options, response=None):
        res = super(AccountReport, self).get_xlsx(options, response)
        logging.warning(options)
        logging.warning(response)
        logging.warning(res)
        if self._get_report_name()[:31] == 'Libro mayor':
            logging.warning('si es ledger')
            return self.get_new_xslx(options, response)
        else:
            return res

    def _get_html_render_values(self, options, report_manager):
        res = super(AccountReport, self)._get_html_render_values(options, report_manager)
        logging.warning('-----------------------_get_html_render_values')
        logging.warning(res)
        date_fom = False
        date_to = False
        if 'date' in options and ('date_from' and 'date_to' in options['date']):
            date_from = datetime.datetime.strptime(options['date']['date_from'], "%Y-%m-%d").strftime("%d/%m/%Y")
            date_to = datetime.datetime.strptime(options['date']['date_to'], "%Y-%m-%d").strftime("%d/%m/%Y")
        res['report']['date_from_gt'] = date_from
        res['report']['date_to_gt'] = date_to
        res['report']['nit_gt'] = self.env.company.vat
        return res

    def get_new_xslx(self, options, reponse):
        self = self.with_context(self._set_context(options))
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {
            'in_memory': True,
            'strings_to_formulas': False,
        })
        logging.warning('get_new_xslx imporgesa')

        date_fom = False
        date_to = False
        if 'date' in options and ('date_from' and 'date_to' in options['date']):
            date_from = datetime.datetime.strptime(options['date']['date_from'], "%Y-%m-%d").strftime("%d/%m/%Y")
            date_to = datetime.datetime.strptime(options['date']['date_to'], "%Y-%m-%d").strftime("%d/%m/%Y")
        sheet = workbook.add_worksheet(self._get_report_name()[:31])

        date_default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2, 'num_format': 'yyyy-mm-dd'})
        date_default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'num_format': 'yyyy-mm-dd'})
        default_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 6, 'font_color': '#666666'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 13, 'bottom': 1, 'font_color': '#666666'})
        level_2_col1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_2_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666'})
        level_3_col1_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666', 'indent': 2})
        level_3_col1_total_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 12, 'font_color': '#666666', 'indent': 1})
        level_3_style = workbook.add_format({'font_name': 'Arial', 'font_size': 12, 'font_color': '#666666'})

        #Set the first column width to 50
        sheet.set_column(0, 0, 50)

        merge_format = workbook.add_format({
            'bold': 1,

            'align': 'center',
            'valign': 'vcenter',
            })
        sheet.merge_range('A1:H1', self.env.company.name,merge_format)
        sheet.merge_range('A2:H2', "NIT: " +  str(self.env.company.vat),merge_format)
        sheet.merge_range('A3:H3', "LIBRO MAYOR",merge_format)
        sheet.merge_range('A4:H4', "PERIODO DEL "+str(date_from)+" AL " +str(date_to),merge_format)
        sheet.merge_range('A5:H5', "CIFRAS EXPRESADAS EN QUETZALES",merge_format)

        y_offset = 6
        headers, lines = self.with_context(no_format=True, print_mode=True, prefetch_fields=False)._get_table(options)

        # Add headers.
        logging.warning('headers')
        logging.warning(headers)
        for header in headers:
            x_offset = 0
            for column in header:
                column_name_formated = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
                colspan = column.get('colspan', 1)
                logging.warning('COLUMNS')
                logging.warning(column)
                if column['name'] == '':
                    logging.warning('SI ES VACIO')
                    column['name'] = 'CUENTA'
                if colspan == 1:
                    if column_name_formated == '':
                        column_name_formated = "CUENTA"
                    if column_name_formated == 'Comunicación':
                        column_name_formated = "Descripcion"
                    if column_name_formated == 'Balance':
                        column_name_formated = "Saldo FInal"
                    sheet.write(y_offset, x_offset, column_name_formated, title_style)
                else:
                    sheet.merge_range(y_offset, x_offset, y_offset, x_offset + colspan - 1, column_name_formated, title_style)
                x_offset += colspan
            y_offset += 1

        if options.get('hierarchy'):
            lines = self.with_context(no_format=True)._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)

        # Add lines.
        for y in range(0, len(lines)):
            level = lines[y].get('level')
            if lines[y].get('caret_options'):
                style = level_3_style
                col1_style = level_3_col1_style
            elif level == 0:
                y_offset += 1
                style = level_0_style
                col1_style = style
            elif level == 1:
                style = level_1_style
                col1_style = style
            elif level == 2:
                style = level_2_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_2_col1_total_style or level_2_col1_style
            elif level == 3:
                style = level_3_style
                col1_style = 'total' in lines[y].get('class', '').split(' ') and level_3_col1_total_style or level_3_col1_style
            else:
                style = default_style
                col1_style = default_col1_style

            #write the first column, with a specific style to manage the indentation
            cell_type, cell_value = self._get_cell_type_value(lines[y])
            if cell_type == 'date':
                sheet.write_datetime(y + y_offset, 0, cell_value, date_default_col1_style)
            else:
                sheet.write(y + y_offset, 0, cell_value, col1_style)

            #write all the remaining cells
            for x in range(1, len(lines[y]['columns']) + 1):
                cell_type, cell_value = self._get_cell_type_value(lines[y]['columns'][x - 1])
                if cell_type == 'date':
                    sheet.write_datetime(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, date_default_style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, cell_value, style)

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()
        return generated_file
