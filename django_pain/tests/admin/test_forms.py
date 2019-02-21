"""Test admin forms."""
from django.test import TestCase, override_settings

from django_pain.admin.forms import BankPaymentForm, UserCreationForm
from django_pain.constants import PaymentState
from django_pain.models import BankPayment
from django_pain.processors import ProcessPaymentResult
from django_pain.tests.mixins import CacheResetMixin
from django_pain.tests.utils import DummyPaymentProcessor, get_account, get_payment


class SuccessPaymentProcessor(DummyPaymentProcessor):
    default_objective = 'Generous bribe'

    def assign_payment(self, payment, client_id):
        return ProcessPaymentResult(result=True)


class FailurePaymentProcessor(DummyPaymentProcessor):
    default_objective = 'Not so generous bribe'

    def assign_payment(self, payment, client_id):
        return ProcessPaymentResult(result=False)


@override_settings(PAIN_PROCESSORS={
    'success': 'django_pain.tests.admin.test_forms.SuccessPaymentProcessor',
    'failure': 'django_pain.tests.admin.test_forms.FailurePaymentProcessor',
})
class TestBankPaymentForm(CacheResetMixin, TestCase):
    """Test BankPaymentForm."""

    def setUp(self):
        super().setUp()
        self.account = get_account()
        self.account.save()
        self.payment = get_payment(account=self.account, state=PaymentState.IMPORTED)
        self.payment.save()

    def _get_form(self, *args, **kwargs):
        form = BankPaymentForm(*args, **kwargs)
        form.fields['processor'].choices = BankPayment.objective_choices()
        return form

    def test_disabled_fields(self):
        """Test disabled fields."""
        form = self._get_form()
        for field in form.fields:
            if field in ('processor', 'client_id'):
                self.assertFalse(form.fields[field].disabled)
            else:
                self.assertTrue(form.fields[field].disabled)

    def test_clean_success(self):
        """Test clean method success."""
        form = self._get_form(data={
            'processor': 'success',
            'client_id': '',
        }, instance=self.payment)
        self.assertTrue(form.is_valid())

    def test_clean_failure(self):
        """Test clean method failure."""
        form = self._get_form(data={
            'processor': 'failure',
            'client_id': '',
        }, instance=self.payment)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'__all__': ['Unable to assign payment']})

    def test_save_processed(self):
        """Test manual assignment save method."""
        form = self._get_form(data={
            'processor': 'success',
            'client_id': '',
        }, instance=self.payment)
        form.is_valid()
        payment = form.save(commit=False)
        self.assertEqual(payment.state, PaymentState.PROCESSED)
        self.assertEqual(payment.objective, 'Generous bribe')

    def test_save_blank(self):
        """Test manual assignment of blank processor."""
        form = self._get_form(data={
            'processor': '',
            'client_id': '',
        }, instance=self.payment)
        self.assertTrue(form.is_valid())
        form.cleaned_data.pop('state', None)
        instance = form.save(commit=False)
        self.assertEqual(instance, self.payment)


class TestUserCreationForm(TestCase):
    """Test UserCreationForm."""

    def test_required_fields(self):
        """Test required fields."""
        form = UserCreationForm()
        self.assertTrue(form.fields['username'].required)
        self.assertFalse(form.fields['password1'].required)
        self.assertFalse(form.fields['password2'].required)

    def test_clean_success(self):
        """Test clean method success."""
        form = UserCreationForm(data={
            'username': 'yoda',
            'password1': '',
            'password2': '',
        })
        self.assertTrue(form.is_valid())

    def test_clean_failure(self):
        """Test clean method failure."""
        form = UserCreationForm(data={
            'username': 'yoda',
            'password1': 'usetheforce',
            'password2': '',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'password2': ['Fill out both fields']})
