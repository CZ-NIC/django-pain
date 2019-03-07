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

"""Application-wide constants."""
from enum import Enum, unique

# Number of decimal places of currency amounts.
# Bitcoin has 8, so 10 should be enough for most practical purposes.
CURRENCY_PRECISION = 10


@unique
class PaymentState(str, Enum):
    """Payment states constants."""

    IMPORTED = 'imported'
    PROCESSED = 'processed'
    DEFERRED = 'deferred'
    EXPORTED = 'exported'


@unique
class InvoiceType(str, Enum):
    """Invoice type constants."""

    ADVANCE = 'advance'
    ACCOUNT = 'account'


@unique
class PaymentProcessingError(str, Enum):
    """Payment processing error constants."""

    DUPLICITY = 'duplicity'
    INSUFFICIENT_AMOUNT = 'insufficient_amount'
    EXCESSIVE_AMOUNT = 'excessive_amount'
    OVERDUE = 'overdue'
    MANUALLY_BROKEN = 'manually_broken'
