"""Payments and invoices models."""
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import BLANK_CHOICE_DASH
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import CurrencyField, MoneyField

from django_pain.constants import CURRENCY_PRECISION, PaymentState
from django_pain.settings import SETTINGS
from django_pain.utils import full_class_name

PAYMENT_STATE_CHOICES = (
    (PaymentState.IMPORTED, _('imported')),
    (PaymentState.PROCESSED, _('processed')),
    (PaymentState.DEFERRED, _('not identified')),
    (PaymentState.EXPORTED, _('exported')),
)


class BankAccount(models.Model):
    """Bank account."""

    account_number = models.TextField(verbose_name=_('Account number'))
    account_name = models.TextField(blank=True, verbose_name=_('Account name'))
    currency = CurrencyField()

    class Meta:
        """Meta class."""

        verbose_name = _('Bank account')
        verbose_name_plural = _('Bank accounts')

    def __str__(self):
        """Return string representation of bank account."""
        return '%s %s' % (self.account_name, self.account_number)


class BankPayment(models.Model):
    """Bank payment."""

    identifier = models.TextField(verbose_name=_('Payment ID'))
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, verbose_name=_('Destination account'))
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=_('Create time'))
    transaction_date = models.DateField(verbose_name=_('Transaction date'))

    counter_account_number = models.TextField(verbose_name=_('Counter account number'))
    counter_account_name = models.TextField(blank=True, verbose_name=_('Counter account name'))

    amount = MoneyField(max_digits=64, decimal_places=CURRENCY_PRECISION, verbose_name=_('Amount'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    state = models.TextField(choices=PAYMENT_STATE_CHOICES, default=PaymentState.IMPORTED,
                             verbose_name=_('Payment state'))

    # Payment symbols (specific for Czech Republic and Slovak Republic).
    constant_symbol = models.CharField(max_length=10, blank=True, verbose_name=_('Constant symbol'))
    variable_symbol = models.CharField(max_length=10, blank=True, verbose_name=_('Variable symbol'))
    specific_symbol = models.CharField(max_length=10, blank=True, verbose_name=_('Specific symbol'))

    processor = models.TextField(verbose_name=_('Processor'), blank=True)
    # client_id = models.TextField(verbose_name=_('Client ID'), blank=True)
    objective = models.TextField(verbose_name=_('Objective'), blank=True)

    class Meta:
        """Model Meta class."""

        unique_together = ('identifier', 'account')
        verbose_name = _('Bank payment')
        verbose_name_plural = _('Bank payments')

    def __str__(self):
        """Return string representation of bank payment."""
        return self.identifier

    def clean(self):
        """Check whether payment currency is the same as currency of related bank account."""
        if self.account.currency != self.amount.currency.code:
            raise ValidationError('Bank payment {} is in different currency ({}) than bank account {} ({}).'.format(
                self.identifier, self.amount.currency.code, self.account.account_number, self.account.currency
            ))
        super().clean()

    @property
    def state_description(self):
        """Return verbose localized string with state description."""
        return dict(PAYMENT_STATE_CHOICES)[self.state]

    @classmethod
    def objective_choices(self):
        """Return payment processor default objectives choices."""
        choices = BLANK_CHOICE_DASH.copy()
        for proc_class in SETTINGS.processors:
            proc = proc_class()
            choices.append((full_class_name(proc_class), proc.default_objective))
        return choices
