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
from collections import OrderedDict
from functools import lru_cache

import appsettings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils import module_loading
from teller.downloaders import BankStatementDownloader
from teller.parsers import BankStatementParser

from .utils import full_class_name


class NamedDictSetting(appsettings.DictSetting):
    """
    Dictionary of names and DictSetting. The Dictsetting is shared between the keys.

    The parameters are the same for each key but the values to which the marameters are set may be different.
    """

    def __init__(self, settings: dict, *args, **kwargs):
        super().__init__(*args, key_type=str, value_type=dict, **kwargs)
        self.settings = settings

    def transform(self, value):
        """Transform the values of each setting group."""
        transformed_value = OrderedDict()
        for key, group in value.items():
            transformed_group = dict()
            for k, v in group.items():
                setting = self.settings[k]
                transformed_group[k] = setting.transform(v)
            transformed_value[key] = transformed_group
        return transformed_value

    def validate(self, value):
        """Run custom validation on the setting value."""
        if not isinstance(value, dict):
            raise ValidationError('{} must be {}, not {}'.format(self.full_name, dict, value.__class__))
        super().validate(value)

    def check(self):
        """Validate the setting value including the subsettings."""
        super().check()

        # We can not use super().check() to validate subgroups so we do it manually.
        exceptions = []
        for name, group in self.raw_value.items():
            try:
                self._check_group(group)
            except ValidationError as error:
                exceptions.extend(error.messages)
        if exceptions:
            raise ImproperlyConfigured(
                "Setting {} is improperly configured.\n".format(self.full_name) + '\n'.join(exceptions))

    def _check_group(self, group):
        if sorted(group.keys()) != sorted(self.settings.keys()):
            raise ValidationError("Invalid keys.")

        for key, subsetting in self.settings.items():
            value = group[key]
            subsetting.validate(value)
            subsetting.run_validators(value)


class ClassPathValidator:
    """Validator which checks type of the imported value."""

    message = "%(value)s is not a subclass of %(type)s."

    def __init__(self, value_type, message=None):
        self.value_type = value_type
        if message:
            self.message = message

    def __call__(self, value):
        """Import value and validate its type."""
        actual_type = module_loading.import_string(value)
        if not issubclass(actual_type, self.value_type):
            params = {"value": value, "type": self.value_type.__name__}
            raise ValidationError(self.message, params=params)


class NamedClassSetting(appsettings.DictSetting):
    """Dictionary of names and dotted paths to classes setting. Class is checked to be specified type."""

    def __init__(self, checked_class_str, *args, **kwargs):
        self.checked_class_str = checked_class_str
        super().__init__(*args, **kwargs)

    def transform(self, value):
        """Transform value from dotted strings into module objects."""
        # Ordred dict and sorting is workaround for Python 3.5 (random test failing)
        return OrderedDict((key, module_loading.import_string(value)) for (key, value) in value.items())

    def validate(self, value):
        """
        Check if properly configured.

        Value has to be dictionary with following properties:
          * all keys must be strings
          * all values must be subclasses of class specified in checked_class_str
        """
        if not isinstance(value, dict):
            raise ValidationError('{} must be {}, not {}'.format(self.full_name, dict, value.__class__))
        if not all(isinstance(key, str) for key in value.keys()):
            raise ValidationError('All keys of {} must be {}'.format(self.full_name, str))
        value = self.transform(value)

        checked_class = module_loading.import_string(self.checked_class_str)
        for name, cls in value.items():
            if not issubclass(cls, checked_class):
                raise ValidationError('{} is not subclass of {}'.format(full_class_name(cls), checked_class.__name__))


class CallableListSetting(appsettings.ListSetting):
    """Contains list of dotted paths referring to callables."""

    def transform(self, value):
        """Translate dotted path to callable."""
        return [module_loading.import_string(call) for call in value]

    def validate(self, value):
        """Check whether dotted path refers to callable."""
        if not all(isinstance(val, str) for val in value):
            raise ValidationError('{} must be a list of dotted paths to callables'.format(self.full_name))

        transformed_value = self.transform(value)
        for call in transformed_value:
            if not callable(call):
                raise ValidationError('{} must be a list of dotted paths to callables'.format(self.full_name))


class PainSettings(appsettings.AppSettings):
    """Specific settings for django-pain app."""

    # Dictionary of names and dotted paths to processor classes setting.
    processors = NamedClassSetting('django_pain.processors.AbstractPaymentProcessor', required=True, key_type=str,
                                   value_type=str)

    # A card payment handler classes.
    card_payment_handlers = NamedClassSetting('django_pain.card_payment_handlers.AbstractCardPaymentHandler',
                                              key_type=str, value_type=str)

    # Location of process_payments command lock file.
    process_payments_lock_file = appsettings.StringSetting(default='/tmp/pain_process_payments.lock')

    # Whether variable symbol should be trimmed of leading zeros.
    trim_varsym = appsettings.BooleanSetting(default=False)

    # List of dotted paths to callables that takes BankPayment object as their argument and return (possibly) changed
    # BankPayment.
    #
    # These callables are called right before the payment is saved during the import. Especially, these callable can
    # raise ValidationError in order to avoid saving payment to the database.
    import_callbacks = CallableListSetting(item_type=str)

    downloaders = NamedDictSetting(
        dict(
            DOWNLOADER=appsettings.ObjectSetting(required=True,
                                                 validators=[ClassPathValidator(BankStatementDownloader)]),
            PARSER=appsettings.ObjectSetting(required=True,
                                             validators=[ClassPathValidator(BankStatementParser)]),
            DOWNLOADER_PARAMS=appsettings.DictSetting(required=True, key_type=str)
        )
    )

    # CSOB card settings
    csob_card = appsettings.NestedDictSetting(dict(
        api_url=appsettings.StringSetting(default='https://api.platebnibrana.csob.cz/api/v1.7/'),
        api_public_key=appsettings.FileSetting(required=True),
        merchant_id=appsettings.StringSetting(required=True),
        merchant_private_key=appsettings.FileSetting(required=True),
        account_name=appsettings.StringSetting(required=True),
    ), default=None)

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
    """Get CardPaymentHandler class."""
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
