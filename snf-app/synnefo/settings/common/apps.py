# -*- coding: utf-8 -*-
#
# Core Django settings
##################################

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'synnefo.aai',
    'synnefo.admin',
    'synnefo.api',
    'synnefo.ui',
    'synnefo.db',
    'synnefo.logic',
    'synnefo.invitations',
    'synnefo.helpdesk',
    'synnefo.plankton',
    'synnefo.ui.userdata',
    'south'
)

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.core.context_processors.i18n',
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.media'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'synnefo.aai.middleware.SynnefoAuthMiddleware',
    'synnefo.api.middleware.ApiAuthMiddleware',
    'synnefo.helpdesk.middleware.HelpdeskMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware'
)

ROOT_URLCONF = 'synnefo.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates"
    # or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

LANGUAGES = (
  #('el', u'Ελληνικά'),
  ('en', 'English'),
)

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'UTC'   # Warning: The API depends on the TIME_ZONE being UTC

