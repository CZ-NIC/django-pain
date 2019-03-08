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

"""Client related models."""
from django.db import models
from django.utils.translation import gettext_lazy as _

from .bank import BankPayment


class Client(models.Model):
    """
    Client model.

    Fields:
        handle      short text representation of client
        remote_id   id in an external system
        payment     link to appropriate payment
    """

    handle = models.TextField(verbose_name=_('Client ID'))
    remote_id = models.IntegerField()
    payment = models.OneToOneField(BankPayment, on_delete=models.CASCADE, related_name='client')
