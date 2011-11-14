#!/usr/bin/env python

import os

from setuptools import setup, find_packages

VERSION = os.popen("git describe --abbrev=0 --tags").read().strip(' \nv')

setup(
    name='Pithos Tools',
    version=VERSION,
    description='Pithos file storage service tools',
    author='GRNET',
    author_email='pithos@grnet.gr',
    url='http://code.grnet.gr/projects/pithos',
    scripts=['pithos-sh', 'pithos-sync', 'pithos-fs'],
    packages=['lib'],
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
        'License :: OSI Approved :: BSD License',
    ]
)
