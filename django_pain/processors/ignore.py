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
from typing import Iterable

from django.utils.translation import gettext_lazy as _

from django_pain.models import BankPayment

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
