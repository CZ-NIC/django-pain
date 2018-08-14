"""Processors utils."""
from functools import lru_cache

from django.utils import module_loading


@lru_cache()
def get_processor_class(processor: str):
    """Get processor class."""
    processor_class = module_loading.import_string(processor)
    return processor_class


@lru_cache()
def get_processor_instance(processor: str):
    """Get processor class instance."""
    processor_class = get_processor_class(processor)
    return processor_class()
