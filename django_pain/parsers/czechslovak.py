"""Module providing Czech and Slovak parser specifics."""
from django_pain.parsers import AbstractBankStatementParser


class CzechSlovakBankStatementParser(AbstractBankStatementParser):
    """Abstract parser class providing Czech and Slovak specifics."""

    @staticmethod
    def compose_account_number(number: str, bank_code: str) -> str:
        """
        Compose account number from number and bank code.

        Czech and Slovak bank accounts have account number separated from bank code using slash.
        """
        return '{}/{}'.format(number, bank_code)
