"""Invoice related models."""
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_pain.constants import InvoiceType

from .bank import BankPayment

INVOICE_TYPE_CHOICES = (
    (InvoiceType.ADVANCE, _('advance')),
    (InvoiceType.ACCOUNT, _('account')),
)


class Invoice(models.Model):
    """Invoice model."""

    number = models.TextField(unique=True, verbose_name=_('Invoice number'))
    remote_id = models.IntegerField()
    invoice_type = models.TextField(choices=INVOICE_TYPE_CHOICES, verbose_name=_('Invoice type'))
    payments = models.ManyToManyField(BankPayment, related_name='invoices')
