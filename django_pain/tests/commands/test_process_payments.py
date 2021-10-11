#
# Copyright (C) 2018-2021  CZ.NIC, z. s. p. o.
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
import threading
from collections import OrderedDict
from datetime import date
from io import StringIO
from queue import Queue
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from freezegun import freeze_time
from testfixtures import LogCapture, TempDirectory

from django_pain.constants import PaymentProcessingError, PaymentState, PaymentType
from django_pain.models import BankAccount, BankPayment
from django_pain.processors import PaymentProcessorError, ProcessPaymentResult
from django_pain.settings import SETTINGS, get_processor_class, get_processor_instance
from django_pain.tests.mixins import CacheResetMixin
from django_pain.tests.utils import DummyPaymentProcessor, get_payment


class DummyTruePaymentProcessor(DummyPaymentProcessor):
    """Simple processor that just returns success."""

    default_objective = 'True objective'

    def process_payments(self, payments):
        for payment in payments:
            yield ProcessPaymentResult(result=True)


class DummyFalsePaymentProcessor(DummyPaymentProcessor):
    """Simple processor that just returns failure."""

    def process_payments(self, payments):
        for payment in payments:
            yield ProcessPaymentResult(result=False)


class DummyTrueErrorPaymentProcessor(DummyPaymentProcessor):
    """Simple processor that returns success with processing error."""

    def process_payments(self, payments):
        for payment in payments:
            yield ProcessPaymentResult(result=True, error=PaymentProcessingError.DUPLICITY)


class DummyFalseErrorPaymentProcessor(DummyPaymentProcessor):
    """Simple processor that returns failure with processing error."""

    def process_payments(self, payments):
        for payment in payments:
            yield ProcessPaymentResult(result=False, error=PaymentProcessingError.DUPLICITY)


class DummyBrokenProcessor(DummyPaymentProcessor):
    """Simple processor that rises error every time it is called."""

    def process_payments(self, payments):
        # Processors may be lazy.
        yield self.fail()

    def fail(self):
        raise PaymentProcessorError('It is broken!')


