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

"""Test common payment processor."""
from django.test import SimpleTestCase

from django_pain.constants import PaymentProcessingError
from django_pain.processors import ProcessPaymentResult


class TestProcessPaymentResult(SimpleTestCase):
    """Test ProcessPaymentResult."""

    def test_process_payment_result_init(self):
        """Test ProcessPaymentResult __init__."""
        self.assertEqual(ProcessPaymentResult(True).result, True)
        self.assertEqual(ProcessPaymentResult(False).result, False)
        self.assertEqual(ProcessPaymentResult(True).error, None)
        self.assertEqual(
            ProcessPaymentResult(True, PaymentProcessingError.DUPLICITY).error,
            PaymentProcessingError.DUPLICITY
        )

    def test_process_payment_result_eq(self):
        """Test ProcessPaymentResult __eq__."""
        self.assertEqual(ProcessPaymentResult(True) == ProcessPaymentResult(True), True)
        self.assertEqual(ProcessPaymentResult(True) == ProcessPaymentResult(False), False)
        self.assertEqual(ProcessPaymentResult(False) == 0, False)
        self.assertEqual(
            ProcessPaymentResult(False) == ProcessPaymentResult(False, PaymentProcessingError.DUPLICITY),
            False
        )
