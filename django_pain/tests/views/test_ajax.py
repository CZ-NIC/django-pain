"""Test ajax views."""
import json

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from django_pain.tests.mixins import CacheResetMixin
from django_pain.tests.utils import DummyPaymentProcessor


class PaymentProcessor(DummyPaymentProcessor):
    """Payment processor with client_choices."""

    @staticmethod
    def get_client_choices():
        """Dummy client choices."""
        return {
            'TNG': 'The Next Generation',
            'DS9': 'Deep Space 9',
        }


@override_settings(
    ROOT_URLCONF='django_pain.tests.urls',
    PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.utils.DummyPaymentProcessor',
        'not_so_dummy': 'django_pain.tests.views.test_ajax.PaymentProcessor'})
class TestLoadProcessorClientChoices(CacheResetMixin, SimpleTestCase):
    """Test load_processor_client_choices."""

    def test_get_empty(self):
        response = self.client.get(reverse('pain:processor_client_choices'))
        self.assertEqual(response.status_code, 404)

    def test_get_choices(self):
        response = self.client.get(reverse('pain:processor_client_choices') + '?processor=not_so_dummy')
        self.assertEqual(json.loads(response.content.decode('utf-8')), {
            'TNG': 'The Next Generation',
            'DS9': 'Deep Space 9',
        })

    def test_dummy_processor(self):
        """Test processor that doesn't implement get_client_choices method."""
        response = self.client.get(reverse('pain:processor_client_choices') + '?processor=dummy')
        self.assertEqual(response.status_code, 404)