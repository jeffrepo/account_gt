"""Exercise the liquidation method without an Odoo database.

The move double checks the debit/credit invariant at creation. Full posting
and reconciliation still need validation in an Odoo 19 database.
"""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class UserError(Exception):
    pass


def load_model():
    odoo = SimpleNamespace(
        api=SimpleNamespace(model_create_multi=lambda method: method),
        fields=Mock(), models=SimpleNamespace(Model=object), tools=Mock(),
        _=lambda message: message,
    )
    with patch.dict(sys.modules, {
        'odoo': odoo,
        'odoo.exceptions': SimpleNamespace(
            UserError=UserError, ValidationError=Exception, AccessError=Exception,
        ),
    }):
        return runpy.run_path(str(
            Path(__file__).resolve().parents[1] / 'models/account_gt.py'
        ))['Liquidacion']


Liquidacion = load_model()


class Currency:
    def __init__(self, name, currency_id, precision='0.01'):
        self.name = name
        self.id = currency_id
        self.precision = Decimal(precision)

    def round(self, amount):
        return float(Decimal(str(amount)).quantize(
            self.precision, rounding=ROUND_HALF_UP,
        ))

    def is_zero(self, amount):
        return self.round(amount) == 0


class Line(SimpleNamespace):
    def __or__(self, other):
        return SimpleNamespace(reconcile=Mock())


class Liquidations(list):
    def write(self, values):
        for record in self:
            record.__dict__.update(values)


class EmptyAccount:
    id = False

    def __bool__(self):
        return False


