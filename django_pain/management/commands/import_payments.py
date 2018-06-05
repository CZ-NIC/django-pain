"""Command for importing payments from bank."""
import sys
from typing import Iterable

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import module_loading

from django_pain.models import BankAccount, BankPayment
from django_pain.parsers.common import AbstractBankStatementParser


class Command(BaseCommand):
    """Import payments from bank."""

    help = 'Import payments from the bank. Bank statement should be provided on standard input.'

    def add_arguments(self, parser):
        """Command takes one argument - dotted path to parser class."""
        parser.add_argument('-p', '--parser', type=str, required=True, help='dotted path to parser class')
        parser.add_argument('input_file', nargs='*', type=str, default=['-'], help='input file with bank statement')

    def handle(self, *args, **options):
        """Run command."""
        self.options = options

        parser_class = module_loading.import_string(options['parser'])
        if not issubclass(parser_class, AbstractBankStatementParser):
            raise CommandError('Parser argument has to be subclass of AbstractBankStatementParser.')
        parser = parser_class()  # type: AbstractBankStatementParser

        for input_file in options['input_file']:
            if input_file == '-':
                handle = sys.stdin
            else:
                handle = open(input_file)

            try:
                payments = parser.parse(handle)
            except BankAccount.DoesNotExist as e:
                raise CommandError(e)
            else:
                self.save_payments(payments)
            finally:
                handle.close()

    def save_payments(self, payments: Iterable[BankPayment]) -> None:
        """Save payments and related objects to database."""
        for payment in payments:
            try:
                with transaction.atomic():
                    payment.full_clean()
                    payment.save()
            except ValidationError as error:
                if self.options['verbosity'] >= 1:
                    for message in error.messages:
                        self.stderr.write(self.style.WARNING(message))
            else:
                if self.options['verbosity'] >= 2:
                    self.stdout.write(self.style.SUCCESS('Payment ID %s has been imported.' % payment.identifier))
