"""Processors utils."""
from functools import lru_cache

from django.utils import module_loading

import django_pain.processors


@lru_cache()
def get_processor_class(processor: str):
    """Get processor class."""
    try:
        processor_class = module_loading.import_string(processor)
    except ImportError:
        raise ValueError("Payment processor {} was not found".format(processor))

    if issubclass(processor_class, django_pain.processors.AbstractPaymentProcessor):
        return processor_class
    else:
        raise ValueError("{} is not a valid subclass of AbstractPaymentProcessor".format(processor))


@lru_cache()
def get_processor_instance(processor: str):
    """Get processor class instance."""
    processor_class = get_processor_class(processor)
    return processor_class()
