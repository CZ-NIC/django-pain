"""Admin interface for django_pain."""
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from django_pain.constants import PaymentState
from django_pain.models import Invoice
from django_pain.processors import get_processor_instance

from .filters import PaymentStateListFilter
from .forms import BankAccountForm, BankPaymentForm


class BankAccountAdmin(admin.ModelAdmin):
    """Model admin for BankAccount."""

    form = BankAccountForm


class InvoicesInline(admin.TabularInline):
    """Inline model admin for invoices related to payment."""

    model = Invoice.payments.through

    can_delete = False

    fields = ('invoice_link', 'invoice_type')
    readonly_fields = ('invoice_link', 'invoice_type')
    extra = 0

    verbose_name = _('Invoice related to payment')
    verbose_name_plural = _('Invoices related to payment')

    def invoice_link(self, obj):
        """Return invoice link."""
        processor = get_processor_instance(obj.bankpayment.processor)
        if hasattr(processor, 'get_invoice_url'):
            return mark_safe('<a href="{}">{}</a>'.format(processor.get_invoice_url(obj.invoice), obj.invoice.number))
        else:
            return obj.invoice.number
    invoice_link.short_description = _('Invoice number')  # type: ignore

    def invoice_type(self, obj):
        """Return invoice type."""
        return obj.invoice.invoice_type
    invoice_type.short_description = _('Invoice type')  # type: ignore

    def has_add_permission(self, request, obj=None):
        """Read only access."""
        return False


class BankPaymentAdmin(admin.ModelAdmin):
    """Model admin for BankPayment."""

    form = BankPaymentForm

    list_display = (
        'identifier', 'counter_account_number', 'variable_symbol', 'amount', 'transaction_date',
        'client_link', 'description', 'invoice_link', 'counter_account_name', 'account', 'state_styled'
    )

    list_filter = (
        ('state', PaymentStateListFilter), 'account__account_name', 'transaction_date',
    )

    readonly_fields = (
        'identifier', 'account', 'create_time', 'transaction_date',
        'counter_account_number', 'counter_account_name', 'amount', 'description', 'state',
        'constant_symbol', 'variable_symbol', 'specific_symbol', 'objective', 'client_link',
    )

    search_fields = ('variable_symbol', 'counter_account_name', 'description',)

    ordering = ('-transaction_date', '-create_time')

    inlines = (
        InvoicesInline,
    )

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
                        'counter_account_number', 'objective', 'client_link',
                        'transaction_date', 'constant_symbol', 'variable_symbol', 'specific_symbol', 'amount',
                        'description', 'counter_account_name', 'create_time', 'account', 'state')
                }),
            ]

    def state_styled(self, obj):
        """
        Payment state enclosed in div with appropriate css class.

        This is used for assigning different colors to payment rows based on payment state.
        """
        return mark_safe('<div class="state_{}">{}</div>'.format(PaymentState(obj.state).value, obj.state_description))
    state_styled.short_description = _('Payment state')  # type: ignore

    def invoice_link(self, obj):
        """Invoice link."""
        invoice = obj.advance_invoice
        invoices_count = obj.invoices.count()
        if invoice is not None:
            processor = get_processor_instance(obj.processor)
            if hasattr(processor, 'get_invoice_url'):
                link = '<a href="{}">{}</a>'.format(processor.get_invoice_url(invoice), invoice.number)
            else:
                link = invoice.number

            if invoices_count > 1:
                link += '&nbsp;(+{})'.format(invoices_count - 1)

            return mark_safe(link)
        else:
            if invoices_count > 0:
                return '(+{})'.format(invoices_count)
            else:
                return ''
    invoice_link.short_description = _('Invoice')  # type: ignore

    def client_link(self, obj):
        """Client link."""
        client = getattr(obj, 'client', None)
        if client is not None:
            processor = get_processor_instance(obj.processor)
            if hasattr(processor, 'get_client_url'):
                return mark_safe('<a href="{}">{}</a>'.format(processor.get_client_url(client), client.handle))
            else:
                return client.handle
        else:
            return ''
    client_link.short_description = _('Client ID')  # type: ignore

    def has_add_permission(self, request):
        """Forbid adding new payments through admin interface."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Forbid deleting payments through admin interface."""
        return False