class TestLiquidacionBalance(unittest.TestCase):
    def setUp(self):
        self.gtq = Currency('GTQ', 1)
        self.usd = Currency('USD', 2)
        self.eur = Currency('EUR', 3)
        self.payable = SimpleNamespace(
            id=10, account_type='liability_payable', reconcile=True,
        )
        self.move_model = SimpleNamespace(create=Mock(side_effect=self.create_move))
        self.company_currency = self.gtq
        self.log_patch = patch('logging.warning')
        self.log_patch.start()
        self.addCleanup(self.log_patch.stop)

    def create_move(self, values):
        amounts = [command[2] for command in values['line_ids']]
        imbalance = sum(line['debit'] - line['credit'] for line in amounts)
        if not self.company_currency.is_zero(imbalance):
            raise AssertionError('Asiento no balanceado: %s' % imbalance)
        self.assertTrue(all(line['account_id'] for line in amounts))
        self.assertTrue(all(line['debit'] >= 0 and line['credit'] >= 0 for line in amounts))
        return SimpleNamespace(
            id=99, line_ids=[Line(**line) for line in amounts], action_post=Mock(),
        )

    def liquidations(self, invoice=100.0, payment=100.0, adjustment=False,
                     invoice_currency=None, payment_currency=None):
        def line(name, debit, credit):
            return Line(
                name=name, debit=debit, credit=credit, account_id=self.payable,
                partner_id=SimpleNamespace(id=7), reconciled=False,
            )

        invoice_amounts = invoice if isinstance(invoice, (list, tuple)) else [invoice]
        record = SimpleNamespace(
            name='APL00050', fecha='2026-01-31', state='borrador',
            company_id=SimpleNamespace(currency_id=self.company_currency),
            diario_id=SimpleNamespace(id=4),
            cuenta_id=SimpleNamespace(id=20) if adjustment else EmptyAccount(),
            factura_relacion_ids=[SimpleNamespace(
                name='COM/%03d' % index, currency_id=invoice_currency or self.gtq,
                line_ids=[line('Factura', 0.0, amount)],
            ) for index, amount in enumerate(invoice_amounts, start=1)],
            pago_relacion_ids=[SimpleNamespace(
                name='PAGO/001', currency_id=payment_currency or self.gtq,
                move_id=SimpleNamespace(line_ids=[line('Pago', payment, 0.0)]),
            )],
        )
        records = Liquidations([record])
        records.env = {'account.move': self.move_model}
        return records

    def values(self):
        return self.move_model.create.call_args.args[0]['line_ids']

    def test_balanced_gtq_needs_no_adjustment_account(self):
        records = self.liquidations()
        self.assertTrue(Liquidacion.conciliar_liquidacion(records))
        self.assertEqual(len(self.values()), 2)
        self.assertEqual(records[0].state, 'conciliado')

    def test_gtq_short_payment_balances_with_credit(self):
        Liquidacion.conciliar_liquidacion(self.liquidations(payment=90, adjustment=True))
        adjustment = self.values()[-1][2]
        self.assertEqual((adjustment['debit'], adjustment['credit']), (0, 10))
        self.assertEqual(adjustment['account_id'], 20)

    def test_gtq_overpayment_balances_with_debit(self):
        Liquidacion.conciliar_liquidacion(self.liquidations(payment=110, adjustment=True))
        adjustment = self.values()[-1][2]
        self.assertEqual((adjustment['debit'], adjustment['credit']), (10, 0))

    def test_same_foreign_currency_and_mixed_currencies(self):
        for invoice_currency, payment_currency in (
            (self.eur, self.eur), (self.usd, self.usd), (self.gtq, self.usd),
        ):
            with self.subTest(invoice=invoice_currency.name, payment=payment_currency.name):
                Liquidacion.conciliar_liquidacion(self.liquidations(
                    payment=90, adjustment=True, invoice_currency=invoice_currency,
                    payment_currency=payment_currency,
                ))
                self.assertEqual(len(self.values()), 3)
                self.assertEqual(self.values()[-1][2]['credit'], 10)

    def test_missing_account_reports_difference_before_creating_move(self):
        for currency in (self.gtq, self.usd):
            with self.subTest(currency=currency.name):
                with self.assertRaisesRegex(UserError, 'APL00050.*10.*GTQ'):
                    Liquidacion.conciliar_liquidacion(self.liquidations(
                        payment=90, invoice_currency=currency, payment_currency=currency,
                    ))
                self.move_model.create.assert_not_called()

    def test_company_precision_is_used_instead_of_two_decimals(self):
        self.company_currency = Currency('TND', 4, '0.001')
        Liquidacion.conciliar_liquidacion(self.liquidations(
            payment=99.999, adjustment=True,
            invoice_currency=self.usd, payment_currency=self.usd,
        ))
        self.assertEqual(self.values()[-1][2]['credit'], 0.001)

    def test_float_noise_does_not_require_adjustment_account(self):
        Liquidacion.conciliar_liquidacion(self.liquidations(
            invoice=0.1 + 0.2, payment=0.3,
            invoice_currency=self.gtq, payment_currency=self.usd,
        ))
        self.assertEqual(len(self.values()), 2)

    def test_balanced_many_gtq_invoices_and_usd_payment(self):
        # The failing liquidation has 81 invoices totaling 11292.83 GTQ.
        # Binary floats leave 1.8189894035458565e-12 after subtracting the
        # payment. That must not create a zero-value line without an account.
        invoices = [
            27.60, 120.75, 100.00, 3126.00, 250.00, 220.47, 385.22, 100.00,
            50.00, 92.00, 256.45, 36.00, 299.90, 110.00, 238.00, 104.00,
            48.74, 321.00, 67.00, 5.69, 75.00, 196.00, 79.00, 239.80,
            59.00, 56.50, 120.00, 46.08, 20.00, 330.00, 41.99, 29.00,
            233.00, 233.00, 8.00, 178.20, 16.00, 76.00, 450.00, 163.37,
            161.20, 243.95, 315.38, 1320.00, 10.00, 10.00, 5.00, 10.00,
            10.00, 10.00, 10.00, 10.00, 5.00, 15.00, 8.00, 10.00,
            10.00, 5.00, 30.00, 10.00, 5.00, 5.00, 15.00, 10.00,
            15.00, 10.00, 30.00, 5.00, 10.00, 15.00, 15.00, 5.00,
            10.00, 5.00, 5.00, 15.00, 10.00, 10.00, 10.00, 214.54, 56.00,
        ]
        self.assertNotEqual(sum(invoices) - 11292.83, 0.0)
        self.assertTrue(self.gtq.is_zero(sum(invoices) - 11292.83))
        records = self.liquidations(
            invoice=invoices, payment=11292.83,
            invoice_currency=self.gtq, payment_currency=self.usd,
        )
        Liquidacion.conciliar_liquidacion(records)
        self.assertEqual(len(self.values()), 82)
        self.assertFalse(any(
            command[2]['name'].startswith('Diferencia de') for command in self.values()
        ))
        self.assertEqual(records[0].state, 'conciliado')

    def test_payment_without_move_is_rejected(self):
        records = self.liquidations()
        records[0].pago_relacion_ids[0].move_id = False
        with self.assertRaisesRegex(UserError, 'no tiene asiento contable'):
            Liquidacion.conciliar_liquidacion(records)
        self.move_model.create.assert_not_called()


if __name__ == '__main__':
    unittest.main()
