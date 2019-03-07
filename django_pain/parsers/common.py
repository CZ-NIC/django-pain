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

"""Base bank statement parser module."""
from abc import ABC, abstractmethod
from typing import IO, Iterable

from django_pain.models import BankPayment


class AbstractBankStatementParser(ABC):
    """Bank statement parser."""

    @abstractmethod
    def parse(self, bank_statement: IO) -> Iterable[BankPayment]:
        """
        Parse bank statement.

        Each parser class has to implement this method. Result is either iterable
        of BankPayment objects or iterable of sequences.

        If result is iterable of sequences, first element of each sequence has to
        be BankPayment object. Other elements (if any) should be other payment
        related objects such as PaymentSymbols.

        If bank account does not exist in database, parser should raise
        BankAccount.DoesNotExist exception.
        """
