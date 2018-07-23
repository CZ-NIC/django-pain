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
            {'selected': False, 'query_string': '?state__exact=imported', 'display': 'imported'},
            {'selected': False, 'query_string': '?state__exact=processed', 'display': 'processed'},
            {'selected': False, 'query_string': '?state__exact=deferred', 'display': 'deferred'},
            {'selected': False, 'query_string': '?state__exact=exported', 'display': 'exported'},
        ]))
