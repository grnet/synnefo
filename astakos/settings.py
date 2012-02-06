# Django settings for astakos project.

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
        'NAME': join(PROJECT_PATH, 'astakos.db')
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
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'astakos.middleware.LoggingConfigMiddleware',
    'astakos.middleware.SecureMiddleware'
)

ROOT_URLCONF = 'astakos.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    join(PROJECT_PATH, 'im/admin/templates/')
)

conf = join(PROJECT_PATH, 'settings.local')

if exists(conf):
    execfile(conf)
elif exists('/etc/astakos/settings.local'):
    execfile('/etc/astakos/settings.local')

INSTALLED_APPS = (
    'astakos.im',
    'south',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.sessions'
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.messages.context_processors.messages',
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'astakos.im.context_processors.media',
    'astakos.im.context_processors.im_modules',
    'astakos.im.context_processors.next',
    'astakos.im.context_processors.code',
    'astakos.im.context_processors.invitations')

AUTHENTICATION_BACKENDS = ('astakos.im.auth_backends.EmailBackend',
                            'astakos.im.auth_backends.TokenBackend')

CUSTOM_USER_MODEL = 'astakos.im.AstakosUser'

# Use to log to a file.
LOGFILE = None

# The server is behind a proxy (apache and gunicorn setup).
USE_X_FORWARDED_HOST = False

# Set umask (needed for gunicorn setup).
#umask(0077)