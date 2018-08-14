"""Django admin forms."""
from django import forms
from django.utils.translation import gettext as _
from djmoney.settings import CURRENCY_CHOICES

from django_pain.constants import PaymentState
from django_pain.models import BankAccount, BankPayment
from django_pain.processors import get_processor_instance


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

    processor = forms.ChoiceField(choices=BankPayment.objective_choices, required=False)
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
                cleaned_data['objective'] = result.objective
                return cleaned_data
            else:
                raise forms.ValidationError(_('Unable to assign payment'), code='unable_to_assign')

    def save(self, commit=True):
        """Manually assign payment objective and save payment."""
        if 'state' in self.cleaned_data:
            self.instance.state = self.cleaned_data['state']
            self.instance.objective = self.cleaned_data['objective']
        return super().save(commit=commit)

    class Meta:
        """Meta class."""

        fields = '__all__'
        model = BankPayment
