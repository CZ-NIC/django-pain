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

"""Test processor utils."""
from warnings import warn

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from django_pain.settings import (SETTINGS, get_card_payment_handler_class, get_card_payment_handler_instance,
                                  get_processor_class, get_processor_instance, get_processor_objective)

from .mixins import CacheResetMixin
from .utils import DummyCardPaymentHandler, DummyPaymentProcessor

try:
    from teller.downloaders import BankStatementDownloader
    from teller.parsers import BankStatementParser
except ImportError:
    warn('Failed to import teller library.')
    BankStatementDownloader = object  # type: ignore
    BankStatementParser = object  # type: ignore


class TestProcessorsSetting(SimpleTestCase):
    """Test ProcessorsSetting checker."""

    @override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
    def test_ok(self):
        """Test ok setting."""
        SETTINGS.check()
        self.assertEqual(SETTINGS.processors, {'dummy': DummyPaymentProcessor})

    @override_settings(PAIN_PROCESSORS=[])
    def test_not_dict(self):
        """Test not dictionary setting."""
        with self.assertRaisesRegex(ImproperlyConfigured, 'PAIN_PROCESSORS must be {}, not {}'.format(dict, list)):
            SETTINGS.check()

    @override_settings(PAIN_PROCESSORS={0: 1})
    def test_not_str_key(self):
        """Test dictionary with not str keys."""
        with self.assertRaisesRegex(ImproperlyConfigured, 'All keys of PAIN_PROCESSORS must be {}'.format(str)):
            SETTINGS.check()

    @override_settings(PAIN_PROCESSORS={'test_class': 'django_pain.tests.test_settings.TestProcessorsSetting'})
    def test_not_correct_subclass(self):
        """Test not subclass of AbstractPaymentProcessor."""
        with self.assertRaisesRegex(ImproperlyConfigured, '{} is not subclass of AbstractPaymentProcessor'.format(
                'django_pain.tests.test_settings.TestProcessorsSetting')):
            SETTINGS.check()


class DummyDownloader(BankStatementDownloader):
    """Dummy class which does not do anything. It is used in TestDownloadersSetting."""


class DummyParser(BankStatementParser):
    """Dummy class which does not do anything. It is used in TestDownloadersSetting."""


class TestDownloadersSetting(SimpleTestCase):
    """Test DownloadersSetting."""

    test_settings = {'DOWNLOADER': 'django_pain.tests.test_settings.DummyDownloader',
                     'PARSER': 'django_pain.tests.test_settings.DummyParser',
                     'DOWNLOADER_PARAMS': {'param_name': 'param_val'}}

    missing_key_settings = {'DOWNLOADER': 'django_pain.tests.test_settings.DummyDownloader',
                            'DOWNLOADER_PARAMS': {'param_name': 'param_val'}}

    invalid_sub_settings = {'DOWNLOADER': 'django_pain.tests.test_settings.DummyDownloader',
                            'PARSER': 'django_pain.tests.test_settings.DummyParser',
                            'DOWNLOADER_PARAMS': {1: 0}}

    invalid_downloader = {'DOWNLOADER': 'django_pain.tests.test_settings.DummyParser',
                          'PARSER': 'django_pain.tests.test_settings.DummyParser',
                          'DOWNLOADER_PARAMS': {'param_name': 'param_val'}}

    invalid_parser = {'DOWNLOADER': 'django_pain.tests.test_settings.DummyDownloader',
                      'PARSER': 'django_pain.tests.test_settings.DummyDownloader',
                      'DOWNLOADER_PARAMS': {'param_name': 'param_val'}}

    @override_settings(PAIN_DOWNLOADERS={'dummy': test_settings})
    def test_ok(self):
        """Test ok setting."""
        SETTINGS.check()
        expected = {'DOWNLOADER': DummyDownloader,
                    'PARSER': DummyParser,
                    'DOWNLOADER_PARAMS': {'param_name': 'param_val'}}
        self.assertEqual(SETTINGS.downloaders, {'dummy': expected})

    @override_settings(PAIN_DOWNLOADERS=[])
    def test_not_dict(self):
        """Test not dictionary setting."""
        with self.assertRaisesRegex(ImproperlyConfigured, 'PAIN_DOWNLOADERS must be {}, not {}'.format(dict, list)):
            SETTINGS.check()

    @override_settings(PAIN_DOWNLOADERS={0: {}})
    def test_not_str_key(self):
        """Test dictionary with not str keys."""
        expected = 'The key 0 is not of type str.'
        with self.assertRaisesRegex(ImproperlyConfigured, expected):
            SETTINGS.check()

    @override_settings(PAIN_DOWNLOADERS={'dummy': 1})
    def test_not_dict_value(self):
        """Test dictionary with not dict values."""
        expected = "Item dummy's value 1 is not of type dict."
        with self.assertRaisesRegex(ImproperlyConfigured, expected):
            SETTINGS.check()

    @override_settings(PAIN_DOWNLOADERS={'dummy': missing_key_settings})
    def test_wrong_keys(self):
        """Test dictionary with wrong keys."""
        expected = "Invalid keys."
        with self.assertRaisesRegex(ImproperlyConfigured, expected):
            SETTINGS.check()

    @override_settings(PAIN_DOWNLOADERS={'dummy': invalid_sub_settings})
    def test_invalid_subsettings(self):
        """Test invalid subsettings."""
        expected = "The key 1 is not of type str."
        with self.assertRaisesRegex(ImproperlyConfigured, expected):
            SETTINGS.check()

    @override_settings()
    def test_not_required(self):
        """Test there is no exception when the setting is missing."""
        del settings.PAIN_DOWNLOADERS
        SETTINGS.check()


