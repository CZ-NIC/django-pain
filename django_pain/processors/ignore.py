"""Ignore payment processor."""
from typing import Iterable

from django.utils.translation import gettext as _

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
            yield ProcessPaymentResult(result=False, objective=self.default_objective)

    def assign_payment(self, payment: BankPayment, client_id: str) -> ProcessPaymentResult:
        """Accept any payment."""
        return ProcessPaymentResult(result=True, objective=self.default_objective)
