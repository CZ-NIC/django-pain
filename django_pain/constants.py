"""Application-wide constants."""

# Number of decimal places of currency amounts.
# Bitcoin has 8, so 10 should be enough for most practical purposes.
CURRENCY_PRECISION = 10

# Payment states constants.
PAYMENT_STATE_IMPORTED = 0
PAYMENT_STATE_PROCESSED = 1
PAYMENT_STATE_EXPORTED = 2
