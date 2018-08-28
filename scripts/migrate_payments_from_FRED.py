"""Load payments from JSON exported by FRED."""
import os  # isort:skip
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_pain.tests.settings')  # noqa: E402

import django  # isort:skip
django.setup()  # noqa: E402

import json
import logging
import sys

import pytz
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import make_aware
from djmoney.money import Money

from django_pain.constants import InvoiceType, PaymentState
from django_pain.models import BankAccount, BankPayment, Client, Invoice


def compose_account_number(account_number: str, bank_code: str) -> str:
    """Compose bank account number from number and bank code."""
    return '{}/{}'.format(account_number, bank_code)


def process_payment(payment: BankPayment, data: dict) -> None:
    """Create client and invoices, assign processor and objective."""
    if data['registrar_handle']:
        # Payment is from registrar.
        # We need to create client and invoices.
        payment.state = PaymentState.PROCESSED
        payment.processor = 'fred'
        payment.objective = 'Registrar payment'
        payment.objective_en = 'Registrar payment'
        payment.objective_cs = 'Platba registrátora'
        payment.save()

        Client.objects.create(
            handle=data['registrar_handle'],
            remote_id=data['registrar_id'],
            payment=payment,
        )

        if data['advance_invoice']:
            for invoice_id, invoice_number in data['advance_invoice'].items():
                invoice, created = Invoice.objects.get_or_create(number=invoice_number, defaults={
                    'remote_id': invoice_id, 'invoice_type': InvoiceType.ADVANCE})
                invoice.payments.add(payment)

        if data['account_invoices']:
            for invoice_id, invoice_number in data['account_invoices'].items():
                invoice, created = Invoice.objects.get_or_create(number=invoice_number, defaults={
                    'remote_id': invoice_id, 'invoice_type': InvoiceType.ACCOUNT})
                invoice.payments.add(payment)

    elif data['type'] == 5:
        # Payment is academy-related.
        payment.state = PaymentState.PROCESSED
        payment.processor = 'payments'
        payment.objective = 'Related to academy'
        payment.objective_en = 'Related to academy'
        payment.objective_cs = 'Platba akademie'
        payment.save()


accounts = dict((acc.account_number, acc) for acc in BankAccount.objects.all())

stats = {
    'imported': 0,
    'skipped': 0,
    'errors': 0,
}


for line in sys.stdin:
    data = json.loads(line.strip())

    account_number = compose_account_number(data['account_number'], data['bank_code'])

    if account_number not in accounts:
        logging.warn('Invalid account number %s. Skipping payment %s.', account_number, data['uuid'])
        stats['skipped'] += 1
        continue

    if data['code'] != 1 or data['status'] != 1:
        # Unfinished payments or any other wierd state payments.
        # We don't want these payments in the system.
        stats['skipped'] += 1
        continue

    if (data['type'] not in [1, 5]) and (not data['advance_invoice']):
        # Payment is of some other type, like transfer between our accounts.
        # We don't want these payments in the system.
        stats['skipped'] += 1
        continue

    try:
        with transaction.atomic():
            if BankPayment.objects.filter(uuid=data['uuid']).count() > 0:
                logging.info('Payment %s has already been imported. Skipping.', data['uuid'])
                stats['skipped'] += 1
                continue

            payment = BankPayment(
                uuid=data['uuid'],
                identifier=data['account_payment_ident'],
                account=accounts[account_number],
                transaction_date=parse_date(data['date']),
                counter_account_number=compose_account_number(data['counter_account_number'],
                                                              data['counter_account_bank_code']),
                counter_account_name=data['counter_account_name'] or '',
                amount=Money(data['price'], 'CZK'),
                description=data['memo'] or '',
                constant_symbol=data['constant_symbol'] or '',
                variable_symbol=data['variable_symbol'] or '',
                specific_symbol=data['specific_symbol'] or '',
            )

            try:
                payment.full_clean()
            except ValidationError as err:
                logging.error('Payment %s has invalid data: %s', data['uuid'], err)
                stats['errors'] += 1
                continue
            else:
                payment.save()

            create_time = parse_datetime(data['creation_time'])
            if settings.USE_TZ:
                create_time = make_aware(create_time, timezone=pytz.utc)
            payment.create_time = create_time
            payment.save()

            process_payment(payment, data)
            stats['imported'] += 1
    except DatabaseError as err:
        logging.error('Payment %s has invalid data: %s', data['uuid'], err)
        stats['errors'] += 1

print('=== Total stats ===\n'
      'imported: {}\n'
      ' skipped: {}\n'
      '  errors: {}'.format(stats['imported'], stats['skipped'], stats['errors']))

sys.exit(0 if stats['errors'] == 0 else 1)
