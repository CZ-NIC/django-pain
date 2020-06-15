#
# Copyright (C) 2020  CZ.NIC, z. s. p. o.
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
from django.test import TestCase
from djmoney.money import Money
from pycsob import conf as CSOB

from django_pain.card_payment_handlers import CartItem, CSOBCardPaymentHandler, PaymentHandlerConnectionError
from django_pain.card_payment_handlers.csob import CsobGateError
from django_pain.constants import PaymentState, PaymentType
from django_pain.tests.utils import get_account, get_payment


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
        result_mock.payload = {'paymentStatus': CSOB.PAYMENT_STATUS_CANCELLED}

        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.payment_status.return_value = result_mock

            handler.update_payments_state(payment)

        self.assertEqual(payment.state, PaymentState.CANCELED)

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
            self.assertRaises(PaymentHandlerConnectionError, handler.init_payment, 100, '123', 'csob',
                              'https://example.com', 'POST', [], 'CZ')

    def test_init_payment_ok(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()

        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.gateway_return.return_value = OrderedDict([
                ('payId', 'unique_id_123'),
                ('resultCode', 0),
                ('resultMessage', 'OK'),
                ('paymentStatus', CSOB.PAYMENT_STATUS_INIT),
                ('dttime', datetime.datetime(2020, 6, 10, 16, 47, 30))
            ])
            gateway_client_mock.get_payment_process_url.return_value = sentinel.url
            payment, redirect_url = handler.init_payment(100, '123', 'donations', 'https://example.com', 'POST',
                                                         [CartItem('Gift for FRED', 1, 1000000,
                                                                   'Gift for the best FRED')],
                                                         'CZ')
        self.assertEqual(redirect_url, sentinel.url)
        self.assertEqual(payment.identifier, 'unique_id_123')
        self.assertEqual(payment.state, PaymentState.INITIALIZED)
        self.assertEqual(payment.card_payment_state, CSOB.PAYMENT_STATUSES[CSOB.PAYMENT_STATUS_INIT])
        self.assertEqual(payment.amount, Money(100, 'XYZ'))
        self.assertEqual(payment.processor, 'donations')
        self.assertEqual(payment.card_handler, 'csob')

    def test_init_payment_not_ok(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()

        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.gateway_return.return_value = OrderedDict([
                ('payId', 'unique_id_123'),
                ('resultCode', 120),
                ('resultMessage', 'Merchant blocked'),
                ('dttime', datetime.datetime(2020, 6, 10, 16, 47, 30))
            ])
            self.assertRaisesRegex(CsobGateError, 'resultCode != OK',
                                   handler.init_payment,
                                   100, '123', 'donations', 'https://example.com', 'POST',
                                   [CartItem('Gift for FRED', 1, 1000000,
                                             'Gift for the best FRED')],
                                   'CZ')

    def test_init_payment_not_wrong_status(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()

        handler = CSOBCardPaymentHandler('csob')
        with patch.object(handler, '_client') as gateway_client_mock:
            gateway_client_mock.gateway_return.return_value = OrderedDict([
                ('payId', 'unique_id_123'),
                ('resultCode', 0),
                ('resultMessage', 'OK'),
                ('paymentStatus', CSOB.PAYMENT_STATUS_CANCELLED),
                ('dttime', datetime.datetime(2020, 6, 10, 16, 47, 30))
            ])
            self.assertRaisesRegex(CsobGateError, 'paymentStatus != PAYMENT_STATUS_INIT',
                                   handler.init_payment,
                                   100, '123', 'donations', 'https://example.com', 'POST',
                                   [CartItem('Gift for FRED', 1, 1000000,
                                             'Gift for the best FRED')],
                                   'CZ')
