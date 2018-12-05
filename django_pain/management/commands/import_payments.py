"""Command for importing payments from bank."""
import logging
import sys
from typing import Iterable

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, no_translations
from django.db import transaction
from django.utils import module_loading

from django_pain.models import BankAccount, BankPayment
from django_pain.parsers.common import AbstractBankStatementParser

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    """Import payments from bank."""

    help = 'Import payments from the bank. Bank statement should be provided on standard input.'

    def add_arguments(self, parser):
        """Command takes one argument - dotted path to parser class."""
        parser.add_argument('-p', '--parser', type=str, required=True, help='dotted path to parser class')
        parser.add_argument('input_file', nargs='*', type=str, default=['-'], help='input file with bank statement')

    @no_translations
    def handle(self, *args, **options):
        """Run command."""
        self.options = options
        LOGGER.info('Command import_payments started.')

        parser_class = module_loading.import_string(options['parser'])
        if not issubclass(parser_class, AbstractBankStatementParser):
            raise CommandError('Parser argument has to be subclass of AbstractBankStatementParser.')
        parser = parser_class()  # type: AbstractBankStatementParser

        for input_file in options['input_file']:
            LOGGER.debug('Importing payments from %s.', input_file)
            if input_file == '-':
                handle = sys.stdin
            else:
                handle = open(input_file)

            try:
                LOGGER.debug('Parsing payments from %s.', input_file)
                payments = list(parser.parse(handle))
                LOGGER.debug('Saving %s payments from %s to database.', len(payments), input_file)
                self.save_payments(payments)
            except BankAccount.DoesNotExist as e:
                LOGGER.error(str(e))
                raise CommandError(e)
            finally:
                handle.close()
        LOGGER.info('Command import_payments finished.')

    def save_payments(self, payments: Iterable[BankPayment]) -> None:
        """Save payments and related objects to database."""
        for payment in payments:
            try:
                with transaction.atomic():
                    payment.full_clean()
                    payment.save()
            except ValidationError as error:
                message = 'Payment ID %s has not been saved due to the following errors:'
                LOGGER.warning(message, payment.identifier)
                if self.options['verbosity'] >= 1:
                    self.stderr.write(self.style.WARNING(message % payment.identifier))

                for field in error.message_dict:
                    prefix = '{}: '.format(field) if field != '__all__' else ''
                    for message in error.message_dict[field]:
                        LOGGER.warning('%s%s', prefix, message)
                        if self.options['verbosity'] >= 1:
                            self.stderr.write(self.style.WARNING('%s%s' % (prefix, message)))
            else:
                if self.options['verbosity'] >= 2:
                    self.stdout.write(self.style.SUCCESS('Payment ID {} has been imported.'.format(payment.identifier)))
