# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.
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
    'djcelery',
    'debug_toolbar',
]

context_processors = [
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.csrf',
    'astakos.im.context_processors.media',
    'astakos.im.context_processors.im_modules',
    'astakos.im.context_processors.next',
    'astakos.im.context_processors.code',
    'astakos.im.context_processors.invitations',
    'astakos.im.context_processors.menu',
    'astakos.im.context_processors.custom_messages',
    'astakos.im.context_processors.group_kinds',
    'synnefo.lib.context_processors.cloudbar'
]

middlware_classes = [
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'astakos.im.middleware.CookieAuthenticationMiddleware',
    'synnefo.lib.middleware.LoggingConfigMiddleware',
    'synnefo.lib.middleware.SecureMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

loggers = {
    'astakos': {
        'handlers': ['console'],
        'level': 'INFO'
    }
}

static_files = {'astakos.im': ''}

# The following settings will replace the default django settings
AUTHENTICATION_BACKENDS = ('astakos.im.auth_backends.EmailBackend',
                           'astakos.im.auth_backends.TokenBackend')
LOGIN_URL = '/im'

CUSTOM_USER_MODEL = 'astakos.im.AstakosUser'

#SOUTH_TESTS_MIGRATE = False

import djcelery
djcelery.setup_loader()

BROKER_URL = ''

# INTERNAL_IPS = ('127.0.0.1',)