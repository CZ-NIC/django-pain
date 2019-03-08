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

"""Test CzechSlovakBankStatementParser."""
from django.test import SimpleTestCase

from django_pain.parsers.czechslovak import CzechSlovakBankStatementParser


class DummyParser(CzechSlovakBankStatementParser):
    """Dummy parser derived from abstract class."""

    def parse(self, bank_statement):
        """Just a dummy implementation, because DummyParser cannot be abstract."""


class TestCzechSlovakBankStatementParser(SimpleTestCase):
    """Test CzechSlovakBankStatementParser."""

    def test_compose_account_number(self):
        parser = DummyParser()
        self.assertEqual(parser.compose_account_number('123456', '0300'), '123456/0300')
