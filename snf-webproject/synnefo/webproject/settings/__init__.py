# Copyright 2011 GRNET S.A. All rights reserved.
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

from synnefo.webproject.settings.default import *

from synnefo.util.entry_points import extend_list_from_entry_point, \
        extend_dict_from_entry_point


# Provide common django settings and extend them from entry_point hooks
INSTALLED_APPS = (
    'django.contrib.contenttypes',
    #'django.contrib.sessions',
    'django.contrib.sites',
    #'django.contrib.messages',
    'django.contrib.admin',
    'south',
    'synnefo.webproject'
)
INSTALLED_APPS = extend_list_from_entry_point(INSTALLED_APPS, 'synnefo', \
        'web_apps')


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
    'synnefo.webproject.middleware.CleanseSettingsMiddleware'
)
MIDDLEWARE_CLASSES = extend_list_from_entry_point(MIDDLEWARE_CLASSES, \
        'synnefo', 'web_middleware')


STATIC_FILES = extend_dict_from_entry_point(STATIC_FILES, 'synnefo', \
        'web_static')


LOGGING_SETUP['loggers'] = \
        extend_dict_from_entry_point(LOGGING_SETUP['loggers'], 'synnefo', \
                'loggers')
