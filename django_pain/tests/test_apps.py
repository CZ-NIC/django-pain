#
# Copyright (C) 2019  CZ.NIC, z. s. p. o.
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

"""Test apps."""
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase, override_settings

from django_pain.models import BankPayment
from django_pain.tests.mixins import CacheResetMixin


class TestDjangoPainConfig(CacheResetMixin, TestCase):
    """Test DjangoPainConfig."""

    @override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
    def test_post_migrate(self):
        content_type = ContentType.objects.get_for_model(BankPayment)
        results = Permission.objects.filter(codename='can_manually_assign_to_dummy', content_type=content_type)
        self.assertEqual(results.count(), 0)

        call_command('migrate', '-v0')

        results = Permission.objects.filter(codename='can_manually_assign_to_dummy', content_type=content_type)
        self.assertEqual(results.count(), 1)
        self.assertQuerysetEqual(
            results.values_list('name'), [
                ('Can manually assign to Dummy objective',)
            ], transform=tuple, ordered=False
        )
