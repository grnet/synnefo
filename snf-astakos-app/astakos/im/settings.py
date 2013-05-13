from django.conf import settings

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

ADMINS = getattr(settings, 'ADMINS', ())
MANAGERS = getattr(settings, 'MANAGERS', ADMINS)
HELPDESK = getattr(settings, 'HELPDESK', ADMINS)

CONTACT_EMAIL = settings.CONTACT_EMAIL
SERVER_EMAIL = settings.SERVER_EMAIL

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

# Set baseurl
BASEURL = getattr(settings, 'ASTAKOS_BASEURL', 'https://accounts.example.synnefo.org')

# Set service name
SITENAME = getattr(settings, 'ASTAKOS_SITENAME', 'Synnefo Cloud')

# Set recaptcha keys
RECAPTCHA_PUBLIC_KEY = getattr(settings, 'ASTAKOS_RECAPTCHA_PUBLIC_KEY', '')
RECAPTCHA_PRIVATE_KEY = getattr(settings, 'ASTAKOS_RECAPTCHA_PRIVATE_KEY', '')
RECAPTCHA_OPTIONS = getattr(settings, 'ASTAKOS_RECAPTCHA_OPTIONS',
                            {'theme': 'custom', 'custom_theme_widget': 'okeanos_recaptcha'})
RECAPTCHA_USE_SSL = getattr(settings, 'ASTAKOS_RECAPTCHA_USE_SSL', True)
RECAPTCHA_ENABLED = getattr(settings, 'ASTAKOS_RECAPTCHA_ENABLED', False)

# set AstakosUser fields to propagate in the billing system
BILLING_FIELDS = getattr(settings, 'ASTAKOS_BILLING_FIELDS', ['is_active'])

# Queue for billing.
QUEUE_CONNECTION = getattr(settings, 'ASTAKOS_QUEUE_CONNECTION', None)  # Example: 'rabbitmq://guest:guest@localhost:5672/astakos'

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
# e.g. {'https://cms.okeanos.grnet.gr/': 'Back to ~okeanos'}
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

# Configurable email subjects
INVITATION_EMAIL_SUBJECT = getattr(
    settings, 'ASTAKOS_INVITATION_EMAIL_SUBJECT',
    'Invitation to %s alpha2 testing' % SITENAME)
GREETING_EMAIL_SUBJECT = getattr(settings, 'ASTAKOS_GREETING_EMAIL_SUBJECT',
                                 'Welcome to %s alpha2 testing' % SITENAME)
FEEDBACK_EMAIL_SUBJECT = getattr(settings, 'ASTAKOS_FEEDBACK_EMAIL_SUBJECT',
                                 'Feedback from %s alpha2 testing' % SITENAME)
VERIFICATION_EMAIL_SUBJECT = getattr(
    settings, 'ASTAKOS_VERIFICATION_EMAIL_SUBJECT',
    '%s alpha2 testing account activation is needed' % SITENAME)
ACCOUNT_CREATION_SUBJECT = getattr(
    settings, 'ASTAKOS_ACCOUNT_CREATION_SUBJECT',
    '%s alpha2 testing account created (%%(user)s)' % SITENAME)
GROUP_CREATION_SUBJECT = getattr(
    settings, 'ASTAKOS_GROUP_CREATION_SUBJECT',
    '%s alpha2 testing group created (%%(group)s)' % SITENAME)
HELPDESK_NOTIFICATION_EMAIL_SUBJECT = getattr(
    settings, 'ASTAKOS_HELPDESK_NOTIFICATION_EMAIL_SUBJECT',
    '%s alpha2 testing account activated (%%(user)s)' % SITENAME)
EMAIL_CHANGE_EMAIL_SUBJECT = getattr(
    settings, 'ASTAKOS_EMAIL_CHANGE_EMAIL_SUBJECT',
    'Email change on %s alpha2 testing' % SITENAME)
PASSWORD_RESET_EMAIL_SUBJECT = getattr(
    settings, 'ASTAKOS_PASSWORD_RESET_EMAIL_SUBJECT',
    'Password reset on %s alpha2 testing' % SITENAME)
PROJECT_CREATION_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_CREATION_SUBJECT',
    '%s alpha2 testing project application created (%%(name)s)' % SITENAME)
