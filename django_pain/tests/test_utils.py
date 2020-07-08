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

"""Test utils."""
from datetime import datetime

from django.test import SimpleTestCase

from django_pain.models.bank import BankAccount
from django_pain.utils import full_class_name, parse_datetime_safe


class FullClassNameTest(SimpleTestCase):

    def test_str(self):
        """Test full_class_name."""
        self.assertEqual(full_class_name(BankAccount), 'django_pain.models.bank.BankAccount')


class ParseDatetimeSafeTest(SimpleTestCase):

    def test_parse_datetime_safe(self):
        self.assertEquals(parse_datetime_safe('2017-01-31 00:00'), datetime(2017, 1, 31, 0, 0))

    def test_parse_datetime_safe_fails_on_invalid(self):
        with self.assertRaises(ValueError):
            parse_datetime_safe('2017-01-32 00:00')
        with self.assertRaises(ValueError):
            parse_datetime_safe('not a date')
