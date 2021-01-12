==============================
 Django Payments and Invoices
==============================

Django application for processing bank payments and invoices.

Bank statements are passed through a parser and imported to a database.
So far, there is only one parser available, ``TransprocXMLParser``,
used to process bank statements collected and transformed by `fred-transproc`_.
Parsers may also be implemented as ``django-pain`` plugins.

Imported payments are regularly processed by payment processors.
The processors are usually implemented as ``django-pain`` plugins, implementing
payment processor interface.

Bank accounts and payments may be managed through a Django admin site.

.. _fred-transproc: https://github.com/CZ-NIC/fred-transproc


Installation
============

You need to add ``django_pain.apps.DjangoPainConfig`` and ``django_lang_switch.apps.DjangoLangSwitchConfig`` to your ``INSTALLED_APPS``.
In order for user interface to work, you also need to add the Django admin site.
See `Django docs`__ for detailed description.

__ https://docs.djangoproject.com/en/dev/ref/contrib/admin/

You also need to include ``django_pain``, ``admin`` and ``django_lang_switch`` urls into your project ``urls.py``:

.. code-block:: python

    urlpatterns = [
        ...
        path('pain/', include('django_pain.urls')),
        path('admin/', admin.site.urls),
        path('django_lang_switch/', include('django_lang_switch.urls')),
        ...
    ]

After installing the ``django-pain`` package and configuring your Django project, you need to generate migrations.
Call ``django-admin makemigrations``.
These migrations depend on ``LANGUAGES`` and ``CURRENCIES`` settings_, so think carefully how you set them.
If you decide to change these settings in the future, you need to generate the migrations again.

Also, JavaScript files use the new ECMAScript 2017 notation and need to be transpiled
in order to work in most of current browsers.
Assuming you have ``Node.js`` and ``npm`` installed,
you need to install necessary packages first by calling ``npm install`` from the command line.
After that, you can transpile the JavaScript code by calling ``npm run build``.

.. _settings: `Other related settings`_

Requirements
============

All requirements are listed in ``requirements.txt``.

If you wish to use LDAP authentication, you can use django-python3-ldap__.

__ https://github.com/etianen/django-python3-ldap


Plugins
=======

``fred-pain``
-------------

https://gitlab.office.nic.cz/fred/pain

Provides payment processor for FRED.

``payments-pain``
-----------------

https://gitlab.office.nic.cz/ginger/payments-pain

Provides payment processor for Ginger Payments (and therefore the Academy).


Settings
========

In order for ``django-pain`` to work, you need to define some settings in your ``settings.py``.

``PAIN_PROCESSORS``
-------------------

A required setting containing a dictionary of payment processor names and dotted paths to payment processors classes.
The payments are offered to the payment processors in that order.

Example configuration:

.. code-block:: python

    PAIN_PROCESSORS = {
        'fred': 'fred_pain.processors.FredPaymentProcessor',
        'payments': 'payments_pain.processors.PaymentsPaymentProcessor',
        'ignore': 'django_pain.processors.IgnorePaymentProcessor',
    }

You should not change processor names unless you have a very good reason.
In that case, you also need to take care of changing processor names saved in the database.

When you change this setting (including the initial setup), you have to run ``django-admin migrate``.
Permissions for manual assignment to individual payment processors are created in this step.

``PAIN_PROCESS_PAYMENTS_LOCK_FILE``
-----------------------------------

Path to the lock file for the ``process_payments`` command.
The default value is ``/tmp/pain_process_payments.lock``.

``PAIN_TRIM_VARSYM``
--------------------

Boolean setting.
If ``True``, bank statement parser removes leading zeros from the variable symbol.
Default is ``False``.

``PAIN_DOWNLOADERS``
--------------------

A setting containing dotted paths to payment downloader and parser classes and downloader parameters.
There should be a separate entry in the dictionary for each bank from which payments should be downloaded.
The downloaders and parsers are provided in `teller` library.

Example configuration:

.. code-block:: python

    DOWNLOADERS = {'test_bank': {'DOWNLOADER': 'teller.downloaders.TestStatementDownloader',
                                 'PARSER': 'teller.downloaders.TestStatementParser',
                                 'DOWNLOADER_PARAMS': {'base_url': 'https://bank.test', 'password': 'letmein'}}}

``PAIN_IMPORT_CALLBACK``
------------------------

List setting containing dotted paths to callables.

