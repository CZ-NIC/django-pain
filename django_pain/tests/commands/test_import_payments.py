#
# Copyright (C) 2018-2022  CZ.NIC, z. s. p. o.
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
from collections import namedtuple
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from typing import List, Optional, Tuple, cast

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from djmoney.money import Money
from freezegun import freeze_time
from testfixtures import LogCapture, TempDirectory

from django_pain.models import BankAccount, BankPayment, PaymentImportHistory
from django_pain.parsers import AbstractBankStatementParser
from django_pain.tests.utils import get_payment


def modify_payment_callback(payment: BankPayment) -> Optional[BankPayment]:
    payment.identifier = payment.identifier + '_mod'
    return payment


def skip_payment_callback(payment: BankPayment) -> Optional[BankPayment]:
    return None


def raise_exception_callback(payment: BankPayment) -> Optional[BankPayment]:
    raise ValidationError('Raised by callback')


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


@freeze_time("2020-01-09T23:30")
class TestImportPayments(TestCase):
    """Test import_payments command."""

    fake_date = datetime(2020, 1, 9, 23, 30)
    ImportHistoryRow = namedtuple('ImportHistoryRow', ('origin', 'start_datetime', 'filenames', 'errors', 'finished'))

    def assertImportHistory(self, *expected):
        self.assertQuerysetEqual(
            PaymentImportHistory.objects.values_list('origin', 'start_datetime', '_filenames', 'errors', 'finished'),
            expected,
            transform=tuple,
            ordered=False)

    def setUp(self):
        account = BankAccount(account_number='123456/7890', currency='CZK')
        account.save()
        self.account = account
        self.log_handler = LogCapture(cast(Tuple[str], (
            'django_pain.management.commands.import_payments',
            'django_pain.management.command_mixins',
        )), propagate=False)

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

        self.assertImportHistory(self.ImportHistoryRow('transproc', self.fake_date, '-', 0, True))

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
        self.assertImportHistory(self.ImportHistoryRow('transproc', self.fake_date, '-', 1, False))
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

        self.assertImportHistory(self.ImportHistoryRow('transproc', self.fake_date, '-', 0, True),
                                 self.ImportHistoryRow('transproc', self.fake_date, '-', 0, True))

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
            ('django_pain.management.command_mixins', 'INFO', 'Payment ID PAYMENT_1 already exists - skipping.'),
            ('django_pain.management.command_mixins', 'INFO', 'Payment ID PAYMENT_2 already exists - skipping.'),
            ('django_pain.management.command_mixins', 'INFO', 'Skipped 2 payments.'),
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

    def _test_callback(self, callbacks: List[str], errors: int, imported_payments: List[Tuple[str]],
                       out_value: List[str], err_value: List[str], log: List[Tuple[str, str, str]]):
        out = StringIO()
        err = StringIO()
        with override_settings(PAIN_IMPORT_CALLBACKS=callbacks):
            call_command('import_payments',
                         '--parser=django_pain.tests.commands.test_import_payments.DummyPaymentsParser',
                         '--no-color', '--verbosity=3', stdout=out, stderr=err)

        self.assertQuerysetEqual(
            BankPayment.objects.values_list('identifier'),
            imported_payments,
            transform=tuple,
            ordered=False
        )
        self.assertEqual(out.getvalue().strip().split('\n'), out_value)
        self.assertEqual(err.getvalue().strip().split('\n'), err_value)
        self.assertImportHistory(self.ImportHistoryRow('transproc', self.fake_date, '-', errors, True))
        self.log_handler.check(*log)

    def test_import_callback_modifies_payments(self):
        log = [
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments started.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Importing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Parsing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Saving 2 payments from - to database.'),
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments finished.'),
        ]
        self. _test_callback(
            callbacks=['django_pain.tests.commands.test_import_payments.modify_payment_callback'],
            errors=0,
            imported_payments=[
                ('PAYMENT_1_mod',),
                ('PAYMENT_2_mod',)
            ],
            out_value=[
                'Payment ID PAYMENT_1_mod has been imported.',
                'Payment ID PAYMENT_2_mod has been imported.',
            ],
            err_value=[''],
            log=log
        )

    def test_import_callback_skip_payments(self):
        log = [
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments started.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Importing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Parsing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Saving 2 payments from - to database.'),
            ('django_pain.management.command_mixins', 'INFO',
             'Payment ID PAYMENT_1 skipped by callback skip_payment_callback'),
            ('django_pain.management.command_mixins', 'INFO',
             'Payment ID PAYMENT_2 skipped by callback skip_payment_callback'),
            ('django_pain.management.command_mixins', 'INFO', 'Skipped 2 payments.'),
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments finished.'),
        ]
        self. _test_callback(
            callbacks=['django_pain.tests.commands.test_import_payments.skip_payment_callback'],
            errors=0,
            imported_payments=[],
            out_value=[
                'Payment ID PAYMENT_1 was skipped.',
                'Payment ID PAYMENT_2 was skipped.',
            ],
            err_value=[''],
            log=log
        )

    def test_import_callback_exception(self):
        log = [
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments started.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Importing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Parsing payments from -.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Saving 2 payments from - to database.'),
            ('django_pain.management.command_mixins', 'WARNING',
                'Payment ID PAYMENT_1 has not been saved due to the following errors:'),
            ('django_pain.management.command_mixins', 'WARNING', 'Raised by callback'),
            ('django_pain.management.command_mixins', 'WARNING',
                'Payment ID PAYMENT_2 has not been saved due to the following errors:'),
            ('django_pain.management.command_mixins', 'WARNING', 'Raised by callback'),
            ('django_pain.management.command_mixins', 'INFO', '2 payments not saved due to errors.'),
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments finished.'),
        ]
        self. _test_callback(
            callbacks=['django_pain.tests.commands.test_import_payments.raise_exception_callback'],
            errors=2,
            imported_payments=[],
            out_value=[''],
            err_value=[
                'Payment ID PAYMENT_1 has not been saved due to the following errors:',
                'Raised by callback',
                'Payment ID PAYMENT_2 has not been saved due to the following errors:',
                'Raised by callback',
            ],
            log=log
        )

    def test_file_not_found(self):
        """Test command call with invalid file name."""
        with self.assertRaises(CommandError) as cm:
            call_command('import_payments',
                         '--parser=django_pain.tests.commands.test_import_payments.DummyPaymentsParser',
                         '--no-color', 'non_existent_file')

        self.assertEqual(str(cm.exception), "[Errno 2] No such file or directory: 'non_existent_file'")

        self.log_handler.check(
            ('django_pain.management.commands.import_payments', 'INFO', 'Command import_payments started.'),
            ('django_pain.management.commands.import_payments', 'DEBUG', 'Importing payments from non_existent_file.'),
            ('django_pain.management.commands.import_payments', 'INFO',
                "File non_existent_file could not be open: [Errno 2] No such file or directory: 'non_existent_file'."),
        )
