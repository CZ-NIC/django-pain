"""Test process_payments command."""
import fcntl
import os
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from freezegun import freeze_time
from testfixtures import LogCapture, tempdir

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
        self.account = BankAccount(account_number='123456/7890', currency='CZK')
        self.account.save()
        payment = get_payment(identifier='PAYMENT_1', account=self.account, state=PaymentState.IMPORTED)
        payment.save()
        self.log_handler = LogCapture('django_pain.management.commands.process_payments', propagate=False)

    def tearDown(self):
        self.log_handler.uninstall()

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_payments_processed(self):
        """Test processed payments."""
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
            ('django_pain.management.commands.process_payments', 'INFO', 'Processing payments with processor dummy.'),
            ('django_pain.management.commands.process_payments', 'INFO', 'Marking 0 unprocessed payments as DEFERRED.'),
            ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
        )

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyFalsePaymentProcessor'})
    def test_payments_deferred(self):
        """Test deferred payments."""
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
            ('django_pain.management.commands.process_payments', 'INFO', 'Processing payments with processor dummy.'),
            ('django_pain.management.commands.process_payments', 'INFO', 'Marking 1 unprocessed payments as DEFERRED.'),
            ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
        )

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyTrueErrorPaymentProcessor'})
    def test_payments_processed_with_error(self):
        """Test processed payments with processing error."""
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
            ('django_pain.management.commands.process_payments', 'INFO', 'Processing payments with processor dummy.'),
            ('django_pain.management.commands.process_payments', 'INFO', 'Marking 0 unprocessed payments as DEFERRED.'),
            ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
        )

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.commands.test_process_payments.DummyFalseErrorPaymentProcessor'})
    def test_payments_deferred_with_error(self):
        """Test deferred payments with processing error."""
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
            ('django_pain.management.commands.process_payments', 'INFO', 'Processing payments with processor dummy.'),
            ('django_pain.management.commands.process_payments', 'INFO',
                'Saving payment %s as DEFERRED with error PaymentProcessingError.DUPLICITY.'
                % BankPayment.objects.first().uuid),
            ('django_pain.management.commands.process_payments', 'INFO', 'Marking 0 unprocessed payments as DEFERRED.'),
            ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments finished.'),
        )

    @override_settings(PAIN_PROCESSORS={
        'dummy_false': 'django_pain.tests.commands.test_process_payments.DummyFalsePaymentProcessor',
        'dummy_true': 'django_pain.tests.commands.test_process_payments.DummyTruePaymentProcessor'})
    def test_payments_from_to(self):
        """Test processed payments."""
        call_command('process_payments', '--from', '2017-01-01 00:00', '--to', '2017-01-02 00:00')

        self.assertQuerysetEqual(
            BankPayment.objects.values_list('identifier', 'account', 'state', 'processor'),
            [('PAYMENT_1', self.account.pk, PaymentState.IMPORTED, '')],
            transform=tuple, ordered=False)
        self.assertEqual(BankPayment.objects.first().objective, '')

    @tempdir()
    def test_lock(self, tempdir):
        """Test process payments lock."""
        with override_settings(PAIN_PROCESS_PAYMENTS_LOCK_FILE=os.path.join(tempdir.path, 'test.lock')):
            lock = open(SETTINGS.process_payments_lock_file, 'a')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            out = StringIO()
            err = StringIO()
            call_command('process_payments', '--no-color', stdout=out, stderr=err)
            self.assertEqual(out.getvalue(), '')
            self.assertEqual(err.getvalue(), 'Command process_payments is already running. Terminating.\n')
            self.assertQuerysetEqual(
                BankPayment.objects.values_list('identifier', 'account', 'state', 'processor'),
                [('PAYMENT_1', self.account.pk, PaymentState.IMPORTED, '')],
                transform=tuple, ordered=False)
            self.log_handler.check(
                ('django_pain.management.commands.process_payments', 'INFO', 'Command process_payments started.'),
                ('django_pain.management.commands.process_payments', 'INFO', 'Command already running. Terminating.'),
            )
