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

from django.core.management.base import BaseCommand, CommandError, no_translations
from django.utils.dateparse import parse_datetime

from django_pain.constants import PaymentState
from django_pain.models import BankAccount, BankPayment
from django_pain.settings import SETTINGS, get_processor_instance

LOGGER = logging.getLogger(__name__)


class AccountDoesNotExist(Exception):
    """Account number does not exist."""


class Command(BaseCommand):
    """Process bank payments."""

    help = 'Process unprocessed payments by predefined payment processors.'

    def add_arguments(self, parser):
        """Command takes optional arguments restricting processed time interval."""
        parser.add_argument('-f', '--from', dest='time_from', type=parse_datetime,
                            help="ISO datetime after which payments should be processed")
        parser.add_argument('-t', '--to', dest='time_to', type=parse_datetime,
                            help="ISO datetime before which payments should be processed")
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--include-accounts', type=(lambda x: set(x.split(','))),
                           help='Comma separated list of account numbers that should be included')
        group.add_argument('--exclude-accounts', type=(lambda x: set(x.split(','))),
                           help='Comma separated list of account numbers that should be excluded')

    @staticmethod
    def _check_accounts_existence(account_numbers):
        """Raise AccountDoesNotExist when an account does not exist."""
        db_account_numbers = set(BankAccount.objects.filter(account_number__in=account_numbers).values_list(
            'account_number', flat=True))
        if len(db_account_numbers) != len(account_numbers):
            non_existing_accounts = sorted(account_numbers.difference(db_account_numbers))
            raise AccountDoesNotExist('Following accounts do not exist: %s. Terminating.'
                                      % ', '.join(non_existing_accounts))

    @staticmethod
    def _process_payments(payments):
        """Process the payments."""
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

    @no_translations
    def handle(self, *args, **options):
        """
        Run command.

        If can't acquire lock, display warning and terminate.
        """
        LOGGER.info('Command process_payments started.')
        LOCK = None
        try:
            LOCK = open(SETTINGS.process_payments_lock_file, 'a')
            fcntl.flock(LOCK, fcntl.LOCK_EX | fcntl.LOCK_NB)
            LOGGER.info('Lock acquired.')
        except OSError as error:
            if LOCK is not None:
                self.stderr.write(self.style.WARNING('Command process_payments is already running. Terminating.'))
                LOCK.close()
                LOGGER.info('Command already running. Terminating.')
                return
            else:
                LOGGER.error(
                    'Error occured while opening lockfile %s: %s. Terminating.',
                    SETTINGS.process_payments_lock_file, str(error)
                )
                raise CommandError('Error occured while opening lockfile {}: {}. Terminating.'.format(
                    SETTINGS.process_payments_lock_file, str(error)))

        try:
            payments = BankPayment.objects.filter(state__in=[PaymentState.IMPORTED, PaymentState.DEFERRED])
            if options['time_from'] is not None:
                payments = payments.filter(create_time__gte=options['time_from'])
            if options['time_to'] is not None:
                payments = payments.filter(create_time__lte=options['time_to'])
            if options['include_accounts']:
                self._check_accounts_existence(options['include_accounts'])
                payments = payments.filter(account__account_number__in=options['include_accounts'])
            if options['exclude_accounts']:
                self._check_accounts_existence(options['exclude_accounts'])
                payments = payments.exclude(account__account_number__in=options['exclude_accounts'])
            payments = payments.order_by('transaction_date')

            LOGGER.info('Processing %s unprocessed payments.', payments.count())

            self._process_payments(payments)

        except AccountDoesNotExist as e:
            LOGGER.error(str(e))
            raise CommandError(str(e))
        finally:
            fcntl.flock(LOCK, fcntl.LOCK_UN)
            LOCK.close()
        LOGGER.info('Command process_payments finished.')
