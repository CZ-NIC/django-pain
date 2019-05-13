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

"""Ignore payment processor."""
from functools import lru_cache
from typing import Iterable

from django.conf import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from django_pain.constants import PaymentState
from django_pain.models import BankPayment
from django_pain.settings import SETTINGS

from .common import AbstractPaymentProcessor, ProcessPaymentResult


# FIXME: This class is sort of hack. It's similar to the way, how payments
# worked in old Daphne. However, it would probably be cleaner to create
# new IGNORED payment state. Then it would be necessary create interface
# for payment to be ignored (or maybe even unignored).
class IgnorePaymentProcessor(AbstractPaymentProcessor):
    """
    Ignore payment processor.

    This processor doesn't accept any payment on automatic processing.
    It does accept every payment on manual assignment.
    """

    default_objective = _('Ignore payment')

    def process_payments(self, payments: Iterable[BankPayment]) -> Iterable[ProcessPaymentResult]:
        """Reject all payments."""
        for payment in payments:
            yield ProcessPaymentResult(result=False)

    def assign_payment(self, payment: BankPayment, client_id: str) -> ProcessPaymentResult:
        """Accept any payment."""
        return ProcessPaymentResult(result=True)


@lru_cache()
def _get_ignore_processor_name() -> str:
    """Get ignore processor name."""
    for proc_name, proc_class in SETTINGS.processors.items():
        if issubclass(proc_class, IgnorePaymentProcessor):
            return proc_name
    else:
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
