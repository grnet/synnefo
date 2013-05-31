from django.conf import settings
from synnefo_branding import settings as synnefo_settings
from synnefo.lib import parse_base_url
from astakosclient import astakos_services as vanilla_astakos_services
from synnefo.util.keypath import get_path
from synnefo.lib import join_urls
from synnefo.lib.services import fill_endpoints

from copy import deepcopy


BASE_URL = getattr(settings, 'ASTAKOS_BASE_URL',
                   'https://accounts.example.synnefo.org')


BASE_HOST, BASE_PATH = parse_base_url(BASE_URL)

astakos_services = deepcopy(vanilla_astakos_services)
fill_endpoints(astakos_services, BASE_URL)
ACCOUNTS_PREFIX = get_path(astakos_services, 'astakos_account.prefix')
VIEWS_PREFIX = get_path(astakos_services, 'astakos_ui.prefix')
KEYSTONE_PREFIX = get_path(astakos_services, 'astakos_keystone.prefix')

# Set the expiration time of newly created auth tokens
# to be this many hours after their creation time.
AUTH_TOKEN_DURATION = getattr(settings, 'ASTAKOS_AUTH_TOKEN_DURATION', 30 * 24)

DEFAULT_USER_LEVEL = getattr(settings, 'ASTAKOS_DEFAULT_USER_LEVEL', 4)

INVITATIONS_PER_LEVEL = getattr(settings, 'ASTAKOS_INVITATIONS_PER_LEVEL', {
    0: 100,
    1: 2,
    2: 0,
    3: 0,
    4: 0
})

ADMINS = tuple(getattr(settings, 'ADMINS', ()))
MANAGERS = tuple(getattr(settings, 'MANAGERS', ()))
HELPDESK = tuple(getattr(settings, 'HELPDESK', ()))

CONTACT_EMAIL = settings.CONTACT_EMAIL
SERVER_EMAIL = settings.SERVER_EMAIL
SECRET_KEY = settings.SECRET_KEY
SESSION_ENGINE = settings.SESSION_ENGINE

# Identity Management enabled modules
# Supported modules are: 'local', 'twitter' and 'shibboleth'
IM_MODULES = getattr(settings, 'ASTAKOS_IM_MODULES', ['local'])

# Force user profile verification
FORCE_PROFILE_UPDATE = getattr(settings, 'ASTAKOS_FORCE_PROFILE_UPDATE', False)

#Enable invitations
INVITATIONS_ENABLED = getattr(settings, 'ASTAKOS_INVITATIONS_ENABLED', False)

COOKIE_NAME = getattr(settings, 'ASTAKOS_COOKIE_NAME', '_pithos2_a')
COOKIE_DOMAIN = getattr(settings, 'ASTAKOS_COOKIE_DOMAIN', None)
COOKIE_SECURE = getattr(settings, 'ASTAKOS_COOKIE_SECURE', True)

IM_STATIC_URL = getattr(settings, 'ASTAKOS_IM_STATIC_URL', '/static/im/')

# If set to False and invitations not enabled newly created user
# will be automatically accepted
MODERATION_ENABLED = getattr(settings, 'ASTAKOS_MODERATION_ENABLED', True)

# Set service name
SITENAME = getattr(settings, 'ASTAKOS_SITENAME', synnefo_settings.SERVICE_NAME)

# Set recaptcha keys
RECAPTCHA_PUBLIC_KEY = getattr(settings, 'ASTAKOS_RECAPTCHA_PUBLIC_KEY', '')
RECAPTCHA_PRIVATE_KEY = getattr(settings, 'ASTAKOS_RECAPTCHA_PRIVATE_KEY', '')
RECAPTCHA_OPTIONS = getattr(settings, 'ASTAKOS_RECAPTCHA_OPTIONS',
                            {'theme': 'custom', 'custom_theme_widget': 'okeanos_recaptcha'})
RECAPTCHA_USE_SSL = getattr(settings, 'ASTAKOS_RECAPTCHA_USE_SSL', True)
RECAPTCHA_ENABLED = getattr(settings, 'ASTAKOS_RECAPTCHA_ENABLED', False)

# Set where the user should be redirected after logout
LOGOUT_NEXT = getattr(settings, 'ASTAKOS_LOGOUT_NEXT', '')

# Set user email patterns that are automatically activated
RE_USER_EMAIL_PATTERNS = getattr(
    settings, 'ASTAKOS_RE_USER_EMAIL_PATTERNS', [])

# Messages to display on login page header
# e.g. {'warning': 'This warning message will be displayed on the top of login page'}
LOGIN_MESSAGES = getattr(settings, 'ASTAKOS_LOGIN_MESSAGES', [])

# Messages to display on login page header
# e.g. {'warning': 'This warning message will be displayed on the top of signup page'}
SIGNUP_MESSAGES = getattr(settings, 'ASTAKOS_SIGNUP_MESSAGES', [])

# Messages to display on login page header
# e.g. {'warning': 'This warning message will be displayed on the top of profile page'}
PROFILE_MESSAGES = getattr(settings, 'ASTAKOS_PROFILE_MESSAGES', [])

