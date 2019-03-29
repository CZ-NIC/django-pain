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

"""django_pain url dispatcher."""
from django.urls import path

from django_pain.views import get_processors_options, load_processor_client_choices

app_name = 'pain'
urlpatterns = [
    path('ajax/processor_client_choices/', load_processor_client_choices, name='processor_client_choices'),
    path('ajax/get_processors_options/', get_processors_options, name='processor_options'),
]
