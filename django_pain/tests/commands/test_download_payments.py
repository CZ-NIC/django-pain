#
# Copyright (C) 2020  CZ.NIC, z. s. p. o.
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
from typing import Any, Mapping
from unittest.mock import patch, sentinel

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from djmoney.money import Money
from freezegun import freeze_time
from teller.downloaders import BankStatementDownloader, TellerDownloadError
from teller.parsers import BankStatementParser
from teller.statement import BankStatement, Payment
from testfixtures import LogCapture

from django_pain.models import BankAccount, BankPayment


class DummyStatementDownloader(BankStatementDownloader):
    """Simple downloader that just returns fixed string"""

    statement = sentinel.statement

    def __init__(self, base_url: str, password: str, timeout: int = 3):
        expected_url = 'https://bank.test'
        expected_password = 'letmein'
        if base_url != expected_url:
            raise ValueError('Expected {} as base_url.'.format(expected_url))  # pragma: no cover
        if password != expected_password:
            raise ValueError('Expected {} as password.'.format(expected_password))  # pragma: no cover

        super().__init__(base_url, timeout)
        self.password = password

    def get_statement(self, start_date: date, end_date: date) -> str:
        return self.statement


class DummyStatementParser(BankStatementParser):
    """Simple downloader that just returns two fixed payments."""

    @classmethod
    def parse_string(cls, source: str) -> BankStatement:
        if source is not DummyStatementDownloader.statement:
            raise ValueError('Expected DummyStatementDownloader.statement as source.')  # pragma: no cover

        statement = BankStatement('1234567890/2010')
        payment_1 = Payment(identifier='PAYMENT_1',
                            counter_account='098765/4321',
                            amount=Money('42.00', 'CZK'),
                            transaction_date=date(2020, 9, 15),
                            variable_symbol='1234')
        payment_2 = Payment(identifier='PAYMENT_2',
                            counter_account='098765/4321',
                            amount=Money('370.00', 'CZK'),
                            transaction_date=date(2020, 9, 17))
        statement.add_payment(payment_1)
        statement.add_payment(payment_2)
        return statement


class DummyCreditCardSummaryParser(BankStatementParser):
    """Simple parser that just returns one credit card summary payment."""

    @classmethod
    def parse_string(self, source: str) -> BankStatement:
        statement = BankStatement('1234567890/2010')
        payment = Payment(identifier='PAYMENT_3',
                          counter_account='None/None',
                          amount=Money('42.00', 'CZK'),
                          transaction_date=date(2020, 9, 15),
                          constant_symbol='1176')
        statement.add_payment(payment)
        return statement


