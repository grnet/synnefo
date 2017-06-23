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

"""Packaging module for snf-stats-app"""

import os

from imp import load_source
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))
VERSION_FILE = os.path.join(HERE, 'synnefo_stats', 'version.py')

# Package info
VERSION = getattr(load_source('version', VERSION_FILE), "__version__")
SHORT_DESCRIPTION = 'Synnefo graphic statistics component'

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
    'gdmodule',
    'py-rrdtool',
    'Django>=1.7, <1.8',
    'snf-django-lib',
    'pycrypto>=2.1.0',
]

setup(
    name='snf-stats-app',
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

    dependency_links=['http://www.synnefo.org/packages/pypi'],
    entry_points={
        'synnefo': [
            'default_settings = synnefo_stats.synnefo_settings',
            'web_apps = synnefo_stats.synnefo_settings:installed_apps',
            'urls = synnefo_stats.urls:urlpatterns',
        ]
    }
)
