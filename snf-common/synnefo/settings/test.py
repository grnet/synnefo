import os

os.umask(0o007)

from synnefo.settings import *

DEBUG = False
TEMPLATE_DEBUG = False
TEST = True

BACKEND_DB_CONNECTION = 'sqlite:////tmp/synnefo_backend_db.sqlite'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/synnefo_test_db.sqlite',
        'TEST': {
            'NAME': '/tmp/synnefo_test_db.sqlite',
        },
    }
}

LOGGING_SETUP['handlers']['console']['level'] = \
    os.environ.get('SYNNEFO_TESTS_LOGGING_LEVEL', 'INFO')

LOGIN_URL = 'http://host:port/'


SNF_TEST_USE_POSTGRES = bool(int(os.environ.get('SNF_TEST_USE_POSTGRES',
                                                True)))
SNF_TEST_PITHOS_UPDATE_MD5 = bool(int(os.environ.get(
    'SNF_TEST_PITHOS_UPDATE_MD5', False)))
SNF_TEST_PITHOS_SQLITE_MODULE = bool(int(os.environ.get(
    'SNF_TEST_PITHOS_SQLITE_MODULE', False)))
PASSWORD_HASHERS = (
    os.environ.get('SNF_TEST_PASSWORD_HASHERS',
                   'django.contrib.auth.hashers.MD5PasswordHasher'),
)

# override default database
if SNF_TEST_USE_POSTGRES:
    NAME = os.environ.get('SNF_TEST_DB_NAME', 'snf_apps')
    TEST_NAME = 'test_' + NAME
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': NAME,
        'TEST': {
            'NAME': os.environ.get('SNF_TEST_DB_TEST_NAME', TEST_NAME),
        },
        'USER': os.environ.get('SNF_TEST_DB_USER', 'postgres'),
        'HOST': os.environ.get('SNF_TEST_DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('SNF_TEST_DB_PORT', '5432'),
    }
    password = os.environ.get('SNF_TEST_DB_PASSWORD', None)
    if password is not None:
        DATABASES['default']['PASSWORD'] = password
elif SNF_TEST_PITHOS_SQLITE_MODULE:
    PITHOS_BACKEND_POOL_ENABLED = False
    PITHOS_BACKEND_DB_MODULE = 'pithos.backends.lib.sqlite'

if SNF_TEST_PITHOS_UPDATE_MD5:
    PITHOS_UPDATE_MD5 = True
else:
    PITHOS_UPDATE_MD5 = False


ASTAKOS_IM_MODULES = ['local', 'shibboleth']


ASTAKOS_BASE_URL = 'http://accounts.example.synnefo.org/astakos/'
ASTAKOS_AUTH_URL = 'http://accounts.example.synnefo.org/astakos/identity/v2.0'
COMPUTE_BASE_URL = 'http://compute.example.synnefo.org/cyclades/'
PITHOS_BASE_URL = 'http://storage.example.synnefo.org/pithos/'

CLOUDBAR_LOCATION = '/static/im/cloudbar/'
CLOUDBAR_SERVICES_URL = '/ui/get_services'
CLOUDBAR_MENU_URL = '/ui/get_menu'

try:
    from pithos.api.test import PithosTestSuiteRunner
    TEST_RUNNER = 'pithos.api.test.PithosTestSuiteRunner'
except ImportError:
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

CYCLADES_VOLUME_MAX_SIZE = 100000

INSTALLED_APPS.append('django_nose')
