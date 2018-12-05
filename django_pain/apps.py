"""Django app configuration."""
from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig
from django.utils.translation import gettext_lazy as _

from django_pain.settings import PainSettings


class DjangoPainConfig(AppConfig):
    """Configuration of django_pain app."""

    name = 'django_pain'
    verbose_name = _('Payments and Invoices')

    def ready(self):
        """Check whether configuration is OK."""
        PainSettings.check()


class DjangoPainAdminConfig(AdminConfig):
    """Override default django-admin site."""

    default_site = 'django_pain.sites.PainAdminSite'
