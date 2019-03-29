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

"""Test admin views."""
from datetime import date

from django.contrib import admin
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from freezegun import freeze_time

from django_pain.admin import BankPaymentAdmin
from django_pain.constants import InvoiceType, PaymentProcessingError, PaymentState
from django_pain.models import BankPayment
from django_pain.tests.mixins import CacheResetMixin
from django_pain.tests.utils import DummyPaymentProcessor, get_account, get_client, get_invoice, get_payment


class LinkedDummyPaymentProcessor(DummyPaymentProcessor):
    """Payment processor with link functions."""

    def get_invoice_url(self, invoice):
        """Dummy url."""
        return 'http://example.com/invoice/'

    def get_client_url(self, client):
        """Dummy url."""
        return 'http://example.com/client/'


@override_settings(ROOT_URLCONF='django_pain.tests.urls')
class TestBankAccountAdmin(TestCase):
    """Test BankAccountAdmin."""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.account = get_account(account_number='123456/0300', currency='USD')
        self.account.save()

    def test_get_list(self):
        """Test GET request on model list."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankaccount_changelist'))
        self.assertContains(response, '123456/0300')

    def test_get_add(self):
        """Test GET request on bank account add."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankaccount_add'))
        self.assertContains(response, '<option value="USD">US Dollar</option>', html=True)

    def test_get_change(self):
        """Test GET request on bank account change."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankaccount_change', args=(self.account.pk,)))
        self.assertContains(response, '123456/0300')
        self.assertContains(response, '<div class="readonly">USD</div>', html=True)


@override_settings(
    ROOT_URLCONF='django_pain.tests.urls',
    PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
class TestBankPaymentAdmin(CacheResetMixin, TestCase):
    """Test BankAccountAdmin."""

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.request_factory = RequestFactory()

        self.account = get_account(account_name='My Account')
        self.account.save()
        self.imported_payment = get_payment(
            identifier='My Payment 1', account=self.account, state=PaymentState.IMPORTED, variable_symbol='VAR1',
            transaction_date=date(2019, 1, 1),
        )
        self.imported_payment.save()
        self.processed_payment = get_payment(
            identifier='My Payment 2', account=self.account, state=PaymentState.PROCESSED, variable_symbol='VAR2',
            processor='dummy', processing_error=PaymentProcessingError.DUPLICITY,
        )
        self.processed_payment.save()
        self.invoice = get_invoice(number='INV111222')
        self.invoice.save()
        self.invoice.payments.add(self.processed_payment)
        self.payment_client = get_client(handle='HANDLE', payment=self.processed_payment)
        self.payment_client.save()

    def test_get_list(self):
        """Test GET request on model list."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankpayment_changelist'))
        self.assertContains(response, 'VAR1')
        self.assertContains(response, 'VAR2')
        self.assertContains(response, 'INV111222')

    def test_get_detail(self):
        """Test GET request on model detail."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankpayment_change', args=[self.processed_payment.pk]))
        self.assertContains(response, 'My Payment 2')
        self.assertContains(response, 'INV111222')
        self.assertContains(response, 'HANDLE')
        self.assertContains(response, 'Duplicate payment')

    def test_get_fieldsets(self):
        """Test get_fieldsets method."""
        modeladmin = BankPaymentAdmin(BankPayment, admin.site)
        request = self.request_factory.get('/', {})
        request.user = self.admin

        fieldsets = modeladmin.get_fieldsets(request)
        self.assertEqual(fieldsets, [
            (None, {
                'fields': (
                    'counter_account_number', 'objective', 'client_link',
                    'transaction_date', 'constant_symbol', 'variable_symbol', 'specific_symbol', 'amount',
                    'description', 'counter_account_name', 'create_time', 'account', 'state'
                )
            }),
        ])

        fieldsets = modeladmin.get_fieldsets(request, self.imported_payment)
        self.assertEqual(fieldsets, [
            (None, {
                'fields': (
                    'counter_account_number',
                    'transaction_date', 'constant_symbol', 'variable_symbol', 'specific_symbol', 'amount',
                    'description', 'counter_account_name', 'create_time', 'account', 'state',
                )
            }),
            ('Assign payment', {
                'fields': ('processor', 'client_id', 'tax_date')
            }),
        ])

        fieldsets = modeladmin.get_fieldsets(request, self.processed_payment)
        self.assertEqual(fieldsets, [
            (None, {
                'fields': (
                    'counter_account_number', 'objective', 'client_link',
                    'transaction_date', 'constant_symbol', 'variable_symbol', 'specific_symbol', 'amount',
                    'description', 'counter_account_name', 'create_time', 'account', ('state', 'processing_error'),
                )
            }),
        ])

    @freeze_time('2019-01-01')
    def test_get_form_payment(self):
        """Test get_form method with payment provided."""
        modeladmin = BankPaymentAdmin(BankPayment, admin.site)
        request = self.request_factory.get('/', {})
        request.user = self.admin

        form = modeladmin.get_form(request, obj=self.imported_payment)
        form_instance = form()
        self.assertEqual(form_instance.fields['tax_date'].initial, date(2019, 1, 1))

    def test_get_initial_tax_date(self):
        """Test method _get_initial_tax_date."""
        modeladmin = BankPaymentAdmin(BankPayment, admin.site)
        with freeze_time('2019-06-20'):
            self.assertEqual(
                modeladmin._get_initial_tax_date(date(2019, 6, 14)),
                date(2019, 6, 14)
            )
        with freeze_time('2019-06-20'):
            self.assertEqual(
                modeladmin._get_initial_tax_date(date(2019, 6, 1)),
                date(2019, 6, 20)
            )
        with freeze_time('2019-07-02'):
            self.assertEqual(
                modeladmin._get_initial_tax_date(date(2019, 6, 14)),
                date(2019, 6, 30)
            )
        with freeze_time('2019-07-10'):
            self.assertEqual(
                modeladmin._get_initial_tax_date(date(2019, 6, 20)),
                date(2019, 6, 30)
            )
        with freeze_time('2019-07-04'):
            self.assertEqual(
                modeladmin._get_initial_tax_date(date(2019, 6, 20)),
                date(2019, 6, 20)
            )
        with freeze_time('2019-06-20'):
            self.assertEqual(
                modeladmin._get_initial_tax_date(date(2019, 6, 21)),
                None
            )
        with freeze_time('2019-06-20'):
            self.assertEqual(
                modeladmin._get_initial_tax_date(date(2019, 4, 25)),
                None
            )
        with freeze_time('2019-06-16'):
            self.assertEqual(
                modeladmin._get_initial_tax_date(date(2019, 5, 30)),
                None
            )


@override_settings(
    ROOT_URLCONF='django_pain.tests.urls',
    PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
class TestBankPaymentAdminNormalUser(CacheResetMixin, TestCase):
    """Test BankAccountAdmin as normal user."""

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user('admin', 'admin@example.com', 'password', is_staff=True)
        self.request_factory = RequestFactory()

    def test_get_form_no_perms(self):
        """Test get_form method without any permissions."""
        modeladmin = BankPaymentAdmin(BankPayment, admin.site)
        request = self.request_factory.get('/', {})
        request.user = self.user

        form = modeladmin.get_form(request)
        form_instance = form()
        self.assertEqual(form_instance.fields['processor'].choices, [('', '---------')])

    def test_get_form_some_perms(self):
        """Test get_form method with some permissions."""
        modeladmin = BankPaymentAdmin(BankPayment, admin.site)
        request = self.request_factory.get('/', {})
        request.user = self.user
        content_type = ContentType.objects.get_for_model(BankPayment)
        perm = Permission.objects.create(codename='can_manually_assign_to_dummy', content_type=content_type)
        request.user.user_permissions.add(perm)

        form = modeladmin.get_form(request)
        form_instance = form()
        self.assertEqual(
            form_instance.fields['processor'].choices,
            [('', '---------'), ('dummy', 'Dummy objective')]
        )


@override_settings(PAIN_PROCESSORS={
    'linked_dummy': 'django_pain.tests.admin.test_admin.LinkedDummyPaymentProcessor',
})
class TestBankPaymentAdminLinks(TestBankPaymentAdmin):
    """Test BankAccountAdmin with invoice and client links."""

    def setUp(self):
        super().setUp()
        self.processed_payment.processor = 'linked_dummy'
        self.processed_payment.save()
        self.invoice2 = get_invoice(number='INV222333', invoice_type=InvoiceType.ACCOUNT)
        self.invoice2.save()
        self.invoice2.payments.add(self.processed_payment)

    def test_get_list_links(self):
        """Test GET request on model list."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankpayment_changelist'))
        self.assertContains(response, '<a href="http://example.com/invoice/">INV111222</a>&nbsp;(+1)')

    def test_get_list_no_advance_invoice(self):
        """Test GET request on model list."""
        self.invoice.invoice_type = InvoiceType.ACCOUNT
        self.invoice.save()
        self.invoice2.invoice_type = InvoiceType.ACCOUNT
        self.invoice2.save()
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankpayment_changelist'))
        self.assertContains(response, '(+2)')

    def test_get_detail_links(self):
        """Test GET request on model detail."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankpayment_change', args=[self.processed_payment.pk]))
        self.assertContains(response, '<a href="http://example.com/invoice/">INV111222</a>')
        self.assertContains(response, '<a href="http://example.com/client/">HANDLE</a>')


@override_settings(ROOT_URLCONF='django_pain.tests.urls')
class TestUserAdmin(TestCase):
    """Test UserAdmin."""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'password')

    def test_get_add(self):
        """Test GET request on add view."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:auth_user_add'))
        self.assertContains(
            response,
            "If you use external authentication system such as LDAP, you don't have to choose a password."
        )

    def test_post_add_password(self):
        """Test POST request on add view."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('admin:auth_user_add'),
            data={'username': 'yoda', 'password1': 'usetheforce', 'password2': 'usetheforce'},
        )
        user = User.objects.get(username='yoda')
        self.assertRedirects(response, reverse('admin:auth_user_change', args=(user.pk,)))
        self.assertTrue(user.has_usable_password())

    def test_post_add_no_password(self):
        """Test POST request on add view without password."""
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('admin:auth_user_add'),
            data={'username': 'yoda', 'password1': '', 'password2': ''},
        )
        user = User.objects.get(username='yoda')
        self.assertRedirects(response, reverse('admin:auth_user_change', args=(user.pk,)))
        self.assertFalse(user.has_usable_password())
