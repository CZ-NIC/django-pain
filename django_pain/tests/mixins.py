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

"""Test mixins."""
from django_pain.processors.ignore import _get_ignore_processor_name
from django_pain.settings import get_processor_class, get_processor_instance, get_processor_objective


class CacheResetMixin(object):
    """Mixin for resetting caches."""

    def setUp(self):
        """Reset functions decorated with lru_cache."""
        super().setUp()  # type: ignore
        get_processor_class.cache_clear()
        get_processor_instance.cache_clear()
        get_processor_objective.cache_clear()
        _get_ignore_processor_name.cache_clear()
