"""Application-wide constants."""
from enum import Enum, unique

# Number of decimal places of currency amounts.
# Bitcoin has 8, so 10 should be enough for most practical purposes.
CURRENCY_PRECISION = 10


@unique
class PaymentState(str, Enum):
    """Payment states constants."""

    IMPORTED = 'imported'
    PROCESSED = 'processed'
    DEFERRED = 'deferred'
    EXPORTED = 'exported'


@unique
class InvoiceType(str, Enum):
    """Invoice type constants."""

    ADVANCE = 'advance'
    ACCOUNT = 'account'


@unique
class PaymentProcessingError(str, Enum):
    """Payment processing error constants."""

    DUPLICITY = 'duplicity'
    INSUFFICIENT_AMOUNT = 'insufficient_amount'
    EXCESSIVE_AMOUNT = 'excessive_amount'
    OVERDUE = 'overdue'
    MANUALLY_BROKEN = 'manually_broken'
