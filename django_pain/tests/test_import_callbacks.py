#
# Copyright (C) 2019-2021  CZ.NIC, z. s. p. o.
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

"""Test import callbacks."""
from collections import OrderedDict
from copy import copy
from typing import cast

from django.conf import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from djmoney.money import Money

from django_pain.constants import PaymentState, PaymentType
from django_pain.import_callbacks import ignore_negative_payments, skip_bank_fees, skip_credit_card_transaction_summary
from django_pain.models.bank import BankPayment
from django_pain.tests.mixins import CacheResetMixin
from django_pain.tests.utils import get_payment


class TestIgnoreNegativePayments(CacheResetMixin, SimpleTestCase):
    """Test ignore_negative_payments callback."""

    def setUp(self):
        super().setUp()
        self.payment = get_payment()

    def test_positive_payment(self):
        self.payment.amount.amount = 42
        payment = ignore_negative_payments(self.payment)
        self.assertEqual(payment.state, PaymentState.READY_TO_PROCESS)
        self.assertEqual(payment.processor, '')

    @override_settings(PAIN_PROCESSORS=OrderedDict([
        ('dummy', 'django_pain.tests.utils.DummyPaymentProcessor'),
        ('ignore', 'django_pain.processors.IgnorePaymentProcessor'),
    ]))
    def test_negative_payment(self):
        self.payment.amount.amount = -42
        payment = ignore_negative_payments(self.payment)
        self.assertEqual(payment.state, PaymentState.PROCESSED)
        self.assertEqual(payment.processor, 'ignore')

    @override_settings(PAIN_PROCESSORS={})
    def test_negative_wrong_setting(self):
        self.payment.amount.amount = -42
        with self.assertRaises(ImproperlyConfigured):
            ignore_negative_payments(self.payment)


class TestSkipCreditCardTransactionSummary(SimpleTestCase):
    """Test skip_credit_card_transaction_summary callback."""

    def setUp(self):
        super().setUp()

    def test_credit_card_summary_payment_none_slash_none(self):
        payment = get_payment(
            counter_account_number='None/None',
            constant_symbol='1176',
        )
        with self.assertWarnsRegex(UserWarning, 'Counter account number "None/None" encountered'):
            self.assertIsNone(skip_credit_card_transaction_summary(payment))

    def test_credit_card_summary_payment_none(self):
        payment = get_payment(
            counter_account_number=None,
            constant_symbol='1176',
        )
        self.assertIsNone(skip_credit_card_transaction_summary(payment))

    def test_credit_card_summary_payment_empty_str(self):
        payment = get_payment(
            counter_account_number='',
            constant_symbol='1176',
        )
        self.assertIsNone(skip_credit_card_transaction_summary(payment))

    def test_normal_payment(self):
        original_payment = get_payment()
        processed_payment = skip_credit_card_transaction_summary(original_payment)
        self.assertIsNotNone(processed_payment)
        self.assertEqual(cast(BankPayment, processed_payment).state, PaymentState.READY_TO_PROCESS)


class TestSkipBankFees(SimpleTestCase):
    """Test skip_bank_fees callback."""

    def setUp(self):
        super().setUp()

    def test_skip_bank_fees(self):
        original_payments = [
            get_payment(counter_account_number=''),
            get_payment(amount=Money('-42.00', 'CZK')),
            get_payment(payment_type=PaymentType.TRANSFER),
            get_payment(counter_account_number='', amount=Money('-42.00', 'CZK'), payment_type=PaymentType.TRANSFER),
        ]
        expected_payments = [copy(p) for p in original_payments[:3]] + [None]  # type: ignore

        for payment, expected in zip(original_payments, expected_payments):
            with self.subTest(payment=payment, expected=expected):
                processed = skip_bank_fees(payment)
                self.assertEqual(type(processed), type(expected))
                if expected is not None:
                    processed = cast(BankPayment, processed)
                    self.assertEqual(processed.identifier, expected.identifier)
                    self.assertEqual(processed.uuid, expected.uuid)
                    self.assertEqual(processed.payment_type, expected.payment_type)
                    self.assertEqual(processed.counter_account_number, expected.counter_account_number)
                    self.assertEqual(processed.state, expected.state)
                    self.assertEqual(processed.card_payment_state, expected.card_payment_state)
                    self.assertEqual(processed.processing_error, expected.processing_error)
                    self.assertEqual(processed.processor, expected.processor)
                    self.assertEqual(processed.card_handler, expected.card_handler)
