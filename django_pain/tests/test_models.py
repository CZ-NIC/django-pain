"""Test models."""
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from djmoney.money import Money

from django_pain.models import BankAccount, BankPayment


class TestBankPayment(SimpleTestCase):
    """Test BankPayment model."""

    def test_constraint_success(self):
        """Test clean method with not violated constraint."""
        account = BankAccount(account_number='123', currency='USD')
        payment = BankPayment(identifier='PAYMENT', account=account, amount=Money('999.00', 'USD'))
        payment.clean()

    def test_constraint_error(self):
        """Test clean method with violated constraint."""
        account = BankAccount(account_number='123', currency='USD')
        payment = BankPayment(identifier='PAYMENT', account=account, amount=Money('999.00', 'CZK'))
        with self.assertRaises(ValidationError, msg='Bank payment PAYMENT is in different currency (CZK) '
                                                    'than bank account 123 (USD).'):
            payment.clean()
