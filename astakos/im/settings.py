from django.conf import settings
from os.path import abspath, dirname, join

PROJECT_PATH = getattr(settings, 'PROJECT_PATH', dirname(dirname(abspath(__file__))))

# Set the expiration time of newly created auth tokens
# to be this many hours after their creation time.
AUTH_TOKEN_DURATION = getattr(settings, 'ASTAKOS_AUTH_TOKEN_DURATION', 30 * 24)

# Bypass authentication for user administration.
BYPASS_ADMIN_AUTH = getattr(settings, 'ASTAKOS_BYPASS_ADMIN_AUTH', False)

# Show these many users per page in admin interface.
ADMIN_PAGE_LIMIT = getattr(settings, 'ASTAKOS_ADMIN_PAGE_LIMIT', 100)

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
DEFAULT_FROM_EMAIL = getattr(settings, 'ASTAKOS_DEFAULT_FROM_EMAIL', '%s <no-reply@grnet.gr>')
DEFAULT_CONTACT_EMAIL = getattr(settings, 'ASTAKOS_DEFAULT_CONTACT_EMAIL', 'support@%s.grnet.gr')

# Identity Management enabled modules
IM_MODULES = getattr(settings, 'ASTAKOS_IM_MODULES', ['local', 'twitter', 'shibboleth'])

# Force user profile verification
FORCE_PROFILE_UPDATE = getattr(settings, 'ASTAKOS_FORCE_PROFILE_UPDATE', True)

#Enable invitations
INVITATIONS_ENABLED = getattr(settings, 'ASTAKOS_INVITATIONS_ENABLED', True)

COOKIE_NAME = getattr(settings, 'ASTAKOS_COOKIE_NAME', '_pithos2_a')
COOKIE_DOMAIN = getattr(settings, 'ASTAKOS_COOKIE_DOMAIN', None)

IM_STATIC_URL = getattr(settings, 'ASTAKOS_IM_STATIC_URL', '/im/static/im/')

# If set to False and invitations not enabled newly created user will be automatically accepted
MODERATION_ENABLED = getattr(settings, 'ASTAKOS_MODERATION_ENABLED', True)

# SQLAlchemy (choose SQLite/MySQL/PostgreSQL).
BACKEND_DB_MODULE =  getattr(settings, 'PITHOS_BACKEND_DB_MODULE', 'pithos.backends.lib.sqlalchemy')
BACKEND_DB_CONNECTION = getattr(settings, 'PITHOS_BACKEND_DB_CONNECTION', 'sqlite:///' + join(PROJECT_PATH, 'backend.db'))

# Block storage.
BACKEND_BLOCK_MODULE = getattr(settings, 'PITHOS_BACKEND_BLOCK_MODULE', 'pithos.backends.lib.hashfiler')
BACKEND_BLOCK_PATH = getattr(settings, 'PITHOS_BACKEND_BLOCK_PATH', join(PROJECT_PATH, 'data/'))

# Default setting for new accounts.
BACKEND_QUOTA = getattr(settings, 'PITHOS_BACKEND_QUOTA', 50 * 1024 * 1024 * 1024)
BACKEND_VERSIONING = getattr(settings, 'PITHOS_BACKEND_VERSIONING', 'auto')

