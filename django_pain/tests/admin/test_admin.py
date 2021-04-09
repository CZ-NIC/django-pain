#
# Copyright (C) 2018-2021  CZ.NIC, z. s. p. o.
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
from decimal import ROUND_HALF_UP
from queue import Queue
from threading import Event, Thread

from django.contrib import admin
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import close_old_connections, transaction
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from freezegun import freeze_time
from moneyed.localization import _FORMATTER

from django_pain.admin import BankPaymentAdmin
from django_pain.constants import InvoiceType, PaymentProcessingError, PaymentState
from django_pain.models import BankAccount, BankPayment, PaymentImportHistory
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
        self.account = get_account(account_number='123456/0300', currency='EUR')
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
        self.assertContains(response, '<option value="EUR">Euro</option>', html=True)

    def test_get_change(self):
        """Test GET request on bank account change."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankaccount_change', args=(self.account.pk,)))
        self.assertContains(response, '123456/0300')
        self.assertContains(response, '<div class="readonly">EUR</div>', html=True)

    def test_get_history(self):
        """Test GET request on bank account history."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankaccount_history', args=(self.account.pk,)))
        self.assertContains(response, '123456/0300')


@freeze_time('2021-03-20 12:45')
@override_settings(ROOT_URLCONF='django_pain.tests.urls')
class TestPaymentImportHistoryAdmin(TestCase):
    """Test PaymentImportHistory."""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.import_history = PaymentImportHistory(origin='some_test_bank')
        self.import_history.save()

    def test_get_list(self):
        """Test GET request on model list."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_paymentimporthistory_changelist'))
        self.assertContains(response, 'some_test_bank')
        self.assertContains(response, 'March')

    def test_get_change(self):
        """Test GET request on PaymentImportHistory change."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_paymentimporthistory_change',
                                           args=(self.import_history.pk,)))
        self.assertContains(response, 'some_test_bank')
        self.assertContains(response, 'March')

    def test_delete_not_allowed(self):
        """Test PaymentImportHistory can not be deleted in admin."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_paymentimporthistory_delete',
                                           args=(self.import_history.pk,)))
        self.assertEqual(response.status_code, 403)

    def test_save_not_allowed(self):
        """Test PaymentImportHistory can not be saved in admin."""
        self.client.force_login(self.admin)
        response_get = self.client.get(reverse('admin:django_pain_paymentimporthistory_change',
                                               args=(self.import_history.pk,)))
        self.assertNotContains(response_get, 'name="_save"', html=True)
        self.assertNotContains(response_get, 'name="_addanother"', html=True)
        self.assertNotContains(response_get, 'name="_continue"', html=True)

        response_post = self.client.post(reverse('admin:django_pain_paymentimporthistory_change',
                                                 args=(self.import_history.pk,)))
        self.assertEqual(response_post.status_code, 403)

    def test_add_not_allowed(self):
        """Test PaymentImportHistory can not be added in admin."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_paymentimporthistory_add'))
        self.assertEqual(response.status_code, 403)


