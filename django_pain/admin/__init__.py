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

"""Django admin."""
from django.contrib.admin import site
from django.contrib.auth.models import User

from django_pain.models import BankAccount, BankPayment

from .admin import BankAccountAdmin, BankPaymentAdmin, UserAdmin

__all__ = ['BankAccountAdmin', 'BankPaymentAdmin', 'UserAdmin']

site.register(BankAccount, BankAccountAdmin)
site.register(BankPayment, BankPaymentAdmin)
site.unregister(User)
site.register(User, UserAdmin)
