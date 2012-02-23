from django.conf import settings
from os.path import abspath, dirname, join
from urlparse import urlparse

PROJECT_PATH = getattr(settings, 'PROJECT_PATH', dirname(dirname(abspath(__file__))))

# Set the expiration time of newly created auth tokens
# to be this many hours after their creation time.
AUTH_TOKEN_DURATION = getattr(settings, 'ASTAKOS_AUTH_TOKEN_DURATION', 30 * 24)

# Authenticate via Twitter.
TWITTER_KEY = getattr(settings, 'ASTAKOS_TWITTER_KEY', '')
TWITTER_SECRET = getattr(settings, 'ASTAKOS_TWITTER_SECRET', '')

DEFAULT_USER_LEVEL = getattr(settings, 'ASTAKOS_DEFAULT_USER_LEVEL', 4)

INVITATIONS_PER_LEVEL = getattr(settings, 'ASTAKOS_INVITATIONS_PER_LEVEL', {
    0   :   100,
    1   :   2,
    2   :   0,
    3   :   0,
    4   :   0
})

# Address to use for outgoing emails
DEFAULT_FROM_EMAIL = getattr(settings, 'ASTAKOS_DEFAULT_FROM_EMAIL', 'GRNET Cloud <no-reply@grnet.gr>')
DEFAULT_CONTACT_EMAIL = getattr(settings, 'ASTAKOS_DEFAULT_CONTACT_EMAIL', 'support@cloud.grnet.gr')

# Identity Management enabled modules
IM_MODULES = getattr(settings, 'ASTAKOS_IM_MODULES', ['local', 'twitter', 'shibboleth'])

# Force user profile verification
FORCE_PROFILE_UPDATE = getattr(settings, 'ASTAKOS_FORCE_PROFILE_UPDATE', True)

#Enable invitations
INVITATIONS_ENABLED = getattr(settings, 'ASTAKOS_INVITATIONS_ENABLED', True)

COOKIE_NAME = getattr(settings, 'ASTAKOS_COOKIE_NAME', '_pithos2_a')
COOKIE_DOMAIN = getattr(settings, 'ASTAKOS_COOKIE_DOMAIN', None)
COOKIE_SECURE = getattr(settings, 'ASTAKOS_COOKIE_SECURE', True)

IM_STATIC_URL = getattr(settings, 'ASTAKOS_IM_STATIC_URL', '/im/static/im/')

# If set to False and invitations not enabled newly created user will be automatically accepted
MODERATION_ENABLED = getattr(settings, 'ASTAKOS_MODERATION_ENABLED', True)

# Set baseurl
BASEURL = getattr(settings, 'ASTAKOS_BASEURL', 'http://pithos.dev.grnet.gr')

# Set service name
SITENAME = getattr(settings, 'ASTAKOS_SITENAME', 'GRNET Cloud')
