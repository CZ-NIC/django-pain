"""Command for processing bank payments."""
from copy import deepcopy

from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from django_pain.apps import PainSettings
from django_pain.constants import PaymentState
from django_pain.models import BankPayment


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
        """Run command."""
        payments = BankPayment.objects.filter(state__in=[PaymentState.IMPORTED, PaymentState.DEFERRED])
        if options['time_from'] is not None:
            payments = payments.filter(create_time__gte=options['time_from'])
        if options['time_to'] is not None:
            payments = payments.filter(create_time__lte=options['time_to'])

        settings = PainSettings()
        processors = [processor() for processor in settings.processors]

        for payment in payments:
            for processor in processors:
                if processor.process_payment(deepcopy(payment)):
                    payment.state = PaymentState.PROCESSED
                    payment.save()
                    break
            else:
                payment.state = PaymentState.DEFERRED
                payment.save()
