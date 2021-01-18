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
from typing import Iterable

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import IntegrityError

from django_pain.models import BankPayment
from django_pain.settings import SETTINGS

LOGGER = logging.getLogger(__name__)


class SavePaymentsMixin(ABC):
    """Mixin to give ability to save BankPayments."""

    def save_payments(self: BaseCommand, payments: Iterable[BankPayment]) -> None:
        """Save payments and related objects to database."""
        skipped = 0
        for payment in payments:
            try:
                skipped += self._save_if_not_exists(payment)
            except ValidationError as error:
                skipped += 1
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
                else:
                    LOGGER.warning('\n'.join(error.messages))
                    if self.options['verbosity'] >= 1:
                        self.stderr.write(self.style.WARNING('\n'.join(error.messages)))
            except IntegrityError as error:
                skipped += 1
                message = 'Payment ID %s has not been saved due to the following error: %s'
                LOGGER.warning(message, payment.identifier, str(error))
                if self.options['verbosity'] >= 1:
                    self.stderr.write(self.style.WARNING(message % (payment.identifier, str(error))))
            else:
                if self.options['verbosity'] >= 2:
                    self.stdout.write(self.style.SUCCESS('Payment ID {} has been imported.'.format(payment.identifier)))
        if skipped:
            LOGGER.info('Skipped %d payments.', skipped)

    def _save_if_not_exists(self: BaseCommand, payment: BankPayment) -> int:
        """Return value is the number of skipped payments."""
        with transaction.atomic():
            if self._payment_exists(payment):
                LOGGER.info('Payment ID %s already exists - skipping.', payment)
                return 1
            else:
                payment.full_clean()
                for callback in SETTINGS.import_callbacks:
                    payment = callback(payment)
                payment.save()
                return 0

    @staticmethod
    def _payment_exists(payment: BankPayment) -> bool:
        query = BankPayment.objects.filter(account=payment.account, identifier=payment.identifier)
        return query.exists()
