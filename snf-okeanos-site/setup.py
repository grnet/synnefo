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
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))

try:
    # try to update the version file
    from synnefo.util.version import update_version
    update_version('okeanos_site', 'version', HERE)
except ImportError:
    pass

from okeanos_site.version import __version__


# Package info
VERSION = __version__
README = open(os.path.join(HERE, 'README')).read()
CHANGES = open(os.path.join(HERE, 'Changelog')).read()
SHORT_DESCRIPTION = 'Package short description'

PACKAGES_ROOT = '.'
PACKAGES = find_packages(PACKAGES_ROOT)

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
        'snf-common>=0.7.3',
        'snf-webproject>=0.7.3',
        'snf-app>=0.7.3'
]

TESTS_REQUIRES = [
]

PACKAGE_DATA = {
    'okeanos_site': [
        'templates/okeanos/*.html',
        'templates/okeanos/pages/*.html',
        'static/okeanos_static/css/*.css',
        'static/okeanos_static/js/*.js',
        'static/okeanos_static/images/*.png',
        'static/okeanos_static/video/*.txt',
        'static/okeanos_static/video/*.js',
        'static/okeanos_static/video/*.css',
        'static/okeanos_static/video/skins/*.css',
    ]
}

setup(
    name = 'snf-okeanos-site',
    version = VERSION,
    license = 'BSD',
    url = 'http://code.grnet.gr/',
    description = SHORT_DESCRIPTION,
    long_description=README + '\n\n' +  CHANGES,
    classifiers = CLASSIFIERS,

    author = '~okeanos dev team - GRNET',
    author_email = 'okeanos-dev@lists.grnet.gr',
    maintainer = 'Kostas Papadimitriou',
    maintainer_email = 'kpap@grnet.gr',

    dependency_links = ['http://docs.dev.grnet.gr/pypi'],

    packages = PACKAGES,
    package_dir= {'': PACKAGES_ROOT},
    include_package_data = True,
    package_data = PACKAGE_DATA,
    zip_safe = False,

    entry_points = {
        'synnefo': [
            'default_settings = okeanos_site.settings',
            'web_apps = okeanos_site:synnefo_web_apps',
            'web_static = okeanos_site:synnefo_static_files',
            'urls = okeanos_site.urls:urlpatterns'
        ]
    },

    install_requires = INSTALL_REQUIRES,
)

