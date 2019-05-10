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


------------
Installation
------------

You need to add ``django_pain.apps.DjangoPainConfig`` to your ``INSTALLED_APPS``.
In order for user interface to work, you also need to add the Django admin site.
See `Django docs`__ for detailed description.

__ https://docs.djangoproject.com/en/dev/ref/contrib/admin/

You also need to include ``django_pain`` and ``admin`` urls into your project ``urls.py``:

.. code-block:: python

    urlpatterns = [
        ...
        path('pain/', include('django_pain.urls')),
        path('admin/', admin.site.urls),
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

------------
Requirements
------------

All requirements are listed in ``requirements.txt``.

If you wish to use LDAP authentication, you can use django-python3-ldap__.

__ https://github.com/etianen/django-python3-ldap


-------
Plugins
-------

``fred-pain``
=============

https://gitlab.office.nic.cz/fred/pain

Provides payment processor for FRED.

``payments-pain``
=================

https://gitlab.office.nic.cz/ginger/payments-pain

Provides payment processor for Ginger Payments (and therefore the Academy).


--------
Settings
--------

In order for ``django-pain`` to work, you need to define some settings in your ``settings.py``.

``PAIN_PROCESSORS``
===================

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
===================================

Path to the lock file for the ``process_payments`` command.
The default value is ``/tmp/pain_process_payments.lock``.

``PAIN_TRIM_VARSYM``
====================

Boolean setting.
If ``True``, bank statement parser removes leading zeros from the variable symbol.
Default is ``False``.

``PAIN_IMPORT_CALLBACK``
========================

Callable setting.

Value should be callable that takes BankPayment object as its argument and returns (possibly) changed BankPayment.
This callable is called right before the payment is saved during the import.
Especially, this callable can throw ValidationError in order to avoid saving payment to the database.
Default value is identity function.

----------------------
Other related settings
----------------------

Plugins usually have settings of their own, see the plugin docs.
Apart from that, there are several settings that don't have to be set, but it's really advisable to do so.

``CURRENCIES``
==============

A list of currency codes used in the application.
The default is the list of all available currencies (which is pretty long).

Example configuration:

.. code-block:: python

    CURRENCIES = ['CZK', 'EUR', 'USD']

This setting comes from django-money_ app. Changing this setting requires generating migrations.

.. _django-money: https://github.com/django-money/django-money

``DEFAULT_CURRENCY``
====================

The currency code of the default currency.
It should be one of the currencies defined in the ``CURRENCIES`` setting.
The default is ``XYZ``.

Example configuration:

.. code-block:: python

    DEFAULT_CURRENCY = 'CZK'

This setting comes from django-money_ app. Changing this setting requires generating migrations.

``LANGUAGES``
=============

See `Django docs`__.
It is advisable to set this only to languages you intend to support.
``django-pain`` natively comes with English and Czech.

__ https://docs.djangoproject.com/en/dev/ref/settings/#languages


--------
Commands
--------

``import_payments``
===================

.. code-block::

    import_payments --parser PARSER [input file [input file ...]]

Import payments from the bank.
A bank statement should be provided on the standard input or in a file as a positional parameter.

The mandatory argument ``PARSER`` must be a dotted path to a payment-parser class such as
``django_pain.parsers.transproc.TransprocXMLParser``.

``list_payments``
=================

.. code-block::

    list_payments [--exclude-accounts ACCOUNTS]
                  [--include-accounts ACCOUNTS]
                  [--limit LIMIT] [--state STATE]

List bank payments.

The options ``--exclude-accounts`` and ``--include-accounts`` are mutually exclusive
and expect a comma-separated list of bank account numbers.

Option ``--state`` can be either ``imported``, ``processed``, ``deferred`` or ``exported``.

If ``--limit LIMIT`` is set, the command will list at most ``LIMIT`` payments.
If there are any non-listed payments, the command will announce their count.

``process_payments``
====================

.. code-block::

    process_payments [--from TIME_FROM] [--to TIME_TO]

Process unprocessed payments with predefined payment processors.

The command takes all payments in the states ``imported`` or ``deferred``
and offers them to the individual payment processors.
If any processor accepts the payment, then payment's state is switched to ``processed``.
Otherwise, its state is switched to ``deferred``.

The options ``--from`` and ``--to`` limit payments to be processed by their creation date.
They expect an ISO-formatted datetime value.


---------
 Changes
---------

See CHANGELOG_.

.. _CHANGELOG: CHANGELOG.rst
