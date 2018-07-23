"""Django admin."""
from django.contrib.admin import site

from django_pain.models import BankAccount, BankPayment

from .admin import BankAccountAdmin, BankPaymentAdmin

__all__ = ['BankAccountAdmin', 'BankPaymentAdmin']

site.register(BankAccount, BankAccountAdmin)
site.register(BankPayment, BankPaymentAdmin)
