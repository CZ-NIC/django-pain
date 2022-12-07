#
# Copyright (C) 2020-2022  CZ.NIC, z. s. p. o.
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

"""Tests of card payment handlers."""
import datetime
from collections import OrderedDict
from unittest.mock import Mock, patch, sentinel

import requests
from django.test import TestCase, override_settings
from djmoney.money import Money
from pycsob import conf as CSOB

from django_pain.card_payment_handlers import (CartItem, CSOBCardPaymentHandler, PaymentHandlerConnectionError,
                                               PaymentHandlerError)
from django_pain.constants import PaymentState, PaymentType
from django_pain.models.bank import BankPayment
from django_pain.tests.utils import get_account, get_payment

csob_settings = {
    'API_PUBLIC_KEY': 'empty_key.txt',
    'MERCHANT_ID': '',
    'MERCHANT_PRIVATE_KEY': 'empty_key.txt',
    'ACCOUNT_NUMBERS': {
        'CZK': '123456',
        'EUR': '234567',
    },
}


class TestCSOBCardPaymentHandlerStatus(TestCase):
    """Test CSOBCardPaymentHandler.payment_status method."""

    def test_get_client(self):
        handler = CSOBCardPaymentHandler('csob')
        client = handler.client
        # repeated calls should get the same client instance
        client2 = handler.client
        self.assertEqual(client, client2)

    def test_update_payment_state_ok(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()
        payment = get_payment(identifier='1', account=account, counter_account_number='',
                              payment_type=PaymentType.CARD_PAYMENT,
                              state=PaymentState.INITIALIZED,
                              card_handler='csob')
        payment.save()

        result_mock = Mock()
        result_mock.payload = {'paymentStatus': CSOB.PAYMENT_STATUS_CANCELLED, 'resultCode': CSOB.RETURN_CODE_OK}

        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.payment_status.return_value = result_mock

            handler.update_payments_state(payment)

        self.assertEqual(payment.state, PaymentState.CANCELED)

    def test_update_payment_state_no_update_not_initialized(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()
        payment = get_payment(identifier='1', account=account, counter_account_number='',
                              payment_type=PaymentType.CARD_PAYMENT,
                              state=PaymentState.PROCESSED,
                              card_handler='csob')
        payment.save()

        result_mock = Mock()
        result_mock.payload = {'paymentStatus': CSOB.PAYMENT_STATUS_CANCELLED, 'resultCode': CSOB.RETURN_CODE_OK}

        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.payment_status.return_value = result_mock

            handler.update_payments_state(payment)

        self.assertEqual(payment.state, PaymentState.PROCESSED)

    def test_update_payment_state_not_ok(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()
        payment = get_payment(identifier='1', account=account, counter_account_number='',
                              payment_type=PaymentType.CARD_PAYMENT,
                              state=PaymentState.INITIALIZED,
                              card_handler='csob')
        payment.save()

        result_mock = Mock()
        result_mock.payload = {'resultCode': CSOB.RETURN_CODE_MERCHANT_BLOCKED}

        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.payment_status.return_value = result_mock
            self.assertRaisesRegex(PaymentHandlerError, 'payment_status resultCode != OK',
                                   handler.update_payments_state, payment)
        self.assertEqual(payment.state, PaymentState.INITIALIZED)

    def test_update_payment_state_connection_error(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()
        payment = get_payment(identifier='1', account=account, counter_account_number='',
                              payment_type=PaymentType.CARD_PAYMENT,
                              state=PaymentState.INITIALIZED,
                              card_handler='csob')
        payment.save()

        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.payment_status.side_effect = requests.ConnectionError()

            self.assertRaises(PaymentHandlerConnectionError, handler.update_payments_state, payment)


class TestCSOBCardPaymentHandlerInit(TestCase):
    """Test CSOBCardPaymentHandler.init_payment method."""
    def test_init_payment_connection_error(self):
        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.payment_init.side_effect = requests.ConnectionError()
            self.assertRaises(PaymentHandlerConnectionError, handler.init_payment, Money(100, 'CZK'), '123', 'csob',
                              'https://example.com', 'POST', [], 'cs')

    def test_init_payment_ok(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()

        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.gateway_return.return_value = OrderedDict([
                ('payId', 'unique_id_123'),
                ('resultCode', CSOB.RETURN_CODE_OK),
                ('resultMessage', 'OK'),
                ('paymentStatus', CSOB.PAYMENT_STATUS_INIT),
                ('dttime', datetime.datetime(2020, 6, 10, 16, 47, 30))
            ])
            gateway_client_mock.get_payment_process_url.return_value = sentinel.url
            payment, redirect_url = handler.init_payment(
                Money(100, 'CZK'),
                '123',
                'donations',
                'https://example.com',
                'POST',
                [CartItem('Gift for FRED', 1, 1000000, 'Gift for the best FRED')],
                'cs'
            )

        gateway_client_mock.payment_init.assert_called_once_with(
            order_no='123',
            total_amount=100 * 100,
            currency='CZK',
            return_url='https://example.com',
            description='Dummy value',
            cart=[{
                'name': 'Gift for FRED',
                'quantity': 1,
                'amount': 100000000,
                'description': 'Gift for the best FRED'
            }],
            return_method='POST',
            language='cs',
        )

        self.assertEqual(redirect_url, sentinel.url)
        self.assertEqual(payment.identifier, 'unique_id_123')
        self.assertEqual(payment.state, PaymentState.INITIALIZED)
        self.assertEqual(payment.card_payment_state, CSOB.PAYMENT_STATUSES[CSOB.PAYMENT_STATUS_INIT])
        self.assertEqual(payment.amount, Money(100, 'CZK'))
        self.assertEqual(payment.processor, 'donations')
        self.assertEqual(payment.card_handler, 'csob')

    @override_settings(PAIN_CSOB_CARD=csob_settings)
    def test_init_payment_select_account_by_currency(self):
        account_czk = get_account(account_number='123456', currency='CZK')
        account_czk.save()
        account_eur = get_account(account_number='234567', currency='EUR')
        account_eur.save()

        test_data = (
            ('CZK', '123', account_czk),
            ('EUR', '456', account_eur),
        )

        handler = CSOBCardPaymentHandler('csob')

        for currency, pay_id, _ in test_data:
            with patch.object(handler, '_client') as gateway_client_mock:
                gateway_client_mock.gateway_return.return_value = OrderedDict([
                    ('payId', 'unique_id_' + pay_id),
                    ('resultCode', CSOB.RETURN_CODE_OK),
                    ('resultMessage', 'OK'),
                    ('paymentStatus', CSOB.PAYMENT_STATUS_INIT),
                    ('dttime', datetime.datetime(2020, 6, 10, 16, 47, 30))
                ])
                handler.init_payment(
                    Money(100, currency),
                    pay_id,
                    'donations',
                    'https://example.com',
                    'POST',
                    [CartItem('Gift for FRED', 1, 1000000, 'Gift for the best FRED')],
                    'cs'
                )

        for currency, pay_id, account in test_data:
            payment = BankPayment.objects.get(identifier='unique_id_' + pay_id)
            self.assertEqual(payment.amount, Money(100, currency))
            self.assertEqual(payment.account, account)

    @override_settings(PAIN_CSOB_CARD=csob_settings)
    def test_init_payment_non_existent_account(self):
        account_czk = get_account(account_number='123456', currency='CZK')
        account_czk.save()

        handler = CSOBCardPaymentHandler('csob')

        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.gateway_return.return_value = OrderedDict([
                ('payId', 'unique_id_123'),
                ('resultCode', CSOB.RETURN_CODE_OK),
                ('resultMessage', 'OK'),
                ('paymentStatus', CSOB.PAYMENT_STATUS_INIT),
                ('dttime', datetime.datetime(2020, 6, 10, 16, 47, 30))
            ])
            message = 'CSOBCardPaymentHandler configured with non-existing account "234567"'
            with self.assertRaisesRegex(ValueError, message):
                handler.init_payment(
                    Money(100, 'EUR'),
                    '123',
                    'donations',
                    'https://example.com',
                    'POST',
                    [CartItem('Gift for FRED', 1, 1000000, 'Gift for the best FRED')],
                    'cs'
                )

    @override_settings(PAIN_CSOB_CARD=csob_settings)
    def test_init_payment_account_not_set(self):
        account_czk = get_account(account_number='123456', currency='CZK')
        account_czk.save()
        account_eur = get_account(account_number='234567', currency='EUR')
        account_eur.save()

        handler = CSOBCardPaymentHandler('csob')

        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.gateway_return.return_value = OrderedDict([
                ('payId', 'unique_id_123'),
                ('resultCode', CSOB.RETURN_CODE_OK),
                ('resultMessage', 'OK'),
                ('paymentStatus', CSOB.PAYMENT_STATUS_INIT),
                ('dttime', datetime.datetime(2020, 6, 10, 16, 47, 30))
            ])
            with self.assertRaisesRegex(ValueError, 'No account for currency USD'):
                handler.init_payment(
                    Money(100, 'USD'),
                    '123',
                    'donations',
                    'https://example.com',
                    'POST',
                    [CartItem('Gift for FRED', 1, 1000000, 'Gift for the best FRED')],
                    'cs'
                )

    def test_init_payment_not_ok(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()

        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.gateway_return.return_value = OrderedDict([
                ('payId', 'unique_id_123'),
                ('resultCode', CSOB.RETURN_CODE_MERCHANT_BLOCKED),
                ('resultMessage', 'Merchant blocked'),
                ('dttime', datetime.datetime(2020, 6, 10, 16, 47, 30))
            ])
            self.assertRaisesRegex(PaymentHandlerError, 'resultCode != OK',
                                   handler.init_payment,
                                   Money(100, 'CZK'), '123', 'donations', 'https://example.com', 'POST',
                                   [CartItem('Gift for FRED', 1, 1000000,
                                             'Gift for the best FRED')],
                                   'cs')

    def test_init_payment_not_wrong_status(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()

        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.gateway_return.return_value = OrderedDict([
                ('payId', 'unique_id_123'),
                ('resultCode', CSOB.RETURN_CODE_OK),
                ('resultMessage', 'OK'),
                ('paymentStatus', CSOB.PAYMENT_STATUS_CANCELLED),
                ('dttime', datetime.datetime(2020, 6, 10, 16, 47, 30))
            ])
            self.assertRaisesRegex(PaymentHandlerError, 'paymentStatus != PAYMENT_STATUS_INIT',
                                   handler.init_payment,
                                   Money(100, 'CZK'), '123', 'donations', 'https://example.com', 'POST',
                                   [CartItem('Gift for FRED', 1, 1000000,
                                             'Gift for the best FRED')],
                                   'cs')
