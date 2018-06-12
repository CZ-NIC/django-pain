"""Payments and invoices models."""
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import CurrencyField, MoneyField

from django_pain.constants import CURRENCY_PRECISION, PaymentState

PAYMENT_STATE_CHOICES = (
    (PaymentState.IMPORTED, _('imported')),
    (PaymentState.PROCESSED, _('processed')),
    (PaymentState.DEFERRED, _('deferred')),
    (PaymentState.EXPORTED, _('exported')),
)


class BankAccount(models.Model):
    """Bank account."""

    account_number = models.TextField(verbose_name=_('Account number'))
    account_name = models.TextField(blank=True, verbose_name=_('Account name'))
    currency = CurrencyField()


class BankPayment(models.Model):
    """Bank payment."""

    identifier = models.TextField(verbose_name=_('Payment ID'))
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
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

    class Meta:
        """Model Meta class."""

        unique_together = ('identifier', 'account')

    def clean(self):
        """Check whether payment currency is the same as currency of related bank account."""
        if self.account.currency != self.amount.currency.code:
            raise ValidationError('Bank payment {} is in different currency ({}) than bank account {} ({}).'.format(
                self.identifier, self.amount.currency.code, self.account.account_number, self.account.currency
            ))
        super().clean()