Each value of the list should be dotted path refering to callable that takes BankPayment object as its argument and returns (possibly) changed BankPayment.
This callable is called right before the payment is saved during the import.
Especially, this callable can throw ValidationError in order to avoid saving payment to the database.
Default value is empty list.


Other related settings
======================

Plugins usually have settings of their own, see the plugin docs.
Apart from that, there are several settings that don't have to be set, but it's really advisable to do so.

``CURRENCIES``
--------------

A list of currency codes used in the application.
The default is the list of all available currencies (which is pretty long).

Example configuration:

.. code-block:: python

    CURRENCIES = ['CZK', 'EUR', 'USD']

This setting comes from django-money_ app. Changing this setting requires generating migrations.

.. _django-money: https://github.com/django-money/django-money

``DEFAULT_CURRENCY``
--------------------

The currency code of the default currency.
It should be one of the currencies defined in the ``CURRENCIES`` setting.
The default is ``XYZ``.

Example configuration:

.. code-block:: python

    DEFAULT_CURRENCY = 'CZK'

This setting comes from django-money_ app. Changing this setting requires generating migrations.

``LANGUAGES``
-------------

See `Django docs`__.
It is advisable to set this only to languages you intend to support.
``django-pain`` natively comes with English and Czech.

__ https://docs.djangoproject.com/en/dev/ref/settings/#languages

Currency formatting
-------------------

In case Django does not format currencies correctly according to its locale setting it may be necessary to define the formatting rules manually:

.. code-block:: python

    from moneyed.localization import _FORMATTER as money_formatter
    from decimal import ROUND_HALF_UP
    money_formatter.add_formatting_definition(
        'cs', group_size=3, group_separator=' ', decimal_point=',',
        positive_sign='',  trailing_positive_sign='',
        negative_sign='-', trailing_negative_sign='',
        rounding_method=ROUND_HALF_UP
    )

First argument of `add_formatting_definition` should be a properly formatted `locale name`_ from the ``LANGUAGES`` setting.

.. _locale name: https://docs.djangoproject.com/en/dev/topics/i18n/#term-locale-name

This setting comes from py-moneyed_ library.

.. _py-moneyed: https://github.com/limist/py-moneyed


Commands
========

``import_payments``
-------------------

.. code-block::

    import_payments --parser PARSER [input file [input file ...]]

Import payments from the bank.
A bank statement should be provided on the standard input or in a file as a positional parameter.

The mandatory argument ``PARSER`` must be a dotted path to a payment-parser class such as
``django_pain.parsers.transproc.TransprocXMLParser``.

``download_payments``
---------------------

.. code-block::

    download_payments [--start START] [--end END] [--downloader DOWNLOADER]

Download payments from the banks.

There are two optional arguments ``--start`` and ``--end`` which set the download interval for which the banks will be
queried. Both parameters should be entered as date in ISO format.
Default value for ``END`` is today.
Default value for ``START`` is seven days before ``END``.

Example ``download_payments --start 2020-09-01 --end 2020-10-31``

Optional repeatable parameter ``--downloader`` selects which downloaders defined in the ``PAIN_DOWNLOADERS`` settings will
be used. If the parameter is omitted all defined downloaders will be used.

Example ``download_payments --downloader somebank --downloader someotherbank``

``list_payments``
-----------------

.. code-block::

    list_payments [--exclude-accounts ACCOUNTS]
                  [--include-accounts ACCOUNTS]
                  [--limit LIMIT] [--state STATE]

List bank payments.

The options ``--exclude-accounts`` and ``--include-accounts`` are mutually exclusive
and expect a comma-separated list of bank account numbers.

Option ``--state`` can be either ``ready_to_process``, ``processed``, ``deferred`` or ``exported``.

If ``--limit LIMIT`` is set, the command will list at most ``LIMIT`` payments.
If there are any non-listed payments, the command will announce their count.

``process_payments``
--------------------

.. code-block::

    process_payments [--from TIME_FROM] [--to TIME_TO]

Process unprocessed payments with predefined payment processors.

The command takes all payments in the states ``ready_to_process`` or ``deferred``
and offers them to the individual payment processors.
If any processor accepts the payment, then payment's state is switched to ``processed``.
Otherwise, its state is switched to ``deferred``.

The options ``--from`` and ``--to`` limit payments to be processed by their creation date.
They expect an ISO-formatted datetime value.


Changes
=======

See CHANGELOG_.

.. _CHANGELOG: CHANGELOG.rst
