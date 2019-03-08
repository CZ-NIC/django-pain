#!/usr/bin/python3
#
# Copyright (C) 2018-2019  CZ.NIC, z. s. p. o.
#
# This file is part of FRED.
#
# FRED is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# FRED is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with FRED.  If not, see <https://www.gnu.org/licenses/>.

"""Setup script for django_pain."""
import os
from distutils.command.build import build

from setuptools import find_packages, setup
from setuptools.command.sdist import sdist

import django_pain


class custom_build(build):
    sub_commands = [('compile_catalog', lambda x: True), ('build_js', None)] + build.sub_commands


class custom_sdist(sdist):

    def run(self):
        self.run_command('compile_catalog')
        # sdist is an old style class so super cannot be used
        sdist.run(self)

    def has_i18n_files(self):
        return bool(self.distribution.i18n_files)


def readme():
    """Return content of README file."""
    with open(os.path.join(os.path.dirname(__file__), 'README.rst'), encoding='utf-8') as f:
        return f.read()


SETUP_REQUIRES = ['Babel >=2.3', 'setuptools_webpack']
INSTALL_REQUIRES = open('requirements.txt').read().splitlines()
EXTRAS_REQUIRE = {'quality': ['isort', 'flake8', 'pydocstyle', 'polint', 'mypy'],
                  'test': ['testfixtures', 'freezegun']}

setup(name='django-pain',
      version=django_pain.__version__,
      description='Django application for managing bank payments and invoices',
      long_description=readme(),
      url='http://www.nic.cz/',
      author='Jan Musílek',
      author_email='jan.musilek@nic.cz',
      packages=find_packages(),
      include_package_data=True,
      setup_requires=SETUP_REQUIRES,
      install_requires=INSTALL_REQUIRES,
      extras_require=EXTRAS_REQUIRE,
      webpack_output_path='django_pain/static/django_pain/js',
      cmdclass={'build': custom_build, 'sdist': custom_sdist},
      classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      ])
