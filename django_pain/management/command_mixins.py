#
# Copyright (C) 2021  CZ.NIC, z. s. p. o.
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

"""Module with mixins used in commands."""
import logging
from abc import ABC
from collections import namedtuple
from typing import Iterable

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import IntegrityError

from django_pain.models import BankPayment
from django_pain.settings import SETTINGS

LOGGER = logging.getLogger(__name__)

Result = namedtuple('Result', ('saved', 'skipped', 'errors'))


class SavePaymentsMixin(ABC):
    """Mixin to give ability to save BankPayments."""

    def save_payments(self: BaseCommand, payments: Iterable[BankPayment]) -> Result:
        """Save payments and related objects to database."""
        saved = 0
        skipped = 0
        errors = 0
        for payment in payments:
            try:
                payment_saved = self._save_if_not_exists(payment)
            except (ValidationError, IntegrityError) as error:
                errors += 1
                self._process_error(payment, error)
            else:
                if payment_saved:
                    saved += 1
                    if self.options['verbosity'] >= 2:
                        self.stdout.write(self.style.SUCCESS(
                            'Payment ID {} has been imported.'.format(payment.identifier)))
                else:
                    skipped += 1
                    if self.options['verbosity'] >= 2:
                        self.stdout.write(self.style.SUCCESS(
                            'Payment ID {} was skipped.'.format(payment.identifier)))
        if skipped:
            LOGGER.info('Skipped %d payments.', skipped)
        if errors:
            LOGGER.info('%d payments not saved due to errors.', errors)
        return Result(saved, skipped, errors)

    def _save_if_not_exists(self: BaseCommand, payment: BankPayment) -> bool:
        """Return True if payment was saved."""
        with transaction.atomic():
            if self._payment_exists(payment):
                LOGGER.info('Payment ID %s already exists - skipping.', payment)
                return False
            else:
                payment.full_clean()
                for callback in SETTINGS.import_callbacks:
                    # Store payment id in case it is turned to None by the callback.
                    payment_id = payment.identifier
                    payment = callback(payment)
                    if payment is None:
                        LOGGER.info('Payment ID %s skipped by callback %s', payment_id, callback.__name__)
                        return False
                payment.save()
                return True

    @staticmethod
    def _payment_exists(payment: BankPayment) -> bool:
        query = BankPayment.objects.filter(account=payment.account, identifier=payment.identifier)
        return query.exists()

    def _process_error(self: BaseCommand, payment, error):
        message = 'Payment ID %s has not been saved due to the following errors:'
        LOGGER.warning(message, payment.identifier)
        if self.options['verbosity'] >= 1:
            self.stderr.write(self.style.WARNING(message % payment.identifier))

        if hasattr(error, 'message_dict'):
            for field in error.message_dict:
                prefix = '{}: '.format(field) if field != '__all__' else ''
                for message in error.message_dict[field]:
                    LOGGER.warning('%s%s', prefix, message)
                    if self.options['verbosity'] >= 1:
                        self.stderr.write(self.style.WARNING('%s%s' % (prefix, message)))
        elif hasattr(error, 'messages'):
            LOGGER.warning('\n'.join(error.messages))
            if self.options['verbosity'] >= 1:
                self.stderr.write(self.style.WARNING('\n'.join(error.messages)))
        else:
            LOGGER.warning(error)
            if self.options['verbosity'] >= 1:
                self.stderr.write(self.style.WARNING(str(error)))
