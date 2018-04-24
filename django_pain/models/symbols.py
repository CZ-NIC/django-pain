"""Payment symbols."""
from django.db import models
from django.utils.translation import gettext_lazy as _

from .bank import BankPayment


class PaymentSymbols(models.Model):
    """Payment symbols (specific for Czech Republic and Slovak Republic)."""

    payment = models.OneToOneField(BankPayment, on_delete=models.CASCADE, related_name='symbols')

    constant_symbol = models.CharField(max_length=10, blank=True, verbose_name=_('Constant symbol'))
    variable_symbol = models.CharField(max_length=10, blank=True, verbose_name=_('Variable symbol'))
    specific_symbol = models.CharField(max_length=10, blank=True, verbose_name=_('Specific symbol'))
