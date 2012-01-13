#!/usr/bin/env python

import os

from setuptools import setup
from synnefo.util.version import update_version

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))
update_version('synnefo.versions', 'ganeti', HERE)
from synnefo.versions.ganeti import __version__

setup(
    name="snf-ganeti-tools",
    version=__version__,
    description="Synnefo Ganeti supplementary tools",
    author="Synnefo Development Team",
    author_email="synnefo@lists.grnet.gr",
    license="BSD",
    url="http://code.grnet.gr/projects/synnefo",
    namespace_packages=["synnefo", "synnefo.versions"],
    packages=["synnefo", "synnefo.ganeti", "synnefo.versions"],
    install_requires=[
        'daemon',
        'pyinotify',
        'amqplib',
        'prctl',
    ],
    entry_points = {
     'console_scripts': [
         'snf-ganeti-eventd = synnefo.ganeti.eventd:main',
         'snf-ganeti-hook = synnefo.ganeti.hook:main',
         'snf-progress-monitor = synnefo.ganeti.progress_monitor:main'
         ],
     },
)
