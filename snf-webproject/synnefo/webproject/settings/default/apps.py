# -*- coding: utf-8 -*-

# Core Django project settings
##################################

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

# This is a django project setting, do not change this unless you know
# what you're doing
ROOT_URLCONF = 'synnefo.webproject.urls'

# Additional template dirs.
TEMPLATE_DIRS = (
    '/etc/synnefo/templates/'
)

LANGUAGES = (
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

