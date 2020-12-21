#
# Copyright (C) 2018-2020  CZ.NIC, z. s. p. o.
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

"""Payments and invoices models."""
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import BLANK_CHOICE_DASH, CheckConstraint, Q
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import CurrencyField, MoneyField

from django_pain.constants import CURRENCY_PRECISION, InvoiceType, PaymentProcessingError, PaymentState, PaymentType
from django_pain.settings import SETTINGS, get_processor_instance, get_processor_objective

PAYMENT_TYPE_CHOICES = (
    (PaymentType.TRANSFER, _('transfer')),
    (PaymentType.CARD_PAYMENT, _('card payment')),
)

PAYMENT_STATE_CHOICES = (
    (PaymentState.INITIALIZED, _('initialized')),
    (PaymentState.READY_TO_PROCESS, _('ready to process')),
    (PaymentState.PROCESSED, _('processed')),
    (PaymentState.DEFERRED, _('not identified')),
    (PaymentState.EXPORTED, _('exported')),
    (PaymentState.CANCELED, _('canceled')),
)

PROCESSING_ERROR_CHOICES = (
    (PaymentProcessingError.DUPLICITY, _('Duplicate payment')),
    (PaymentProcessingError.INSUFFICIENT_AMOUNT, _('Received amount is lower than expected')),
    (PaymentProcessingError.EXCESSIVE_AMOUNT, _('Received amount is greater than expected')),
    (PaymentProcessingError.OVERDUE, _('Payment is overdue')),
    (PaymentProcessingError.MANUALLY_BROKEN, _('Payment was manually broken')),
    (PaymentProcessingError.TOO_OLD, _("Payment is older than 15 days, it can't be processed automatically")),
)


class BankAccount(models.Model):
    """Bank account."""

    account_number = models.TextField(unique=True, verbose_name=_('Account number'))
    account_name = models.TextField(blank=True, verbose_name=_('Account name'))
    currency = CurrencyField()

    class Meta:
        """Meta class."""

        verbose_name = _('Bank account')
        verbose_name_plural = _('Bank accounts')

    def __str__(self):
        """Return string representation of bank account."""
        return '{} {}'.format(self.account_name, self.account_number)


class BankPayment(models.Model):
    """Bank payment."""

    identifier = models.TextField(verbose_name=_('Payment ID'))
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    payment_type = models.TextField(choices=PAYMENT_TYPE_CHOICES, default=PaymentType.TRANSFER,
                                    verbose_name=_('Payment type'))
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, verbose_name=_('Destination account'))
    create_time = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('Create time'))
    transaction_date = models.DateField(null=True, db_index=True, verbose_name=_('Transaction date'))

    counter_account_number = models.TextField(blank=True, verbose_name=_('Counter account number'))
    counter_account_name = models.TextField(blank=True, verbose_name=_('Counter account name'))

    amount = MoneyField(max_digits=64, decimal_places=CURRENCY_PRECISION, verbose_name=_('Amount'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    state = models.TextField(choices=PAYMENT_STATE_CHOICES, default=PaymentState.READY_TO_PROCESS, db_index=True,
                             verbose_name=_('Payment state'))
    card_payment_state = models.TextField(blank=True, verbose_name=_('Card payment state'))

    processing_error = models.TextField(choices=PROCESSING_ERROR_CHOICES, null=True, blank=True,
                                        verbose_name=_('Automatic processing error'))

    # Payment symbols (specific for Czech Republic and Slovak Republic).
    constant_symbol = models.CharField(max_length=10, blank=True, verbose_name=_('Constant symbol'))
    variable_symbol = models.CharField(max_length=10, blank=True, verbose_name=_('Variable symbol'))
    specific_symbol = models.CharField(max_length=10, blank=True, verbose_name=_('Specific symbol'))

    processor = models.TextField(verbose_name=_('Processor'), blank=True)
    card_handler = models.TextField(verbose_name=_('Card handler'), blank=True)

    class Meta:
        """Model Meta class."""

        unique_together = ('identifier', 'account')
        verbose_name = _('Bank payment')
        verbose_name_plural = _('Bank payments')

        constraints = [
            CheckConstraint(check=Q(payment_type=PaymentType.TRANSFER) & ~Q(counter_account_number__exact='')
                            | Q(payment_type=PaymentType.CARD_PAYMENT, counter_account_number__exact=''),
                            name='payment_counter_account_only_for_transfer')
        ]

    def __str__(self):
        """Return string representation of bank payment."""
        return self.identifier

    def clean(self):
        """Check whether payment currency is the same as currency of related bank account."""
        if self.account.currency != self.amount.currency.code:
            raise ValidationError('Bank payment {} is in different currency ({}) than bank account {} ({}).'.format(
                self.identifier, self.amount.currency.code, self.account, self.account.currency
            ))
        super().clean()

    @property
    def advance_invoice(self):
        """Return advance invoice if it exists."""
        invoices = self.invoices.filter(invoice_type=InvoiceType.ADVANCE)
        return invoices.first()

    @property
    def objective(self):
        """Return processed payment objective."""
        if self.processor:
            return get_processor_objective(self.processor)
        else:
            return ''
    objective.fget.short_description = _('Objective')  # type: ignore

    @classmethod
    def objective_choices(self):
        """Return payment processor default objectives choices."""
        choices = BLANK_CHOICE_DASH.copy()
        for proc_name in SETTINGS.processors:
            proc = get_processor_instance(proc_name)
            choices.append((proc_name, proc.default_objective))
        return choices
