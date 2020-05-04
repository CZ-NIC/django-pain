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

"""Test admin filters."""
from django.contrib import admin
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from django_pain.admin import BankPaymentAdmin
from django_pain.models import BankPayment


class TestChoicesFieldListFilter(TestCase):
    """Test ChoicesFieldListFilter."""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.request_factory = RequestFactory()

    def test_filter(self):
        modeladmin = BankPaymentAdmin(BankPayment, admin.site)
        request = self.request_factory.get('/', {})
        request.user = self.admin
        changelist = modeladmin.get_changelist_instance(request)
        filterspec = changelist.get_filters(request)[0][0]
        choices = list(filterspec.choices(changelist))
        self.assertEqual(choices, ([
            {'selected': True, 'query_string': '?', 'display': 'All'},
            {'selected': False, 'query_string': '?state__exact=ready_to_process', 'display': 'ready to process'},
            {'selected': False, 'query_string': '?state__exact=processed', 'display': 'processed'},
            {'selected': False, 'query_string': '?state__exact=deferred', 'display': 'not identified'},
            {'selected': False, 'query_string': '?state__exact=exported', 'display': 'exported'},
            {'selected': False, 'query_string': '?state__exact=canceled', 'display': 'canceled'},
        ]))
