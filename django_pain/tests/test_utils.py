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

"""Test utils."""
from django.test import SimpleTestCase

from django_pain.models.bank import BankAccount
from django_pain.utils import full_class_name


class TestUtils(SimpleTestCase):

    def test_str(self):
        """Test full_class_name."""
        self.assertEqual(full_class_name(BankAccount), 'django_pain.models.bank.BankAccount')
