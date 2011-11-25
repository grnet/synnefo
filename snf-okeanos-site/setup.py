import distribute_setup
distribute_setup.use_setuptools()

import os
from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))

# Package info
VERSION = "0.8"
README = open(os.path.join(HERE, 'README')).read()
CHANGES = open(os.path.join(HERE, 'Changelog')).read()
SHORT_DESCRIPTION = 'Package short description'

PACKAGES_ROOT = '.'
PACKAGES = find_packages(PACKAGES_ROOT)

# Package meta
CLASSIFIERS = []

# Package requirements
INSTALL_REQUIRES = [
    'synnefo==0.8'
]

TESTS_REQUIRES = [
]

PACKAGE_DATA = {
    '': ['templates/*.html', 'fixtures/*.json',
         'templates/*.xml', 'templates/partials/*.html',
         'templates/*.txt', 'templates/userdata/*.html'],
}

setup(
    name = 'okeanos-web',
    version = VERSION,
    license = 'BSD',
    url = 'http://code.grnet.gr/',
    description = SHORT_DESCRIPTION,
    long_description=README + '\n\n' +  CHANGES,
    classifiers = CLASSIFIERS,

    author = 'GRNet',
    author_email = 'info@grnet.gr',
    maintainer = 'Kostas Papadimitriou',
    maintainer_email = 'kpap@grnet.gr',

    packages = PACKAGES,
    package_dir= {'': PACKAGES_ROOT},
    include_package_data = True,
    package_data = PACKAGE_DATA,
    zip_safe = False,

    install_requires = INSTALL_REQUIRES,
)

