#
# Copyright (C) 2018-2019  CZ.NIC, z. s. p. o.
#
# This file is part of FRED.
#
# FRED is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# FRED is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with FRED.  If not, see <https://www.gnu.org/licenses/>.

"""Test admin forms."""
from datetime import date

from django.test import TestCase, override_settings

from django_pain.admin.forms import BankPaymentForm, UserCreationForm
from django_pain.constants import PaymentState
from django_pain.models import BankPayment
from django_pain.processors import InvalidTaxDateError, ProcessPaymentResult
from django_pain.tests.mixins import CacheResetMixin
from django_pain.tests.utils import DummyPaymentProcessor, get_account, get_payment


class SuccessPaymentProcessor(DummyPaymentProcessor):
    default_objective = 'Generous bribe'
    manual_tax_date = True

    def assign_payment(self, payment, client_id, tax_date):
        return ProcessPaymentResult(result=True)


class FailurePaymentProcessor(DummyPaymentProcessor):
    default_objective = 'Not so generous bribe'

    def assign_payment(self, payment, client_id):
        return ProcessPaymentResult(result=False)


class ExceptionPaymentProcessor(DummyPaymentProcessor):
    default_objective = 'Exceptional bribe'

    def assign_payment(self, payment, client_id):
        raise InvalidTaxDateError('Invalid tax date')


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
        self.payment = get_payment(account=self.account, state=PaymentState.READY_TO_PROCESS)
        self.payment.save()

    def _get_form(self, *args, **kwargs):
        form = BankPaymentForm(*args, **kwargs)
        form.fields['processor'].choices = BankPayment.objective_choices()
        return form

    def test_disabled_fields(self):
        """Test disabled fields."""
        form = self._get_form()
        for field in form.fields:
            if field in ('processor', 'client_id', 'tax_date'):
                self.assertFalse(form.fields[field].disabled)
            else:
                self.assertTrue(form.fields[field].disabled)

    def test_clean_success(self):
        """Test clean method success."""
        form = self._get_form(data={
            'processor': 'success',
            'client_id': '',
            'tax_date': date(2019, 1, 1),
        }, instance=self.payment)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})

    def test_clean_failure(self):
        """Test clean method failure."""
        form = self._get_form(data={
            'processor': 'failure',
            'client_id': '',
        }, instance=self.payment)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'__all__': ['Unable to assign payment']})

    def test_clean_missing_tax_date(self):
        """Test clean method with missing tax date."""
        form = self._get_form(data={
            'processor': 'success',
            'client_id': '',
        }, instance=self.payment)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'tax_date': ['This field is required']})

    def test_clean_invalid_tax_date(self):
        """Test clean method with invalid tax date."""
        form = self._get_form(data={
            'processor': 'success',
            'client_id': '',
            'tax_date': 'XXXXX',
        }, instance=self.payment)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'tax_date': ['Enter a valid date.']})

    @override_settings(PAIN_PROCESSORS={'exception': 'django_pain.tests.admin.test_forms.ExceptionPaymentProcessor'})
    def test_clean_invalid_tax_date_exception(self):
        """Test clean method with invalid tax date exception."""
        form = self._get_form(data={
            'processor': 'exception',
            'client_id': '',
            'tax_date': date(2019, 1, 1),
        }, instance=self.payment)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'tax_date': ['Invalid tax date']})

    def test_save_processed(self):
        """Test manual assignment save method."""
        form = self._get_form(data={
            'processor': 'success',
            'client_id': '',
            'tax_date': date(2019, 1, 1),
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
            'tax_date': '',
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
