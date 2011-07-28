import os, sys
sys.path.append('/pithos')
os.environ['DJANGO_SETTINGS_MODULE'] = 'pithos.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
