"""Payment views."""
from django.views.generic import ListView

from .models import BankPayment


class PaymentListView(ListView):
    """Payment list view."""

    template_name = 'django_pain/payments_list.html'
    model = BankPayment
    context_object_name = 'payments'
