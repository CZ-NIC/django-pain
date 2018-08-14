"""Test utils."""
from datetime import date
from typing import Any

from djmoney.money import Money

from django_pain.constants import InvoiceType
from django_pain.models import BankAccount, BankPayment, Invoice
from django_pain.processors import AbstractPaymentProcessor


class DummyPaymentProcessor(AbstractPaymentProcessor):
    """Dummy payment processor."""

    default_objective = 'Dummy objective'

    def process_payments(self, payments):
        """Dummy function."""

    def assign_payment(self, payment, client_id):
        """Dummy function."""

    def get_invoice_url(self, invoice):
        """Dummy function."""
        return "http://example.com/invoice/%s" % invoice.remote_id


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
