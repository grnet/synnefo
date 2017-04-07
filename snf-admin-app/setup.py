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

"""Packaging module for snf-admin-app"""

import os
import sys

from imp import load_source
from setuptools import setup, find_packages

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
    'Django>=1.7, <1.8',
    'snf-django-lib',
    'django-filter',
    'django-eztables',
    'pycrypto>=2.1.0',
]

BUILD_TRIGGERING_COMMANDS = ["sdist", "build", "develop", "install"]


def compile_sass():
    """Compiles sass files to css"""
    import sass

    static_dir = os.path.join(".", "synnefo_admin", "admin", "static")
    sass_dir = os.path.join(static_dir, "sass")
    css_dir = os.path.join(static_dir, "css")

    output_style = "nested" if "develop" in sys.argv else "compressed"
    try:
        sass.compile(dirname=(sass_dir, css_dir,), output_style=output_style)
    except Exception as e:
        print(e)
        raise Exception('Sass compile failed')


if any(x in sys.argv for x in BUILD_TRIGGERING_COMMANDS):
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
