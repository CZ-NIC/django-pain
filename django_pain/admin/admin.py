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

"""Admin interface for django_pain."""
from calendar import monthrange
from copy import deepcopy
from datetime import date

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.templatetags.static import static
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import get_language, gettext_lazy as _, to_locale
from moneyed.localization import format_money

from django_pain.constants import PaymentState
from django_pain.models import BankPayment, Invoice
from django_pain.settings import get_processor_instance

from .filters import PaymentStateListFilter
from .forms import BankAccountForm, BankPaymentForm, UserCreationForm


class BankAccountAdmin(admin.ModelAdmin):
    """Model admin for BankAccount."""

    form = BankAccountForm

    def get_readonly_fields(self, request, obj):
        """Currency field should be editable only when creating new bank account."""
        if obj is None:
            return ()
        else:
            return ('currency',)


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
            return format_html('<a href="{}">{}</a>', processor.get_invoice_url(obj.invoice), obj.invoice.number)
        else:
            return obj.invoice.number
    invoice_link.short_description = _('Invoice number')  # type: ignore

    def invoice_type(self, obj):
        """Return invoice type."""
        return obj.invoice.get_invoice_type_display()
    invoice_type.short_description = _('Invoice type')  # type: ignore

    def has_add_permission(self, request, obj=None):
        """Read only access."""
        return False


