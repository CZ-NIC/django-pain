#!/usr/bin/python3
#
# Copyright (C) 2018-2022  CZ.NIC, z. s. p. o.
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
from distutils.command.build import build

from setuptools import setup
from setuptools_npm import npm_not_skipped


class custom_build(build):
    sub_commands = [
        ('compile_catalog', None),
        ('npm_install', npm_not_skipped),
        ('npm_run', npm_not_skipped),
    ] + build.sub_commands


setup(cmdclass={'build': custom_build})
