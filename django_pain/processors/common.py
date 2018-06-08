"""Base payment processor module."""
from abc import ABC, abstractmethod

from django_pain.models import BankPayment


class AbstractPaymentProcessor(ABC):
    """Bank payment processor."""

    @abstractmethod
    def process_payment(self, payment: BankPayment) -> bool:
        """
        Process bank payment.

        Each processor class has to implement this method. Result is True if payment
        was recognized and processed, False otherwise.
        """
