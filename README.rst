==============================
 Django Payments and Invoices
==============================

Django application for processing bank payments and invoices.

Bank statements are passed through parser and imported to database.
So far, there is only one parser available, ``TransprocXMLParser``,
used to process bank statements downloaded and processed by `fred-transproc`_.
Parsers may also be implemented as ``django-pain`` plugins.

Imported payments are regularly processed by payment processors.
Processors are usually implemented as ``django-pain`` plugins, implementing payment processor API.

Bank accounts and payments may be accessed through django admin site interface.

.. _fred-transproc: https://github.com/CZ-NIC/fred-transproc


------------
Installation
------------

You need to add ``django_pain.apps.DjangoPainConfig`` to your ``INSTALLED_APPS``.
In order for user interface to work, you also need to add django admin site.
See `django docs`__ for detailed description.

__ https://docs.djangoproject.com/en/dev/ref/contrib/admin/

You also need to include ``django_pain`` and ``admin`` urls into your project ``urls.py``:

.. code-block:: python

    urlpatterns = [
        ...
        path('pain/', include('django_pain.urls')),
        path('admin/', admin.site.urls),
        ...
    ]

After installing ``django-pain`` package and configuring your django project, you need to generate migrations.
Call ``django-admin makemigrations``.
These migrations depend on ``LANGUAGES`` and ``CURRENCIES`` settings, so think carefully how you set them.
If you decide to change these settings in the future, you need to generate the migrations again.

Also, JavaScript files use new ECMAScript 2017 notation and needs to be transpiled to work in most of current browsers.
Assuming you have ``Node.js`` and ``npm`` installed,
you first need to install necessary packages by calling ``npm install`` from the command line.
After that you can transpile the JavaScript code by calling ``npm run build``.


------------
Requirements
------------

All requirements are listed in ``requirements.txt``.


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

Provides payment processor for Payments (and therefore the Academy).


--------
Settings
--------

In order for ``django-pain`` to work, you need to define some settings in your ``settings.py``.

``PAIN_PROCESSORS``
===================

Required setting containing dictionary of payment processor names and dotted paths to payment processors classes.
The payments are offered to different payment processors in that order.

Example configuration:

.. code-block:: python

    PAIN_PROCESSORS = {
        'fred': 'fred_pain.processors.FredPaymentProcessor',
        'payments': 'payments_pain.processors.PaymentsPaymentProcessor',
        'ignore': 'django_pain.processors.IgnorePaymentProcessor',
    }

You should not change processor names unless you have a very good reason.
In that case, you also need to take care of changing processor names saved in database.


----------------------
Other related settings
----------------------

Plugins usually have settings on their own – see the docs.
Apart from that, there are several settings that doesn't have to be set, but it's really advisable to do so.

``CURRENCIES``
==============

List of currency codes used in the application.
Default is list of all available currencies (which is pretty long).

Example configuration:

.. code-block:: python

    CURRENCIES = ['CZK', 'EUR', 'USD']

This setting comes from django-money_ app. Changing this setting requires generating migrations.

.. _django-money: https://github.com/django-money/django-money

``DEFAULT_CURRENCY``
====================

Currency code of default currency.
It should be one of currencies defined in ``CURRENCIES`` setting.
Default is ``XYZ``.

Example configuration:

.. code-block:: python

    DEFAULT_CURRENCY = 'CZK'

This setting comes from django-money_ app. Changing this setting requires generating migrations.

``LANGUAGES``
=============

See `django docs`__.
It's advisable to set this only to languages you intend to support.
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
Bank statement should be provided on standard input or in a file as positional parameter.

Mandatory argument ``PARSER`` must be dotted path to payment parser class such as
``django_pain.parsers.transproc.TransprocXMLParser``.

``list_payments``
=================

.. code-block::

    list_payments [--exclude-accounts ACCOUNTS]
                  [--include-accounts ACCOUNTS]
                  [--limit LIMIT] [--state STATE]

List bank payments.

Options ``--exclude-accounts`` and ``--include-accounts`` are mutually exclusive
and expect comma separated list of bank account numbers.

Option ``--state`` can be either ``imported``, ``processed``, ``deferred`` or ``exported``.

If ``--limit LIMIT`` is set, command will list at most ``LIMIT`` payments.
If there any not-listed payments, command will announce their count.

``process_payments``
====================

.. code-block::

    process_payments [--from TIME_FROM] [--to TIME_TO]

Process unprocessed payments by predefined payment processors.

Command ``process_payments`` takes all payments in state ``imported`` or ``deferred``
and offers them to individual payment processors.
If any processor accepts the payment, it's state is changed do ``processed``.
Otherwise, it's state is changed to ``deferred``.

Options ``--from`` and ``--to`` limit payments to process by their creation date.
They expect ISO formatted datetime value.


---------
 Changes
---------

See changelog_.

.. _changelog: CHANGELOG.rst
