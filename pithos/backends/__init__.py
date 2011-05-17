from django.conf import settings

from simple import SimpleBackend

backend = None
options = getattr(settings, 'BACKEND', None)
if options:
	c = globals()[options[0]]
	backend = c(*options[1])
