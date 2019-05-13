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
from django.conf import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from django_pain.constants import PaymentState
from django_pain.processors import IgnorePaymentProcessor, ProcessPaymentResult
from django_pain.processors.ignore import ignore_negative_payments
from django_pain.tests.mixins import CacheResetMixin
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


class TestIgnoreNegativePayments(CacheResetMixin, SimpleTestCase):
    """Test ignore_negative_payments callback."""

    def setUp(self):
        super().setUp()
        self.payment = get_payment()

    def test_positive_payment(self):
        self.payment.amount.amount = 42
        payment = ignore_negative_payments(self.payment)
        self.assertEqual(payment.state, PaymentState.IMPORTED)
        self.assertEqual(payment.processor, '')

    @override_settings(PAIN_PROCESSORS={
        'dummy': 'django_pain.tests.utils.DummyPaymentProcessor',
        'ignore': 'django_pain.processors.IgnorePaymentProcessor',
    })
    def test_negative_payment(self):
        self.payment.amount.amount = -42
        payment = ignore_negative_payments(self.payment)
        self.assertEqual(payment.state, PaymentState.PROCESSED)
        self.assertEqual(payment.processor, 'ignore')

    @override_settings(PAIN_PROCESSORS={})
    def test_negative_wrong_setting(self):
        self.payment.amount.amount = -42
        with self.assertRaises(ImproperlyConfigured):
            ignore_negative_payments(self.payment)
