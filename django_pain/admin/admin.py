"""Admin interface for django_pain."""
from django.contrib import admin
from django.utils.translation import gettext as _

from django_pain.constants import PaymentState

from .filters import PaymentStateListFilter
from .forms import BankAccountForm, BankPaymentForm


class BankAccountAdmin(admin.ModelAdmin):
    """Model admin for BankAccount."""

    form = BankAccountForm


class BankPaymentAdmin(admin.ModelAdmin):
    """Model admin for BankPayment."""

    form = BankPaymentForm
    list_display = (
        'identifier', 'transaction_date', 'account_name', 'counter_account_name',
        'amount', 'variable_symbol', 'state'
    )
    list_filter = (
        ('state', PaymentStateListFilter), 'account__account_name', 'transaction_date',
    )

    readonly_fields = (
        'identifier', 'account', 'create_time', 'transaction_date',
        'counter_account_number', 'counter_account_name', 'amount', 'description', 'state',
        'constant_symbol', 'variable_symbol', 'specific_symbol', 'objective',
    )

    def get_fieldsets(self, request, obj=None):
        """
        Return form fieldsets.

        For imported or deferred payment, display form fields to manually assign
        payment. Otherwise, display payment objective.
        """
        fieldsets = [
            (None, {
                'fields': ('identifier', 'account', 'create_time', 'transaction_date',
                           'counter_account_number', 'counter_account_name', 'amount', 'description', 'state',
                           'constant_symbol', 'variable_symbol', 'specific_symbol',)
            }),
        ]
        if obj is not None and obj.state in (PaymentState.IMPORTED, PaymentState.DEFERRED):
            fieldsets.append((_('Assign payment'), {'fields': ('processor', 'client_id')}),)  # type: ignore
        else:
            fieldsets.append((_('Assign payment'), {'fields': ('objective',)}),)  # type: ignore
        return fieldsets

    @staticmethod
    def account_name(obj):
        """Return related account name."""
        return obj.account.account_name
    account_name.short_description = _('Account name')  # type: ignore
