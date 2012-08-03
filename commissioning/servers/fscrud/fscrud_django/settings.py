from os import environ
environ['COMMISSIONING_APP_NAME'] = 'fscrud'

from commissioning.servers.django_server.settings import *

ROOT_URLCONF = 'commissioning.servers.fscrud.fscrud_django.urls'

