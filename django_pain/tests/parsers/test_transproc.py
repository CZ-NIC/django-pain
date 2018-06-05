"""Test TransprocXMLParser."""
from datetime import datetime
from io import BytesIO

from django.test import TestCase
from djmoney.money import Money

from django_pain.models import BankAccount
from django_pain.parsers.transproc import TransprocXMLParser


class TestTransprocXMLParser(TestCase):
    """Test FioXMLParser."""

    XML_INPUT = b'''<?xml version="1.0" encoding="UTF-8"?>
        <statements>
            <statement>
                <account_number>123456789</account_number>
                <account_bank_code>0123</account_bank_code>
                <date>2012-12-31</date>
                <items>
                    <item>
                        <ident>111</ident>
                        <account_number>123456777</account_number>
                        <account_bank_code>0123</account_bank_code>
                        <const_symbol>0558</const_symbol>
                        <var_symbol>11111111</var_symbol>
                        <spec_symbol></spec_symbol>
                        <price>1000.00</price>
                        <memo>See you later</memo>
                        <date>2012-12-20</date>
                        <name>Company Inc.</name>
                    </item>
                    <item>
                        <ident>222</ident>
                        <account_number>123456888</account_number>
                        <account_bank_code>1234</account_bank_code>
                        <const_symbol>0558</const_symbol>
                        <var_symbol></var_symbol>
                        <spec_symbol>600</spec_symbol>
                        <price>2000.00</price>
                        <memo></memo>
                        <date>2012-12-20</date>
                        <name>Company Ltd.</name>
                    </item>
                </items>
            </statement>
        </statements>'''

    def test_parse(self):
        account = BankAccount(account_number='123456789/0123', currency='CZK')
        account.save()
        parser = TransprocXMLParser()
        payments = list(parser.parse(BytesIO(self.XML_INPUT)))

        payment1 = {
            'identifier': '111',
            'account': account,
            'transaction_date': datetime(2012, 12, 20, 0, 0),
            'counter_account_number': '123456777/0123',
            'counter_account_name': 'Company Inc.',
            'amount': Money('1000.00', 'CZK'),
            'description': 'See you later',
            'constant_symbol': '0558',
            'variable_symbol': '11111111',
            'specific_symbol': '',
        }
        payment2 = {
            'identifier': '222',
            'account': account,
            'transaction_date': datetime(2012, 12, 20, 0, 0),
            'counter_account_number': '123456888/1234',
            'counter_account_name': 'Company Ltd.',
            'amount': Money('2000.00', 'CZK'),
            'description': '',
            'constant_symbol': '0558',
            'variable_symbol': '',
            'specific_symbol': '600',
        }

        self.assertEqual(len(payments), 2)

        for field in payment1:
            self.assertEqual(getattr(payments[0], field), payment1[field])
        for field in payment2:
            self.assertEqual(getattr(payments[1], field), payment2[field])

    def test_parse_account_not_exists(self):
        """Parser should raise an exception if bank account does not exist."""
        parser = TransprocXMLParser()
        with self.assertRaisesRegex(BankAccount.DoesNotExist, 'Bank account 123456789/0123 does not exist.'):
            output = parser.parse(BytesIO(self.XML_INPUT))
            next(output)
