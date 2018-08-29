"""Test mixins."""
from django_pain.settings import get_processor_class, get_processor_instance, get_processor_objective


class CacheResetMixin(object):
    """Mixin for resetting caches."""

    def setUp(self):
        """Reset functions decorated with lru_cache."""
        super().setUp()  # type: ignore
        get_processor_class.cache_clear()
        get_processor_instance.cache_clear()
        get_processor_objective.cache_clear()