# Messages to display on all pages
# e.g. {'warning': 'This warning message will be displayed on the top of every page'}
GLOBAL_MESSAGES = getattr(settings, 'ASTAKOS_GLOBAL_MESSAGES', [])

# messages to display as extra actions in account forms
# e.g. {'https://www.myhomepage.com': 'Back to <service_name>'}
PROFILE_EXTRA_LINKS = getattr(settings, 'ASTAKOS_PROFILE_EXTRA_LINKS', {})

# The number of unsuccessful login requests per minute allowed for a specific user
RATELIMIT_RETRIES_ALLOWED = getattr(
    settings, 'ASTAKOS_RATELIMIT_RETRIES_ALLOWED', 3)

# If False the email change mechanism is disabled
EMAILCHANGE_ENABLED = getattr(settings, 'ASTAKOS_EMAILCHANGE_ENABLED', False)

# Set the expiration time (in days) of email change requests
EMAILCHANGE_ACTIVATION_DAYS = getattr(
    settings, 'ASTAKOS_EMAILCHANGE_ACTIVATION_DAYS', 10)

# Set the astakos main functions logging severity (None to disable)
from logging import INFO
LOGGING_LEVEL = getattr(settings, 'ASTAKOS_LOGGING_LEVEL', INFO)

# Set how many objects should be displayed per page
PAGINATE_BY = getattr(settings, 'ASTAKOS_PAGINATE_BY', 50)

# Set how many objects should be displayed per page in show all projects page
PAGINATE_BY_ALL = getattr(settings, 'ASTAKOS_PAGINATE_BY_ALL', 50)

# Enforce token renewal on password change/reset
NEWPASSWD_INVALIDATE_TOKEN = getattr(
    settings, 'ASTAKOS_NEWPASSWD_INVALIDATE_TOKEN', True)

USAGE_UPDATE_INTERVAL = getattr(settings, 'ASTAKOS_USAGE_UPDATE_INTERVAL', 5000)

# Permit local account migration
ENABLE_LOCAL_ACCOUNT_MIGRATION = getattr(settings, 'ASTAKOS_ENABLE_LOCAL_ACCOUNT_MIGRATION', True)

# Strict shibboleth usage
SHIBBOLETH_REQUIRE_NAME_INFO = getattr(settings,
                                       'ASTAKOS_SHIBBOLETH_REQUIRE_NAME_INFO',
                                       False)

default_redirect_url = join_urls(BASE_URL, VIEWS_PREFIX, "landing")
ACTIVATION_REDIRECT_URL = getattr(settings, 'ASTAKOS_ACTIVATION_REDIRECT_URL',
                                  default_redirect_url)

# If true, this enables a ui compatibility layer for the introduction of UUIDs
# in identity management. WARNING: Setting to True will break your installation.
TRANSLATE_UUIDS = getattr(settings, 'ASTAKOS_TRANSLATE_UUIDS', False)

# Users that can approve or deny project applications from the web.
PROJECT_ADMINS = getattr(settings, 'ASTAKOS_PROJECT_ADMINS', set())

# OAuth2 Twitter credentials.
TWITTER_TOKEN = getattr(settings, 'ASTAKOS_TWITTER_TOKEN', '')
TWITTER_SECRET = getattr(settings, 'ASTAKOS_TWITTER_SECRET', '')
TWITTER_AUTH_FORCE_LOGIN = getattr(settings, 'ASTAKOS_TWITTER_AUTH_FORCE_LOGIN',
                                  False)

# OAuth2 Google credentials.
GOOGLE_CLIENT_ID = getattr(settings, 'ASTAKOS_GOOGLE_CLIENT_ID', '')
GOOGLE_SECRET = getattr(settings, 'ASTAKOS_GOOGLE_SECRET', '')

# OAuth2 LinkedIn credentials.
LINKEDIN_TOKEN = getattr(settings, 'ASTAKOS_LINKEDIN_TOKEN', '')
LINKEDIN_SECRET = getattr(settings, 'ASTAKOS_LINKEDIN_SECRET', '')

# URL to redirect the user after successful login when no next parameter is set
default_success_url = join_urls(BASE_URL, VIEWS_PREFIX, "landing")
LOGIN_SUCCESS_URL = getattr(settings, 'ASTAKOS_LOGIN_SUCCESS_URL',
                            default_redirect_url)

# Whether or not to display projects in astakos menu
PROJECTS_VISIBLE = getattr(settings, 'ASTAKOS_PROJECTS_VISIBLE', False)

# A way to extend the services presentation metadata
SERVICES_META = getattr(settings, 'ASTAKOS_SERVICES_META', {})

# A way to extend the resources presentation metadata
RESOURCES_META = getattr(settings, 'ASTAKOS_RESOURCES_META', {})

# Do not require email verification for new users
SKIP_EMAIL_VERIFICATION = getattr(settings,
                                  'ASTAKOS_SKIP_EMAIL_VERIFICATION', False)
