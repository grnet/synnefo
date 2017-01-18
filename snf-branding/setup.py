#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2016 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Packaging module for snf-branding"""

import os

from imp import load_source
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))
VERSION_PY = os.path.join(HERE, 'synnefo_branding', 'version.py')

# Package info
VERSION = getattr(load_source('VERSION', VERSION_PY), '__version__')
SHORT_DESCRIPTION = 'Branding components for Synnefo'

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
]

setup(
    name='snf-branding',
    version=VERSION,
    license='GNU GPLv3',
    url='http://www.synnefo.org/',
    description=SHORT_DESCRIPTION,
    classifiers=CLASSIFIERS,

    author='Synnefo development team',
    author_email='synnefo-devel@googlegroups.com',
    maintainer='Synnefo development team',
    maintainer_email='synnefo-devel@googlegroups.com',

    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,

    install_requires=INSTALL_REQUIRES,

    dependency_links=['http://docs.dev.grnet.gr/pypi'],
    entry_points={
        'synnefo': [
            'web_apps = synnefo_branding.synnefo_settings:installed_apps',
            'web_context_processors = synnefo_branding.synnefo_settings:context_processors',
            'web_static = synnefo_branding.synnefo_settings:static_files',
        ]
    }
)
