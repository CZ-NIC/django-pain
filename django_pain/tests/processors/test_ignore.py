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

"""Test ignore payment processor."""
from django.test import SimpleTestCase

from django_pain.processors import IgnorePaymentProcessor, ProcessPaymentResult
from django_pain.tests.utils import get_payment


class TestIgnorePaymentProcessor(SimpleTestCase):
    """Test IgnorePaymentProcessor."""

    def setUp(self):
        self.processor = IgnorePaymentProcessor()
        self.payment = get_payment()

    def test_process_payments(self):
        """Test process_payments."""
        self.assertEqual(list(self.processor.process_payments([self.payment])),
                         [ProcessPaymentResult(False)])

    def test_assign_payment(self):
        """Test assign_payment."""
        self.assertEqual(self.processor.assign_payment(self.payment, ''),
                         ProcessPaymentResult(True))
