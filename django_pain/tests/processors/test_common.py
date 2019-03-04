"""Test common payment processor."""
from django.test import SimpleTestCase

from django_pain.constants import PaymentProcessingError
from django_pain.processors import ProcessPaymentResult


class TestProcessPaymentResult(SimpleTestCase):
    """Test ProcessPaymentResult."""

    def test_process_payment_result_init(self):
        """Test ProcessPaymentResult __init__."""
        self.assertEqual(ProcessPaymentResult(True).result, True)
        self.assertEqual(ProcessPaymentResult(False).result, False)
        self.assertEqual(ProcessPaymentResult(True).error, None)
        self.assertEqual(
            ProcessPaymentResult(True, PaymentProcessingError.DUPLICITY).error,
            PaymentProcessingError.DUPLICITY
        )

    def test_process_payment_result_eq(self):
        """Test ProcessPaymentResult __eq__."""
        self.assertEqual(ProcessPaymentResult(True) == ProcessPaymentResult(True), True)
        self.assertEqual(ProcessPaymentResult(True) == ProcessPaymentResult(False), False)
        self.assertEqual(ProcessPaymentResult(False) == 0, False)
        self.assertEqual(
            ProcessPaymentResult(False) == ProcessPaymentResult(False, PaymentProcessingError.DUPLICITY),
            False
        )
