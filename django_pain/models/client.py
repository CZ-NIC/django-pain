"""Client related models."""
from django.db import models
from django.utils.translation import gettext_lazy as _

from .bank import BankPayment


class Client(models.Model):
    """Client model."""

    handle = models.TextField(verbose_name=_('Client ID'))
    remote_id = models.IntegerField()
    payment = models.OneToOneField(BankPayment, models.CASCADE, related_name='client')
