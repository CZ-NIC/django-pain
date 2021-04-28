#
# Copyright (C) 2020-2021  CZ.NIC, z. s. p. o.
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
import sys
from collections import OrderedDict, namedtuple
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any, Mapping, TextIO, Tuple, Union
from unittest import skipUnless
from unittest.mock import MagicMock, patch

import pytz
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.utils import IntegrityError
from django.test import TestCase, override_settings
from djmoney.money import Money
from freezegun import freeze_time
from testfixtures import LogCapture

from django_pain.management.commands.download_payments import Command as DownloadCommand
from django_pain.models import BankAccount, BankPayment, PaymentImportHistory

try:
    from teller.downloaders import BankStatementDownloader, RawStatement, TellerDownloadError
    from teller.parsers import BankStatementParser
    from teller.statement import BankStatement, Payment
except ImportError:
    BankStatementDownloader = object  # type: ignore
    BankStatementParser = object  # type: ignore
    BankStatement = object  # type: ignore
    Payment = object  # type: ignore
    RawStatement = object  # type: ignore


class DummyStatementDownloader(BankStatementDownloader):
    """Simple downloader that just returns fixed string"""

    statement = MagicMock(spec=StringIO)
    statement.name = None

    def __init__(self, base_url: str, password: str, timeout: int = 3):
        expected_url = 'https://bank.test'
        expected_password = 'letmein'
        if base_url != expected_url:
            raise ValueError('Expected {} as base_url.'.format(expected_url))  # pragma: no cover
        if password != expected_password:
            raise ValueError('Expected {} as password.'.format(expected_password))  # pragma: no cover

        super().__init__(base_url, timeout)
        self.password = password

    def _download_data(self, start_date: date, end_date: date) -> Tuple[RawStatement, ...]:
        return (self.statement,)


class DummyStatementParser(BankStatementParser):
    """Simple downloader that just returns two fixed payments."""

    @classmethod
    def parse_file(cls, source: Union[str, TextIO, Path], encoding='utf-8') -> BankStatement:
        cls._verify_source(source)

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

    @classmethod
    def _verify_source(cls, source: Union[str, TextIO, Path]) -> None:
        if source is not DummyStatementDownloader.statement:
            raise ValueError('Expected DummyStatementDownloader.statement as source.')  # pragma: no cover


class DummyCreditCardSummaryParser(BankStatementParser):
    """Simple parser that just returns one credit card summary payment."""

    @classmethod
    def parse_file(cls, source: Union[str, TextIO, Path], encoding='utf-8') -> BankStatement:
        statement = BankStatement('1234567890/2010')
        payment = Payment(identifier='PAYMENT_3',
                          counter_account='',
                          amount=Money('42.00', 'CZK'),
                          transaction_date=date(2020, 9, 15),
                          constant_symbol='1176')
        statement.add_payment(payment)
        return statement


