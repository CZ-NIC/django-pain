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
import threading
from queue import Queue
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from testfixtures import LogCapture

from django_pain.constants import PaymentState
from django_pain.models import BankAccount, BankPayment
from django_pain.settings import get_card_payment_handler_class, get_card_payment_handler_instance
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


@skipUnlessDBFeature('has_select_for_update')
@override_settings(PAIN_CARD_PAYMENT_HANDLERS={
    'dummy': 'django_pain.tests.utils.DummyCardPaymentHandler'}
)
class TestGetPaymentsStatesLocking(TransactionTestCase):

    def setUp(self):
        self.account = BankAccount(account_number='123456/7890', currency='CZK')
        self.account.save()
        self.log_handler = LogCapture('django_pain.management.commands.get_card_payments_states', propagate=False)
        # Exception in a threads does not fail the test - wee need to collect it somemehow
        self.errors = Queue()  # type: Queue

    def tearDown(self):
        self.log_handler.uninstall()

    def test_processing_does_not_overwrite_locked_rows(self):
        get_payment(identifier='PAYMENT_1', transaction_date=datetime.date(2018, 5, 2), account=self.account,
                    state=PaymentState.INITIALIZED, card_handler='dummy').save()
        get_payment(identifier='PAYMENT_2', transaction_date=datetime.date(2018, 4, 1), account=self.account,
                    state=PaymentState.INITIALIZED, card_handler='dummy').save()

        processing_finished = threading.Event()
        query_finished = threading.Event()

        def target_processing():
            query_finished.wait()
            try:
                call_command('get_card_payments_states')
            except Exception as e:  # pragma: no cover
                self.errors.put(e)
                raise e
            finally:
                processing_finished.set()
                close_old_connections()

        def target_query():
            try:
                with transaction.atomic():
                    BankPayment.objects.select_for_update().filter(identifier='PAYMENT_1').get()
                    query_finished.set()
                    processing_finished.wait()
            except Exception as e:  # pragma: no cover
                self.errors.put(e)
                raise e
            finally:
                query_finished.set()
                close_old_connections()

        threads = [threading.Thread(target=target_processing), threading.Thread(target=target_query)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(self.errors.empty())
        self.assertQuerysetEqual(BankPayment.objects.values_list('identifier', 'state').order_by('identifier'),
                                 [('PAYMENT_1', PaymentState.INITIALIZED.value),
                                  ('PAYMENT_2', PaymentState.READY_TO_PROCESS.value)],
                                 transform=tuple)

    def test_processed_rows_not_overwritten(self):
        processing_started = threading.Event()
        query_finished = threading.Event()

        p1 = get_payment(identifier='PAYMENT_1', account=self.account, state=PaymentState.INITIALIZED,
                         card_handler='dummy')
        p2 = get_payment(identifier='PAYMENT_2', account=self.account, state=PaymentState.INITIALIZED,
                         card_handler='dummy')
        p1.save()
        p2.save()

        p1.create_time = datetime.datetime(2018, 5, 2)
        p2.create_time = datetime.datetime(2018, 4, 1)
        p1.save()
        p2.save()

        def mock_update_state(payment):
            processing_started.set()
            query_finished.wait()
            payment.state = PaymentState.READY_TO_PROCESS
            payment.save()

        def target_processing():
            try:
                # cache may prevent mocking
                get_card_payment_handler_instance.cache_clear()
                get_card_payment_handler_class.cache_clear()
                with patch('django_pain.tests.utils.DummyCardPaymentHandler') as MockClass:
                    instance = MockClass.return_value
                    instance.update_payments_state = mock_update_state
                    call_command('get_card_payments_states', '--from', datetime.datetime(2018, 5, 1))
            except Exception as e:  # pragma: no cover
                self.errors.put(e)
                raise e
            finally:
                processing_started.set()
                close_old_connections()
                # mock might be cached
                get_card_payment_handler_instance.cache_clear()
                get_card_payment_handler_class.cache_clear()

        def target_query():
            processing_started.wait()
            try:
                with transaction.atomic():
                    payments = BankPayment.objects.select_for_update(skip_locked=True).all()
                    for p in payments:
                        p.state = PaymentState.PROCESSED
                        p.save()
            except Exception as e:  # pragma: no cover
                self.errors.put(e)
                raise e
            finally:
                query_finished.set()
                close_old_connections()

        threads = [threading.Thread(target=target_processing), threading.Thread(target=target_query)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertTrue(self.errors.empty())
        self.assertQuerysetEqual(BankPayment.objects.values_list('identifier', 'state').order_by('identifier'),
                                 [('PAYMENT_1', PaymentState.READY_TO_PROCESS.value),
                                  ('PAYMENT_2', PaymentState.PROCESSED.value)],
                                 transform=tuple)
