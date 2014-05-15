# Copyright (C) 2010-2014 GRNET S.A.
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

import distribute_setup
distribute_setup.use_setuptools()

import os
import sys

from setuptools import setup, find_packages
HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))

# Add snfdeploy to sys.path and load version module
sys.path.insert(0, "snfdeploy")
from version import __version__

# Package info
VERSION = __version__
SHORT_DESCRIPTION = 'Deployment tool for synnefo from scratch'

PACKAGES_ROOT = '.'
PACKAGES = find_packages(PACKAGES_ROOT)

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
    'argparse',
    'simplejson',
    'ipaddr',
    'fabric>=1.3',
]

setup(
    name='snf-deploy',
    version=VERSION,
    license='BSD',
    url='http://code.grnet.gr/',
    description=SHORT_DESCRIPTION,
    long_description=SHORT_DESCRIPTION,
    classifiers=CLASSIFIERS,

    author='Synnefo development team',
    author_email='synnefo-devel@googlegroups.com',
    maintainer='Synnefo development team',
    maintainer_email='synnefo-devel@googlegroups.com',

    packages=PACKAGES,
    package_dir={'': PACKAGES_ROOT},
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
