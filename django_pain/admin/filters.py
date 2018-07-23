"""Admin filters."""
from django.contrib.admin import ChoicesFieldListFilter
from django.utils.translation import gettext as _

from django_pain.constants import PaymentState
from django_pain.models import PAYMENT_STATE_CHOICES


class PaymentStateListFilter(ChoicesFieldListFilter):
    """Custom filter for payment state."""

    def choices(self, cl):
        """Return modified enum choices."""
        yield {
            'selected': self.lookup_val is None,
            'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
            'display': _('All'),
        }
        for enum_value in PaymentState:
            str_value = enum_value.value
            yield {
                'selected': (str_value == self.lookup_val),
                'query_string': cl.get_query_string({self.lookup_kwarg: str_value}),
                'display': dict(PAYMENT_STATE_CHOICES).get(enum_value),
            }
