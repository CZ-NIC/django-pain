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

"""Test import callbacks."""
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from django_pain.constants import PaymentState
from django_pain.import_callbacks import skip_credit_card_transaction_summary
from django_pain.tests.utils import get_payment


class TestSkipCreditCardTransactionSummary(SimpleTestCase):
    """Test skip_credit_card_transaction_summary callback."""

    def setUp(self):
        super().setUp()

    def test_credit_card_summary_payment(self):
        payment = get_payment(
            counter_account_number='None/None',
            constant_symbol='1176',
        )
        with self.assertRaises(ValidationError):
            payment = skip_credit_card_transaction_summary(payment)

    def test_normal_payment(self):
        payment = get_payment()
        payment = skip_credit_card_transaction_summary(payment)
        self.assertEqual(payment.state, PaymentState.IMPORTED)
