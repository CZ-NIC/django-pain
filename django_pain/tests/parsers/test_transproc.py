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

"""Test TransprocXMLParser."""
from datetime import datetime
from io import BytesIO

from django.test import TestCase, override_settings
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
                        <status>1</status>
                        <code>1</code>
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
                        <status>1</status>
                        <code>2</code>
                    </item>
                </items>
            </statement>
        </statements>'''

    ZERO_IN_VARSYM_XML = b'''<?xml version="1.0" encoding="UTF-8"?>
        <statements>
            <statement>
                <account_number>123456789</account_number>
                <account_bank_code>0123</account_bank_code>
                <date>2012-12-31</date>
                <items>
                    <item>
                        <ident>333</ident>
                        <account_number>123456777</account_number>
                        <account_bank_code>0123</account_bank_code>
                        <var_symbol>00700</var_symbol>
                        <const_symbol></const_symbol>
                        <spec_symbol></spec_symbol>
                        <price>1000.00</price>
                        <date>2012-12-20</date>
                        <name>Company Inc.</name>
                        <memo></memo>
                        <status>1</status>
                        <code>1</code>
                    </item>
                </items>
            </statement>
        </statements>'''

    def test_parse(self):
        account = BankAccount(account_number='123456789/0123', currency='CZK')
        account.save()
        parser = TransprocXMLParser()
        payments = list(parser.parse(BytesIO(self.XML_INPUT)))

        payment = {
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

        self.assertEqual(len(payments), 1)

        for field in payment:
            self.assertEqual(getattr(payments[0], field), payment[field])

    @override_settings(PAIN_TRIM_VARSYM=True)
    def test_trim_varsym(self):
        account = BankAccount(account_number='123456789/0123', currency='CZK')
        account.save()
        parser = TransprocXMLParser()
        payments = list(parser.parse(BytesIO(self.ZERO_IN_VARSYM_XML)))
        self.assertEqual(payments[0].variable_symbol, '700')

    def test_parse_account_not_exists(self):
        """Parser should raise an exception if bank account does not exist."""
        parser = TransprocXMLParser()
        with self.assertRaisesRegex(BankAccount.DoesNotExist, 'Bank account 123456789/0123 does not exist.'):
            output = parser.parse(BytesIO(self.XML_INPUT))
            next(output)
