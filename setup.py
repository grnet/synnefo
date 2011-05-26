#!/usr/bin/env python

#from distutils.core import setup
from setuptools import setup

from pithos import __version__ as version

setup(
    name='Pithos',
    version=version,
    description='Pithos file storage service',
    author='GRNET',
    author_email='pithos@grnet.gr',
    url='http://code.grnet.gr/projects/pithos',
    packages=['pithos'],
)
