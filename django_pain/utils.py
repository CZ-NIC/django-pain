#
# Copyright (C) 2018-2021  CZ.NIC, z. s. p. o.
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

"""Various utils."""
from datetime import date, datetime
from enum import Enum

from django.utils.dateparse import parse_date, parse_datetime


# TODO: Replace by models.TextChoices once we drop support for Django 2.2
class StrEnum(str, Enum):
    """String Enum with overridden __str__ method to prevent errors caused by using Enum in forms."""

    # inspired by
    # https://github.com/django/django/blob/ca9872905559026af82000e46cde6f7dedc897b6/django/db/models/enums.py#L71
    def __str__(self):
        return str(self.value)


def full_class_name(cls):
    """Return full class name includeing the module path."""
    return "{}.{}".format(cls.__module__, cls.__qualname__)


def parse_date_safe(value: str) -> date:
    """Parse date using Django utils, but raise an exception when unsuccessful."""
    result = parse_date(value)
    if result is None:
        raise ValueError('Could not parse date.')
    return result


def parse_datetime_safe(value: str) -> datetime:
    """Parse date_time using Django utils, but raise an exception when unsuccessful."""
    result = parse_datetime(value)
    if result is None:
        raise ValueError('Could not parse date_time.')
    return result
