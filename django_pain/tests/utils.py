#
# Copyright (C) 2018-2021  CZ.NIC, z. s. p. o.
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

"""Test utils."""
from datetime import date
from typing import Any

from djmoney.money import Money

from django_pain.card_payment_handlers import (AbstractCardPaymentHandler, PaymentHandlerConnectionError,
                                               PaymentHandlerError)
from django_pain.constants import InvoiceType, PaymentState
from django_pain.models import BankAccount, BankPayment, Client, Invoice
from django_pain.processors import AbstractPaymentProcessor


class DummyPaymentProcessor(AbstractPaymentProcessor):
    """Dummy payment processor."""

    default_objective = 'Dummy objective'

    def process_payments(self, payments):
        """Do nothing."""

    def assign_payment(self, payment, client_id):
        """Do nothing."""


class DummyCardPaymentHandler(AbstractCardPaymentHandler):
    """Dummy card payment handler."""

    def init_payment(self, **kwargs):
        """Do nothing."""

    def update_payments_state(self, payment):
        """Update payment state."""
        payment.state = PaymentState.READY_TO_PROCESS
        payment.save()


class DummyCardPaymentHandlerExc(DummyCardPaymentHandler):
    """Dummy card payment handler which throws connectoin exception."""

    def init_payment(self, **kwargs):
        """Do nothing."""

    def update_payments_state(self, payment):
        """Raise exception."""
        raise PaymentHandlerError('Card Handler Error')


class DummyCardPaymentHandlerConnExc(DummyCardPaymentHandler):
    """Dummy card payment handler which throws connectoin exception."""

    def init_payment(self, **kwargs):
        """Do nothing."""

    def update_payments_state(self, payment):
        """Raise exception."""
        raise PaymentHandlerConnectionError('Gateway connection error')


def get_account(**kwargs: Any) -> BankAccount:
    """Create bank account object."""
    default = {
        'account_number': '123456/0300',
        'account_name': 'Account',
        'currency': 'CZK',
    }
    default.update(kwargs)
    return BankAccount(**default)


def get_payment(**kwargs: Any) -> BankPayment:
    """Create payment object."""
    default = {
        'identifier': 'PAYMENT1',
        'account': None,
        'transaction_date': date(2018, 5, 9),
        'counter_account_number': '098765/4321',
        'counter_account_name': 'Another account',
        'amount': Money('42.00', 'CZK'),
    }
    default.update(kwargs)
    return BankPayment(**default)


def get_invoice(**kwargs: Any) -> Invoice:
    """Create invoice object."""
    default = {
        'number': '1111122222',
        'remote_id': 0,
        'invoice_type': InvoiceType.ADVANCE,
    }
    default.update(kwargs)
    return Invoice(**default)


def get_client(**kwargs: Any) -> Client:
    """Create client object."""
    default = {
        'handle': 'HANDLE',
        'remote_id': 0,
    }
    default.update(kwargs)
    return Client(**default)
