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

"""Command for listing bank payments."""
import argparse

from django.core.management.base import BaseCommand, no_translations

from django_pain.models import BankPayment


def format_payment(payment: BankPayment) -> str:
    """Return formatted payment row."""
    row = ('{ident:10}   {create:32}   amount: {amount:>13}   '
           'account_memo: {memo:40}   account_name: {account:26}').format(
                ident=payment.identifier, create=payment.create_time.isoformat(), amount=str(payment.amount),
                memo=payment.description.strip(), account=payment.counter_account_name,
           )
    if payment.processing_error:
        row += '   processing_error: {}'.format(payment.get_processing_error_display())
    return row.strip()


def non_negative_integer(x: str) -> int:
    """Transform string to integer and check that it's non-negative."""
    value = int(x)
    if value < 0:
        raise argparse.ArgumentTypeError('limit must be non-negative integer')
    return value


@no_translations
class Command(BaseCommand):
    """List bank payments."""

    help = 'List bank payments.'

    def add_arguments(self, parser):
        """Command takes optional arguments restricting processed time interval."""
        parser.add_argument('--state', type=str, choices=['imported', 'processed', 'deferred', 'exported'],
                            help='Payments state')
        parser.add_argument('--limit', type=non_negative_integer, help='Limit number of payments on output')
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--include-accounts', type=(lambda x: x.split(',')),
                           help='Comma separated list of account numbers that should be included')
        group.add_argument('--exclude-accounts', type=(lambda x: x.split(',')),
                           help='Comma separated list of account numbers that should be excluded')

    def handle(self, *args, **options):
        """Run command."""
        VERBOSITY = options['verbosity']

        payments = BankPayment.objects.all()
        if options['state']:
            payments = payments.filter(state=options['state'])

        if options['include_accounts']:
            payments = payments.filter(account__account_number__in=options['include_accounts'])

        if options['exclude_accounts']:
            payments = payments.exclude(account__account_number__in=options['exclude_accounts'])

        payments = payments.order_by('-create_time')

        payments_total = payments.count()
        if options['limit'] is not None:
            payments = payments[0:options['limit']]

        for payment in payments:
            if VERBOSITY == 0:
                self.stdout.write(payment.identifier)
            else:
                self.stdout.write(format_payment(payment))

        not_displayed = payments_total - payments.count()
        if not_displayed > 0:
            self.stdout.write('... and %s more payments' % not_displayed)
