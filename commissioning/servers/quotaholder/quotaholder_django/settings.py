from os import environ
environ['COMMISSIONING_APP_NAME'] = 'quotaholder'

from commissioning.servers.django_server.settings import *

ROOT_URLCONF = 'commissioning.servers.quotaholder.quotaholder_django.urls'

