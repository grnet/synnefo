import distribute_setup
distribute_setup.use_setuptools()

import os

from distutils.util import convert_path
from fnmatch import fnmatchcase
from setuptools import setup, find_packages
from synnefo import get_version

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))

# Package info
VERSION = get_version().replace(" ","")
README = open(os.path.join(HERE, 'README')).read()
CHANGES = open(os.path.join(HERE, 'Changelog')).read()
SHORT_DESCRIPTION = 'Package short description'

PACKAGES_ROOT = '.'
PACKAGES = find_packages(PACKAGES_ROOT, exclude=['okeanos_site'])

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
    'Django==1.2.4',
    'simplejson==2.1.3',
    'pycurl==7.19.0',
    'python-dateutil==1.4.1',
    'IPy==0.75',
    'south==0.7.1',
    'pycrypto==2.1.0',
    'amqplib==0.6.1',
    'python-daemon==1.5.5'
]

EXTRAS_REQUIRES = {
        'DISPATCHER': ['amqplib==0.6.1', 'python-daemon==1.5.5',],
        'INVITATIONS': ['pycrypto==2.1.0'],
        'SSH_KEYS': ['pycrypto==2.1.0'],
        'BURNIN': ['unittest2==0.5.1', 'paramiko==1.7.6', 'python-prctl==1.3.0']
}

TESTS_REQUIRES = [
]


# Provided as an attribute, so you can append to these instead
# of replicating them:
standard_exclude = ["*.py", "*.pyc", "*$py.class", "*~", ".*", "*.bak"]
standard_exclude_directories = [
    ".*", "CVS", "_darcs", "./build", "./dist", "EGG-INFO", "*.egg-info", "snf-0.7"
]

# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# Note: you may want to copy this into your setup.py file verbatim, as
# you can't import this from another package, when you don't know if
# that package is installed yet.
def find_package_data(
    where=".",
    package="",
    exclude=standard_exclude,
    exclude_directories=standard_exclude_directories,
    only_in_packages=True,
    show_ignored=False):
    """
    Return a dictionary suitable for use in ``package_data``
    in a distutils ``setup.py`` file.

    The dictionary looks like::

        {"package": [files]}

    Where ``files`` is a list of all the files in that package that
    don"t match anything in ``exclude``.

    If ``only_in_packages`` is true, then top-level directories that
    are not packages won"t be included (but directories under packages
    will).

    Directories matching any pattern in ``exclude_directories`` will
    be ignored; by default directories with leading ``.``, ``CVS``,
    and ``_darcs`` will be ignored.

    If ``show_ignored`` is true, then all the files that aren"t
    included in package data are shown on stderr (for debugging
    purposes).

    Note patterns use wildcards, or can be exact paths (including
    leading ``./``), and all searching is case-insensitive.
    """
    out = {}
    stack = [(convert_path(where), "", package, only_in_packages)]
    while stack:
        where, prefix, package, only_in_packages = stack.pop(0)
        for name in os.listdir(where):
            fn = os.path.join(where, name)
            if os.path.isdir(fn):
                bad_name = False
                for pattern in exclude_directories:
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
                        bad_name = True
                        if show_ignored:
                            print >> sys.stderr, (
                                "Directory %s ignored by pattern %s"
                                % (fn, pattern))
                        break
                if bad_name:
                    continue
                if (os.path.isfile(os.path.join(fn, "__init__.py"))
                    and not prefix):
                    if not package:
                        new_package = name
                    else:
                        new_package = package + "." + name
                    stack.append((fn, "", new_package, False))
                else:
                    stack.append((fn, prefix + name + "/", package, only_in_packages))
            elif package or not only_in_packages:
                # is a file
                bad_name = False
                for pattern in exclude:
                    if (fnmatchcase(name, pattern)
                        or fn.lower() == pattern.lower()):
                        bad_name = True
                        if show_ignored:
                            print >> sys.stderr, (
                                "File %s ignored by pattern %s"
                                % (fn, pattern))
                        break
                if bad_name:
                    continue
                out.setdefault(package, []).append(prefix+name)
    return out

setup(
    name = 'synnefo',
    version = VERSION,
    license = 'BSD',
    url = 'http://code.grnet.gr/',
    description = SHORT_DESCRIPTION,
    long_description=README + '\n\n' +  CHANGES,
    classifiers = CLASSIFIERS,

    author = 'Package author',
    author_email = 'author@grnet.gr',
    maintainer = 'Package maintainer',
    maintainer_email = 'maintainer@grnet.gr',

    packages = PACKAGES,
    package_dir= {'': PACKAGES_ROOT},
    include_package_data = True,
    package_data = find_package_data('.'),
    zip_safe = False,

    install_requires = INSTALL_REQUIRES,
    extras_require = EXTRAS_REQUIRES,
    tests_require = TESTS_REQUIRES,

    entry_points = {
     'console_scripts': [
         'snf-manage = synnefo.manage:main',
         'snf-dispatcher = synnefo.logic.dispatcher:scriptmain',
         'snf-burnin = synnefo.tools.burnin:main',
         'snf-admin = synnefo.tools.admin:main',
         'snf-cloud = synnefo.tools.cloud:main',
         ],
      },
    )

