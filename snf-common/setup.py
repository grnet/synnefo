# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.
#

import distribute_setup
distribute_setup.use_setuptools()

import os

from distutils.util import convert_path
from fnmatch import fnmatchcase
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))

try:
    # use devtools to update the version file
    from devtools.version import update_version
    update_version('synnefo.versions', 'common', HERE)
except ImportError:
    raise RuntimeError("devtools is a build dependency")

from synnefo.versions.common import __version__

# Package info
VERSION = __version__
README = open(os.path.join(HERE, 'README')).read()
CHANGES = open(os.path.join(HERE, 'Changelog')).read()
SHORT_DESCRIPTION = 'Package short description'

PACKAGES_ROOT = '.'
PACKAGES = find_packages(PACKAGES_ROOT, exclude=['okeanos_site'])

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
]

EXTRAS_REQUIRES = {
}

TESTS_REQUIRES = [
]

setup(
    name = 'snf-common',
    version = VERSION,
    license = 'BSD',
    url = 'http://code.grnet.gr/',
    description = SHORT_DESCRIPTION,
    long_description=README + '\n\n' +  CHANGES,
    classifiers = CLASSIFIERS,

    author = 'Package author',
    author_email = 'author@grnet.gr',
    maintainer = 'Package maintainer',
    maintainer_email = 'maintainer@grnet.gr',

    namespace_packages = ['synnefo', 'synnefo.versions'],
    packages = PACKAGES,
    package_dir= {'': PACKAGES_ROOT},
    include_package_data = True,
    zip_safe = False,

    install_requires = INSTALL_REQUIRES,
    extras_require = EXTRAS_REQUIRES,
    tests_require = TESTS_REQUIRES,

    dependency_links = ['http://docs.dev.grnet.gr/pypi']
)

