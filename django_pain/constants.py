#
# Copyright (C) 2018-2021  CZ.NIC, z. s. p. o.
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

from django_pain.utils import StrEnum

# Number of decimal places of currency amounts.
# Bitcoin has 8, so 10 should be enough for most practical purposes.
CURRENCY_PRECISION = 10


@unique
class PaymentType(StrEnum):
    """Payment types constants."""

    TRANSFER = 'transfer'
    CARD_PAYMENT = 'card_payment'


@unique
class PaymentState(StrEnum):
    """Payment states constants."""

    INITIALIZED = 'initialized'
    READY_TO_PROCESS = 'ready_to_process'
    PROCESSED = 'processed'
    DEFERRED = 'deferred'
    EXPORTED = 'exported'
    CANCELED = 'canceled'


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
    TOO_OLD = 'too_old'
