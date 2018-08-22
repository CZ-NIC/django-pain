==============================
 Django Payments and Invoices
==============================

Django application for processing bank payments and invoices.

--------
Settings
--------

``PAIN_PROCESSORS``
===================

Required setting containing list of dotted paths to payment processors.
The payments are offered to different payment processors in that order.

If you do not wish to use ``process_payments`` command, you may set it to ``[]``.
