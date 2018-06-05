"""
Transproc XML parser.

Transproc is collection of scripts for downloading bank statements and
transforming them into unified XML format.

URL: https://github.com/CZ-NIC/fred-transproc
"""
from datetime import datetime
from typing import IO, Iterator

from djmoney.money import Money
from lxml import etree

from django_pain.models import BankAccount, BankPayment
from django_pain.parsers.czechslovak import CzechSlovakBankStatementParser


def none_to_str(value: str) -> str:
    """Return value if value is not None, otherwise return empty string."""
    return value if value is not None else ''


class TransprocXMLParser(CzechSlovakBankStatementParser):
    """Transproc XML parser."""

    def parse(self, bank_statement: IO[bytes]) -> Iterator[BankPayment]:
        """Parse XML input."""
        parser = etree.XMLParser(resolve_entities=False)
        tree = etree.parse(bank_statement, parser)

        account_number = self.compose_account_number(tree.find('//*/account_number').text,
                                                     tree.find('//*/account_bank_code').text)
        try:
            account = BankAccount.objects.get(account_number=account_number)
        except BankAccount.DoesNotExist:
            raise BankAccount.DoesNotExist('Bank account %s does not exist.' % account_number)

        for item in tree.findall('//*/*/item'):
            attrs = dict((el.tag, el.text) for el in item.iterchildren())

            payment = BankPayment(
                identifier=attrs['ident'],
                account=account,
                transaction_date=datetime.strptime(attrs['date'], '%Y-%m-%d'),
                counter_account_number=self.compose_account_number(attrs['account_number'], attrs['account_bank_code']),
                counter_account_name=none_to_str(attrs['name']),
                amount=Money(attrs['price'], account.currency),
                description=none_to_str(attrs['memo']),
                constant_symbol=none_to_str(attrs['const_symbol']),
                variable_symbol=none_to_str(attrs['var_symbol']),
                specific_symbol=none_to_str(attrs['spec_symbol']),
            )

            yield payment
