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

"""Import callbacks."""
from functools import lru_cache
from warnings import warn

from django.conf import ImproperlyConfigured
from django.core.exceptions import ValidationError

from django_pain.constants import PaymentState
from django_pain.models import BankPayment
from django_pain.processors.ignore import IgnorePaymentProcessor
from django_pain.settings import SETTINGS


@lru_cache()
def _get_ignore_processor_name() -> str:
    """Get ignore processor name."""
    for proc_name, proc_class in SETTINGS.processors.items():
        if issubclass(proc_class, IgnorePaymentProcessor):
            return proc_name

    raise ImproperlyConfigured("IgnorePaymentProcessor is not present in PAIN_PROCESSORS setting.")


def ignore_negative_payments(payment: BankPayment) -> BankPayment:
    """
    Process negative bank payments by IgnorePaymentProcessor.

    This function can be used as pain import callback.
    It expects that there is the IgnorePaymentProcessor among PAIN_PROCESSORS.
    """
    if (payment.amount.amount < 0):
        payment.state = PaymentState.PROCESSED
        payment.processor = _get_ignore_processor_name()
    return payment


def skip_credit_card_transaction_summary(payment: BankPayment) -> BankPayment:
    """
    Import callback for ignoring payments with credit card transactions summary.

    This function is intended to be used as pain import callback.
    """
    if payment.counter_account_number in ('None/None', None, '') and payment.constant_symbol in ('1176', '1178'):
        if payment.counter_account_number == 'None/None':
            warn('Counter account number "None/None" encountered. This is deprecated. Use empty str or None instead.',
                 UserWarning)
        raise ValidationError('Payment is credit card transaction summary.')
    return payment
