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

"""Module providing Czech and Slovak parser specifics."""
from django_pain.parsers import AbstractBankStatementParser


class CzechSlovakBankStatementParser(AbstractBankStatementParser):
    """Abstract parser class providing Czech and Slovak specifics."""

    @staticmethod
    def compose_account_number(number: str, bank_code: str) -> str:
        """
        Compose account number from number and bank code.

        Czech and Slovak bank accounts have account number separated from bank code using slash.
        """
        return '{}/{}'.format(number, bank_code)
