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

"""Test process_payments command."""
import fcntl
import os
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from freezegun import freeze_time
from testfixtures import LogCapture, TempDirectory

from django_pain.constants import PaymentProcessingError, PaymentState
from django_pain.models import BankAccount, BankPayment
from django_pain.processors import ProcessPaymentResult
from django_pain.settings import SETTINGS
from django_pain.tests.mixins import CacheResetMixin
from django_pain.tests.utils import DummyPaymentProcessor, get_payment


class DummyTruePaymentProcessor(DummyPaymentProcessor):
    """Simple processor that just returns success."""

    default_objective = 'True objective'

    def process_payments(self, payments):
        return [ProcessPaymentResult(result=True)]


class DummyFalsePaymentProcessor(DummyPaymentProcessor):
    """Simple processor that just returns failure."""

    def process_payments(self, payments):
        return [ProcessPaymentResult(result=False)]


class DummyTrueErrorPaymentProcessor(DummyPaymentProcessor):
    """Simple processor that returns success with processing error."""

    def process_payments(self, payments):
        return [ProcessPaymentResult(result=True, error=PaymentProcessingError.DUPLICITY)]


class DummyFalseErrorPaymentProcessor(DummyPaymentProcessor):
    """Simple processor that returns failure with processing error."""

    def process_payments(self, payments):
        return [ProcessPaymentResult(result=False, error=PaymentProcessingError.DUPLICITY)]


