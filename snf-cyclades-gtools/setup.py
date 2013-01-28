#!/usr/bin/env python
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

import os

from setuptools import setup

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))

try:
    # try to update the version file
    from synnefo.util.version import update_version
    update_version('synnefo.versions', 'ganeti', HERE)
except ImportError:
    pass

from synnefo.versions.ganeti import __version__

setup(
    name="snf-cyclades-gtools",
    version=__version__,
    description="Synnefo Ganeti supplementary tools",
    author="Synnefo Development Team",
    author_email="synnefo@lists.grnet.gr",
    license="BSD",
    url="http://code.grnet.gr/projects/synnefo",
    namespace_packages=["synnefo", "synnefo.versions"],
    packages=["synnefo", "synnefo.ganeti", "synnefo.versions"],
    dependency_links = ['http://docs.dev.grnet.gr/pypi'],
    install_requires=[
        'snf-common',
        'python-daemon>=1.5.5',
        'pyinotify>=0.8.9',
        'puka',
        'python-prctl>=1.1.1',
        'setproctitle>=1.0.1'
    ],
    entry_points = {
     'console_scripts': [
         'snf-ganeti-eventd = synnefo.ganeti.eventd:main',
         'snf-ganeti-hook = synnefo.ganeti.hook:main',
         'snf-progress-monitor = synnefo.ganeti.progress_monitor:main'
         ],
     'synnefo': [
            'default_settings = synnefo.ganeti.settings'
         ]
     },
)
