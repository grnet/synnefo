#!/usr/bin/env python

from setuptools import setup

setup(
    name="snf-ganeti-tools",
    version="0.7",
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
        'ganeti',
    ],
    scripts=['snf-ganeti-eventd.py', 'snf-ganeti-hook.py',
             'snf-progress-monitor.py'],
)
