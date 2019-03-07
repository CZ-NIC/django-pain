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

"""Test import_payments command."""
from datetime import date
from decimal import Decimal
from io import StringIO
from typing import List

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from djmoney.money import Money
from testfixtures import LogCapture, TempDirectory

from django_pain.models import BankAccount, BankPayment
from django_pain.parsers import AbstractBankStatementParser
from django_pain.tests.utils import get_payment


class DummyPaymentsParser(AbstractBankStatementParser):
    """Simple parser that just returns two fixed payments."""

    def parse(self, bank_statement) -> List[BankPayment]:
        account = BankAccount.objects.get(account_number='123456/7890')
        return [
            get_payment(identifier='PAYMENT_1', account=account, variable_symbol='1234'),
            get_payment(identifier='PAYMENT_2', account=account, amount=Money('370.00', 'CZK')),
        ]


class DummyExceptionParser(AbstractBankStatementParser):
    """Simple parser that just throws account not exist exception."""

    def parse(self, bank_statement):
        raise BankAccount.DoesNotExist('Bank account ACCOUNT does not exist.')


class TestImportPayments(TestCase):
    """Test import_payments command."""

    def setUp(self):
        account = BankAccount(account_number='123456/7890', currency='CZK')
        account.save()
        self.account = account
        self.log_handler = LogCapture('django_pain.management.commands.import_payments', propagate=False)

    def tearDown(self):
        self.log_handler.uninstall()

    def test_import_payments(self):
        """Test import_payments command."""
        out = StringIO()
        call_command('import_payments', '--parser=django_pain.tests.commands.test_import_payments.DummyPaymentsParser',
                     '--no-color', '--verbosity=3', stdout=out)

        self.assertEqual(out.getvalue().strip().split('\n'), [
            'Payment ID PAYMENT_1 has been imported.',
            'Payment ID PAYMENT_2 has been imported.',
        ])

        self.assertQuerysetEqual(BankPayment.objects.values_list(
            'identifier', 'account', 'counter_account_number', 'transaction_date', 'amount', 'amount_currency',
            'variable_symbol',
        ), [
            ('PAYMENT_1', self.account.pk, '098765/4321', date(2018, 5, 9), Decimal('42.00'), 'CZK', '1234'),
            ('PAYMENT_2', self.account.pk, '098765/4321', date(2018, 5, 9), Decimal('370.00'), 'CZK', ''),
        ], transform=tuple, ordered=False)

        self.log_handler.check(
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments started.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Importing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Parsing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Saving 2 payments from - to database.'),
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments finished.'),
        )

    def test_account_not_exist(self):
        """Test command while account does not exist."""
        with self.assertRaises(CommandError) as cm:
            call_command('import_payments',
                         '--parser=django_pain.tests.commands.test_import_payments.DummyExceptionParser', '--no-color')

        self.assertEqual(str(cm.exception), 'Bank account ACCOUNT does not exist.')
        self.log_handler.check(
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments started.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Importing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Parsing payments from -.'),
            ('django_pain.management.commands.import_payments', 'ERROR', 'Bank account ACCOUNT does not exist.'),
        )

    def test_payment_already_exist(self):
        """Test command for payments that already exist in database."""
        out = StringIO()
        err = StringIO()
        call_command('import_payments', '--parser=django_pain.tests.commands.test_import_payments.DummyPaymentsParser',
                     '--no-color', stdout=out)
        call_command('import_payments', '--parser=django_pain.tests.commands.test_import_payments.DummyPaymentsParser',
                     '--no-color', stderr=err)

        self.assertEqual(err.getvalue().strip().split('\n'), [
            'Payment ID PAYMENT_1 has not been saved due to the following errors:',
            'Bank payment with this Payment ID and Destination account already exists.',
            'Payment ID PAYMENT_2 has not been saved due to the following errors:',
            'Bank payment with this Payment ID and Destination account already exists.',
        ])
        self.log_handler.check(
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments started.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Importing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Parsing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Saving 2 payments from - to database.'),
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments finished.'),

            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments started.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Importing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Parsing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Saving 2 payments from - to database.'),
            ('django_pain.management.commands.import_payments', 'WARNING',
                'Payment ID PAYMENT_1 has not been saved due to the following errors:'),
            ('django_pain.management.commands.import_payments', 'WARNING',
                'Bank payment with this Payment ID and Destination account already exists.'),
            ('django_pain.management.commands.import_payments', 'WARNING',
                'Payment ID PAYMENT_2 has not been saved due to the following errors:'),
            ('django_pain.management.commands.import_payments', 'WARNING',
                'Bank payment with this Payment ID and Destination account already exists.'),
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments finished.'),
        )

    def test_quiet_command(self):
        """Test command call with verbosity set to 0."""
        out = StringIO()
        err = StringIO()
        call_command('import_payments', '--parser=django_pain.tests.commands.test_import_payments.DummyPaymentsParser',
                     '--no-color', '--verbosity=0', stdout=out, stderr=err)
        call_command('import_payments', '--parser=django_pain.tests.commands.test_import_payments.DummyPaymentsParser',
                     '--no-color', '--verbosity=0', stdout=out, stderr=err)

        self.assertEqual(out.getvalue(), '')
        self.assertEqual(err.getvalue(), '')

    def test_input_from_files(self):
        """Test command call with input files."""
        out = StringIO()
        err = StringIO()
        with TempDirectory() as d:
            d.write('input_file.xml', b'<whatever></whatever>')
            call_command('import_payments',
                         '--parser=django_pain.tests.commands.test_import_payments.DummyPaymentsParser',
                         '--no-color', '--verbosity=0', '-', '/'.join([d.path, 'input_file.xml']),
                         stdout=out, stderr=err)

        self.assertEqual(out.getvalue(), '')
        self.assertEqual(err.getvalue(), '')

    def test_invalid_parser(self):
        """Test command call with invalid parser."""
        with self.assertRaises(CommandError) as cm:
            call_command('import_payments', '--parser=decimal.Decimal',
                         '--no-color')

        self.assertEqual(str(cm.exception), 'Parser argument has to be subclass of AbstractBankStatementParser.')
