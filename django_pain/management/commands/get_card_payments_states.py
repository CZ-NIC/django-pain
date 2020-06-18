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

"""Command for updating states of card payments in non-final state."""
import logging

from django.core.management.base import BaseCommand, no_translations
from django.db import transaction
from django.utils.dateparse import parse_datetime

from django_pain.card_payment_handlers import PaymentHandlerConnectionError, PaymentHandlerError
from django_pain.constants import PaymentState
from django_pain.models import BankPayment
from django_pain.settings import get_card_payment_handler_instance

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    """Update states of card payments."""

    help = 'Update states of payments by their card handler.'

    def add_arguments(self, parser):
        """Command takes optional arguments restricting processed time interval."""
        parser.add_argument('-f', '--from', dest='time_from', type=parse_datetime,
                            help="ISO datetime after which payments should be processed")
        parser.add_argument('-t', '--to', dest='time_to', type=parse_datetime,
                            help="ISO datetime before which payments should be processed")

    def _get_payments_states(self, payments):
        """Get states of the payments using their card_payment_handler."""
        for payment in payments:
            try:
                with transaction.atomic():
                    payment = BankPayment.objects.select_for_update().get(id=payment.id)
                    card_payment_handler = get_card_payment_handler_instance(payment.card_handler)
                    card_payment_handler.update_payments_state(payment)
            except PaymentHandlerConnectionError:
                LOGGER.error('Connection error while updating state of payment identifier=%s', payment.identifier)
            except PaymentHandlerError:
                LOGGER.error('Error while updating state of payment identifier=%s', payment.identifier)

    @no_translations
    def handle(self, *args, **options):
        """Run the command."""
        LOGGER.info('Command get_card_payments_states started.')
        payments = BankPayment.objects.filter(state__in=[PaymentState.INITIALIZED])
        if options['time_from'] is not None:
            payments = payments.filter(create_time__gte=options['time_from'])
        if options['time_to'] is not None:
            payments = payments.filter(create_time__lte=options['time_to'])
        payments = payments.order_by('create_time')
        if payments:
            LOGGER.info('Getting state of %s payment(s).', payments.count())
            self._get_payments_states(payments)
        else:
            LOGGER.info('No payments to update state.')
