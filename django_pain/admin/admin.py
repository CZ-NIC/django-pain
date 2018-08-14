"""Admin interface for django_pain."""
from django.contrib import admin
from django.utils.safestring import mark_safe
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
        'identifier', 'counter_account_number', 'variable_symbol', 'amount', 'transaction_date',
        'description', 'counter_account_name', 'account', 'state_styled'
    )

    list_filter = (
        ('state', PaymentStateListFilter), 'account__account_name', 'transaction_date',
    )

    readonly_fields = (
        'identifier', 'account', 'create_time', 'transaction_date',
        'counter_account_number', 'counter_account_name', 'amount', 'description', 'state',
        'constant_symbol', 'variable_symbol', 'specific_symbol', 'objective',
    )

    ordering = ('-transaction_date', '-create_time')

    class Media:
        """Media class."""

        js = ('django_pain/js/state_colors.js',)
        css = {
            'all': ('django_pain/css/admin.css',),
        }

    def get_fieldsets(self, request, obj=None):
        """
        Return form fieldsets.

        For imported or deferred payment, display form fields to manually assign
        payment. Otherwise, display payment objective.
        """
        if obj is not None and obj.state in (PaymentState.IMPORTED, PaymentState.DEFERRED):
            return [
                (None, {
                    'fields': (
                        'counter_account_number',
                        'transaction_date', 'constant_symbol', 'variable_symbol', 'specific_symbol', 'amount',
                        'description', 'counter_account_name', 'create_time', 'account', 'state')
                }),
                (_('Assign payment'), {
                    'fields': ('processor', 'client_id')
                }),
            ]
        else:
            return [
                (None, {
                    'fields': (
                        'counter_account_number', 'objective',
                        'transaction_date', 'constant_symbol', 'variable_symbol', 'specific_symbol', 'amount',
                        'description', 'counter_account_name', 'create_time', 'account', 'state')
                }),
            ]

    def state_styled(self, obj):
        """
        Payment state enclosed in div with appropriate css class.

        This is used for assigning different colors to payment rows based on payment state.
        """
        return mark_safe('<div class="state_%s">%s</div>' % (
                         PaymentState(obj.state).value, obj.state_description))
    state_styled.short_description = _('Payment state')  # type: ignore

    def has_add_permission(self, request):
        """Forbid adding new payments through admin interface."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Forbid deleting payments through admin interface."""
        return False
