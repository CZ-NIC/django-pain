"""Test CzechSlovakBankStatementParser."""
from django.test import SimpleTestCase

from django_pain.parsers.czechslovak import CzechSlovakBankStatementParser


class DummyParser(CzechSlovakBankStatementParser):
    """Dummy parser derived from abstract class."""

    def parse(self, bank_statement):
        """Just a dummy implementation, because DummyParser cannot be abstract."""


class TestCzechSlovakBankStatementParser(SimpleTestCase):
    """Test CzechSlovakBankStatementParser."""

    def test_compose_account_number(self):
        parser = DummyParser()
        self.assertEqual(parser.compose_account_number('123456', '0300'), '123456/0300')
