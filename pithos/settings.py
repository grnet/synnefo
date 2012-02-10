#coding=utf8
# Django settings for pithos project.

from os.path import abspath, dirname, exists, join

PROJECT_PATH = dirname(abspath(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': join(PROJECT_PATH, 'pithos.db')
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '$j0cdrfm*0sc2j+e@@2f-&3-_@2=^!z#+b-8o4_i10@2%ev7si'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    #'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    'pithos.middleware.LoggingConfigMiddleware',
    'pithos.middleware.SecureMiddleware',
    'pithos.middleware.UserMiddleware'
)

ROOT_URLCONF = 'pithos.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# Setup logging (use this name for the setting to avoid conflicts with django > 1.2.x).
LOGGING_SETUP = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'simple': {
            'format': '%(message)s'
        },
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(name)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'pithos': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO'
        },
    }
}

# The server is behind a proxy (apache and gunicorn setup).
USE_X_FORWARDED_HOST = False

# Set umask (needed for gunicorn setup).
#umask(0077)

# Either set local users here, or a remote host.
# To disable local users set to None.
AUTHENTICATION_USERS = {
    '0000': 'test',
    '0001': 'verigak',
    '0002': 'chazapis',
    '0003': 'gtsouk',
    '0004': 'papagian',
    '0005': 'louridas',
    '0006': 'chstath',
    '0007': 'pkanavos',
    '0008': 'mvasilak',
    '0009': 'διογένης'
}

# Where astakos is hosted.
AUTHENTICATION_HOST = '127.0.0.1:10000'

conf = join(PROJECT_PATH, 'settings.local')
if exists(conf):
    execfile(conf)
elif exists('/etc/pithos/settings.local'):
    execfile('/etc/pithos/settings.local')

INSTALLED_APPS = (
    'pithos.api',
)
