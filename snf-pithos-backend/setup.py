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

"""Packaging module for snf-pithos-backend"""

import os

from imp import load_source
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))
VERSION_PY = os.path.join(HERE, 'pithos', 'backends', 'version.py')

# Package info
VERSION = getattr(load_source('version', VERSION_PY), '__version__')
SHORT_DESCRIPTION = 'Backend library for the File/Object Storage component'

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
    'snf-common',
    'SQLAlchemy>=0.9, <1.0',
    'alembic>=0.6, <0.7',
    'objpool>=0.3',
    'archipelago'
]

EXTRAS_REQUIRES = {
}

TESTS_REQUIRES = [
]

setup(
    name='snf-pithos-backend',
    version=VERSION,
    license='GNU GPLv3',
    url='http://www.synnefo.org/',
    description=SHORT_DESCRIPTION,
    classifiers=CLASSIFIERS,

    author='Synnefo development team',
    author_email='synnefo-devel@googlegroups.com',
    maintainer='Synnefo development team',
    maintainer_email='synnefo-devel@googlegroups.com',

    namespace_packages=['pithos'],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,

    dependency_links=[
        'http://www.synnefo.org/packages/pypi'],

    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRES,
    tests_require=TESTS_REQUIRES,

    entry_points={
        'console_scripts': [
            'pithos-migrate = pithos.backends.migrate:main'
        ],
    },
)
