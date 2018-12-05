"""Django custom sites."""
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _


class PainAdminSite(AdminSite):
    """Custom django-admin site."""

    site_header = _('PAIN Administration')
    site_title = _('PAIN Administration')
    site_url = None
