"""Translation module for django-modeltranslation."""
from modeltranslation import translator

from django_pain.models import BankPayment


@translator.register(BankPayment)
class BankPaymentTranslationOptions(translator.TranslationOptions):
    """Translate field ``objective``."""

    fields = ('objective',)
