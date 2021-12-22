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
"""Tests of the REST API."""
import datetime
from collections import OrderedDict
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from pycsob import conf as CSOB
from testfixtures import LogCapture

from django_pain.card_payment_handlers import PaymentHandlerConnectionError
from django_pain.constants import PaymentState, PaymentType
from django_pain.models import BankPayment
from django_pain.serializers import ExternalPaymentState
from django_pain.settings import get_card_payment_handler_instance
from django_pain.tests.mixins import CacheResetMixin
from django_pain.tests.utils import get_account, get_payment


@override_settings(ROOT_URLCONF='django_pain.tests.urls',
                   PAIN_CARD_PAYMENT_HANDLERS={
                       'csob': 'django_pain.card_payment_handlers.csob.CSOBCardPaymentHandler'
                   },
                   PAIN_CSOB_CARD={
                        'API_PUBLIC_KEY': 'empty_key.txt',
                        'MERCHANT_ID': '',
                        'MERCHANT_PRIVATE_KEY': 'empty_key.txt',
                        'ACCOUNT_NUMBERS': {
                            'CZK': '123456',
                            'EUR': '234567',
                        },
                    })
class TestBankPaymentRestAPI(CacheResetMixin, TestCase):
    def test_retrieve_not_exists(self):
        response = self.client.get('/api/private/bankpayment/no-i-do-not-exists/')
        self.assertEqual(response.status_code, 404)

    def test_retrieve_exists(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()
        payment = get_payment(identifier='1', account=account, counter_account_number='',
                              payment_type=PaymentType.CARD_PAYMENT,
                              state=PaymentState.INITIALIZED,
                              card_handler='csob')
        payment.save()

        result_mock = Mock()
        result_mock.payload = {'paymentStatus': CSOB.PAYMENT_STATUS_CANCELLED, 'resultCode': CSOB.RETURN_CODE_OK}

        card_payment_hadler = get_card_payment_handler_instance(payment.card_handler)
        with patch.object(card_payment_hadler, '_client') as gateway_client_mock:
            gateway_client_mock.payment_status.return_value = result_mock
            response = self.client.get('/api/private/bankpayment/{}/'.format(payment.uuid))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['state'], ExternalPaymentState.CANCELED)

    def test_retrieve_gateway_connection_error(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()
        payment = get_payment(identifier='1', account=account, counter_account_number='',
                              payment_type=PaymentType.CARD_PAYMENT,
                              state=PaymentState.READY_TO_PROCESS,
                              card_handler='csob')
        payment.save()

        card_payment_hadler = get_card_payment_handler_instance(payment.card_handler)
        with patch.object(card_payment_hadler, '_client') as gateway_client_mock:
            gateway_client_mock.payment_status.side_effect = PaymentHandlerConnectionError()
            response = self.client.get('/api/private/bankpayment/{}/'.format(payment.uuid))

        self.assertEqual(response.status_code, 503)

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_retrieve_process_paid(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()
        payment = get_payment(identifier='1', account=account, counter_account_number='',
                              payment_type=PaymentType.CARD_PAYMENT, processor='dummy',
                              state=PaymentState.INITIALIZED,
                              card_handler='csob')
        payment.save()

        result_mock = Mock()
        result_mock.payload = {'paymentStatus': CSOB.PAYMENT_STATUS_CONFIRMED, 'resultCode': CSOB.RETURN_CODE_OK}

        card_payment_hadler = get_card_payment_handler_instance(payment.card_handler)
        with patch.object(card_payment_hadler, '_client') as gateway_client_mock:
            gateway_client_mock.payment_status.return_value = result_mock
            response = self.client.get('/api/private/bankpayment/{}/'.format(payment.uuid))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['state'], ExternalPaymentState.PAID)
        self.assertEqual(BankPayment.objects.first().state, PaymentState.PROCESSED)

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyFalsePaymentProcessor'})
    def test_retrieve_process_paid_error(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()
        payment = get_payment(identifier='1', account=account, counter_account_number='',
                              payment_type=PaymentType.CARD_PAYMENT, processor='dummy',
                              state=PaymentState.INITIALIZED,
                              card_handler='csob')
        payment.save()

        result_mock = Mock()
        result_mock.payload = {'paymentStatus': CSOB.PAYMENT_STATUS_CONFIRMED, 'resultCode': CSOB.RETURN_CODE_OK}

        card_payment_hadler = get_card_payment_handler_instance(payment.card_handler)
        with patch.object(card_payment_hadler, '_client') as gateway_client_mock:
            gateway_client_mock.payment_status.return_value = result_mock
            response = self.client.get('/api/private/bankpayment/{}/'.format(payment.uuid))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['state'], ExternalPaymentState.PAID)
        self.assertEqual(BankPayment.objects.first().state, PaymentState.DEFERRED)

    def _test_create(self, post_data, account_number='123456', account_currency='CZK'):
        account = get_account(account_number=account_number, currency=account_currency)
        account.save()

        with patch('django_pain.card_payment_handlers.csob.CsobClient') as gateway_client_mock:
            gateway_client_mock.return_value.gateway_return.return_value = OrderedDict([
                ('payId', 'unique_id_123'),
                ('resultCode', 0),
                ('resultMessage', 'OK'),
                ('paymentStatus', CSOB.PAYMENT_STATUS_INIT),
                ('dttime', datetime.datetime(2020, 6, 10, 16, 47, 30))
            ])
            gateway_client_mock.return_value.get_payment_process_url.return_value = 'https://example.com'

            response = self.client.post('/api/private/bankpayment/', data=post_data)

        self.assertEqual(response.status_code, 201)

    def test_create_no_currency(self):
        post_data = {
            'amount': '1000',
            'variable_symbol': '130',
            'processor': 'donations',
            'card_handler': 'csob',
            'return_url': 'https://donations.nic.cz/return/',
            'return_method': 'POST',
            'language': 'cs',
            'cart': '[{"name":"Dar","amount":1000,"description":"Longer description","quantity":1}]',
        }
        with LogCapture(('django_pain.serializers',), propagate=False) as log_handler:
            self._test_create(post_data)
        log_handler.check((
            'django_pain.serializers',
            'WARNING',
            'Parameter "amount_currency" not set. Using default currency. Processor for this payment: "donations"'
        ))

    def test_create_custom_currency(self):
        post_data = {
            'amount': '100',
            'amount_currency': 'EUR',
            'variable_symbol': '130',
            'processor': 'donations',
            'card_handler': 'csob',
            'return_url': 'https://donations.nic.cz/return/',
            'return_method': 'POST',
            'language': 'cs',
            'cart': '[{"name":"Dar","amount":100,"description":"Longer description","quantity":1}]',
        }
        self._test_create(post_data, account_number='234567', account_currency='EUR')

    def test_create_gw_connection_error(self):
        account = get_account(account_number='123456', currency='CZK')
        account.save()

        with patch('django_pain.card_payment_handlers.csob.CsobClient') as gateway_client_mock:
            gateway_client_mock.side_effect = PaymentHandlerConnectionError()
            response = self.client.post('/api/private/bankpayment/', data={
                'amount': '1000',
                'amount_currency': 'EUR',
                'variable_symbol': '130',
                'processor': 'donations',
                'card_handler': 'csob',
                'return_url': 'https://donations.nic.cz/return/',
                'return_method': 'POST',
                'language': 'cs',
                'cart': '[{"name":"Dar","amount":1000,"description":"Longer description","quantity":1}]',
            })

        self.assertEqual(response.status_code, 503)
