==============================
 Django Payments and Invoices
==============================

Django application for processing bank payments and invoices.


--------
Settings
--------

``CURRENCIES``
==============

List of currency codes used in the application.
Default is list of all available currencies (which is pretty long).

Example configuration:

.. code-block:: python

    CURRENCIES = ['CZK', 'EUR', 'USD']

Changing this setting requires generating migrations.

``DEFAULT_CURRENCY``
====================

Currency code of default currency.
It should be one of currencies defined in ``CURRENCIES`` setting.
Default is ``XYZ``.

Example configuration:

.. code-block:: python

    DEFAULT_CURRENCY = 'CZK'

Changing this setting requires generating migrations.

``PAIN_PROCESSORS``
===================

Required setting containing dictionary of payment processor names and dotted paths to payment processors classes.
The payments are subsequently offered to all payment processors, until the payment is accepted.

Example configuration:

.. code-block:: python

    PAIN_PROCESSORS = {
        'fred': 'fred_pain.processors.FredPaymentProcessor',
        'payments': 'payments_pain.processors.PaymentsPaymentProcessor',
        'ignore': 'django_pain.processors.IgnorePaymentProcessor',
    }

You should not change processor names unless you have a very good reason.
In that case, you also need to take care of changing processor names saved in database.


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
