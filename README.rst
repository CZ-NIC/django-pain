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

``DEFAULT_CURRENCY``
====================

Currency code of default currency.
It should be one of currencies defined in ``CURRENCIES`` setting.
Default is ``XYZ``.

Example configuration:

.. code-block:: python

    DEFAULT_CURRENCY = 'CZK'

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
