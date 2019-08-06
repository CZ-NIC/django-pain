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

"""Import callbacks."""

from django.core.exceptions import ValidationError

from django_pain.models import BankPayment


def skip_credit_card_transaction_summary(payment: BankPayment) -> BankPayment:
    """Import callback for ignoring payments with credit card transactions summary."""
    if payment.counter_account_number == 'None/None' and payment.constant_symbol in ('1176', '1178'):
        raise ValidationError('Payment is credit card transaction summary.')
    return payment
