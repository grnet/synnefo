# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from synnefo.webproject.settings.default import *

from synnefo.util.entry_points import extend_list_from_entry_point, \
        extend_dict_from_entry_point


# Provide common django settings and extend them from entry_point hooks
INSTALLED_APPS = (
    'django.contrib.contenttypes',
    #'django.contrib.sessions',
    'django.contrib.sites',
    #'django.contrib.messages',
    'south',
    'synnefo.webproject'
)
INSTALLED_APPS = extend_list_from_entry_point(INSTALLED_APPS, 'synnefo', \
        'web_apps')

DATABASE_ROUTERS = []
DATABASE_ROUTERS = extend_list_from_entry_point(DATABASE_ROUTERS, 'synnefo', \
        'db_routers')

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media'
)
TEMPLATE_CONTEXT_PROCESSORS = extend_list_from_entry_point(
        TEMPLATE_CONTEXT_PROCESSORS, 'synnefo', 'web_context_processors')


MIDDLEWARE_CLASSES = (
    #'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    'synnefo.webproject.middleware.LoggingConfigMiddleware',
)
MIDDLEWARE_CLASSES = extend_list_from_entry_point(MIDDLEWARE_CLASSES, \
        'synnefo', 'web_middleware')


STATIC_FILES = extend_dict_from_entry_point(STATIC_FILES, 'synnefo', \
        'web_static')


LOGGING_SETUP['loggers'] = \
        extend_dict_from_entry_point(LOGGING_SETUP['loggers'], 'synnefo', \
                'loggers')
