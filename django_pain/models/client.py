"""Client related models."""
from django.db import models
from django.utils.translation import gettext_lazy as _

from .bank import BankPayment


class Client(models.Model):
    """
    Client model.

    Fields:
        handle      short text representation of client
        remote_id   id in an external system
        payment     link to appropriate payment
    """

    handle = models.TextField(verbose_name=_('Client ID'))
    remote_id = models.IntegerField()
    payment = models.OneToOneField(BankPayment, on_delete=models.CASCADE, related_name='client')
