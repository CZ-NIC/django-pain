"""Processors module."""
from .common import AbstractPaymentProcessor, ProcessPaymentResult
from .ignore import IgnorePaymentProcessor

__all__ = ['AbstractPaymentProcessor', 'ProcessPaymentResult',
           'IgnorePaymentProcessor']
