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

"""Packaging module for snf-cyclades-app"""

import os

from imp import load_source
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))
VERSION_PY = os.path.join(HERE, 'synnefo', 'versions', 'app.py')

# Package info
VERSION = getattr(load_source('version', VERSION_PY), '__version__')
SHORT_DESCRIPTION = 'Synnefo Compute, Network and Image component'

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
    'Django>=1.7, <1.8',
    'python-dateutil>=1.4.1',
    'IPy>=0.70',
    'pycrypto>=2.1.0',
    'puka',
    'python-daemon>=1.5.5, <1.6',
    'snf-common',
    'snf-pithos-backend',
    'lockfile>=0.8, <0.9',
    'ipaddr',
    'setproctitle>=1.0.1',
    'bitarray>=0.8',
    'objpool>=0.3',
    'astakosclient',
    'snf-django-lib',
    'snf-branding',
    'snf-webproject',
    'requests>=0.12.1',
    'paramiko'
]

EXTRAS_REQUIRES = {
    'DISPATCHER': ['puka', 'python-daemon==1.5.5', 'lockfile==0.8',
                   'setproctitle>=1.0.1'],
    'SSH_KEYS': ['pycrypto>=2.1.0'],
}

TESTS_REQUIRES = [
    'factory_boy==2.1.0'
]

setup(
    name='snf-cyclades-app',
    version=VERSION,
    license='GNU GPLv3',
    url='http://www.synnefo.org/',
    description=SHORT_DESCRIPTION,
    classifiers=CLASSIFIERS,

    author='Synnefo development team',
    author_email='synnefo-devel@googlegroups.com',
    maintainer='Synnefo development team',
    maintainer_email='synnefo-devel@googlegroups.com',

    namespace_packages=['synnefo', 'synnefo.versions'],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,

    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRES,
    tests_require=TESTS_REQUIRES,

    dependency_links=['http://www.synnefo.org/packages/pypi'],

    entry_points={
        'console_scripts': [
            'snf-dispatcher = synnefo.logic.dispatcher:main',
        ],
        'synnefo': [
            'default_settings = synnefo.app_settings.default',
            'web_apps = synnefo.app_settings:synnefo_web_apps',
            'web_middleware = synnefo.app_settings:synnefo_web_middleware',
            'web_context_processors = synnefo.app_settings:synnefo_web_context_processors',
            'urls = synnefo.app_settings.urls:urlpatterns',
            'web_static = synnefo.app_settings:synnefo_static_files',
        ]
    },
)