class TestCallableListSetting(SimpleTestCase):
    """Test CallableListSetting."""

    @override_settings(PAIN_IMPORT_CALLBACKS=['django_pain.settings.PainSettings'])
    def test_ok(self):
        SETTINGS.check()

    @override_settings(PAIN_IMPORT_CALLBACKS=['django_pain.tests.test_settings'])
    def test_not_callable(self):
        with self.assertRaisesMessage(ImproperlyConfigured, 'CALLBACKS must be a list of dotted paths to callables'):
            SETTINGS.check()

    @override_settings(PAIN_IMPORT_CALLBACKS=[1, 2, 3])
    def test_not_a_string(self):
        with self.assertRaisesMessage(ImproperlyConfigured, 'CALLBACKS must be a list of dotted paths to callables'):
            SETTINGS.check()

    @override_settings(PAIN_IMPORT_CALLBACKS=['django_pain._non._existing._module'])
    def test_non_existing_import(self):
        with self.assertRaises(ImportError):
            SETTINGS.check()


@override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
class TestGetProcessorClass(CacheResetMixin, SimpleTestCase):
    """Test get_processor_class."""

    def test_success(self):
        """Test successful import."""
        self.assertEqual(
            get_processor_class('dummy'),
            DummyPaymentProcessor
        )

    def test_invalid(self):
        """Test not defined processor."""
        processor = 'invalid.package.name'
        with self.assertRaisesRegex(
                ValueError, '{} is not present in PAIN_PROCESSORS setting'.format(processor)):
            get_processor_class(processor)


@override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
class TestGetProcessorInstance(CacheResetMixin, SimpleTestCase):
    """Test get_processor_instance."""

    def test_success(self):
        """Test success."""
        self.assertIsInstance(
            get_processor_instance('dummy'),
            DummyPaymentProcessor
        )


@override_settings(PAIN_PROCESSORS={'dummy': 'django_pain.tests.utils.DummyPaymentProcessor'})
class TestGetProcessorObjective(CacheResetMixin, SimpleTestCase):
    """Test get_processor_objective."""

    def test_success(self):
        """Test success."""
        self.assertEqual(
            get_processor_objective('dummy'),
            'Dummy objective'
        )


@override_settings(PAIN_CARD_PAYMENT_HANDLERS={'dummy': 'django_pain.tests.utils.DummyCardPaymentHandler'})
class TestGetCardPaymentHandlerClass(CacheResetMixin, SimpleTestCase):
    """Test get_payment_handler_class."""

    def test_success(self):
        """Test successful import."""
        self.assertEqual(
            get_card_payment_handler_class('dummy'),
            DummyCardPaymentHandler
        )

    def test_invalid(self):
        """Test not defined card payment handler."""
        handler = 'invalid.package.name'
        with self.assertRaisesRegex(ValueError,
                                    '{} is not present in PAIN_CARD_PAYMENT_HANDLERS setting'.format(handler)):
            get_card_payment_handler_class(handler)


@override_settings(PAIN_CARD_PAYMENT_HANDLERS={'dummy': 'django_pain.tests.utils.DummyCardPaymentHandler'})
class TestGetCardPaymentHandlerInstance(CacheResetMixin, SimpleTestCase):
    """Test get_processor_instance."""

    def test_success(self):
        """Test success."""
        self.assertIsInstance(
            get_card_payment_handler_instance('dummy'),
            DummyCardPaymentHandler
        )
