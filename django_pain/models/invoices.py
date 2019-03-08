#
# Copyright (C) 2018-2019  CZ.NIC, z. s. p. o.
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

"""Invoice related models."""
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_pain.constants import InvoiceType

from .bank import BankPayment

INVOICE_TYPE_CHOICES = (
    (InvoiceType.ADVANCE, _('advance')),
    (InvoiceType.ACCOUNT, _('account')),
)


class Invoice(models.Model):
    """Invoice model."""

    number = models.TextField(unique=True, verbose_name=_('Invoice number'))
    remote_id = models.IntegerField()
    invoice_type = models.TextField(choices=INVOICE_TYPE_CHOICES, verbose_name=_('Invoice type'))
    payments = models.ManyToManyField(BankPayment, related_name='invoices')
