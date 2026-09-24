"""Currency regressions with ORM doubles; run with unittest discover -s tests.

These tests exercise the actual report and wizard methods without an Odoo
database. Full ORM and QWeb integration must also be checked in Odoo 19.
"""

from datetime import date
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def load_models():
    def depends(*args):
        return lambda method: method

    odoo = SimpleNamespace(
        api=SimpleNamespace(model=lambda method: method,
                            depends=depends, depends_context=depends),
        models=SimpleNamespace(AbstractModel=object, TransientModel=object),
        fields=SimpleNamespace(
            Date=Mock(), Monetary=Mock(),
            Many2one=lambda *args, **kwargs: SimpleNamespace(**kwargs),
        ),
    )
    with patch.dict(sys.modules, {
        'odoo': odoo,
        'odoo.exceptions': SimpleNamespace(UserError=Exception),
    }):
        report = runpy.run_path(str(ROOT / 'report/libro_conciliacion_bancaria_report.py'))
        wizard = runpy.run_path(str(ROOT / 'wizard/libro_conciliacion_bancaria_wizard.py'))
    return report['LibroConciliacionBancaria'], wizard['LibroConciliacionBancariaWizard']


Report, Wizard = load_models()


class TestReconciliationCurrency(unittest.TestCase):
    def setUp(self):
        self.mxn = SimpleNamespace(id=1, name='MXN', _convert=Mock(return_value=100.0))
        self.usd = SimpleNamespace(id=2, name='USD')
        self.gtq = SimpleNamespace(id=3, name='GTQ')
        currencies = {currency.id: currency for currency in (self.mxn, self.usd, self.gtq)}
        self.company = SimpleNamespace(id=2, currency_id=self.mxn)
        self.account = SimpleNamespace(currency_id=False)
        self.lines = SimpleNamespace(search=Mock())
        self.docs = object()
        self.models = {
            'account.account': SimpleNamespace(browse=Mock(return_value=self.account)),
            'account.move.line': self.lines,
            'res.currency': SimpleNamespace(browse=Mock(side_effect=currencies.__getitem__)),
            'account_gt.libro_conciliacion_bancaria.wizard': SimpleNamespace(
                browse=Mock(return_value=self.docs),
            ),
        }

        class Environment(dict):
            pass

        self.env = Environment(self.models)
        self.env.company = self.company
        # The user's default company is deliberately different from the active one.
        self.env.user = SimpleNamespace(company_id=SimpleNamespace(currency_id=self.gtq))
        self.env.context = {
            'active_model': 'account_gt.libro_conciliacion_bancaria.wizard',
            'active_ids': [7],
            'allowed_company_ids': [2, 1],
        }
        self.report = Report()
        self.report.env = self.env
        self.report.ids = []
        self.data = {
            'cuenta_id': [10, 'Banco'],
            'fecha_inicio': '2026-09-01',
            'fecha_fin': '2026-09-30',
            'saldo': 125.0,
        }
        self.log_patch = patch('logging.warn')
        self.log_patch.start()
        self.addCleanup(self.log_patch.stop)

    def line(self, debit=0.0, credit=0.0, amount_currency=0.0, currency=None):
        return SimpleNamespace(
            debit=debit, credit=credit, balance=debit - credit,
            amount_currency=amount_currency, currency_id=currency or self.usd,
            company_currency_id=self.mxn, company_id=self.company,
            date=date(2026, 9, 10), move_id=SimpleNamespace(name='BNK/0001'),
            partner_id=False, ref='Transferencia',
        )

    def test_active_company_currency_overrides_user_default(self):
        values = self.report._get_report_values([], {'form': self.data})
        self.assertIs(values['currency'], self.mxn)
        self.assertIs(values['docs'], self.docs)
        self.lines.search.return_value = [self.line(debit=2000, amount_currency=100)]
        result = values['documentos_conciliados'](self.data)
        self.assertEqual(result['documentos'][0]['debito'], 2000)
        self.assertEqual(result['saldo_conciliado'], 2000)
        self.mxn._convert.assert_not_called()

    def test_account_currency_overrides_company_currency(self):
        self.account.currency_id = self.usd
        values = self.report._get_report_values([], {'form': self.data})
        self.assertIs(values['currency'], self.usd)

    def test_wizard_currency_is_editable_and_persisted(self):
        self.assertFalse(Wizard.currency_id.readonly)
        self.assertTrue(Wizard.currency_id.store)
        self.assertTrue(Wizard.currency_id.required)

    def test_selected_currency_overrides_account_and_company(self):
        self.account.currency_id = self.gtq
        for selected in ([2, 'USD'], (2, 'USD'), 2):
            with self.subTest(selected=selected):
                self.data['currency_id'] = selected
                values = self.report._get_report_values([], {'form': self.data})
                self.assertIs(values['currency'], self.usd)
                self.assertIs(self.account.currency_id, self.gtq)

    def test_selected_company_currency_overrides_foreign_account(self):
        self.account.currency_id = self.usd
        self.data['currency_id'] = [1, 'MXN']
        self.lines.search.return_value = [self.line(debit=2000, amount_currency=100)]
        values = self.report._get_report_values([], {'form': self.data})
        self.assertIs(values['currency'], self.mxn)
        cleared = values['documentos_conciliados'](self.data)
        self.assertEqual(cleared['documentos'][0]['debito'], 2000)
        self.assertEqual(cleared['saldo_conciliado'], 2000)
        self.mxn._convert.assert_not_called()

    def test_selected_foreign_currency_applies_to_every_section(self):
        # The account remains in company currency; the wizard selects USD.
        self.account.currency_id = self.mxn
        self.data['currency_id'] = [2, 'USD']
        self.data['saldo'] = 110.0
        opening_line = self.line(debit=1000, amount_currency=1000, currency=self.mxn)
        opening_line.date = date(2026, 8, 31)
        debit_line = self.line(debit=2100, amount_currency=100, currency=self.usd)
        credit_line = self.line(credit=800, amount_currency=-800, currency=self.mxn)
        credit_line.date = date(2026, 9, 15)
        pending_line = self.line(credit=420, amount_currency=-420, currency=self.mxn)
        pending_line.date = date(2026, 9, 20)
        self.lines.search.side_effect = [
            [opening_line], [debit_line, credit_line], [pending_line],
        ]
        self.mxn._convert.side_effect = [50.0, -40.0, -20.0]
        values = self.report._get_report_values([], {'form': self.data})
        self.assertIs(values['currency'], self.usd)
        opening = values['saldo_inicial'](self.data)
        cleared = values['documentos_conciliados'](self.data)
        pending = values['documentos_circulacion'](self.data)
        self.assertEqual(opening, 50)
        self.assertEqual(cleared['documentos'][0]['debito'], 100)
        self.assertEqual(cleared['documentos'][1]['credito'], 40)
        self.assertEqual(cleared['saldo_conciliado'], 60)
        self.assertEqual(pending[0]['credito'], 20)
        self.assertEqual(opening + cleared['saldo_conciliado'] - self.data['saldo'], 0)
        self.assertEqual([call.args for call in self.mxn._convert.call_args_list], [
            (1000, self.usd, self.company, date(2026, 8, 31)),
            (-800, self.usd, self.company, date(2026, 9, 15)),
            (-420, self.usd, self.company, date(2026, 9, 20)),
        ])
        self.assertIs(self.account.currency_id, self.mxn)

    def test_print_report_preserves_selected_currency_in_payload(self):
        self.data['currency_id'] = [2, 'USD']
        wizard = Wizard()
        wizard.read = Mock(return_value=[self.data.copy()])
        action = SimpleNamespace(report_action=Mock(return_value={'type': 'ir.actions.report'}))
        wizard.env = SimpleNamespace(ref=Mock(return_value=action))
        self.assertEqual(wizard.print_report(), {'type': 'ir.actions.report'})
        payload = action.report_action.call_args.kwargs['data']['form']
        self.assertEqual(payload['currency_id'], [2, 'USD'])
        self.assertIs(self.report._get_report_currency(payload), self.usd)

    def test_company_currency_keeps_debit_and_credit(self):
        self.assertEqual(self.report._get_line_amounts(
            self.line(debit=2000, amount_currency=100), self.mxn), (2000, 0))
        self.assertEqual(self.report._get_line_amounts(
            self.line(credit=500, amount_currency=-25), self.mxn), (0, 500))

    def test_foreign_debit_and_credit_use_recorded_amount(self):
        self.assertEqual(self.report._get_line_amounts(
            self.line(debit=2000, amount_currency=100), self.usd), (100, 0))
        self.assertEqual(self.report._get_line_amounts(
            self.line(credit=500, amount_currency=-25), self.usd), (0, 25))
        self.mxn._convert.assert_not_called()

    def test_exchange_difference_does_not_inflate_foreign_balance(self):
        self.assertEqual(self.report._get_line_amounts(
            self.line(debit=50, amount_currency=0), self.usd), (0, 0))
        self.mxn._convert.assert_not_called()

    def test_historical_other_currency_uses_line_date_and_company(self):
        line = self.line(debit=2000, amount_currency=800, currency=self.gtq)
        self.assertEqual(self.report._get_line_amounts(line, self.usd), (100, 0))
        self.mxn._convert.assert_called_once_with(2000, self.usd, self.company, line.date)

    def test_all_report_sections_use_account_currency_and_active_company(self):
        self.account.currency_id = self.usd
        self.lines.search.side_effect = [
            [self.line(debit=1000, amount_currency=50)],
            [self.line(debit=2000, amount_currency=100),
             self.line(credit=500, amount_currency=-25),
             self.line(debit=50, amount_currency=0)],
            [self.line(credit=400, amount_currency=-20)],
        ]
        opening = self.report.saldo_inicial(self.data)
        cleared = self.report.documentos_conciliados(self.data)
        pending = self.report.documentos_circulacion(self.data)
        self.assertEqual(opening, 50)
        self.assertEqual(cleared['saldo_conciliado'], 75)
        self.assertEqual(cleared['documentos'][0]['debito'], 100)
        self.assertEqual(cleared['documentos'][1]['credito'], 25)
        self.assertEqual(pending[0]['credito'], 20)
        self.assertEqual(opening + cleared['saldo_conciliado'] - self.data['saldo'], 0)
        calls = self.lines.search.call_args_list
        for call in calls:
            self.assertIn(('company_id', '=', self.company.id), call.args[0])
            self.assertIn(('account_id', '=', 10), call.args[0])
        self.assertIn(('date', '<', '2026-09-01'), calls[0].args[0])
        self.assertIn(('conciliacion_bancaria', '=', True), calls[0].args[0])
        for call in calls[1:]:
            self.assertIn(('date', '>=', '2026-09-01'), call.args[0])
            self.assertIn(('date', '<=', '2026-09-30'), call.args[0])
        self.assertIn(('conciliacion_bancaria', '=', True), calls[1].args[0])
        self.assertIn(('conciliacion_bancaria', '=', False), calls[2].args[0])

    def test_empty_report_returns_zero_balances(self):
        self.lines.search.return_value = []
        self.assertEqual(self.report.saldo_inicial(self.data), 0)
        self.assertEqual(self.report.documentos_conciliados(self.data),
                         {'documentos': [], 'saldo_conciliado': 0})
        self.assertEqual(self.report.documentos_circulacion(self.data), [])

    def test_wizard_currency_matches_report_currency(self):
        class Wizards(list):
            pass

        wizard = SimpleNamespace(cuenta_id=self.account)
        records = Wizards([wizard])
        records.env = self.env
        for currency in (False, self.usd, self.mxn):
            with self.subTest(currency=currency):
                self.account.currency_id = currency
                Wizard._compute_currency_id(records)
                self.assertIs(wizard.currency_id, self.report._get_report_currency(self.data))

    def test_template_uses_report_currency_for_every_amount(self):
        root = ET.parse(ROOT / 'report/reporte_libro_conciliacion_bancaria_views.xml')
        amounts = [node for node in root.iter()
                   if 'monetary' in node.get('t-options', '')]
        self.assertEqual(len(amounts), 8)
        for node in amounts:
            self.assertEqual(node.get('t-options'),
                             "{'widget': 'monetary', 'display_currency': currency}")
        self.assertTrue(any(node.get('t-esc') == 'currency.name' for node in root.iter()))


if __name__ == '__main__':
    unittest.main()
