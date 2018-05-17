"""Test utils."""
from datetime import date
from typing import Any

from djmoney.money import Money

from django_pain.models import BankPayment


def get_payment(**kwargs: Any) -> BankPayment:
    """Create payment object."""
    default = {
        'identifier': 'PAYMENT1',
        'account': None,
        'transaction_date': date(2018, 5, 9),
        'counter_account_number': '098765/4321',
        'amount': Money('42.00', 'CZK'),
    }
    default.update(kwargs)
    return BankPayment(**default)
