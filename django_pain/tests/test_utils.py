"""Test utils."""
from django.test import SimpleTestCase

from django_pain.models.bank import BankAccount
from django_pain.utils import full_class_name


class TestUtils(SimpleTestCase):

    def test_str(self):
        """Test full_class_name."""
        self.assertEqual(full_class_name(BankAccount), 'django_pain.models.bank.BankAccount')
