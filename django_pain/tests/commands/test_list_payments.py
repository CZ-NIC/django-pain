#
# Copyright (C) 2018-2020  CZ.NIC, z. s. p. o.
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

"""Test list_payments command."""
import argparse
from datetime import datetime
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from djmoney.money import Money

from django_pain.constants import PaymentProcessingError, PaymentState
from django_pain.management.commands.list_payments import format_payment, non_negative_bigint
from django_pain.tests.utils import get_account, get_payment


class TestHelperFunctions(SimpleTestCase):
    """Test list_payments helper functions."""

    def test_non_negative_bigint(self):
        """Test non_negative_bigint."""
        self.assertEqual(non_negative_bigint("42"), 42)
        self.assertEqual(non_negative_bigint("0"), 0)
        with self.assertRaisesRegex(argparse.ArgumentTypeError, r'^limit must be non-negative integer$'):
            non_negative_bigint("-3")
        with self.assertRaisesRegex(argparse.ArgumentTypeError, r'^limit is too big$'):
            non_negative_bigint("100000000000000000000000000000")

    def test_format_payment(self):
        """Test format_payment."""
        payment = get_payment(identifier='ID', create_time=datetime(2018, 1, 1, 12, 0, 0),
                              amount=Money('42.00', 'CZK'), description='Memo...',
                              counter_account_name='Acc')
        self.assertRegex(
            format_payment(payment),
            r'^ID\s+2018-01-01T12:00:00\s+amount:\s+42.00 Kč\s+account_memo: Memo...\s+account_name: Acc$'
        )

    def test_format_payment_with_processing_error(self):
        """Test format_payment with processing_error."""
        payment = get_payment(identifier='ID', create_time=datetime(2018, 1, 1, 12, 0, 0),
                              amount=Money('42.00', 'CZK'), description='Memo...',
                              counter_account_name='Acc', processing_error=PaymentProcessingError.DUPLICITY)
        self.assertRegex(
            format_payment(payment),
            r'^ID\s+2018-01-01T12:00:00\s+amount:\s+42.00 Kč\s+'
            r'account_memo: Memo...\s+account_name: Acc\s+processing_error: Duplicate payment$'
        )


class TestListPayments(TestCase):
    """Test list_payments command."""

    @classmethod
    def setUpTestData(cls):
        account1 = get_account(account_number='123456', currency='CZK')
        account1.save()
        account2 = get_account(account_number='654321', currency='CZK')
        account2.save()
        get_payment(identifier='1', account=account1, counter_account_name='Account one',
                    state=PaymentState.READY_TO_PROCESS).save()
        get_payment(identifier='2', account=account2, counter_account_name='Account two',
                    state=PaymentState.READY_TO_PROCESS).save()
        get_payment(identifier='3', account=account1, counter_account_name='Account three',
                    state=PaymentState.PROCESSED).save()
        get_payment(identifier='4', account=account2, counter_account_name='Account four',
                    description='I am your father!', state=PaymentState.PROCESSED).save()
        get_payment(identifier='5', account=account1, counter_account_name='Account five',
                    state=PaymentState.DEFERRED).save()
        get_payment(identifier='6', account=account1, counter_account_name='Account six',
                    description='May the force be with you', state=PaymentState.DEFERRED).save()
        get_payment(identifier='7', account=account2, counter_account_name='Account seven',
                    state=PaymentState.DEFERRED).save()

    def test_list_all(self):
        """Test listing all payments."""
        out = StringIO()
        call_command('list_payments', stdout=out)

        self.assertRegex(
            out.getvalue(),
            r'7\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account seven\n'
            r'6\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo: May the force be with you\s+'
            r'account_name: Account six\n'
            r'5\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account five\n'
            r'4\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo: I am your father!\s+account_name: Account four\n'
            r'3\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account three\n'
            r'2\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account two\n'
            r'1\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account one\n'
        )

    def test_list_by_state(self):
        """Test listing payments with particular state."""
        out = StringIO()
        call_command('list_payments', '--state=processed', stdout=out)

        self.assertRegex(
            out.getvalue(),
            r'4\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo: I am your father!\s+account_name: Account four\n'
            r'3\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account three\n'
        )

    def test_list_limit(self):
        """Test listing limited number of payments."""
        out = StringIO()
        call_command('list_payments', '--limit=3', stdout=out)

        self.assertRegex(
            out.getvalue(),
            r'7\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account seven\n'
            r'6\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo: May the force be with you\s+'
            r'account_name: Account six\n'
            r'5\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account five\n'
            r'... and 4 more payments'
        )

    def test_quiet_mode(self):
        """Test listing payments in quiet mode."""
        out = StringIO()
        call_command('list_payments', '--verbosity=0', stdout=out)

        self.assertRegex(
            out.getvalue(),
            r'7\n6\n5\n4\n3\n2\n1\n'
        )

    def test_include_accounts(self):
        """Test listing payments to specific accounts."""
        out = StringIO()
        call_command('list_payments', '--include-accounts=123456', stdout=out)

        self.assertRegex(
            out.getvalue(),
            r'6\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo: May the force be with you\s+'
            r'account_name: Account six\n'
            r'5\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account five\n'
            r'3\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account three\n'
            r'1\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account one\n'
        )

    def test_exclude_accounts(self):
        """Test listing payments except for specific accounts."""
        out = StringIO()
        call_command('list_payments', '--exclude-accounts=654321', stdout=out)

        self.assertRegex(
            out.getvalue(),
            r'6\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo: May the force be with you\s+'
            r'account_name: Account six\n'
            r'5\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account five\n'
            r'3\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account three\n'
            r'1\s+[0-9T:.-]+\s+amount:\s+42.00 Kč\s+account_memo:\s+account_name: Account one\n'
        )