@skipUnlessDBFeature('has_select_for_update')
class TestProcessPaymentsLocks(CacheResetMixin, TransactionTestCase):

    def setUp(self):
        self.tempdir = TempDirectory()
        self.account_in = BankAccount(account_number='123456/7890', currency='CZK')
        self.account_ex = BankAccount(account_number='987654/3210', currency='CZK')
        self.account_in.save()
        self.account_ex.save()
        get_payment(identifier='PAYMENT_1', account=self.account_in, state=PaymentState.READY_TO_PROCESS).save()
        get_payment(identifier='PAYMENT_2', account=self.account_ex, state=PaymentState.READY_TO_PROCESS).save()
        self.log_handler = LogCapture('django_pain.management.commands.process_payments', propagate=False)
        # Exception in a threads does not fail the test - wee need to collect it somemehow
        self.errors = Queue()  # type: Queue

    def tearDown(self):
        self.log_handler.uninstall()
        self.tempdir.cleanup()

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_processing_does_not_overwrite_locked_rows(self):
        processing_finished = threading.Event()
        query_finished = threading.Event()

        def target_processing():
            query_finished.wait()
            try:
                call_command('process_payments')
            except Exception as e:  # pragma: no cover
                self.errors.put(e)
                raise e
            finally:
                processing_finished.set()
                close_old_connections()

        def target_query():
            try:
                with transaction.atomic():
                    payment = BankPayment.objects.select_for_update().filter(identifier='PAYMENT_2').get()
                    payment.processor = 'manual'
                    payment.save()
                    query_finished.set()
                    processing_finished.wait()
            except Exception as e:  # pragma: no cover
                self.errors.put(e)
                raise e
            finally:
                query_finished.set()
                close_old_connections()

        threads = [threading.Thread(target=target_processing), threading.Thread(target=target_query)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(self.errors.empty())
        self.assertQuerysetEqual(
            BankPayment.objects.values_list('identifier', 'account', 'state', 'processor'),
            [('PAYMENT_1', self.account_in.pk, PaymentState.PROCESSED, 'dummy'),
                ('PAYMENT_2', self.account_ex.pk, PaymentState.READY_TO_PROCESS, 'manual')],
            transform=tuple, ordered=False)

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_processed_rows_not_overwritten(self):
        processing_started = threading.Event()
        query_finished = threading.Event()

        def mock_process_payments(payments):
            processing_started.set()
            query_finished.wait()
            return [ProcessPaymentResult(result=True) for p in payments]

        def target_processing():
            try:
                # cache may prevent mocking
                get_processor_instance.cache_clear()
                get_processor_class.cache_clear()
                with patch('django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor') as MockClass:
                    instance = MockClass.return_value
                    instance.process_payments = mock_process_payments
                    call_command('process_payments', '--exclude-accounts', self.account_ex.account_number)
            except Exception as e:  # pragma: no cover
                self.errors.put(e)
                raise e
            finally:
                processing_started.set()
                # mock might be cached
                get_processor_instance.cache_clear()
                get_processor_class.cache_clear()
                close_old_connections()

        def target_query():
            processing_started.wait()
            try:
                with transaction.atomic():
                    payments = BankPayment.objects.select_for_update(skip_locked=True).all()
                    for p in payments:
                        p.state = PaymentState.PROCESSED
                        p.processor = 'manual'
                        p.save()
            except Exception as e:  # pragma: no cover
                self.errors.put(e)
                raise e
            finally:
                query_finished.set()
                close_old_connections()

        threads = [threading.Thread(target=target_processing), threading.Thread(target=target_query)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(self.errors.empty())
        self.assertQuerysetEqual(
            BankPayment.objects.values_list('identifier', 'account', 'state', 'processor'),
            [('PAYMENT_1', self.account_in.pk, PaymentState.PROCESSED, 'dummy'),
                ('PAYMENT_2', self.account_ex.pk, PaymentState.PROCESSED, 'manual')],
            transform=tuple, ordered=False)


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

    @override_settings(PAIN_PROCESSORS=OrderedDict([
        ('broken', 'django_pain.tests.commands.test_process_payments.DummyBrokenProcessor'),
        ('dummy', 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor')]))
    def test_payments_processed_after_first_processor_fails(self):
        """Test payments processed after first_processor fails."""
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
                    'Processing payments with processor broken.'),
                ('django_pain.management.commands.process_payments', 'ERROR',
                 'Error occured while processing payments with processor broken: It is broken! Skipping.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Processing payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                    'Marking 0 unprocessed payments as DEFERRED.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
            )

    @override_settings(PAIN_PROCESSORS=OrderedDict([
        ('dummy_false', 'django_pain.tests.commands.test_process_payments.DummyFalsePaymentProcessor'),
        ('dummy_true', 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'),
    ]))
    def test_payments_from_to(self):
        """Test processed payments."""
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            call_command('process_payments', '--from', '2017-01-01 00:00', '--to', '2017-01-02 00:00')

            self.assertQuerysetEqual(
                BankPayment.objects.values_list('identifier', 'account', 'state', 'processor'),
                [('PAYMENT_1', self.account.pk, PaymentState.READY_TO_PROCESS, '')],
                transform=tuple, ordered=False)
            self.assertEqual(BankPayment.objects.first().objective, '')

    def test_invalid_date_raises_exception(self):
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            with self.assertRaises(CommandError):
                call_command('process_payments', '--from', '2017-01-32 00:00', '--to', '2017-02-01 00:00')
            with self.assertRaises(CommandError):
                call_command('process_payments', '--from', 'not a date', '--to', '2017-02-01 00:00')
            with self.assertRaises(CommandError):
                call_command('process_payments', '--from', '2017-01-01 00:00', '--to', '2017-01-32 00:00')
            with self.assertRaises(CommandError):
                call_command('process_payments', '--from', '2017-01-01 00:00', '--to', 'not a date')

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

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_card_payments_processed(self):
        get_payment(identifier='PAYMENT_2', account=self.account, state=PaymentState.READY_TO_PROCESS,
                    payment_type=PaymentType.CARD_PAYMENT, counter_account_number='', processor='dummy').save()
        get_payment(identifier='PAYMENT_3', account=self.account, state=PaymentState.READY_TO_PROCESS,
                    payment_type=PaymentType.CARD_PAYMENT, counter_account_number='', processor='dummy').save()
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            call_command('process_payments')
            self.assertQuerysetEqual(
                BankPayment.objects.values_list('identifier', 'state', 'processor'),
                [('PAYMENT_1', PaymentState.PROCESSED, 'dummy'),
                 ('PAYMENT_2', PaymentState.PROCESSED, 'dummy'),
                 ('PAYMENT_3', PaymentState.PROCESSED, 'dummy')],
                transform=tuple, ordered=False)
            self.assertEqual(BankPayment.objects.first().objective, 'True objective')
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Lock acquired.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing 3 unprocessed payments.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing card payments.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Processing card payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Processing payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Marking 0 unprocessed payments as DEFERRED.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
            )

    @override_settings(PAIN_PROCESSORS=OrderedDict([
        ('dummy', 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'),
        ('dummy_false', 'django_pain.tests.commands.test_process_payments.DummyFalsePaymentProcessor'),
    ]))
    def test_card_payments_unprocessed(self):
        get_payment(identifier='PAYMENT_2', account=self.account, state=PaymentState.READY_TO_PROCESS,
                    payment_type=PaymentType.CARD_PAYMENT, counter_account_number='', processor='dummy_false',
                    transaction_date=date(2018, 5, 10)).save()
        get_payment(identifier='PAYMENT_3', account=self.account, state=PaymentState.READY_TO_PROCESS,
                    payment_type=PaymentType.CARD_PAYMENT, counter_account_number='', processor='dummy',
                    transaction_date=date(2018, 5, 11)).save()
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            call_command('process_payments')
            self.assertQuerysetEqual(
                BankPayment.objects.values_list('identifier', 'state', 'processor'),
                [('PAYMENT_1', PaymentState.PROCESSED, 'dummy'),
                 ('PAYMENT_2', PaymentState.DEFERRED, 'dummy_false'),
                 ('PAYMENT_3', PaymentState.PROCESSED, 'dummy')],
                transform=tuple, ordered=False)
            self.assertEqual(BankPayment.objects.first().objective, 'True objective')
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Lock acquired.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing 3 unprocessed payments.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing card payments.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Processing card payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Processing card payments with processor dummy_false.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Saving payment %s as DEFERRED with error None.'
                 % BankPayment.objects.get(identifier='PAYMENT_2').uuid),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Processing payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Marking 0 unprocessed payments as DEFERRED.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
            )

    @override_settings(PAIN_PROCESSORS=OrderedDict([
        ('dummy', 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'),
        ('dummy_error', 'django_pain.tests.commands.test_process_payments.DummyFalseErrorPaymentProcessor'),
    ]))
    def test_card_payments_defferred(self):
        get_payment(identifier='PAYMENT_2', account=self.account, state=PaymentState.READY_TO_PROCESS,
                    payment_type=PaymentType.CARD_PAYMENT, counter_account_number='', processor='dummy_error',
                    transaction_date=date(2018, 5, 10)).save()
        get_payment(identifier='PAYMENT_3', account=self.account, state=PaymentState.READY_TO_PROCESS,
                    payment_type=PaymentType.CARD_PAYMENT, counter_account_number='', processor='dummy',
                    transaction_date=date(2018, 5, 11)).save()
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(self.tempdir.path, 'test.lock')):
            call_command('process_payments')
            self.assertQuerysetEqual(
                BankPayment.objects.values_list('identifier', 'state', 'processor'),
                [('PAYMENT_1', PaymentState.PROCESSED, 'dummy'),
                 ('PAYMENT_2', PaymentState.DEFERRED, 'dummy_error'),
                 ('PAYMENT_3', PaymentState.PROCESSED, 'dummy')],
                transform=tuple, ordered=False)
            self.assertEqual(BankPayment.objects.first().objective, 'True objective')
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Lock acquired.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing 3 unprocessed payments.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Processing card payments.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Processing card payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Processing card payments with processor dummy_error.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Saving payment %s as DEFERRED with error PaymentProcessingError.DUPLICITY.'
                 % BankPayment.objects.get(identifier='PAYMENT_2').uuid),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Processing payments with processor dummy.'),
                ('django_pain.management.commands.process_payments', 'INFO',
                 'Marking 0 unprocessed payments as DEFERRED.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
            )
