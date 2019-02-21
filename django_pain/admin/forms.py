"""Django admin forms."""
from django import forms
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.utils.translation import gettext_lazy as _
from djmoney.settings import CURRENCY_CHOICES

from django_pain.constants import PaymentState
from django_pain.models import BankAccount, BankPayment
from django_pain.settings import get_processor_instance


class BankAccountForm(forms.ModelForm):
    """Admin form for BankAccount model."""

    class Meta:
        """Meta class."""

        fields = '__all__'
        model = BankAccount
        widgets = {
            'account_number': forms.TextInput(),
            'account_name': forms.TextInput(),
            'currency': forms.Select(choices=CURRENCY_CHOICES),
        }


class BankPaymentForm(forms.ModelForm):
    """Admin form for BankPayment model."""

    processor = forms.ChoiceField(choices=(), required=False)
    client_id = forms.CharField(label=_('Client ID'), required=False)

    def __init__(self, *args, **kwargs):
        """Initialize form and disable most of the fields."""
        super().__init__(*args, **kwargs)
        for key, value in self.fields.items():
            if key not in ('processor', 'client_id'):
                value.disabled = True

    def clean(self):
        """
        Check whether payment processor has been set.

        If so, assign payment to chosen payment processor and note the result.
        """
        cleaned_data = super().clean()
        if cleaned_data.get('processor', None):
            # The only valid choices are those from PAIN_PROCESSORS settings.
            # Those are already validated during startup.
            processor = get_processor_instance(cleaned_data['processor'])
            result = processor.assign_payment(self.instance, cleaned_data['client_id'])
            if result.result:
                cleaned_data['state'] = PaymentState.PROCESSED
                return cleaned_data
            else:
                raise forms.ValidationError(_('Unable to assign payment'), code='unable_to_assign')

    def save(self, commit=True):
        """Manually assign payment objective and save payment."""
        if 'state' in self.cleaned_data:
            self.instance.state = self.cleaned_data['state']
        return super().save(commit=commit)

    class Meta:
        """Meta class."""

        fields = '__all__'
        model = BankPayment

    class Media:
        """Media class."""

        js = (
            # The ordering is important!
            # First, jQuery introduces django.jQuery global.
            # Then, processor_client_field exposes jQuery global as alias for django.jQuery.
            # At last, Select2 is loaded, which needs jQuery global to run correctly.
            'admin/js/vendor/jquery/jquery.js',
            'django_pain/js/processor_client_field.js',
            'admin/js/vendor/select2/select2.full.min.js',
            'django_pain/js/edit_confirmation.js',
        )
        css = {
           'all': ('admin/css/vendor/select2/select2.min.css',)
        }


class UserCreationForm(DjangoUserCreationForm):
    """User creation form without mandatory password."""

    def __init__(self, *args, **kwargs):
        """Don't require password fields."""
        super().__init__(*args, **kwargs)
        self.fields['password1'].required = False
        self.fields['password2'].required = False

    def clean_password2(self):
        """Check whether both password fields are filled in or none of them is."""
        password1 = self.cleaned_data.get('password1')
        password2 = super().clean_password2()
        if bool(password1) ^ bool(password2):
            raise forms.ValidationError(_('Fill out both fields'))
        return password2
