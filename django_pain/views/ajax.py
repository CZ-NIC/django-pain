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

"""AJAX helper views."""
from django.http import Http404, JsonResponse

from django_pain.settings import SETTINGS, get_processor_instance


def load_processor_client_choices(request):
    """Load client choices from the appropriate payment processor."""
    try:
        processor = get_processor_instance(request.GET.get('processor', ''))
    except ValueError:
        raise Http404

    if hasattr(processor, 'get_client_choices'):
        return JsonResponse(processor.get_client_choices())
    else:
        raise Http404


def get_processors_options(request):
    """
    Get following processors options.

      * manual_tax_date
    """
    options = {}  # type: dict
    for proc_name in SETTINGS.processors:
        options[proc_name] = {}
        proc = get_processor_instance(proc_name)
        options[proc_name]['manual_tax_date'] = proc.manual_tax_date
    return JsonResponse(options)
