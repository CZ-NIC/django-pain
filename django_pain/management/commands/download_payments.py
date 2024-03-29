#
# Copyright (C) 2020-2021  CZ.NIC, z. s. p. o.
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

"""Command for downloading payments from bank."""
import logging
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple
from warnings import warn

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, no_translations
from django.utils import timezone

from django_pain.management.command_mixins import SavePaymentsMixin
from django_pain.models import BankAccount, BankPayment, PaymentImportHistory
from django_pain.settings import SETTINGS
from django_pain.utils import parse_datetime_safe

try:
    from teller.downloaders import RawStatement
    from teller.statement import BankStatement, Payment
except ImportError:
    warn('Failed to import teller library.', UserWarning)
    BankStatement = object  # type: ignore
    Payment = object  # type: ignore
    RawStatement = object  # type: ignore

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand, SavePaymentsMixin):
    """Download payments from banks."""

    help = 'Download payments from the banks.'
    default_interval = 7

    def add_arguments(self, parser):
        """Command takes two argument - end date and interval in days."""
        parser.add_argument('-e', '--end', type=parse_datetime_safe, required=False,
                            help='end date of the download interval, default: TODAY')
        parser.add_argument('-s', '--start', type=parse_datetime_safe, required=False,
                            help='start date of the download interval, default: END minus seven days')
        parser.add_argument('-d', '--downloader', type=str, action='append', choices=SETTINGS.downloaders.keys(),
                            dest='downloaders', required=False,
                            help='select subset of PAIN_DOWNLOADERS, default: all defined downloaders')

    @no_translations
    def handle(self, *args, **options):
        """Run command."""
        self.options = options
        LOGGER.info('Command download_payments started.')

        start_date, end_date = self._set_dates(options['start'], options['end'])
        downloaders = self._filter_downloaders(options['downloaders'])

        for key, value in downloaders.items():
            LOGGER.info('Processing: {}'.format(key))
            import_history = PaymentImportHistory(origin=key)
            import_history.save()

            downloader_class = value['DOWNLOADER']
            parser_class = value['PARSER']

            try:
                downloader = downloader_class(**value['DOWNLOADER_PARAMS'])
            except Exception:
                # Do not log the error message here as it may contain sensitive information such as login credentials.
                LOGGER.error('Could not init Downloader for %s.', key)
                continue
            try:
                # TODO: urllib3.connectionpool logs the URL in the DEBUG mode
                LOGGER.debug('Downloading payments for %s.', key)
                raw_statements = downloader.get_statements(start_date, end_date)
            except Exception:
                # Do not log the error message here as it may contain sensitive information such as login credentials.
                LOGGER.error('Downloading payments for %s failed.', key)
                continue

            for statement in raw_statements:
                if statement.name:
                    import_history.add_filename(statement.name)
            import_history.save()

            LOGGER.debug('Parsing payments for %s.', key)
            payments, parsing_errors = self._parse_payments(parser_class, raw_statements)

            if len(payments) > 0:
                LOGGER.debug('Saving payments for %s.', key)
            result = self.save_payments(payments)

            import_history.errors = result.errors + parsing_errors
            import_history.finished = True
            import_history.save()

        LOGGER.info('Command download_payments finished.')

    def _set_dates(self, start_date: Optional[datetime], end_date: Optional[datetime]) -> Tuple[datetime, datetime]:
        if end_date is None:
            end_date = timezone.now()

        if start_date is None:
            start_date = end_date - timedelta(days=7)

        if settings.USE_TZ:
            start_date = self._update_tzinfo(start_date)
            end_date = self._update_tzinfo(end_date)

        if (start_date.tzinfo is None) != (end_date.tzinfo is None):
            raise CommandError('Offset-naive used with offset-aware datetime.')

        if start_date > end_date:
            raise CommandError('Start date has to be lower or equal to the end date.')
        return start_date, end_date

    def _update_tzinfo(self, item: datetime) -> datetime:
        current_timezone = timezone.get_current_timezone()
        if item.tzinfo is None:
            item = item.replace(tzinfo=current_timezone)
        else:
            item = item.astimezone(current_timezone)
        return item

    def _filter_downloaders(self, selected_downloaders: Optional[List[str]]) -> Dict[str, Dict[str, Any]]:
        if selected_downloaders is not None:
            return OrderedDict((k, v) for k, v in SETTINGS.downloaders.items() if k in selected_downloaders)
        else:
            return SETTINGS.downloaders

    def _parse_payments(self, parser, raw_statements: Iterable[RawStatement]) -> Tuple[List[BankPayment], int]:
        parsing_errors = 0
        payments = []  # type: List[BankPayment]
        for raw_statement in raw_statements:
            try:
                statement = parser.parse_file(raw_statement.buffer, encoding=raw_statement.encoding)
            except Exception as e:
                LOGGER.error(str(e))
                parsing_errors += 1
                continue
            if len(statement.payments) > 0:
                payments.extend(self._convert_to_models(statement))
        return payments, parsing_errors

    def _convert_to_models(self, statement: BankStatement) -> Iterable[BankPayment]:
        account_number = statement.account_number
        try:
            account = BankAccount.objects.get(account_number=account_number)
        except BankAccount.DoesNotExist:
            raise CommandError('Bank account {} does not exist.'.format(account_number))
        payments = []
        for payment_data in statement:
            payment = self._payment_from_data_class(account, payment_data)
            payments.append(payment)
        return payments

    def _payment_from_data_class(self, account: BankAccount, payment: Payment) -> BankPayment:
        """Convert Payment data class from teller to Django model."""
        result = BankPayment(identifier=payment.identifier,
                             account=account,
                             transaction_date=payment.transaction_date,
                             counter_account_number=self._value_or_blank(payment.counter_account),
                             counter_account_name=self._value_or_blank(payment.name),
                             amount=payment.amount,
                             description=self._value_or_blank(payment.description),
                             constant_symbol=self._value_or_blank(payment.constant_symbol),
                             variable_symbol=self._value_or_blank(payment.variable_symbol),
                             specific_symbol=self._value_or_blank(payment.specific_symbol))
        return result

    def _value_or_blank(self, value: Optional[str]) -> str:
        return '' if value is None else value
