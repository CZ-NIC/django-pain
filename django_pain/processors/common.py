"""Base payment processor module."""
from abc import ABC, abstractmethod
from collections import namedtuple
from typing import Iterable

from django_pain.models import BankPayment

ProcessPaymentResult = namedtuple('ProcessPaymentResult', ['result', 'objective'])


class AbstractPaymentProcessor(ABC):
    """Bank payment processor."""

    @property
    @abstractmethod
    def default_objective(self):
        """
        Return default objective of payments processed by payment processor.

        This property should contain human readable objective.
        """

    @abstractmethod
    def process_payments(self, payments: Iterable[BankPayment]) -> Iterable[ProcessPaymentResult]:
        """
        Process bank payment.

        Each processor class has to implement this method. Result is iterable
        of named tuples (``ProcessPaymentResult``). If n-th payment has been
        recognized and processed, n-th position of returned iterable must
        have ``result`` set to True, otherwise value of ``result`` must be
        False.
        """

    @abstractmethod
    def assign_payment(self, payment: BankPayment, client_id: str) -> ProcessPaymentResult:
        """
        Assign bank payment to this payment processor.

        Each processor class has to implement this method. This method
        implements forced assignment of payment to particular payment
        processor. As a hint, ``client_id`` may be provided.
        """