PROJECT_APPROVED_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_APPROVED_SUBJECT',
    '%s alpha2 testing project application approved (%%(name)s)' % SITENAME)
PROJECT_DENIED_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_DENIED_SUBJECT',
    '%s alpha2 testing project application denied (%%(name)s)' % SITENAME)
PROJECT_TERMINATION_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_TERMINATION_SUBJECT',
    '%s alpha2 testing project terminated (%%(name)s)' % SITENAME)
PROJECT_SUSPENSION_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_SUSPENSION_SUBJECT',
    '%s alpha2 testing project suspended (%%(name)s)' % SITENAME)
PROJECT_MEMBERSHIP_CHANGE_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_MEMBERSHIP_CHANGE_SUBJECT',
    '%s alpha2 testing project membership changed (%%(name)s)' % SITENAME)
PROJECT_MEMBERSHIP_ENROLL_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_MEMBERSHIP_ENROLL_SUBJECT',
    '%s alpha2 testing project enrollment (%%(name)s)' % SITENAME)
PROJECT_MEMBERSHIP_REQUEST_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_MEMBERSHIP_REQUEST_SUBJECT',
    '%s alpha2 testing project membership request (%%(name)s)' % SITENAME)
PROJECT_MEMBERSHIP_LEAVE_REQUEST_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_MEMBERSHIP_LEAVE_REQUEST_SUBJECT',
    '%s alpha2 testing project membership leave request (%%(name)s)' % SITENAME)

# Set the quota holder component URI
QUOTAHOLDER_URL = getattr(settings, 'ASTAKOS_QUOTAHOLDER_URL', '')
QUOTAHOLDER_TOKEN = getattr(settings, 'ASTAKOS_QUOTAHOLDER_TOKEN', '')
QUOTAHOLDER_POOLSIZE = getattr(settings, 'ASTAKOS_QUOTAHOLDER_POOLSIZE', 50)

# Set the billing URI
AQUARIUM_URL = getattr(settings, 'ASTAKOS_AQUARIUM_URL', '')

# Set how many objects should be displayed per page
PAGINATE_BY = getattr(settings, 'ASTAKOS_PAGINATE_BY', 8)

# Set how many objects should be displayed per page in show all projects page
PAGINATE_BY_ALL = getattr(settings, 'ASTAKOS_PAGINATE_BY_ALL', 15)

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

PROJECT_MEMBER_JOIN_POLICIES = getattr(settings,
                                'ASTAKOS_PROJECT_MEMBER_JOIN_POLICIES',
                                {'1':'automatically accepted',
                                 '2':'owner accepts',
                                 '3':'closed'})

PROJECT_MEMBER_LEAVE_POLICIES = getattr(settings,
                                'ASTAKOS_PROJECT_MEMBER_LEAVE_POLICIES',
                                {'1':'automatically accepted',
                                 '2':'owner accepts',
                                 '3':'closed'})

ACTIVATION_REDIRECT_URL = getattr(settings,
                                  'ASTAKOS_ACTIVATION_REDIRECT_URL',
                                  "/im/landing")


# If true, this enables a ui compatibility layer for the introduction of UUIDs
# in identity management. WARNING: Setting to True will break your installation.
TRANSLATE_UUIDS = getattr(settings, 'ASTAKOS_TRANSLATE_UUIDS', False)

# Users that can approve or deny project applications from the web.
PROJECT_ADMINS = getattr(settings, 'ASTAKOS_PROJECT_ADMINS', set())

# Maximum pending project applications per applicant.
# This is to reduce the volume of applications
# in case users abuse the mechanism.
PENDING_APPLICATION_LIMIT = getattr(settings,
                                    'ASTAKOS_PENDING_APPLICATION_LIMIT', 0)

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
LOGIN_SUCCESS_URL = getattr(settings, 'ASTAKOS_LOGIN_SUCCESS_URL',
                            '/im/landing')

# Whether or not to display projects in astakos menu
PROJECTS_VISIBLE = getattr(settings, 'ASTAKOS_PROJECTS_VISIBLE', False)

# A way to extend the services presentation metadata
SERVICES_META = getattr(settings, 'ASTAKOS_SERVICES_META', {})

# A way to extend the resources presentation metadata
RESOURCES_META = getattr(settings, 'ASTAKOS_RESOURCES_META', {})
