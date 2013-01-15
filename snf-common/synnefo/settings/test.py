from synnefo.settings import *

DEBUG = True
TEST = True

DATABASES = {
    'default': {
        'ENGINE': 'sqlite3',
        'NAME': '/tmp/synnefo_test_db.sqlite',
    }
}

LOGGING_SETUP['handlers']['console']['level'] = 'WARNING'
LOGIN_URL = 'http://host:port/'
