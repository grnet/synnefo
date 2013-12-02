# Patch hard-coded 'django.views.debug.HIDDEN_SETTINGS' to the list of Synnefo
# HIDDEN_SETTINGS
import re

from django.views import debug
from django.conf import settings

debug.HIDDEN_SETTINGS = re.compile(settings.HIDDEN_SETTINGS)
