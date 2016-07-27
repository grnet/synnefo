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

import os
import sys

from setuptools import setup, find_packages
from fnmatch import fnmatchcase
from distutils.util import convert_path
from imp import load_source

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))
VERSION_PY = os.path.join('synnefo_admin', 'version.py')

os.chdir(HERE)

# Package info
VERSION = getattr(load_source("VERSION", VERSION_PY), '__version__')
SHORT_DESCRIPTION = 'Synnefo Admin component'

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
    'Django>=1.4, <1.5',
    'snf-django-lib',
    'django-filter',
    'django-eztables',
    'pycrypto>=2.1.0',
]

trigger_build = ["sdist", "build", "develop", "install"]


def compile_sass():
    import subprocess
    from distutils.spawn import find_executable

    css_dir = os.path.join(".", "synnefo_admin", "admin", "static")
    css_dir = os.path.abspath(css_dir)

    if not find_executable("gem"):
        raise Exception("gem not found, please install ruby and gem")

    os.environ["PATH"] += ":/usr/local/bin"
    if not find_executable("compass"):
        print "Install compass"
        ret = subprocess.call(["gem", "install", "compass"])
        if ret == 1:
            raise Exception("gem install failed")

    environment = "development" if "develop" in sys.argv else "production"
    compass_bin = find_executable("compass")
    compass_cmd = [compass_bin, "compile", css_dir,
                   "-e", environment, "--force"]
    ret = subprocess.call(compass_cmd)
    if ret == 1:
        raise Exception("compass compile failed")


if any(x in sys.argv for x in trigger_build):
    if os.environ.get('SNFADMIN_AUTO_COMPILE', True) not in \
            ['False', 'false', '0']:
        compile_sass()


setup(
    name='snf-admin-app',
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
            'default_settings = synnefo_admin.app_settings.default',
            'web_apps = synnefo_admin.app_settings:installed_apps',
            'web_middleware = synnefo_admin.app_settings:middleware_classes',
            'urls = synnefo_admin.urls:urlpatterns',
            'web_static = synnefo_admin.app_settings:static_files'
        ]
    },
)
