#!/usr/bin/python3
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
    with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
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
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      ])
