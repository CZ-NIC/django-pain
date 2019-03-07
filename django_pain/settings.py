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

"""django_pain settings."""
from functools import lru_cache

import appsettings
from django.utils import module_loading

from .utils import full_class_name


class ProcessorsSetting(appsettings.Setting):
    """Dictionary of names and dotted paths to classes setting."""

    def transform(self, value):
        """Import all classes from setting."""
        return dict((key, module_loading.import_string(value)) for (key, value) in value.items())

    def checker(self, name, value):
        """
        Check if properly configured.

        Value has to be dictionary with following properties:
          * all keys must be strings
          * all values must be subclasses of AbstractPaymentProcessor
        """
        if not isinstance(value, dict):
            raise ValueError('{} must be {}, not {}'.format(name, dict, value.__class__))
        if not all(isinstance(key, str) for key in value.keys()):
            raise ValueError('All keys of {} must be {}'.format(name, str))
        value = self.transform(value)

        from django_pain.processors import AbstractPaymentProcessor
        for name, cls in value.items():
            if not issubclass(cls, AbstractPaymentProcessor):
                raise ValueError('{} is not subclass of AbstractPaymentProcessor'.format(full_class_name(cls)))


class PainSettings(appsettings.AppSettings):
    """Application specific settings."""

    processors = ProcessorsSetting(required=True)
    process_payments_lock_file = appsettings.StringSetting(default='/tmp/pain_process_payments.lock')
    trim_varsym = appsettings.BooleanSetting(default=False)

    class Meta:
        """Meta class."""

        setting_prefix = 'pain_'


SETTINGS = PainSettings()


@lru_cache()
def get_processor_class(processor: str):
    """Get processor class."""
    cls = SETTINGS.processors.get(processor)
    if cls is None:
        raise ValueError("{} is not present in PAIN_PROCESSORS setting".format(processor))
    else:
        return cls


@lru_cache()
def get_processor_instance(processor: str):
    """Get processor class instance."""
    processor_class = get_processor_class(processor)
    return processor_class()


@lru_cache()
def get_processor_objective(processor: str):
    """Get processor objective."""
    proc = get_processor_instance(processor)
    return proc.default_objective
