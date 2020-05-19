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

"""django_pain settings."""
from functools import lru_cache

import appsettings
from django.utils import module_loading

from .utils import full_class_name


class NamedClassSetting(appsettings.Setting):
    """Dictionary of names and dotted paths to classes setting. Class is checked to be specified type."""

    def __init__(self, checked_class_str, *args, **kwargs):
        self.checked_class_str = checked_class_str
        super().__init__(*args, **kwargs)

    def transform(self, value):
        """Import all classes from setting."""
        return dict((key, module_loading.import_string(value)) for (key, value) in value.items())

    def checker(self, name, value):
        """
        Check if properly configured.

        Value has to be dictionary with following properties:
          * all keys must be strings
          * all values must be subclasses of class specified in checked_class_str
        """
        if not isinstance(value, dict):
            raise ValueError('{} must be {}, not {}'.format(name, dict, value.__class__))
        if not all(isinstance(key, str) for key in value.keys()):
            raise ValueError('All keys of {} must be {}'.format(name, str))
        value = self.transform(value)

        checked_class = module_loading.import_string(self.checked_class_str)
        for name, cls in value.items():
            if not issubclass(cls, checked_class):
                raise ValueError('{} is not subclass of {}'.format(full_class_name(cls), checked_class.__name__))


class CallableListSetting(appsettings.ListSetting):
    """
    Callable list setting.

    Contains list of dotted paths refering to callables.
    """

    def __init__(self, *args, **kwargs):
        """Ensure that list items are strings."""
        kwargs['item_type'] = str
        super().__init__(*args, **kwargs)

    def transform(self, value):
        """Translate dotted path to callable."""
        return [module_loading.import_string(call) for call in value]

    def checker(self, name, value):
        """Check whether dotted path refers to callable."""
        transformed_value = self.transform(value)
        for call in transformed_value:
            if not callable(call):
                raise ValueError('{} must be a list of dotted paths to callables'.format(name))


class PainSettings(appsettings.AppSettings):
    """
    Application specific settings.

    Attributes:
        processors: Dictionary of names and dotted paths to processor classes setting.
        process_payments_lock_file: Location of process_payments command lock file.
        trim_varsym: Whether variable symbol should be trimmed of leading zeros.
        import_callbacks: List of dotted paths to callables that takes BankPayment object as
            their argument and return (possibly) changed BankPayment.

            These callables are called right before the payment is saved during the import.
            Especially, these callable can raise ValidationError in order to avoid
            saving payment to the database.
    """

    processors = NamedClassSetting('django_pain.processors.AbstractPaymentProcessor', required=True)
    card_payment_handlers = NamedClassSetting('django_pain.card_payment_handlers.AbstractCardPaymentHandler')
    process_payments_lock_file = appsettings.StringSetting(default='/tmp/pain_process_payments.lock')
    trim_varsym = appsettings.BooleanSetting(default=False)
    import_callbacks = CallableListSetting()

    csob_card_api_url = appsettings.StringSetting()
    csob_card_api_public_key = appsettings.StringSetting()
    csob_card_merchant_id = appsettings.StringSetting()
    csob_card_merchant_private_key = appsettings.StringSetting()
    csob_card_account_name = appsettings.StringSetting()

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


@lru_cache()
def get_card_payment_handler_class(card_payment_handler: str):
    """Get CardPayemntHandler class."""
    cls = SETTINGS.card_payment_handlers.get(card_payment_handler)
    if cls is None:
        raise ValueError("{} is not present in PAIN_CARD_PAYMENT_HANDLERS setting".format(card_payment_handler))
    else:
        return cls


@lru_cache()
def get_card_payment_handler_instance(card_payment_handler: str):
    """Get card_payment_handler class instance."""
    card_payment_handler_class = get_card_payment_handler_class(card_payment_handler)
    return card_payment_handler_class(name=card_payment_handler)
