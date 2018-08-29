"""Test processor utils."""
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from django_pain.settings import SETTINGS, get_processor_class, get_processor_instance, get_processor_objective

from .mixins import CacheResetMixin
from .utils import DummyPaymentProcessor


class TestProcessorsSetting(SimpleTestCase):
    """Test ProcessorsSetting checker."""

    @override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
    def test_ok(self):
        """Test ok setting."""
        SETTINGS.check()
        self.assertEqual(SETTINGS.processors, {'dummy': DummyPaymentProcessor})

    @override_settings(PAIN_PROCESSORS=[])
    def test_not_dict(self):
        """Test not dictionary setting."""
        with self.assertRaisesRegex(ImproperlyConfigured, 'PAIN_PROCESSORS must be {}, not {}'.format(dict, list)):
            SETTINGS.check()

    @override_settings(PAIN_PROCESSORS={0: 1})
    def test_not_str_key(self):
        """Test dictionary with not str keys."""
        with self.assertRaisesRegex(ImproperlyConfigured, 'All keys of PAIN_PROCESSORS must be {}'.format(str)):
            SETTINGS.check()

    @override_settings(PAIN_PROCESSORS={'test_class': 'django_pain.tests.test_settings.TestProcessorsSetting'})
    def test_not_correct_subclass(self):
        """Test not subclass of AbstractPaymentProcessor."""
        with self.assertRaisesRegex(ImproperlyConfigured, '{} is not subclass of AbstractPaymentProcessor'.format(
                'django_pain.tests.test_settings.TestProcessorsSetting')):
            SETTINGS.check()


@override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
class TestGetProcessorClass(CacheResetMixin, SimpleTestCase):
    """Test get_processor_class."""

    def test_success(self):
        """Test successful import."""
        self.assertEqual(
            get_processor_class('dummy'),
            DummyPaymentProcessor
        )

    def test_invalid(self):
        """Test not defined processor."""
        processor = 'invalid.package.name'
        with self.assertRaisesRegex(
                ValueError, '{} is not present in PAIN_PROCESSORS setting'.format(processor)):
            get_processor_class(processor)


@override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
class TestGetProcessorInstance(CacheResetMixin, SimpleTestCase):
    """Test get_processor_instance."""

    def test_success(self):
        """Test success."""
        self.assertIsInstance(
            get_processor_instance('dummy'),
            DummyPaymentProcessor
        )


@override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
class TestGetProcessorObjective(CacheResetMixin, SimpleTestCase):
    """Test get_processor_objective."""

    def test_success(self):
        """Test success."""
        self.assertEqual(
            get_processor_objective('dummy'),
            'Dummy objective'
        )
