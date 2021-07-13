#
# Copyright (C) 2020-2021  CZ.NIC, z. s. p. o.
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

"""Tests of serializers."""
from decimal import Decimal
from typing import Any, Dict

from django.test import SimpleTestCase, override_settings
from djmoney.money import Money
from rest_framework.serializers import ValidationError
from testfixtures import LogCapture

from django_pain.card_payment_handlers import CartItem
from django_pain.constants import PaymentState
from django_pain.serializers import BankPaymentSerializer, ExternalPaymentState
from django_pain.tests.utils import get_account, get_payment


class TestBankPaymentSerializer(SimpleTestCase):
    """
    Test BankPayment serializer.
    """

    def setUp(self):
        self.log_handler = LogCapture(('django_pain.serializers',), propagate=False)

    def tearDown(self):
        self.log_handler.uninstall()

    def test_get_state(self):
        account = get_account(account_number='123456', currency='CZK')
        payment = get_payment(identifier='1', account=account, counter_account_name='Account one',
                              state=PaymentState.PROCESSED)

        serializer = BankPaymentSerializer()
        self.assertEqual(serializer.get_state(payment), ExternalPaymentState.PAID)

    def test_validate_cart(self):
        serializer = BankPaymentSerializer()

        self.assertRaisesRegex(ValidationError, 'one or two item', serializer.validate_cart, [])
        self.assertRaisesRegex(ValidationError, 'one or two item', serializer.validate_cart, [{}, {}, {}])

        self.assertRaisesRegex(ValidationError, 'must not exceede 20', serializer.validate_cart,
                               [{'name': 'Dar too long to fit max length',
                                 'amount': 20, 'description': 'Dar datovce', 'quantity': 1}])

        result = serializer.validate_cart([{'name': 'Dar',
                                            'amount': 20,
                                            'description': 'Dar datovce',
                                            'quantity': 1}])
        self.assertEqual(result, [CartItem(name='Dar', amount=20, description='Dar datovce', quantity=1)])

    @override_settings(DEFAULT_CURRENCY='EUR')
    def test_validate_amount(self):
        data = {
            'cart': [CartItem(name='Dar', amount=10, description='Dar datovce', quantity=1)]
        }  # type: Dict[str, Any]
        serializer = BankPaymentSerializer()

        data['amount'] = Money(10, 'CZK')
        validated = serializer.validate(data)
        self.assertEqual(validated['amount'], Money(10, 'CZK'))

        data['amount'] = Decimal(10)
        validated = serializer.validate(data)
        self.assertEqual(validated['amount'], Money(10, 'EUR'))

        data['amount'] = 10
        data['processor'] = 'processor'
        validated = serializer.validate(data)
        self.assertEqual(validated['amount'], Money(10, 'EUR'))

        message = 'Parameter "amount_currency" not set. Using default currency. Processor for this payment: "{}"'
        self.log_handler.check(
            ('django_pain.serializers', 'WARNING', message.format('')),
            ('django_pain.serializers', 'WARNING', message.format('processor')),
        )

    def test_validate_amount_and_cart(self):
        data = {
            'amount': Money(40, 'CZK'),
            'cart': [CartItem(name='Dar', amount=20, description='Dar datovce', quantity=2)]
        }
        serializer = BankPaymentSerializer()
        self.assertEqual(data, serializer.validate(data))

        data['amount'] = Money(100, 'CZK')
        self.assertRaisesRegex(ValidationError, 'amounts must be equal', serializer.validate, data)
