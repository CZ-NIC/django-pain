"""Command for processing bank payments."""
import fcntl
from copy import deepcopy

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from django_pain.constants import PaymentState
from django_pain.models import BankPayment
from django_pain.settings import SETTINGS, get_processor_instance


class Command(BaseCommand):
    """Process bank payments."""

    help = 'Process unprocessed payments by predefined payment processors.'

    def add_arguments(self, parser):
        """Command takes optional arguments restricting processed time interval."""
        parser.add_argument('-f', '--from', dest='time_from', type=parse_datetime,
                            help="ISO datetime after which payments should be processed")
        parser.add_argument('-t', '--to', dest='time_to', type=parse_datetime,
                            help="ISO datetime before which payments should be processed")

    def handle(self, *args, **options):
        """
        Run command.

        If can't acquire lock, display warning and terminate.
        """
        try:
            LOCK = open(SETTINGS.process_payments_lock_file, 'a')
            fcntl.flock(LOCK, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stderr.write(self.style.WARNING('Command process_payments is already running. Terminating.'))
            LOCK.close()
            return

        try:
            payments = BankPayment.objects.filter(state__in=[PaymentState.IMPORTED, PaymentState.DEFERRED])
            if options['time_from'] is not None:
                payments = payments.filter(create_time__gte=options['time_from'])
            if options['time_to'] is not None:
                payments = payments.filter(create_time__lte=options['time_to'])
            payments = payments.order_by('transaction_date')

            for processor_name in SETTINGS.processors:
                processor = get_processor_instance(processor_name)
                if not payments:
                    break

                results = processor.process_payments(deepcopy(payment) for payment in payments)  # pragma: no cover
                unprocessed_payments = []

                for payment, processed in zip(payments, results):
                    if processed.result:
                        payment.state = PaymentState.PROCESSED
                        payment.processor = processor_name
                        payment.save()
                    else:
                        unprocessed_payments.append(payment)

                payments = unprocessed_payments

            for unprocessed_payment in payments:
                unprocessed_payment.state = PaymentState.DEFERRED
                unprocessed_payment.save()
        finally:
            fcntl.flock(LOCK, fcntl.LOCK_UN)
            LOCK.close()
