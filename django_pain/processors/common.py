"""Base payment processor module."""
from abc import ABC, abstractmethod
from typing import Iterable

from django_pain.models import BankPayment


class AbstractPaymentProcessor(ABC):
    """Bank payment processor."""

    @abstractmethod
    def process_payments(self, payments: Iterable[BankPayment]) -> Iterable[bool]:
        """
        Process bank payment.

        Each processor class has to implement this method. Result is iterable
        of booleans. If n-th payment has been recognized and processed, n-th
        position of returned iterable must be True, otherwise it must be False.
        """
