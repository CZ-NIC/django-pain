#
# Copyright (C) 2020  CZ.NIC, z. s. p. o.
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
from typing import List, NamedTuple, Tuple

from djmoney.money import Money

from django_pain.models import BankPayment

CartItem = NamedTuple('CartItem', [
    ('name', str),
    ('quantity', int),
    ('amount', float),
    ('description', str),
])


class PaymentHandlerError(Exception):
    """Generic payment handler error."""

    pass


class PaymentHandlerConnectionError(PaymentHandlerError):
    """Peyment handler connection error."""

    pass


class AbstractCardPaymentHandler(ABC):
    """Card payment handler."""

    def __init__(self, name):
        self.name = name

    @abstractmethod
    def init_payment(self, amount: Money, variable_symbol: str, processor: str, return_url: str,
                     return_method: str, cart: List[CartItem], language: str) -> Tuple[BankPayment, str]:
        """
        Initialize card payment.

        Args:
            amount: Total amount of money to pay.
            variable_symbol: Symbol of the order (sometimes called order_id) to be seen in bank administration.
            processor: Name of the processor in settings.
            return_url: URL to wich Gateway redirects back after payment is done.
            return_method: HTTP method for the redirection (POST/GET).
            cart: List of CartItems of length from 1 to 2.
            language: Two capital letter language code e.g. 'EN' for English.

        Returns newly created BankPayment and CSOB gateway URL to redirect to.

        Each descendant has to implement this method.
        Returns newly created BankPayment and redirect URL to Card Payment Gateway.
        """

    @abstractmethod
    def update_payments_state(self, payment: BankPayment) -> None:
        """Update state of the payment form Card Gateway and if newly paid, process the payment."""
