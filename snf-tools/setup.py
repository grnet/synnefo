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

#from distutils.util import convert_path
#from fnmatch import fnmatchcase
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))

from synnefo_tools.version import __version__

# Package info
VERSION = __version__
SHORT_DESCRIPTION = 'Integration testing tool for a running Synnefo deployment'

PACKAGES_ROOT = '.'
PACKAGES = find_packages(PACKAGES_ROOT)

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
    "IPy",
    "paramiko",
    "vncauthproxy",
    "kamaki >= 0.12.3"]

setup(
    name='snf-tools',
    version=VERSION,
    license='BSD',
    url='http://www.synnefo.org/',
    description=SHORT_DESCRIPTION,
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

    dependency_links=['http://www.synnefo.org/packages/pypi'],

    entry_points={
        'console_scripts': ['snf-burnin = synnefo_tools.burnin:main']}
)