@skipUnless('teller' in sys.modules, 'Can not run without teller library.')
@freeze_time("2020-01-09T23:30")
class DownloadPaymentsTest(TestCase):

    test_settings = {'DOWNLOADER': 'django_pain.tests.commands.test_download_payments.DummyStatementDownloader',
                     'PARSER': 'django_pain.tests.commands.test_download_payments.DummyStatementParser',
                     'DOWNLOADER_PARAMS': {'base_url': 'https://bank.test', 'password': 'letmein'}
                     }  # type: Mapping[str, Any]

    fake_date = datetime(2020, 1, 9, 23, 30)
    ImportHistoryRow = namedtuple('ImportHistoryRow', ('origin', 'start_datetime', 'filenames', 'errors', 'finished'))

    def assertImportHistory(self, *expected):
        self.assertQuerysetEqual(
            PaymentImportHistory.objects.values_list('origin', 'start_datetime', '_filenames', 'errors', 'finished'),
            expected,
            transform=tuple,
            ordered=False)

    def setUp(self):
        account = BankAccount(account_number='1234567890/2010', currency='CZK')
        account.save()
        self.account = account
        self.log_handler = LogCapture(('django_pain.management.commands.download_payments',
                                       'django_pain.management.command_mixins'), propagate=False)

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

        self.assertImportHistory(self.ImportHistoryRow('test', self.fake_date, None, 0, True))

        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Saving payments for test.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementDownloader.get_statements')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_default_parameters(self, mock_method):
        with override_settings(USE_TZ=False):
            call_command('download_payments', '--no-color')
        mock_method.assert_called_with(datetime(2020, 1, 2, 23, 30), datetime(2020, 1, 9, 23, 30))

        with override_settings(USE_TZ=True):
            call_command('download_payments', '--no-color')
        mock_method.assert_called_with(datetime(2020, 1, 2, 23, 30, tzinfo=pytz.utc),
                                       datetime(2020, 1, 9, 23, 30, tzinfo=pytz.utc))

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_default_start_date(self):
        mock_path = 'django_pain.tests.commands.test_download_payments.DummyStatementDownloader.get_statements'
        with override_settings(USE_TZ=False):
            with patch(mock_path) as mock_method:
                call_command('download_payments', '--no-color', '--end', '2020-01-09T20:30')
                mock_method.assert_called_with(datetime(2020, 1, 2, 20, 30), datetime(2020, 1, 9, 20, 30))

            with patch(mock_path) as mock_method:
                call_command('download_payments', '--no-color', '--end', '2020-01-09T20:30+01:00')
                mock_method.assert_called_with(datetime(2020, 1, 2, 19, 30, tzinfo=pytz.utc),
                                               datetime(2020, 1, 9, 19, 30, tzinfo=pytz.utc))

        with override_settings(USE_TZ=True, TIME_ZONE='UTC'):
            with patch(mock_path) as mock_method:
                call_command('download_payments', '--no-color', '--end', '2020-01-09T20:30')
                mock_method.assert_called_with(datetime(2020, 1, 2, 20, 30, tzinfo=pytz.utc),
                                               datetime(2020, 1, 9, 20, 30, tzinfo=pytz.utc))

            with patch(mock_path) as mock_method:
                call_command('download_payments', '--no-color', '--end', '2020-01-09T20:30+01:00')
                mock_method.assert_called_with(datetime(2020, 1, 2, 19, 30, tzinfo=pytz.utc),
                                               datetime(2020, 1, 9, 19, 30, tzinfo=pytz.utc))

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_default_end_date(self):
        mock_path = 'django_pain.tests.commands.test_download_payments.DummyStatementDownloader.get_statements'
        with override_settings(USE_TZ=False):
            with patch(mock_path) as mock_method:
                call_command('download_payments', '--no-color', '--start', '2020-01-05T20:30')
                mock_method.assert_called_with(datetime(2020, 1, 5, 20, 30), datetime(2020, 1, 9, 23, 30))

            with self.assertRaisesRegex(CommandError, 'Offset-naive used with offset-aware datetime'):
                call_command('download_payments', '--no-color', '--start', '2020-01-05T20:30+01:00')

        with override_settings(USE_TZ=True, TIME_ZONE='UTC'):
            with patch(mock_path) as mock_method:
                call_command('download_payments', '--no-color', '--start', '2020-01-05T20:30')
                mock_method.assert_called_with(datetime(2020, 1, 5, 20, 30, tzinfo=pytz.utc),
                                               datetime(2020, 1, 9, 23, 30, tzinfo=pytz.utc))

            with patch(mock_path) as mock_method:
                call_command('download_payments', '--no-color', '--start', '2020-01-05T20:30+01:00')
                mock_method.assert_called_with(datetime(2020, 1, 5, 19, 30, tzinfo=pytz.utc),
                                               datetime(2020, 1, 9, 23, 30, tzinfo=pytz.utc))

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementDownloader.get_statements')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_parameters(self, mock_method):
        call_command('download_payments', '--no-color', '--start', '2020-01-01T23:30', '--end', '2020-01-21T23:30')

        end_date = datetime(2020, 1, 21, 23, 30)
        start_date = datetime(2020, 1, 1, 23, 30)
        mock_method.assert_called_with(start_date, end_date)

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementDownloader.get_statements')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_parameters_timezone(self, mock_method):
        call_command('download_payments', '--no-color', '--start', '2020-01-01T23:30+01:00',
                     '--end', '2020-01-21T23:30+01:00')

        tzinfo = timezone(timedelta(hours=1), '+01:00')
        end_date = datetime(2020, 1, 21, 23, 30, tzinfo=tzinfo)
        start_date = datetime(2020, 1, 1, 23, 30, tzinfo=tzinfo)
        mock_method.assert_called_with(start_date, end_date)

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_invalid_start(self):
        with self.assertRaisesRegex(CommandError, 'Error: argument -s/--start: invalid parse_datetime_safe value'):
            call_command('download_payments', '--no-color', '--start', 'abc')

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_invalid_end(self):
        with self.assertRaisesRegex(CommandError, 'Error: argument -e/--end: invalid parse_datetime_safe value'):
            call_command('download_payments', '--no-color', '--end', 'abc')

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_invalid_time_interval(self):
        with self.assertRaisesRegex(CommandError, 'Start date has to be lower or equal to the end date'):
            call_command('download_payments', '--no-color', '--start', '2020-09-02T00:00', '--end', '2020-09-01T00:00')

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementDownloader.__init__')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_downloader_init_error(self, mock_method):
        mock_method.side_effect = ValueError
        call_command('download_payments', '--no-color')

        self.assertImportHistory(self.ImportHistoryRow('test', self.fake_date, None, None, False))

        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'ERROR', 'Could not init Downloader for test.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementDownloader.get_statements')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_download_error(self, mock_method):
        mock_method.side_effect = TellerDownloadError
        call_command('download_payments', '--no-color')

        self.assertImportHistory(self.ImportHistoryRow('test', self.fake_date, None, None, False))

        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'ERROR', 'Downloading payments for test failed.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementParser.parse_file')
    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_parser_error(self, mock_method):
        mock_method.side_effect = ValueError('Something went wrong.')
        call_command('download_payments', '--no-color')

        self.assertImportHistory(self.ImportHistoryRow('test', self.fake_date, None, 1, True))

        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for test.'),
            ('django_pain.management.commands.download_payments', 'ERROR', 'Something went wrong.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @patch('django_pain.tests.commands.test_download_payments.DummyStatementParser.parse_file')
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

        self.assertImportHistory(self.ImportHistoryRow('test', self.fake_date, None, 0, True),
                                 self.ImportHistoryRow('test', self.fake_date, None, 0, True))

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
            ('django_pain.management.command_mixins', 'INFO', 'Payment ID PAYMENT_1 already exists - skipping.'),
            ('django_pain.management.command_mixins', 'INFO', 'Payment ID PAYMENT_2 already exists - skipping.'),
            ('django_pain.management.command_mixins', 'INFO', 'Skipped 2 payments.'),
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

        self.assertImportHistory(self.ImportHistoryRow('test', self.fake_date, None, 1, True))

        self.assertEqual(BankPayment.objects.count(), 0)
        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Saving payments for test.'),
            ('django_pain.management.command_mixins', 'WARNING',
                'Payment ID PAYMENT_3 has not been saved due to the following errors:'),
            ('django_pain.management.command_mixins', 'WARNING', 'Payment is credit card transaction summary.'),
            ('django_pain.management.command_mixins', 'INFO', '1 payments not saved due to errors.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    @patch('django_pain.management.command_mixins.SavePaymentsMixin._save_if_not_exists')
    def test_validation_error(self, save_method):
        out = StringIO()
        err = StringIO()

        save_method.side_effect = ValidationError(['It is broken', 'It is even more broken'])
        call_command('download_payments', '--no-color', '--verbosity=3', stdout=out, stderr=err)

        self.assertEqual(out.getvalue().strip(), '')
        self.assertEqual(err.getvalue().strip().split('\n'), [
            'Payment ID PAYMENT_1 has not been saved due to the following errors:',
            'It is broken',
            'It is even more broken',
            'Payment ID PAYMENT_2 has not been saved due to the following errors:',
            'It is broken',
            'It is even more broken',
        ])

        self.assertImportHistory(self.ImportHistoryRow('test', self.fake_date, None, 2, True))

        self.assertEqual(BankPayment.objects.count(), 0)
        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Saving payments for test.'),
            ('django_pain.management.command_mixins', 'WARNING',
                'Payment ID PAYMENT_1 has not been saved due to the following errors:'),
            ('django_pain.management.command_mixins', 'WARNING', 'It is broken\nIt is even more broken'),
            ('django_pain.management.command_mixins', 'WARNING',
                'Payment ID PAYMENT_2 has not been saved due to the following errors:'),
            ('django_pain.management.command_mixins', 'WARNING', 'It is broken\nIt is even more broken'),
            ('django_pain.management.command_mixins', 'INFO', '2 payments not saved due to errors.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    @patch('django_pain.management.command_mixins.SavePaymentsMixin._save_if_not_exists')
    def test_validation_error_dict(self, save_method):
        out = StringIO()
        err = StringIO()

        save_method.side_effect = ValidationError(OrderedDict(here='It is broken', there='It is even more broken'))
        call_command('download_payments', '--no-color', '--verbosity=3', stdout=out, stderr=err)

        self.assertEqual(out.getvalue().strip(), '')
        # This is not nice but py35 does not keep the order of items in the dict
        self.assertEqual(set(err.getvalue().strip().split('\n')), set([
            'Payment ID PAYMENT_1 has not been saved due to the following errors:',
            'here: It is broken',
            'there: It is even more broken',
            'Payment ID PAYMENT_2 has not been saved due to the following errors:',
            'here: It is broken',
            'there: It is even more broken',
        ]))

        self.assertImportHistory(self.ImportHistoryRow('test', self.fake_date, None, 2, True))

        self.assertEqual(BankPayment.objects.count(), 0)
        self.log_handler.check_present(
            ('django_pain.management.command_mixins', 'WARNING',
                'Payment ID PAYMENT_1 has not been saved due to the following errors:'),
            ('django_pain.management.command_mixins', 'WARNING', 'here: It is broken'),
            ('django_pain.management.command_mixins', 'WARNING', 'there: It is even more broken'),
            ('django_pain.management.command_mixins', 'WARNING',
                'Payment ID PAYMENT_2 has not been saved due to the following errors:'),
            ('django_pain.management.command_mixins', 'WARNING', 'here: It is broken'),
            ('django_pain.management.command_mixins', 'WARNING', 'there: It is even more broken'),
            ('django_pain.management.command_mixins', 'INFO', '2 payments not saved due to errors.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.'),
            order_matters=False
        )

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    @patch('django_pain.management.command_mixins.SavePaymentsMixin._save_if_not_exists')
    def test_integrity_error(self, save_method):
        out = StringIO()
        err = StringIO()

        save_method.side_effect = IntegrityError('It is broken')
        call_command('download_payments', '--no-color', '--verbosity=3', stdout=out, stderr=err)

        self.assertEqual(out.getvalue().strip(), '')
        self.assertEqual(err.getvalue().strip().split('\n'), [
            'Payment ID PAYMENT_1 has not been saved due to the following errors:',
            'It is broken',
            'Payment ID PAYMENT_2 has not been saved due to the following errors:',
            'It is broken',
        ])

        self.assertImportHistory(self.ImportHistoryRow('test', self.fake_date, None, 2, True))

        self.assertEqual(BankPayment.objects.count(), 0)
        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: test'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for test.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Saving payments for test.'),
            ('django_pain.management.command_mixins', 'WARNING',
                'Payment ID PAYMENT_1 has not been saved due to the following errors:'),
            ('django_pain.management.command_mixins', 'WARNING', 'It is broken'),
            ('django_pain.management.command_mixins', 'WARNING',
                'Payment ID PAYMENT_2 has not been saved due to the following errors:'),
            ('django_pain.management.command_mixins', 'WARNING', 'It is broken'),
            ('django_pain.management.command_mixins', 'INFO', '2 payments not saved due to errors.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @override_settings(PAIN_DOWNLOADERS=OrderedDict([('earth', test_settings),
                                                     ('mars', test_settings),
                                                     ('pluto', test_settings)]))
    def test_select_subset_of_banks(self):
        out = StringIO()
        err = StringIO()
        call_command('download_payments', '--verbosity=3', '--downloader', 'earth', '--downloader', 'mars',
                     stdout=out, stderr=err)

        self.log_handler.check(
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments started.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: earth'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for earth.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for earth.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Saving payments for earth.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Processing: mars'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Downloading payments for mars.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Parsing payments for mars.'),
            ('django_pain.management.commands.download_payments', 'DEBUG', 'Saving payments for mars.'),
            ('django_pain.management.command_mixins', 'INFO', 'Payment ID PAYMENT_1 already exists - skipping.'),
            ('django_pain.management.command_mixins', 'INFO', 'Payment ID PAYMENT_2 already exists - skipping.'),
            ('django_pain.management.command_mixins', 'INFO', 'Skipped 2 payments.'),
            ('django_pain.management.commands.download_payments', 'INFO', 'Command download_payments finished.')
        )

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    def test_invalid_cli_option_raises_error(self):
        out = StringIO()
        err = StringIO()
        with self.assertRaisesRegex(CommandError, "Error: argument -d/--downloader: invalid choice: 'invalid'"):
            call_command('download_payments', '--verbosity=3', '--downloader', 'test', '--downloader', 'invalid',
                         stdout=out, stderr=err)

    def test_from_payment_data_class(self):
        payment_data = Payment()
        payment_data.identifier = 'abc123'
        payment_data.transaction_date = date(2020, 9, 1)
        payment_data.counter_account = '12345/678'
        payment_data.name = 'John Doe'
        payment_data.amount = Money(1, 'CZK')
        payment_data.description = 'Hello!'
        payment_data.constant_symbol = '123'
        payment_data.variable_symbol = '456'
        payment_data.specific_symbol = '789'

        account = BankAccount(account_number='1234567890/2010')
        model = DownloadCommand()._payment_from_data_class(account, payment_data)

        self.assertEqual(model.identifier, payment_data.identifier)
        self.assertEqual(model.account, account)
        self.assertEqual(model.transaction_date, payment_data.transaction_date)
        self.assertEqual(model.counter_account_number, payment_data.counter_account)
        self.assertEqual(model.counter_account_name, payment_data.name)
        self.assertEqual(model.amount, payment_data.amount)
        self.assertEqual(model.description, payment_data.description)
        self.assertEqual(model.constant_symbol, payment_data.constant_symbol)
        self.assertEqual(model.variable_symbol, payment_data.variable_symbol)
        self.assertEqual(model.specific_symbol, payment_data.specific_symbol)

    def test_from_payment_data_class_blank_values(self):
        payment_data = Payment()
        payment_data.identifier = 'abc123'
        payment_data.transaction_date = date(2020, 9, 1)
        payment_data.counter_account = None
        payment_data.name = None
        payment_data.amount = Money(1, 'CZK')
        payment_data.description = None
        payment_data.constant_symbol = None
        payment_data.variable_symbol = None
        payment_data.specific_symbol = None

        account = BankAccount(account_number='1234567890/2010')
        model = DownloadCommand()._payment_from_data_class(account, payment_data)

        self.assertEqual(model.identifier, payment_data.identifier)
        self.assertEqual(model.account, account)
        self.assertEqual(model.transaction_date, payment_data.transaction_date)
        self.assertEqual(model.counter_account_number, '')
        self.assertEqual(model.counter_account_name, '')
        self.assertEqual(model.amount, payment_data.amount)
        self.assertEqual(model.description, '')
        self.assertEqual(model.constant_symbol, '')
        self.assertEqual(model.variable_symbol, '')
        self.assertEqual(model.specific_symbol, '')

    @override_settings(PAIN_DOWNLOADERS={'test': test_settings})
    @patch('django_pain.tests.commands.test_download_payments.DummyStatementDownloader._download_data')
    @patch('django_pain.tests.commands.test_download_payments.DummyStatementParser._verify_source')
    def test_payment_history_filenames(self, mock_verify, mock_download):
        mock_download.return_value = [RawStatement(content='Raw statement content', name='file_1.txt'),
                                      RawStatement(content='Raw statement content', name='file_2.txt')]

        out = StringIO()
        call_command('download_payments', '--no-color', '--verbosity=3', stdout=out)

        self.assertImportHistory(self.ImportHistoryRow('test', self.fake_date, 'file_1.txt;file_2.txt', 0, True))
