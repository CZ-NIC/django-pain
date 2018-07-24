"""Django app configuration."""
from django.apps import AppConfig

from django_pain.settings import PainSettings


class DjangoPainConfig(AppConfig):
    """Configuration of django_pain app."""

    name = 'django_pain'
    verbose_name = 'Django Payments and Invoices'

    def ready(self):
        """Check whether configuration is OK."""
        PainSettings.check()
