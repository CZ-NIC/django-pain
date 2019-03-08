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

"""Command for processing bank payments."""
import fcntl
import logging
from copy import deepcopy

from django.core.management.base import BaseCommand, no_translations
from django.utils.dateparse import parse_datetime

from django_pain.constants import PaymentState
from django_pain.models import BankPayment
from django_pain.settings import SETTINGS, get_processor_instance

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    """Process bank payments."""

    help = 'Process unprocessed payments by predefined payment processors.'

    def add_arguments(self, parser):
        """Command takes optional arguments restricting processed time interval."""
        parser.add_argument('-f', '--from', dest='time_from', type=parse_datetime,
                            help="ISO datetime after which payments should be processed")
        parser.add_argument('-t', '--to', dest='time_to', type=parse_datetime,
                            help="ISO datetime before which payments should be processed")

    @no_translations
    def handle(self, *args, **options):
        """
        Run command.

        If can't acquire lock, display warning and terminate.
        """
        LOGGER.info('Command process_payments started.')
        try:
            LOCK = open(SETTINGS.process_payments_lock_file, 'a')
            fcntl.flock(LOCK, fcntl.LOCK_EX | fcntl.LOCK_NB)
            LOGGER.info('Lock acquired.')
        except OSError:
            self.stderr.write(self.style.WARNING('Command process_payments is already running. Terminating.'))
            LOCK.close()
            LOGGER.info('Command already running. Terminating.')
            return

        try:
            payments = BankPayment.objects.filter(state__in=[PaymentState.IMPORTED, PaymentState.DEFERRED])
            if options['time_from'] is not None:
                payments = payments.filter(create_time__gte=options['time_from'])
            if options['time_to'] is not None:
                payments = payments.filter(create_time__lte=options['time_to'])
            payments = payments.order_by('transaction_date')

            LOGGER.info('Processing %s unprocessed payments.', payments.count())

            for processor_name in SETTINGS.processors:
                processor = get_processor_instance(processor_name)
                if not payments:
                    break

                LOGGER.info('Processing payments with processor %s.', processor_name)
                results = processor.process_payments(deepcopy(payment) for payment in payments)  # pragma: no cover
                unprocessed_payments = []

                for payment, processed in zip(payments, results):
                    if processed.result:
                        payment.state = PaymentState.PROCESSED
                        payment.processor = processor_name
                        payment.processing_error = processed.error
                        payment.save()
                    elif processed.error is not None:
                        LOGGER.info('Saving payment %s as DEFERRED with error %s.', payment.uuid, processed.error)
                        payment.state = PaymentState.DEFERRED
                        payment.processor = processor_name
                        payment.processing_error = processed.error
                        payment.save()
                    else:
                        unprocessed_payments.append(payment)

                payments = unprocessed_payments

            LOGGER.info('Marking %s unprocessed payments as DEFERRED.', len(payments))
            for unprocessed_payment in payments:
                unprocessed_payment.state = PaymentState.DEFERRED
                unprocessed_payment.save()
        finally:
            fcntl.flock(LOCK, fcntl.LOCK_UN)
            LOCK.close()
        LOGGER.info('Command process_payments finished.')
