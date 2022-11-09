#
# Copyright (C) 2018-2022  CZ.NIC, z. s. p. o.
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

"""Base payment processor module."""
from abc import ABC, abstractmethod
from typing import Iterable, Optional

from django_pain.constants import PaymentProcessingError
from django_pain.models import BankPayment


class PaymentProcessorError(Exception):
    """Generic payment processor error."""


class InvalidTaxDateError(Exception):
    """Invalid tax date exception."""


class ProcessPaymentResult(object):
    """Result of payment processing."""

    def __init__(self, result: bool, error: Optional[PaymentProcessingError] = None) -> None:
        """
        Initialize the result.

        Args:
            result: True if payment was successfully processed. False otherwise.
            error: Optional payment processing error code.
        """
        self.result = result
        self.error = error

    def __eq__(self, other) -> bool:
        """Compare processing results by their value."""
        if isinstance(other, ProcessPaymentResult):
            return self.result == other.result and self.error == other.error
        return False


class AbstractPaymentProcessor(ABC):
    """
    Bank payment processor.

    Aside from mandatory methods, payment processor MAY implement
    these methods:
        * get_invoice_url(self, invoice: Invoice) -> str
        * get_client_url(self, client: Client) -> str
        * get_client_choices(self) -> Dict[str,str]

    Method get_invoice_url should return url of invoice in external system.
    Method get_client_url should return url of client in external system.
    Method get_client_choices returns dictionary with client handles as keys
        and client names as values.
    """

    @property
    @abstractmethod
    def default_objective(self):
        """
        Return default objective of payments processed by payment processor.

        This property should contain human readable objective.
        """

    @property
    def manual_tax_date(self):
        """
        Return whether payment processor allows to specify tax date for manual assignment.

        Default is False.
        """
        return False

    @abstractmethod
    def process_payments(self, payments: Iterable[BankPayment]) -> Iterable[ProcessPaymentResult]:
        """
        Process bank payment.

        Each processor class has to implement this method.

        Returns:
            Iterable of named tuples (``ProcessPaymentResult``). If n-th payment
            has been recognized and processed, n-th position of returned iterable
            must have ``result`` set to True, otherwise value of ``result`` must
            be False.

        Raises:
            PaymentProcessorError when a major error which precents processing
            of all payments occurs.
        """

    @abstractmethod
    def assign_payment(self, payment: BankPayment, client_id: str) -> ProcessPaymentResult:
        """
        Assign bank payment to this payment processor.

        Each processor class has to implement this method. This method
        implements forced assignment of payment to particular payment
        processor. As a hint, ``client_id`` may be provided.

        For processors where manual_tax_date=True, optional attr tax_date is
        also provided. In that case, this method may raise InvalidTaxDateError.
        """
