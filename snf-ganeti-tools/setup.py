#!/usr/bin/env python

from setuptools import setup
from synnefo.version import vcs_version

setup(
    name="snf-ganeti-tools",
    version=vcs_version(),
    description="Synnefo Ganeti supplementary tools",
    author="Synnefo Development Team",
    author_email="synnefo@lists.grnet.gr",
    license="BSD",
    url="http://code.grnet.gr/projects/synnefo",
    namespace_packages=["synnefo"],
    packages=["synnefo", "synnefo.ganeti"],
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
