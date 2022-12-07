Changelog
=========

2.3.0 (2022-01-26)
------------------

* Add help text to enforce currency field
* Use account number instead of name in csob handler
* Select account by currency in csob handler

2.2.1 (2021-10-12)
------------------

* Skip to next processor after one fails
* Use teller 0.4
* Evaluate processor result inside try blok

2.2.0 (2021-08-13)
------------------

* Upgrade django-money
* Add type stubs
* Skip bank fees callback
* Fix requirements and tests for Django 3.0
* Test with Django up to version 3.2
* Fix default auto field warnings
* Convert amount to type Money and handle it correctly
* Convert currency to str for csob client
* Update test settings and fix licence check
* Do not run in parallel
* Allow empty counter account

2.1.1 (2021-05-20)
------------------

* Allow callback to cancel saving of a payment

2.1.0 (2021-04-29)
------------------

* Rise exception on invalid datetime
* Set default currency and allowed currencies
* Round money amounts to two decimal places
* Add README entry on currency formatting
* Add select for update to admin
* Fix thread synchronisation
* Use teller to download statements
* Allow to select subset of downloaders
* Add downloader cli param to README
* Add mixin for commands which save payments
* Do not check downloaders when not required and raw is missing
* Skip empty account with callback
* Pin teller version
* Add PaymentImportHistory
* Wrap admin views in a transaction
* Catch the OSError during import
* Use datetime as download_payments parameters
* Do not raise invalid account number for empty statements
* Lock the DB only when request is POST

2.0.0 (2020-10-06)
------------------

* Add support for Python 3.8
* Drop support for Django 2.1
* Add models for card payments
* Add Card payment handler and REST API
* Add get_card_payments_states mangagemend command
* Command process_payments now process also card payments.
* Add payment filtering by realized paymnets
* Add processing newly paid payments after status update by REST API
* Fix coverage of generators from payments processors
* Add transaction to retrieve() in REST API
* Allow only needed methods in BankPayment REST API
* Update state of only initialized card payments
* Return 503 while connection error during creating new card payment on gateway
* Fix FileSettings for Python 3.5
* Make PROCESSORS OrderedDict for tests to pass in Python 3.5

1.3.0 (2019-11-22)
------------------

* Update setup.py and requirements
* Return accidentally removed language switch
* Use constraints in tox
* Replace concurrent process_payments command info with warning

1.2.0 (2019-08-29)
------------------

* Including accounts in payment processing
* Add check for non-existing accounts
* Generate migration for django-money 0.15
* Update settings to allow multiple import callbacks
* Add skip_credit_card_transaction_summary import callback
* Move ignore_negative_payments callback to import_callbacks module
* Add favicon

1.1.0 (2019-04-29)
------------------

* Add separate permissions for manual assignment to individual payment processors
* Expand payment processors API to allow sending processing error codes.
  * Admissible processing error codes are defined in ``django_pain.constants.PaymentProcessingError`` enum.
  * This change is backward compatible.
* Add tax date to manual assignment of payment processor
  * If processor accepts a tax date, it has to have ``manual_tax_date`` set to ``True``.

1.0.1 (2019-01-22)
------------------

* Added ``PAIN_TRIM_VARSYM`` setting.
* Fix czech translation of account invoice

0.3.0 (2018-07-24)
------------------

* Remove view PaymentListView
* Add django admin interface for accounts and payments `[#21]`_
* Payment processors now must return payment objective `[#21]`_
* Payment processors now must implement assign_payment method `[#21]`_
* Use modeltranslation on BankPayment model

.. _[#21]: https://github.com/stinovlas/django-pain/issues/21

0.2.0 (2018-06-25)
------------------

* Change payment processors API to allow bulk processing `[#19]`_

.. _[#19]: https://github.com/stinovlas/django-pain/issues/19

0.1.1 (2018-06-12)
------------------

* Add uuid_ field to BankPayment

.. _uuid: https://en.wikipedia.org/wiki/Universally_unique_identifier

0.1.0 (2018-06-11)
------------------

* Add bank statement parsers
* Add command ``import_payments``
* Add bank payment processors
* Add command ``process_payments``
* Add simple list view for payments

0.0.2 (2018-04-26)
------------------

* Add models ``BankAccount`` and ``BankPayment``
* Update setup.py for PyPI release

0.0.1 (2018-04-17)
------------------

* Initial version