class DownloadPaymentsTest(TestCase):

    test_settings = {'DOWNLOADER': 'django_pain.tests.commands.test_download_payments.DummyStatementDownloader',
                     'PARSER': 'django_pain.tests.commands.test_download_payments.DummyStatementParser',
                     'DOWNLOADER_PARAMS': {'base_url': 'https://bank.test', 'password': 'letmein'}
                     }  # type: Mapping[str, Any]

    def setUp(self):
        account = BankAccount(account_number='1234567890/2010', currency='CZK')
        account.save()
        self.account = account
        self.log_handler = LogCapture('django_pain.management.commands.download_payments', propagate=False)

    def tearDown(self):
        self.log_handler.uninstall()

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_import_payments(self):
        out = StringIO()
        call_command('download_payments', '--no-color', '--verbosity=3', stdout=out)

        self.assertQuerysetEqual(BankPayment.objects.values_list(
            'identifier', 'account', 'counter_account_number', 'transaction_date', 'amount', 'amount_currency',
            'variable_symbol',
        ), [
            ('PAYMENT_1', self.account.pk, '098765/4321', date(2020, 9, 15), Decimal('42.00'), 'CZK', '1234'),
            ('PAYMENT_2', self.account.pk, '098765/4321', date(2020, 9, 17), Decimal('370.00'), 'CZK', ''),
        ], transform=tuple, ordered=False)

        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Saving payments for test.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @freeze_time("2020-01-09T23:30")
    @patch('django_pain.tests.commands.test_download_payments.DummyStatementDownloader.get_statement')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_default_parameters(self, mock_method):
        with override_settings(USE_TZ=False):
            call_command('download_payments', '--no-color')
        mock_method.assert_called_with(date(year=2020, month=1, day=2), date(year=2020, month=1, day=9))

        with override_settings(USE_TZ=True, TIME_ZONE='Europe/Prague'):
            call_command('download_payments', '--no-color')
        mock_method.assert_called_with(date(year=2020, month=1, day=3), date(year=2020, month=1, day=10))

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementDownloader.get_statement')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_parameters(self, mock_method):
        call_command('download_payments', '--no-color', '--start', '2020-01-01', '--end', '2020-01-21')

        end_date = date(2020, 1, 21)
        start_date = date(2020, 1, 1)
        mock_method.assert_called_with(start_date, end_date)

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_invalid_start(self):
        with self.assertRaisesRegex(CommandError, 'Error: argument -s/--start: invalid parse_date_safe value'):
            call_command('download_payments', '--no-color', '--start', 'abc')

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_invalid_end(self):
        with self.assertRaisesRegex(CommandError, 'Error: argument -e/--end: invalid parse_date_safe value'):
            call_command('download_payments', '--no-color', '--end', 'abc')

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_invalid_time_interval(self):
        with self.assertRaisesRegex(CommandError, 'Start date has to be lower or equal to the end date'):
            call_command('download_payments', '--no-color', '--start', '2020-09-02', '--end', '2020-09-01')

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementDownloader.__init__')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_downloader_init_error(self, mock_method):
        mock_method.side_effect = ValueError
        call_command('download_payments', '--no-color')
        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'ERROR', 'Could not init Downloader for test.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementDownloader.get_statement')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_download_error(self, mock_method):
        mock_method.side_effect = TellerDownloadError
        call_command('download_payments', '--no-color')
        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'ERROR', 'Downloading payments for test failed.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementParser.parse_string')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_parser_error(self, mock_method):
        mock_method.side_effect = ValueError('Something went wrong.')
        call_command('download_payments', '--no-color')
        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for test.'),
            ('django_pain.management.commands.download_payments', 'ERROR', 'Something went wrong.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementParser.parse_string')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_invalid_account(self, mock_method):
        statement = BankStatement('11111/11')
        mock_method.return_value = statement
        with self.assertRaisesRegex(CommandError, 'Bank account 11111/11 does not exist'):
            call_command('download_payments', '--no-color')

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_payment_already_exist(self):
        out = StringIO()
        err = StringIO()
        call_command('download_payments', '--no-color', '--verbosity=3', stdout=out)
        call_command('download_payments', '--no-color', '--verbosity=3', stdout=out, stderr=err)

        self.assertEqual(err.getvalue(), '')
        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Saving payments for test.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Saving payments for test.'),
            ('django_pain.management.commands.download_payments', 'INFO',
                'Payment ID PAYMENT_1 already exists - skipping.'),
            ('django_pain.management.commands.download_payments', 'INFO',
                'Payment ID PAYMENT_2 already exists - skipping.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Skipped 2 payments.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_quiet_command(self):
        out = StringIO()
        err = StringIO()
        call_command('download_payments', '--no-color', '--verbosity=0', stdout=out)
        call_command('download_payments', '--no-color', '--verbosity=0', stderr=err)

        self.assertEqual(out.getvalue(), '')
        self.assertEqual(err.getvalue(), '')

    @override_settings(PAIN_IMPORT_CALLBACKS=['django_pain.import_callbacks.skip_credit_card_transaction_summary'],
                       PAIN_DOWNLOADERS={'test': {**test_settings, 'PARSER':
                           'django_pain.tests.commands.test_download_payments.DummyCreditCardSummaryParser'}}) # noqa
    def test_import_callback_exception(self):
        out = StringIO()
        err = StringIO()
        call_command('download_payments', '--no-color', '--verbosity=3', stdout=out, stderr=err)

        self.assertEqual(out.getvalue().strip(), '')
        self.assertEqual(err.getvalue().strip().split('\n'), [
            'Payment ID PAYMENT_3 has not been saved due to the following errors:',
            'Payment is credit card transaction summary.',
        ])
        self.assertEqual(BankPayment.objects.count(), 0)
        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Saving payments for test.'),
            ('django_pain.management.commands.download_payments', 'WARNING',
                'Payment ID PAYMENT_3 has not been saved due to the following errors:'),
            ('django_pain.management.commands.download_payments', 'WARNING',
                'Payment is credit card transaction summary.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Skipped 1 payments.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )
