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

"""Settings for tests."""
import os

SECRET_KEY = 'Qapla\'!'

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'djmoney',
    'django_pain.apps.DjangoPainConfig',
    'django_lang_switch.apps.DjangoLangSwitchConfig',
    'django_pain.apps.DjangoPainAdminConfig',
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

DATABASES = {
        'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}
}

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

PAIN_PROCESSORS = {}  # type: dict
PAIN_CSOB_CARD = {
    'API_PUBLIC_KEY': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'empty_key.txt'),
    'MERCHANT_ID': '',
    'MERCHANT_PRIVATE_KEY': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'empty_key.txt'),
    'ACCOUNT_NUMBER': '123456',
}

DEFAULT_CURRENCY = 'CZK'
CURRENCIES = ['CZK', 'EUR']

PAIN_DOWNLOADERS = {}  # type: dict
