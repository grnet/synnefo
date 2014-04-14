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

import os

from setuptools import setup

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))

from synnefo.versions.ganeti import __version__

setup(
    name="snf-cyclades-gtools",
    version=__version__,
    description="Synnefo tools for interaction with Ganeti",

    url="http://www.synnefo.org/",
    author='Synnefo development team',
    author_email='synnefo-devel@googlegroups.com',
    maintainer='Synnefo development team',
    maintainer_email='synnefo-devel@googlegroups.com',

    license="BSD",
    namespace_packages=["synnefo", "synnefo.versions"],
    packages=["synnefo", "synnefo.ganeti", "synnefo.versions"],
    dependency_links=['http://www.synnefo.org/packages/pypi'],
    install_requires=[
        'snf-common',
        'python-daemon>=1.5.5',
        'pyinotify>=0.8.9',
        'puka',
        'setproctitle>=1.0.1'
    ],
    entry_points={
        'console_scripts': [
            'snf-ganeti-eventd = synnefo.ganeti.eventd:main',
            'snf-progress-monitor = synnefo.ganeti.progress_monitor:main'
        ],
        'synnefo': [
            'default_settings = synnefo.ganeti.settings'
        ]
    },
)
