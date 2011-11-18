import os

from setuptools import setup, find_packages

HERE = os.path.abspath(os.path.normpath(os.path.dirname(__file__)))

# Package info
VERSION = '0.1'
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

PACKAGE_DATA = {
    '': ['templates/*.html', 'fixtures/*.json',
         'templates/*.xml', 'templates/partials/*.html',
         'templates/userdata/*.html'],

    'synnefo': ['settings.d/*.conf']
}

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
    package_data = PACKAGE_DATA,
    zip_safe = False,

    install_requires = INSTALL_REQUIRES,
    extras_require = EXTRAS_REQUIRES,
    tests_require = TESTS_REQUIRES,

    entry_points = {
     'console_scripts': [
         'synnefo-manage = synnefo.manage:main',
         'synnefo-dispatcher = synnefo.logic.dispatcher:scriptmain',
         'synnefo-burnin = synnefo.tools.burnin:main',
         'synnefo-admin = synnefo.tools.admin:main',
         'synnefo-cloud = synnefo.tools.cloud:main',
         ],
      },
    )

