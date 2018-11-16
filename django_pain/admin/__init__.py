"""Django admin."""
from django.contrib.admin import site
from django.contrib.auth.models import User

from django_pain.models import BankAccount, BankPayment

from .admin import BankAccountAdmin, BankPaymentAdmin, UserAdmin

__all__ = ['BankAccountAdmin', 'BankPaymentAdmin', 'UserAdmin']

site.register(BankAccount, BankAccountAdmin)
site.register(BankPayment, BankPaymentAdmin)
site.unregister(User)
site.register(User, UserAdmin)
