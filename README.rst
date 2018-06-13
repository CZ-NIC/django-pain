==============================
 Django Payments and Invoices
==============================

.. image:: https://travis-ci.org/stinovlas/django-pain.svg?branch=master
   :target: https://travis-ci.org/stinovlas/django-pain
.. image:: https://codecov.io/gh/stinovlas/django-pain/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/stinovlas/django-pain
.. image:: https://img.shields.io/pypi/pyversions/django-pain.svg
   :target: https://pypi.org/project/django-pain
.. image:: https://img.shields.io/pypi/djversions/django-pain.svg
   :target: https://pypi.org/project/django-pain

Django application for processing bank payments and invoices.

--------
Settings
--------

``PAIN_PROCESSORS``
===================

Required setting containing list of dotted paths to payment processors.
The payments are offered to different payment processors in that order.

If you do not wish to use ``process_payments`` command, you may set it to ``[]``.

---------
 Changes
---------

See changelog_.

.. _changelog: CHANGELOG.rst
