#!/usr/bin/python3
"""Setup script for django_pain."""
from setuptools import find_packages, setup

import django_pain

INSTALL_REQUIRES = ['Django>=2.0', 'django-money']
EXTRAS_REQUIRE = {'quality': ['isort', 'flake8', 'pydocstyle', 'polint']}

setup(name='django-pain',
      version=django_pain.__version__,
      description='Django application for managing bank payments and invoices',
      packages=find_packages(),
      install_requires=INSTALL_REQUIRES,
      extras_require=EXTRAS_REQUIRE)
