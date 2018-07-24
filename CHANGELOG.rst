===========
 Changelog
===========

git
===
* Remove view PaymentListView
* Add django admin interface for accounts and payments `[#21]`_
* Payment processors now must return payment objective `[#21]`_
* Payment processors now must implement assign_payment method `[#21]`_
* Use modeltranslation on BankPayment model

.. _[#21]: https://github.com/stinovlas/django-pain/issues/21

0.2.0
=====
* Change payment processors API to allow bulk processing `[#19]`_

.. _[#19]: https://github.com/stinovlas/django-pain/issues/19

0.1.1
=====
* Add uuid_ field to BankPayment

.. _uuid: https://en.wikipedia.org/wiki/Universally_unique_identifier

0.1.0
=====
* Add bank statement parsers
* Add command ``import_payments``
* Add bank payment processors
* Add command ``process_payments``
* Add simple list view for payments

0.0.2
=====
* Add models ``BankAccount`` and ``BankPayment``
* Update setup.py for PyPI release

0.0.1
=====
* Initial version
