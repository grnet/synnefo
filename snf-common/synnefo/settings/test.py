import os
os.environ['SYNNEFO_SETTINGS_DIR'] = '/etc/synnefo-test-settings'

from synnefo.settings import *

DEBUG = False
TEST = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/synnefo_test_db.sqlite',
    }
}

LOGGING_SETUP['handlers']['console']['level'] = \
    os.environ.get('SYNNEFO_TESTS_LOGGING_LEVEL', 'WARNING')

LOGIN_URL = 'http://host:port/'


SOUTH_TESTS_MIGRATE = bool(int(os.environ.get('SOUTH_TESTS_MIGRATE', True)))
SNF_TEST_USE_POSTGRES = bool(int(os.environ.get('SNF_TEST_USE_POSTGRES',
                                                False)))

# override default database
if SNF_TEST_USE_POSTGRES:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'pithos',
        'TEST_NAME': 'test_pithos',
        'USER': 'postgres',
        'PORT': '5432',
    }

ASTAKOS_IM_MODULES = ['local', 'shibboleth']

CYCLADES_PROXY_USER_SERVICES = False
PITHOS_PROXY_USER_SERVICES = False

ASTAKOS_BASE_URL = 'http://accounts.example.synnefo.org/astakos/'
COMPUTE_BASE_URL = 'http://compute.example.synnefo.org/cyclades/'
PITHOS_BASE_URL = 'http://storage.example.synnefo.org/pithos/'

CLOUDBAR_LOCATION = '/static/im/cloudbar/'
CLOUDBAR_SERVICES_URL = '/ui/get_services'
CLOUDBAR_MENU_URL = '/ui/get_menu'
