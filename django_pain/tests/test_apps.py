"""Test apps."""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase, override_settings

from django_pain.models import BankPayment
from django_pain.tests.mixins import CacheResetMixin


class TestDjangoPainConfig(CacheResetMixin, TestCase):
    """Test DjangoPainConfig."""

    @override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
    def test_post_migrate(self):
        content_type = ContentType.objects.get_for_model(BankPayment)
        results = Permission.objects.filter(codename='can_manually_assign_to_dummy', content_type=content_type)
        self.assertEqual(results.count(), 0)

        call_command('migrate', '-v0')

        results = Permission.objects.filter(codename='can_manually_assign_to_dummy', content_type=content_type)
        self.assertEqual(results.count(), 1)
        self.assertQuerysetEqual(
            results.values_list('name'), [
                ('Can manually assign to Dummy objective',)
            ], transform=tuple, ordered=False
        )
