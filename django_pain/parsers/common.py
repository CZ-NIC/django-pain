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
