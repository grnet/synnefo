from os import environ
environ['COMMISSIONING_APP_NAME'] = 'quotaholder'

from commissioning.lib.django_server.settings import *

ROOT_URLCONF = 'quotaholder.servers.quotaholder_django.urls'

