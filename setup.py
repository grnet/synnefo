#!/usr/bin/env python

import os

from setuptools import setup, find_packages
from pithos import get_version


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


VERSION = get_version().replace(' ', '')

INSTALL_REQUIRES = [
    'Django==1.2.3',
    'South==0.7',
    'httplib2==0.6.0',
    'SQLAlchemy==0.6.3',
    'MySQL-python==1.2.2',
    'psycopg2==2.2.1'
]

setup(
    name='Pithos',
    version=VERSION,
    description='Pithos file storage service and tools',
	long_description=read('README'),
    author='GRNET',
    author_email='pithos@grnet.gr',
    url='http://code.grnet.gr/projects/pithos',
    packages=find_packages(),
    #install_requires = INSTALL_REQUIRES,
    license='BSD',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
        'License :: OSI Approved :: BSD License',
    ],
    entry_points={
        'console_scripts': ['pithos-manage = pithos.manage:main']
    },
    scripts=[
        'pithos/tools/pithos-sh',
        'pithos/tools/pithos-sync',
        'pithos/tools/pithos-fs',
        'pithos/tools/pithos-test'
    ]
)
