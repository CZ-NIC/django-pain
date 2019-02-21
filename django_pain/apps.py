"""Django app configuration."""
from django.apps import AppConfig, apps
from django.contrib.admin.apps import AdminConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _

from django_pain.settings import SETTINGS, PainSettings, get_processor_instance


def create_permissions(app_config, **kwargs):
    """
    Create payment processor specific permissions.

    These permission depend on application settings.
    For every payment processor in PAIN_PROCESSORS
    there is one permission to manually assign payments to this processor.
    Codename of this permission is dependent on payment processor label in PAIN_PROCESSORS.
    """
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Permission = apps.get_model('auth', 'Permission')
    BankPayment = app_config.get_model('BankPayment')
    content_type = ContentType.objects.get_for_model(BankPayment)

    for proc_name in SETTINGS.processors:
        proc = get_processor_instance(proc_name)
        Permission.objects.update_or_create(
            codename='can_manually_assign_to_{}'.format(proc_name),
            content_type=content_type,
            defaults={
                'name': 'Can manually assign to {}'.format(proc.default_objective),
            },
        )


class DjangoPainConfig(AppConfig):
    """Configuration of django_pain app."""

    name = 'django_pain'
    verbose_name = _('Payments and Invoices')

    def ready(self):
        """Check whether configuration is OK."""
        PainSettings.check()
        post_migrate.connect(create_permissions, sender=self)


class DjangoPainAdminConfig(AdminConfig):
    """Override default django-admin site."""

    default_site = 'django_pain.sites.PainAdminSite'
