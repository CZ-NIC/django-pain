#
# Copyright (C) 2018-2020  CZ.NIC, z. s. p. o.
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

"""Test admin filters."""
from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from django_pain.admin import BankPaymentAdmin
from django_pain.constants import PaymentState
from django_pain.models import BankAccount, BankPayment
from django_pain.tests.utils import get_payment


class TestChoicesFieldListFilter(TestCase):
    """Test ChoicesFieldListFilter."""

    def setUp(self):
        self.request_factory = RequestFactory()
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        account = BankAccount(account_number='123456/7890', currency='CZK')
        account.save()
        get_payment(identifier='PAYMENT_1', account=account, state=PaymentState.INITIALIZED).save()
        get_payment(identifier='PAYMENT_2', account=account, state=PaymentState.READY_TO_PROCESS).save()
        get_payment(identifier='PAYMENT_3', account=account, state=PaymentState.DEFERRED).save()
        get_payment(identifier='PAYMENT_4', account=account, state=PaymentState.PROCESSED).save()
        get_payment(identifier='PAYMENT_5', account=account, state=PaymentState.CANCELED).save()

    def test_filter_default(self):
        modeladmin = BankPaymentAdmin(BankPayment, admin.site)
        request = self.request_factory.get('/', {})
        request.user = self.admin
        changelist = modeladmin.get_changelist_instance(request)
        filterspec = changelist.get_filters(request)[0][0]
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices, ([
            {'selected': True, 'query_string': '?', 'display': 'Realized'},
            {'selected': False, 'query_string': '?state__exact=all', 'display': 'All'},
            {'selected': False, 'query_string': '?state__exact=initialized', 'display': 'initialized'},
            {'selected': False, 'query_string': '?state__exact=ready_to_process', 'display': 'ready to process'},
            {'selected': False, 'query_string': '?state__exact=processed', 'display': 'processed'},
            {'selected': False, 'query_string': '?state__exact=deferred', 'display': 'not identified'},
            {'selected': False, 'query_string': '?state__exact=exported', 'display': 'exported'},
            {'selected': False, 'query_string': '?state__exact=canceled', 'display': 'canceled'},
        ]))
        self.assertQuerysetEqual(changelist.get_queryset(request).values_list('identifier', flat=True),
                                 ['PAYMENT_2', 'PAYMENT_3', 'PAYMENT_4'], ordered=False, transform=str)

    def test_filter_all(self):
        modeladmin = BankPaymentAdmin(BankPayment, admin.site)
        request = self.request_factory.get('/?state__exact=all', {})
        request.user = self.admin
        changelist = modeladmin.get_changelist_instance(request)
        filterspec = changelist.get_filters(request)[0][0]
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices, ([
            {'selected': False, 'query_string': '?', 'display': 'Realized'},
            {'selected': True, 'query_string': '?state__exact=all', 'display': 'All'},
            {'selected': False, 'query_string': '?state__exact=initialized', 'display': 'initialized'},
            {'selected': False, 'query_string': '?state__exact=ready_to_process', 'display': 'ready to process'},
            {'selected': False, 'query_string': '?state__exact=processed', 'display': 'processed'},
            {'selected': False, 'query_string': '?state__exact=deferred', 'display': 'not identified'},
            {'selected': False, 'query_string': '?state__exact=exported', 'display': 'exported'},
            {'selected': False, 'query_string': '?state__exact=canceled', 'display': 'canceled'},
        ]))
        self.assertQuerysetEqual(changelist.get_queryset(request).values_list('identifier', flat=True),
                                 ['PAYMENT_1', 'PAYMENT_2', 'PAYMENT_3', 'PAYMENT_4', 'PAYMENT_5'],
                                 ordered=False, transform=str)

    def test_filter_one_state(self):
        modeladmin = BankPaymentAdmin(BankPayment, admin.site)
        request = self.request_factory.get('/?state__exact=initialized', {})
        request.user = self.admin
        changelist = modeladmin.get_changelist_instance(request)
        filterspec = changelist.get_filters(request)[0][0]
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices, ([
            {'selected': False, 'query_string': '?', 'display': 'Realized'},
            {'selected': False, 'query_string': '?state__exact=all', 'display': 'All'},
            {'selected': True, 'query_string': '?state__exact=initialized', 'display': 'initialized'},
            {'selected': False, 'query_string': '?state__exact=ready_to_process', 'display': 'ready to process'},
            {'selected': False, 'query_string': '?state__exact=processed', 'display': 'processed'},
            {'selected': False, 'query_string': '?state__exact=deferred', 'display': 'not identified'},
            {'selected': False, 'query_string': '?state__exact=exported', 'display': 'exported'},
            {'selected': False, 'query_string': '?state__exact=canceled', 'display': 'canceled'},
        ]))
        self.assertQuerysetEqual(changelist.get_queryset(request).values_list('identifier', flat=True),
                                 ['PAYMENT_1'], ordered=False, transform=str)
