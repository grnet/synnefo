# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
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
import sys

from distutils.util import convert_path
from fnmatch import fnmatchcase
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))

from synnefo.versions.app import __version__

# Package info
VERSION = __version__
SHORT_DESCRIPTION = 'Synnefo Compute, Network and Image component'

PACKAGES_ROOT = '.'
PACKAGES = find_packages(PACKAGES_ROOT)

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
    'Django >=1.2, <1.3',
    'simplejson>=2.1.1',
    'pycurl>=7.19.0',
    'python-dateutil>=1.4.1',
    'IPy>=0.70',
    'South>=0.7.3',
    'pycrypto>=2.1.0',
    'puka',
    'python-daemon>=1.5.5, <1.6',
    'snf-common',
    'vncauthproxy>=1.2',
    'snf-pithos-backend',
    'lockfile>=0.8, <0.9',
    'ipaddr',
    'setproctitle>=1.0.1',
    'bitarray>=0.8',
    'objpool>=0.3',
    'astakosclient',
    'snf-django-lib',
    'snf-branding',
    'snf-webproject'
]

EXTRAS_REQUIRES = {
        'DISPATCHER': ['puka', 'python-daemon==1.5.5', 'lockfile==0.8',
                       'setproctitle>=1.0.1'],
        'SSH_KEYS': ['pycrypto==2.1.0'],
}

TESTS_REQUIRES = [
    'factory_boy==2.1.0'
]


# Provided as an attribute, so you can append to these instead
# of replicating them:
standard_exclude = ["*.py", "*.pyc", "*$py.class", "*~", ".*", "*.bak"]
standard_exclude_directories = [
    ".*", "CVS", "_darcs", "./build", "./dist", "EGG-INFO", "*.egg-info", "snf-0.7"
]

# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# Note: you may want to copy this into your setup.py file verbatim, as
# you can't import this from another package, when you don't know if
# that package is installed yet.
def find_package_data(
    where=".",
    package="",
    exclude=standard_exclude,
    exclude_directories=standard_exclude_directories,
    only_in_packages=True,
    show_ignored=False):
    """
    Return a dictionary suitable for use in ``package_data``
    in a distutils ``setup.py`` file.

    The dictionary looks like::

        {"package": [files]}

    Where ``files`` is a list of all the files in that package that
    don"t match anything in ``exclude``.

    If ``only_in_packages`` is true, then top-level directories that
    are not packages won"t be included (but directories under packages
    will).

    Directories matching any pattern in ``exclude_directories`` will
    be ignored; by default directories with leading ``.``, ``CVS``,
    and ``_darcs`` will be ignored.

    If ``show_ignored`` is true, then all the files that aren"t
    included in package data are shown on stderr (for debugging
    purposes).

    Note patterns use wildcards, or can be exact paths (including
    leading ``./``), and all searching is case-insensitive.
    """
    out = {}
    stack = [(convert_path(where), "", package, only_in_packages)]
    while stack:
        where, prefix, package, only_in_packages = stack.pop(0)
        for name in os.listdir(where):
            fn = os.path.join(where, name)
            if os.path.isdir(fn):
                bad_name = False
                for pattern in exclude_directories:
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
                        bad_name = True
                        if show_ignored:
                            print >> sys.stderr, (
                                "Directory %s ignored by pattern %s"
                                % (fn, pattern))
                        break
                if bad_name:
                    continue
                if (os.path.isfile(os.path.join(fn, "__init__.py"))
                    and not prefix):
                    if not package:
                        new_package = name
                    else:
                        new_package = package + "." + name
                    stack.append((fn, "", new_package, False))
                else:
                    stack.append((fn, prefix + name + "/", package, only_in_packages))
            elif package or not only_in_packages:
                # is a file
                bad_name = False
                for pattern in exclude:
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
                        bad_name = True
                        if show_ignored:
                            print >> sys.stderr, (
                                "File %s ignored by pattern %s"
                                % (fn, pattern))
                        break
                if bad_name:
                    continue
                out.setdefault(package, []).append(prefix+name)
    return out

setup(
    name = 'snf-cyclades-app',
    version = VERSION,
    license = 'BSD',
    url = 'http://www.synnefo.org/',
    description = SHORT_DESCRIPTION,
    classifiers = CLASSIFIERS,

    author='Synnefo development team',
    author_email='synnefo-devel@googlegroups.com',
    maintainer='Synnefo development team',
    maintainer_email='synnefo-devel@googlegroups.com',

    namespace_packages = ['synnefo', 'synnefo.versions'],
    packages = PACKAGES,
    package_dir= {'': PACKAGES_ROOT},
    include_package_data = True,
    package_data = find_package_data('.'),
    zip_safe = False,

    install_requires = INSTALL_REQUIRES,
    extras_require = EXTRAS_REQUIRES,
    tests_require = TESTS_REQUIRES,

    dependency_links = ['http://www.synnefo.org/packages/pypi'],

    entry_points = {
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
