#
# Copyright (C) 2020  CZ.NIC, z. s. p. o.
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

"""Test get_payments_states command."""
import datetime

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from testfixtures import LogCapture

from django_pain.constants import PaymentState
from django_pain.models import BankAccount, BankPayment
from django_pain.tests.utils import get_payment


@override_settings(PAIN_CARD_PAYMENT_HANDLERS={
    'dummy': 'django_pain.tests.utils.DummyCardPaymentHandler'}
)
class TestGetPaymentsStates(TestCase):
    """Test get_payments_states command."""

    def setUp(self):
        super().setUp()
        self.account = BankAccount(account_number='123456/7890', currency='CZK')
        self.account.save()
        self.log_handler = LogCapture('django_pain.management.commands.get_card_payments_states', propagate=False)

    def tearDown(self):
        self.log_handler.uninstall()

    def test_no_payments(self):
        call_command('get_card_payments_states')

        self.log_handler.check(
            ('django_pain.management.commands.get_card_payments_states', 'INFO',
             'Command get_card_payments_states started.'),
            ('django_pain.management.commands.get_card_payments_states', 'INFO', 'No payments to update state.')
        )

    def test_normal_run(self):
        payment = get_payment(identifier='PAYMENT_1', account=self.account, state=PaymentState.INITIALIZED,
                              card_handler='dummy')
        payment.save()
        payment2 = get_payment(identifier='PAYMENT_2', account=self.account, state=PaymentState.READY_TO_PROCESS,
                               card_handler='dummy')
        payment2.save()

        call_command('get_card_payments_states')

        self.log_handler.check(
            ('django_pain.management.commands.get_card_payments_states', 'INFO',
             'Command get_card_payments_states started.'),
            ('django_pain.management.commands.get_card_payments_states', 'INFO', 'Getting state of 1 payment(s).'),
        )
        self.assertQuerysetEqual(BankPayment.objects.values_list('identifier', 'state').order_by('identifier'),
                                 [('PAYMENT_1', PaymentState.READY_TO_PROCESS.value),
                                  ('PAYMENT_2', PaymentState.READY_TO_PROCESS.value)],
                                 transform=tuple)

    @override_settings(PAIN_CARD_PAYMENT_HANDLERS={
        'dummy_exc': 'django_pain.tests.utils.DummyCardPaymentHandlerExc'}
    )
    def test_error(self):
        payment = get_payment(identifier='PAYMENT_1', account=self.account, state=PaymentState.INITIALIZED,
                              card_handler='dummy_exc')
        payment.save()

        call_command('get_card_payments_states')
        self.log_handler.check(
            ('django_pain.management.commands.get_card_payments_states', 'INFO',
             'Command get_card_payments_states started.'),
            ('django_pain.management.commands.get_card_payments_states', 'INFO', 'Getting state of 1 payment(s).'),
            ('django_pain.management.commands.get_card_payments_states', 'ERROR',
             'Error while updating state of payment identifier=PAYMENT_1')
        )

    @override_settings(PAIN_CARD_PAYMENT_HANDLERS={
        'dummy_cexc': 'django_pain.tests.utils.DummyCardPaymentHandlerConnExc'}
    )
    def test_connection_error(self):
        payment = get_payment(identifier='PAYMENT_1', account=self.account, state=PaymentState.INITIALIZED,
                              card_handler='dummy_cexc')
        payment.save()

        call_command('get_card_payments_states')
        self.log_handler.check(
            ('django_pain.management.commands.get_card_payments_states', 'INFO',
             'Command get_card_payments_states started.'),
            ('django_pain.management.commands.get_card_payments_states', 'INFO', 'Getting state of 1 payment(s).'),
            ('django_pain.management.commands.get_card_payments_states', 'ERROR',
             'Connection error while updating state of payment identifier=PAYMENT_1')
        )

    def test_payments_from_to(self):
        """Test from/to parameters."""
        payment = get_payment(identifier='PAYMENT_1', account=self.account, state=PaymentState.INITIALIZED,
                              card_handler='dummy')
        payment.save()
        payment2 = get_payment(identifier='PAYMENT_2', account=self.account, state=PaymentState.INITIALIZED,
                               card_handler='dummy', create_time=datetime.date(2010, 1, 1))
        payment2.save()
        payment3 = get_payment(identifier='PAYMENT_3', account=self.account, state=PaymentState.INITIALIZED,
                               card_handler='dummy')
        payment3.save()

        # auto_add fields must be changed after first save:
        payment.create_time = datetime.date(2000, 1, 1)
        payment.save()
        payment2.create_time = datetime.date(2010, 1, 1)
        payment2.save()
        payment3.create_time = datetime.date(2020, 1, 1)
        payment3.save()

        call_command('get_card_payments_states', '--from', '2009-01-01 00:00', '--to', '2017-01-02 00:00')

        self.assertQuerysetEqual(BankPayment.objects.values_list('identifier', 'state').order_by('identifier'),
                                 [('PAYMENT_1', PaymentState.INITIALIZED.value),
                                  ('PAYMENT_2', PaymentState.READY_TO_PROCESS.value),
                                  ('PAYMENT_3', PaymentState.INITIALIZED.value)],
                                 transform=tuple)

    def test_invalid_from_to_raises_exception(self):
        with self.assertRaises(CommandError):
            call_command('get_card_payments_states', '--from', '2009-01-32 00:00', '--to', '2017-02-01 00:00')
        with self.assertRaises(CommandError):
            call_command('get_card_payments_states', '--from', 'not a date', '--to', '2017-01-02 00:00')
        with self.assertRaises(CommandError):
            call_command('get_card_payments_states', '--from', '2009-01-01 00:00', '--to', '2017-01-32 00:00')
        with self.assertRaises(CommandError):
            call_command('get_card_payments_states', '--from', '2009-01-01 00:00', '--to', 'not a date')
