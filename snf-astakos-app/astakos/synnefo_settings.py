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
#

"""
Django settings metadata. To be used in setup.py snf-webproject entry points.
"""

installed_apps = [
    {'before': 'django.contrib.admin',
     'insert': 'astakos.im', },
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django_tables2',
    'astakos.quotaholder_app',
    'synnefo_branding',
    'astakos.oa2',
]

context_processors = [
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.csrf',
    'django.contrib.messages.context_processors.messages',
    'astakos.im.context_processors.media',
    'astakos.im.context_processors.im_modules',
    'astakos.im.context_processors.auth_providers',
    'astakos.im.context_processors.next',
    'astakos.im.context_processors.code',
    'astakos.im.context_processors.invitations',
    'astakos.im.context_processors.menu',
    'astakos.im.context_processors.custom_messages',
    'astakos.im.context_processors.last_login_method',
    'astakos.im.context_processors.membership_policies',
    'synnefo.webproject.context_processors.cloudbar'
]

middlware_classes = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'synnefo.webproject.middleware.LoggingConfigMiddleware',
    'synnefo.webproject.middleware.SecureMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
]

static_files = {'astakos.im': ''}

# The following settings will replace the default django settings
AUTHENTICATION_BACKENDS = (
    'astakos.im.auth_backends.EmailBackend',
    'astakos.im.auth_backends.TokenBackend')

CUSTOM_USER_MODEL = 'astakos.im.AstakosUser'

#SOUTH_TESTS_MIGRATE = False

BROKER_URL = ''

# INTERNAL_IPS = ('127.0.0.1',)
