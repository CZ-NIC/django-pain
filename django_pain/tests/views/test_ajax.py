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

"""Test ajax views."""
import json

from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from django_pain.tests.mixins import CacheResetMixin
from django_pain.tests.utils import DummyPaymentProcessor


class PaymentProcessor(DummyPaymentProcessor):
    """Payment processor with client_choices."""

    manual_tax_date = True

    @staticmethod
    def get_client_choices():
        """Dummy client choices."""
        return {
            'TNG': 'The Next Generation',
            'DS9': 'Deep Space 9',
        }


@override_settings(
    ROOT_URLCONF='django_pain.tests.urls',
    PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.utils.DummyPaymentProcessor',
        'not_so_dummy': 'django_pain.tests.views.test_ajax.PaymentProcessor'})
class TestLoadProcessorClientChoices(CacheResetMixin, SimpleTestCase):
    """Test load_processor_client_choices."""

    def test_get_empty(self):
        response = self.client.get(reverse('pain:processor_client_choices'))
        self.assertEqual(response.status_code, 404)

    def test_get_choices(self):
        response = self.client.get(reverse('pain:processor_client_choices') + '?processor=not_so_dummy')
        self.assertEqual(json.loads(response.content.decode('utf-8')), {
            'TNG': 'The Next Generation',
            'DS9': 'Deep Space 9',
        })

    def test_dummy_processor(self):
        """Test processor that doesn't implement get_client_choices method."""
        response = self.client.get(reverse('pain:processor_client_choices') + '?processor=dummy')
        self.assertEqual(response.status_code, 404)


@override_settings(
    ROOT_URLCONF='django_pain.tests.urls',
    PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.utils.DummyPaymentProcessor',
        'not_so_dummy': 'django_pain.tests.views.test_ajax.PaymentProcessor'})
class TestGetProcessorsOptions(CacheResetMixin, SimpleTestCase):
    """Test get_processors_options."""

    def test_get(self):
        response = self.client.get(reverse('pain:processor_options'))
        self.assertJSONEqual(response.content.decode('utf-8'), {
            'dummy': {'manual_tax_date': False},
            'not_so_dummy': {'manual_tax_date': True},
        })
