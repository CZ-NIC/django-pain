"""Test ignore payment processor."""
from django.test import SimpleTestCase

from django_pain.processors import IgnorePaymentProcessor, ProcessPaymentResult
from django_pain.tests.utils import get_payment


class TestIgnorePaymentProcessor(SimpleTestCase):
    """Test IgnorePaymentProcessor."""

    def setUp(self):
        self.processor = IgnorePaymentProcessor()
        self.payment = get_payment()

    def test_process_payments(self):
        """Test process_payments."""
        self.assertEqual(list(self.processor.process_payments([self.payment])),
                         [ProcessPaymentResult(False)])

    def test_assign_payment(self):
        """Test assign_payment."""
        self.assertEqual(self.processor.assign_payment(self.payment, ''),
                         ProcessPaymentResult(True))
