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

"""Packaging module for snf-deploy"""

import os

from imp import load_source
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))
VERSION_PY = os.path.join(HERE, 'snfdeploy', 'version.py')

# Package info
VERSION = getattr(load_source('version', VERSION_PY), "__version__")
SHORT_DESCRIPTION = 'Deployment tool for synnefo from scratch'

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
    'argparse',
    'ipaddr',
    'fabric>=1.3',
]

setup(
    name='snf-deploy',
    version=VERSION,
    license='GNU GPLv3',
    url='https://www.synnefo.org/',
    description=SHORT_DESCRIPTION,
    long_description=SHORT_DESCRIPTION,
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
        'console_scripts': [
            'snf-deploy=snfdeploy:main',
            ],
        },
)
