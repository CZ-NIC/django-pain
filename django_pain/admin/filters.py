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

"""Admin filters."""
from django.contrib.admin import ChoicesFieldListFilter
from django.contrib.admin.options import IncorrectLookupParameters
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from django_pain.constants import PaymentState
from django_pain.models import PAYMENT_STATE_CHOICES


class PaymentStateListFilter(ChoicesFieldListFilter):
    """Custom filter for payment state."""

    REALIZED_STATES = (PaymentState.READY_TO_PROCESS, PaymentState.DEFERRED, PaymentState.PROCESSED)

    def choices(self, cl):
        """Return modified enum choices."""
        yield {
            'selected': self.lookup_val is None,
            'query_string': cl.get_query_string(remove=self.expected_parameters()),
            'display': _('Realized'),
        }
        yield {
            'selected': self.lookup_val == 'all',
            'query_string': cl.get_query_string({self.lookup_kwarg: 'all'}, [self.lookup_kwarg]),
            'display': _('All'),
        }
        for enum_value in list(PaymentState):  # type: PaymentState
            str_value = enum_value.value
            yield {
                'selected': (str_value == self.lookup_val),
                'query_string': cl.get_query_string({self.lookup_kwarg: str_value}),
                'display': dict(PAYMENT_STATE_CHOICES)[enum_value],
            }

    def queryset(self, request, queryset):
        """Return filtered queryset."""
        if not self.used_parameters:
            return queryset.filter(state__in=self.REALIZED_STATES)
        elif self.used_parameters.get(self.lookup_kwarg) == 'all':
            return queryset

        try:
            return queryset.filter(**self.used_parameters)
        except (ValueError, ValidationError) as e:
            # Fields may raise a ValueError or ValidationError when converting
            # the parameters to the correct type.
            raise IncorrectLookupParameters(e)
