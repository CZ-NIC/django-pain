#
# Copyright (C) 2018-2019  CZ.NIC, z. s. p. o.
#
# This file is part of FRED.
#
# FRED is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# FRED is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with FRED.  If not, see <https://www.gnu.org/licenses/>.

"""Test models."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import BLANK_CHOICE_DASH
from django.test import SimpleTestCase, TestCase, override_settings
from djmoney.money import Money

from django_pain.constants import InvoiceType, PaymentType
from django_pain.models import BankPayment

from .mixins import CacheResetMixin
from .utils import get_account, get_invoice, get_payment


class TestBankAccount(SimpleTestCase):
    """Test BankAccount model."""

    def test_str(self):
        """Test string representation."""
        account = get_account(account_name='Account', account_number='123')
        self.assertEqual(str(account), 'Account 123')


class TestBankPayment(CacheResetMixin, TestCase):
    """Test BankPayment model."""

    def test_str(self):
        """Test string representation."""
        payment = get_payment(identifier='PID')
        self.assertEqual(str(payment), 'PID')

    def test_currency_constraint_success(self):
        """Test clean method with not violated constraint."""
        account = get_account(currency='USD')
        payment = get_payment(account=account, amount=Money('999.00', 'USD'))
        payment.clean()

    def test_currency_constraint_error(self):
        """Test clean method with violated constraint."""
        account = get_account(account_name='ACCOUNT', account_number='123', currency='USD')
        payment = get_payment(identifier='PAYMENT', account=account, amount=Money('999.00', 'CZK'))
        with self.assertRaisesMessage(ValidationError, 'Bank payment PAYMENT is in different currency (CZK) '
                                                       'than bank account ACCOUNT 123 (USD).'):
            payment.clean()

    @override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
    def test_objective_choices(self):
        self.assertEqual(BankPayment.objective_choices(), BLANK_CHOICE_DASH + [
            ('dummy', 'Dummy objective'),
        ])

    def test_advance_invoice(self):
        account = get_account()
        account.save()
        payment = get_payment(account=account)
        payment.save()

        account_invoice = get_invoice(number='1', invoice_type=InvoiceType.ACCOUNT)
        account_invoice.save()
        account_invoice.payments.add(payment)
        self.assertEqual(payment.advance_invoice, None)

        advance_invoice = get_invoice(number='2', invoice_type=InvoiceType.ADVANCE)
        advance_invoice.save()
        advance_invoice.payments.add(payment)
        self.assertEqual(payment.advance_invoice, advance_invoice)

    @override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
    def test_objective(self):
        payment = get_payment()
        self.assertEqual(payment.objective, '')

        payment = get_payment(processor='dummy')
        self.assertEqual(payment.objective, 'Dummy objective')

    def test_transfer_must_have_counter_account(self):
        account = get_account()
        account.save()

        payment = get_payment(account=account, payment_type=PaymentType.TRANSFER, counter_account_number='')
        self.assertRaises(IntegrityError, payment.save)

    def test_card_payment_must_not_have_counter_account(self):
        account = get_account()
        account.save()

        payment = get_payment(account=account, payment_type=PaymentType.CARD_PAYMENT, counter_account_number='123')
        self.assertRaises(IntegrityError, payment.save)
