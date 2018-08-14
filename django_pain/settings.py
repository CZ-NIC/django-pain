"""django_pain settings."""
import appsettings

from django_pain.processors.utils import get_processor_class


class ClassListSetting(appsettings.ListSetting):
    """List of dotted paths to classes setting."""

    def transform(self, value):
        """Import all classes from setting."""
        return [get_processor_class(item) for item in value]


class PainSettings(appsettings.AppSettings):
    """Application specific settings."""

    processors = ClassListSetting(required=True, item_type=str)

    class Meta:
        """Meta class."""

        setting_prefix = 'pain_'


SETTINGS = PainSettings()
