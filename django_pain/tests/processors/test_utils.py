"""Test processor utils."""
from django.test import SimpleTestCase

from django_pain.processors.utils import get_processor_class, get_processor_instance
from django_pain.tests.utils import DummyPaymentProcessor


class TestGetProcessorClass(SimpleTestCase):
    """Test get_processor_class."""

    def test_success(self):
        """Test successful import."""
        self.assertEqual(
            get_processor_class('django_pain.tests.utils.DummyPaymentProcessor'),
            DummyPaymentProcessor
        )

    def test_not_processor(self):
        """Test existing object which is not a payment processor."""
        processor = 'django_pain.tests.processors.test_utils.TestGetProcessorClass'
        with self.assertRaisesRegex(
                ValueError, '{} is not a valid subclass of AbstractPaymentProcessor'.format(processor)):
            get_processor_class(processor)

    def test_import_error(self):
        """Test not existing object."""
        processor = 'invalid.package.name'
        with self.assertRaisesRegex(
                ValueError, 'Payment processor {} was not found'.format(processor)):
            get_processor_class(processor)


class TestGetProcessorInstance(SimpleTestCase):
    """Test get_processor_instance."""

    def test_success(self):
        """Test success."""
        self.assertIsInstance(
            get_processor_instance('django_pain.tests.utils.DummyPaymentProcessor'),
            DummyPaymentProcessor
        )
