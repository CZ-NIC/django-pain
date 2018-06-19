"""Test process_payments command."""
from django.core.management import call_command
from django.test import TestCase, override_settings
from freezegun import freeze_time

from django_pain.constants import PaymentState
from django_pain.models import BankAccount, BankPayment
from django_pain.processors import AbstractPaymentProcessor
from django_pain.tests.utils import get_payment


class DummyTruePaymentsProcessor(AbstractPaymentProcessor):
    """Simple processor that just returns success."""

    def process_payments(self, payments):
        return [True]


class DummyFalsePaymentsProcessor(AbstractPaymentProcessor):
    """Simple processor that just returns failure."""

    def process_payments(self, payments):
        return [False]


@freeze_time('2018-01-01')
class TestProcessPayments(TestCase):
    """Test process_payments command."""

    def setUp(self):
        self.account = BankAccount(account_number='123456/7890', currency='CZK')
        self.account.save()
        self.payment = get_payment(identifier='PAYMENT_1', account=self.account, state=PaymentState.IMPORTED)
        self.payment.save()

    @override_settings(PAIN_PROCESSORS=['django_pain.tests.commands.test_process_payments.DummyTruePaymentsProcessor'])
    def test_payments_processed(self):
        """Test processed payments."""
        call_command('process_payments')

        self.assertQuerysetEqual(
            BankPayment.objects.values_list('identifier', 'account', 'state'),
            [('PAYMENT_1', self.account.pk, PaymentState.PROCESSED)],
            transform=tuple, ordered=False)

    @override_settings(PAIN_PROCESSORS=['django_pain.tests.commands.test_process_payments.DummyFalsePaymentsProcessor'])
    def test_payments_deferred(self):
        """Test deferred payments."""
        call_command('process_payments')

        self.assertQuerysetEqual(
            BankPayment.objects.values_list('identifier', 'account', 'state'),
            [('PAYMENT_1', self.account.pk, PaymentState.DEFERRED)],
            transform=tuple, ordered=False)

    @override_settings(PAIN_PROCESSORS=[
        'django_pain.tests.commands.test_process_payments.DummyFalsePaymentsProcessor',
        'django_pain.tests.commands.test_process_payments.DummyTruePaymentsProcessor'])
    def test_payments_from_to(self):
        """Test processed payments."""
        call_command('process_payments', '--from', '2017-01-01 00:00', '--to', '2017-01-02 00:00')

        print(self.payment.create_time)

        self.assertQuerysetEqual(
            BankPayment.objects.values_list('identifier', 'account', 'state'),
            [('PAYMENT_1', self.account.pk, PaymentState.IMPORTED)],
            transform=tuple, ordered=False)