class BankPaymentAdmin(admin.ModelAdmin):
    """Model admin for BankPayment."""

    form = BankPaymentForm

    list_display = (
        'detail_link', 'counter_account_number', 'variable_symbol', 'unbreakable_amount', 'short_transaction_date',
        'client_link', 'description', 'advance_invoice_link', 'counter_account_name', 'account'
    )

    list_filter = (
        ('state', PaymentStateListFilter), 'account__account_name', 'transaction_date',
    )

    readonly_fields = (
        'identifier', 'account', 'create_time', 'transaction_date',
        'counter_account_number', 'counter_account_name', 'unbreakable_amount', 'description', 'state',
        'constant_symbol', 'variable_symbol', 'specific_symbol', 'objective', 'client_link',
        'processing_error',
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

    def get_form(self, request, obj=None, **kwargs):
        """Filter allowed processors for manual assignment of payments."""
        form = super().get_form(request, obj, **kwargs)
        allowed_choices = []
        for processor, label in BankPayment.objective_choices():
            if not processor or request.user.has_perm('django_pain.can_manually_assign_to_{}'.format(processor)):
                allowed_choices.append((processor, label))

        processor_field = deepcopy(form.base_fields['processor'])
        processor_field.choices = allowed_choices
        form.base_fields['processor'] = processor_field

        if obj is not None:
            initial_tax_date = self._get_initial_tax_date(obj.transaction_date)
            if initial_tax_date is not None:
                tax_date_field = deepcopy(form.base_fields['tax_date'])
                tax_date_field.initial = initial_tax_date
                form.base_fields['tax_date'] = tax_date_field

        return form

    @staticmethod
    def _get_initial_tax_date(payment_date):
        """
        Get initial tax date.

        Tax date needs to be in the same month as payment date.
        Tax date can set at most 15 days into the past.
        """
        today = date.today()
        if payment_date > today:
            # payment_date is from the future
            # manual correction needed
            return None
        elif (today - payment_date).days <= 15:
            # payment_date is recent, use it as a tax date
            return payment_date
        elif (today.year*12 + today.month) - (payment_date.year*12 + payment_date.month) > 1:
            # payment_date is too old (not from the current or previous month)
            # manual correction needed
            return None
        elif today.month == payment_date.month:
            # payment_date is from the current month (but not within last 15 days)
            # use current date
            return today
        elif today.day > 15:
            # payment_date is from the last month and has been identified after 15th day of the current month
            # manual correction needed
            return None
        else:
            # payment_date is from the last month (and has been identified before 15th day of the current month)
            # return the last day of the last month
            return date(payment_date.year, payment_date.month, monthrange(payment_date.year, payment_date.month)[1])

    def get_fieldsets(self, request, obj=None):
        """
        Return form fieldsets.

        For imported or deferred payment, display form fields to manually assign
        payment. Otherwise, display payment objective.
        """
        if obj is not None and obj.processing_error:
            state = ('state', 'processing_error')  # type: ignore
        else:
            state = 'state'  # type: ignore

        if obj is not None and obj.state in (PaymentState.READY_TO_PROCESS, PaymentState.DEFERRED):
            return [
                (None, {
                    'fields': (
                        'counter_account_number',
                        'transaction_date', 'constant_symbol', 'variable_symbol', 'specific_symbol',
                        'unbreakable_amount', 'description', 'counter_account_name', 'create_time', 'account', state,
                    )
                }),
                (_('Assign payment'), {
                    'fields': ('processor', 'client_id', 'tax_date')
                }),
            ]
        else:
            return [
                (None, {
                    'fields': (
                        'counter_account_number', 'objective', 'client_link',
                        'transaction_date', 'constant_symbol', 'variable_symbol', 'specific_symbol',
                        'unbreakable_amount', 'description', 'counter_account_name', 'create_time', 'account', state,
                    )
                }),
            ]

    def detail_link(self, obj):
        """Object detail link."""
        return format_html('<div class="state_{}"></div><a href="{}"><img src="{}" class="open-detail-icon" /></a>',
                           PaymentState(obj.state).value,
                           reverse('admin:django_pain_bankpayment_change', args=[obj.pk]),
                           static('django_pain/images/folder-open.svg'))
    detail_link.short_description = ''  # type: ignore

    def unbreakable_amount(self, obj):
        """Correctly formatted amount with unbreakable spaces."""
        locale = to_locale(get_language())
        amount = format_money(obj.amount, locale=locale)
        return mark_safe(amount.replace(' ', '&nbsp;'))
    unbreakable_amount.short_description = _('Amount')  # type: ignore

    def short_transaction_date(self, obj):
        """Short transaction date."""
        return date_format(obj.transaction_date, format='SHORT_DATE_FORMAT')
    short_transaction_date.short_description = _('Date')  # type: ignore

    def advance_invoice_link(self, obj):
        """
        Display advance invoice link.

        If there are any other invoices, number of remaining (not displayed)
        invoices is displayed as well.
        """
        advance_invoice = obj.advance_invoice
        invoices_count = obj.invoices.count()
        if advance_invoice is not None:
            processor = get_processor_instance(obj.processor)
            if hasattr(processor, 'get_invoice_url'):
                link = format_html('<a href="{}">{}</a>',
                                   processor.get_invoice_url(advance_invoice), advance_invoice.number)
            else:
                link = advance_invoice.number

            if invoices_count > 1:
                link = format_html('{}&nbsp;(+{})', link, invoices_count - 1)

            return link
        else:
            if invoices_count > 0:
                return '(+{})'.format(invoices_count)
            else:
                return ''
    advance_invoice_link.short_description = _('Invoice')  # type: ignore

    def client_link(self, obj):
        """Client link."""
        client = getattr(obj, 'client', None)
        if client is not None:
            processor = get_processor_instance(obj.processor)
            if hasattr(processor, 'get_client_url'):
                return format_html('<a href="{}">{}</a>', processor.get_client_url(client), client.handle)
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


class UserAdmin(DjangoUserAdmin):
    """Model admin for Django user."""

    add_form = UserCreationForm

    add_fieldsets = (
        (None, {
            'fields': ('username',),
        }),
        (_('Password'), {
            'description': _("If you use external authentication system such as LDAP, "
                             "you don't have to choose a password."),
            'fields': ('password1', 'password2',),
        }),
    )

    def save_model(self, request, obj, form, change):
        """If password isn't provided, set unusable password."""
        if not change and (not form.cleaned_data['password1'] or not obj.has_usable_password()):
            obj.set_unusable_password()
        super().save_model(request, obj, form, change)