@freeze_time('2018-01-01')
class TestProcessPayments(CacheResetMixin, TestCase):
    """Test process_payments command."""

    def setUp(self):
        super().setUp()
        self.tempdir = TempDirectory()
        self.account = BankAccount(account_number='123456/7890', currency='CZK')
        self.account.save()
        payment = get_payment(identifier='PAYMENT_1', account=self.account, state=PaymentState.READY_TO_PROCESS)
        payment.save()
        self.log_handler = LogCapture('django_pain.management.commands.process_payments', propagate=False)

    def tearDown(self):
        self.log_handler.uninstall()
        self.tempdir.cleanup()

    def _test_non_existing_account(self, param_name):
        """
        Test non existing account.

        param_name should contain either '--include-accounts' or '--exclude-accounts'
        """
        BankAccount.objects.create(account_number='987654/3210', currency='CZK')
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            out = StringIO()
            err = StringIO()
            with self.assertRaises(CommandError):
                call_command('process_payments', param_name, 'xxxxxx/xxxx,yyyyyy/yyyy,987654/3210', stdout=out,
                             stderr=err)

            self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), '')
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Lock acquired.'),
                ('django_pain.management.commands.process_payments', 'ERROR',
                 'Following accounts do not exist: xxxxxx/xxxx, yyyyyy/yyyy. Terminating.'),
            )

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_payments_processed(self):
        """Test processed payments."""
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            call_command('process_payments')

            self.assertQuerysetEqual(
                BankPayment.objects.values_list('identifier', 'account', 'state', 'processor'),
                [('PAYMENT_1', self.account.pk, PaymentState.PROCESSED, 'dummy')],
                transform=tuple, ordered=False)
            self.assertEqual(BankPayment.objects.first().objective, 'True objective')
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Lock acquired.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing 1 unprocessed payments.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Processing payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Marking 0 unprocessed payments as DEFERRED.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
            )

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyFalsePaymentProcessor'})
    def test_payments_deferred(self):
        """Test deferred payments."""
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            call_command('process_payments')

            self.assertQuerysetEqual(
                BankPayment.objects.values_list('identifier', 'account', 'state', 'processor'),
                [('PAYMENT_1', self.account.pk, PaymentState.DEFERRED, '')],
                transform=tuple, ordered=False)
            self.assertEqual(BankPayment.objects.first().objective, '')
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Lock acquired.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing 1 unprocessed payments.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Processing payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Marking 1 unprocessed payments as DEFERRED.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
            )

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTrueErrorPaymentProcessor'})
    def test_payments_processed_with_error(self):
        """Test processed payments with processing error."""
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            call_command('process_payments')

            self.assertQuerysetEqual(
                BankPayment.objects.values_list('identifier', 'account', 'state', 'processor', 'processing_error'),
                [('PAYMENT_1', self.account.pk, PaymentState.PROCESSED, 'dummy', PaymentProcessingError.DUPLICITY)],
                transform=tuple, ordered=False)
            self.assertEqual(BankPayment.objects.first().objective, 'Dummy objective')
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Lock acquired.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing 1 unprocessed payments.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Processing payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Marking 0 unprocessed payments as DEFERRED.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
            )

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyFalseErrorPaymentProcessor'})
    def test_payments_deferred_with_error(self):
        """Test deferred payments with processing error."""
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            call_command('process_payments')

            self.assertQuerysetEqual(
                BankPayment.objects.values_list('identifier', 'account', 'state', 'processor', 'processing_error'),
                [('PAYMENT_1', self.account.pk, PaymentState.DEFERRED, 'dummy', PaymentProcessingError.DUPLICITY)],
                transform=tuple, ordered=False)
            self.assertEqual(BankPayment.objects.first().objective, 'Dummy objective')
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Lock acquired.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing 1 unprocessed payments.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Processing payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Saving payment %s as DEFERRED with error PaymentProcessingError.DUPLICITY.'
                    % BankPayment.objects.first().uuid),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Marking 0 unprocessed payments as DEFERRED.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
            )

    @override_settings(PAIN_PROCESSORS={
        'dummy_false': 'django_pain.tests.commands.test_process_payments.DummyFalsePaymentProcessor',
        'dummy_true': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_payments_from_to(self):
        """Test processed payments."""
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            call_command('process_payments', '--from', '2017-01-01 00:00', '--to', '2017-01-02 00:00')

            self.assertQuerysetEqual(
                BankPayment.objects.values_list('identifier', 'account', 'state', 'processor'),
                [('PAYMENT_1', self.account.pk, PaymentState.READY_TO_PROCESS, '')],
                transform=tuple, ordered=False)
            self.assertEqual(BankPayment.objects.first().objective, '')

    def test_lock(self):
        """Test process payments lock."""
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            lock = open(SETTINGS.process_payments_lock_file, 'a')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            out = StringIO()
            err = StringIO()
            call_command('process_payments', '--no-color', stdout=out, stderr=err)
            self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), 'Command process_payments is already running. Terminating.\n')
            self.assertQuerysetEqual(
                BankPayment.objects.values_list('identifier', 'account', 'state', 'processor'),
                [('PAYMENT_1', self.account.pk, PaymentState.READY_TO_PROCESS, '')],
                transform=tuple, ordered=False)
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'WARNING', 'Command already running. Terminating.')
            )

    def test_invalid_lock(self):
        """Test process payments with invalid lock file."""
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            os.mkdir(SETTINGS.process_payments_lock_file, mode=0o0)
            out = StringIO()
            err = StringIO()
            with self.assertRaisesRegexp(CommandError, r'^Error occured while opening lockfile .*/test.lock:.*Is a '
                                                       r'directory: .*\. Terminating\.$'):
                call_command('process_payments', '--no-color', stdout=out, stderr=err)
            self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), '')
            self.assertEqual(len(self.log_handler.actual()), 2)
            self.assertEqual(
                self.log_handler.actual()[0],
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
            )
            self.assertEqual(
                self.log_handler.actual()[1][:2],
                ('django_pain.management.commands.process_payments', 'ERROR')
            )
            self.assertRegex(
                self.log_handler.actual()[1][2],
                r'^Error occured while opening lockfile .*/test.lock:.*Is a directory.*Terminating\.$'
            )
            os.chmod(SETTINGS.process_payments_lock_file, 0o755)

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_exclusion_in_payment_processing(self):
        """Test excluding accounts from payment processing"""
        account2 = BankAccount(account_number='987654/3210', currency='CZK')
        account2.save()
        get_payment(identifier='PAYMENT_2', account=self.account, state=PaymentState.READY_TO_PROCESS).save()
        get_payment(identifier='PAYMENT_3', account=account2, state=PaymentState.READY_TO_PROCESS).save()
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            out = StringIO()
            err = StringIO()
            call_command('process_payments', '--exclude-accounts', '987654/3210', stdout=out, stderr=err)

            self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), '')
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Lock acquired.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing 2 unprocessed payments.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Processing payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Marking 0 unprocessed payments as DEFERRED.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
            )

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_exclusion_of_non_existing_account_in_payment_processing(self):
        """Test excluding non-existing accounts from payment processing"""
        self._test_non_existing_account('--exclude-accounts')

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_inclusion_in_payment_processing(self):
        """Test including accounts from payment processing"""
        account2 = BankAccount(account_number='987654/3210', currency='CZK')
        account2.save()
        get_payment(identifier='PAYMENT_2', account=self.account, state=PaymentState.READY_TO_PROCESS).save()
        get_payment(identifier='PAYMENT_3', account=account2, state=PaymentState.READY_TO_PROCESS).save()
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            out = StringIO()
            err = StringIO()
            call_command('process_payments', '--include-accounts', '123456/7890', stdout=out, stderr=err)

            self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), '')
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Lock acquired.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing 2 unprocessed payments.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Processing payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Marking 0 unprocessed payments as DEFERRED.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
            )

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_inclusion_of_non_existing_account_in_payment_processing(self):
        """Test including non-existing accounts from payment processing"""
        self._test_non_existing_account('--include-accounts')