@skipUnlessDBFeature('has_select_for_update')
@override_settings(ROOT_URLCONF='django_pain.tests.urls')
class TestDatabaseLocking(TransactionTestCase):

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'password')

    def tearDown(self):
        self.admin.delete()

    def test_account_admin_locking(self):
        instance = get_account(account_number='123456/0300', currency='EUR')
        viewname = 'admin:django_pain_bankaccount_changelist'
        find_in_response = '123456/0300'
        model_class = BankAccount
        self._test_admin_locking(instance, viewname, find_in_response, model_class)

    def test_payment_admin_locking(self):
        account = get_account(account_name='My Account')
        account.save()
        instance = get_payment(
            identifier='My Payment 1', account=account, state=PaymentState.READY_TO_PROCESS,
            variable_symbol='VAR1', transaction_date=date(2019, 1, 1),
        )
        viewname = 'admin:django_pain_bankpayment_changelist'
        find_in_response = 'VAR1'
        model_class = BankPayment
        self._test_admin_locking(instance, viewname, find_in_response, model_class)

    def _test_admin_locking(self, instance, viewname, find_in_response, model_class):
        instance.save()
        self.client.force_login(self.admin)

        admin_started = Event()
        admin_finished = Event()
        external_started = Event()
        external_finished = Event()

        # Exception in a threads does not fail the test - wee need to collect it somemehow
        errors = Queue()   # type: Queue

        def target_admin():
            try:
                with transaction.atomic():
                    external_started.wait()
                    response = self.client.get(reverse(viewname))
                    self.assertContains(response, find_in_response)
                    admin_started.set()
                    external_finished.wait()
                admin_finished.set()
            except Exception as e:  # pragma: no cover
                errors.put(e)
                raise e
            finally:
                admin_started.set()
                admin_finished.set()
                close_old_connections()

        def target_external():
            try:
                external_started.set()
                with transaction.atomic():
                    admin_started.wait()
                    instances = list(model_class.objects.select_for_update(skip_locked=True).all())
                    self.assertEquals([], instances)
                external_finished.set()

                with transaction.atomic():
                    admin_finished.wait()
                    instances = list(model_class.objects.select_for_update(skip_locked=True).all())
                    self.assertEqual([instance], instances)
            except Exception as e:  # pragma: no cover
                errors.put(e)
                raise e
            finally:
                external_started.set()
                external_finished.set()
                close_old_connections()

        threads = [Thread(target=target_admin), Thread(target=target_external)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(errors.empty())


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
            identifier='My Payment 1', account=self.account, state=PaymentState.READY_TO_PROCESS,
            variable_symbol='VAR1', transaction_date=date(2019, 1, 1),
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

    def test_get_add(self):
        """Test GET request on model addition."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankpayment_add'))
        self.assertEqual(response.status_code, 403)

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

    def test_get_history(self):
        """Test GET request on model history."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:django_pain_bankpayment_history', args=[self.processed_payment.pk]))
        self.assertContains(response, 'Change history: My Payment 2')

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
                    'transaction_date', 'constant_symbol', 'variable_symbol', 'specific_symbol', 'unbreakable_amount',
                    'description', 'counter_account_name', 'create_time', 'account', 'state'
                )
            }),
        ])

        fieldsets = modeladmin.get_fieldsets(request, self.imported_payment)
        self.assertEqual(fieldsets, [
            (None, {
                'fields': (
                    'counter_account_number',
                    'transaction_date', 'constant_symbol', 'variable_symbol', 'specific_symbol', 'unbreakable_amount',
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
                    'transaction_date', 'constant_symbol', 'variable_symbol', 'specific_symbol', 'unbreakable_amount',
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

    @override_settings(LANGUAGE_CODE='cs')
    def test_unbreakable_amount_cs(self):
        modeladmin = BankPaymentAdmin(BankPayment, admin.site)
        payment = BankPayment(amount=10000.445)

        original_definition = _FORMATTER.formatting_definitions.get('CS', None)
        try:
            _FORMATTER.add_formatting_definition(
                'cs', group_size=3, group_separator=' ', decimal_point=',', positive_sign='', trailing_positive_sign='',
                negative_sign='-', trailing_negative_sign='', rounding_method=ROUND_HALF_UP)
            formatted = modeladmin.unbreakable_amount(payment)
        finally:
            _FORMATTER.formatting_definitions['CS'] = original_definition
        self.assertEquals('10&nbsp;000,45&nbsp;Kč', formatted)

    @override_settings(LANGUAGE_CODE='en')
    def test_unbreakable_amount_en(self):
        modeladmin = BankPaymentAdmin(BankPayment, admin.site)
        payment = BankPayment(amount=10000.445)

        original_definition = _FORMATTER.formatting_definitions.get('EN', None)
        try:
            _FORMATTER.add_formatting_definition(
                'en', group_size=3, group_separator=',', decimal_point='.', positive_sign='', trailing_positive_sign='',
                negative_sign='-', trailing_negative_sign='', rounding_method=ROUND_HALF_UP)
            formatted = modeladmin.unbreakable_amount(payment)
        finally:
            _FORMATTER.formatting_definitions['EN'] = original_definition
        self.assertEquals('10,000.45&nbsp;Kč', formatted)


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
