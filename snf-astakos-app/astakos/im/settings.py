from django.conf import settings

# Set the expiration time of newly created auth tokens
# to be this many hours after their creation time.
AUTH_TOKEN_DURATION = getattr(settings, 'ASTAKOS_AUTH_TOKEN_DURATION', 30 * 24)

# Authenticate via Twitter.
TWITTER_KEY = getattr(settings, 'ASTAKOS_TWITTER_KEY', '')
TWITTER_SECRET = getattr(settings, 'ASTAKOS_TWITTER_SECRET', '')

DEFAULT_USER_LEVEL = getattr(settings, 'ASTAKOS_DEFAULT_USER_LEVEL', 4)

INVITATIONS_PER_LEVEL = getattr(settings, 'ASTAKOS_INVITATIONS_PER_LEVEL', {
    0: 100,
    1: 2,
    2: 0,
    3: 0,
    4: 0
})

# Address to use for outgoing emails
DEFAULT_CONTACT_EMAIL = getattr(
    settings, 'ASTAKOS_DEFAULT_CONTACT_EMAIL', 'support@cloud.grnet.gr')

# Identity Management enabled modules
IM_MODULES = getattr(settings, 'ASTAKOS_IM_MODULES', ['local', 'shibboleth'])

# Force user profile verification
FORCE_PROFILE_UPDATE = getattr(settings, 'ASTAKOS_FORCE_PROFILE_UPDATE', True)

#Enable invitations
INVITATIONS_ENABLED = getattr(settings, 'ASTAKOS_INVITATIONS_ENABLED', True)

COOKIE_NAME = getattr(settings, 'ASTAKOS_COOKIE_NAME', '_pithos2_a')
COOKIE_DOMAIN = getattr(settings, 'ASTAKOS_COOKIE_DOMAIN', None)
COOKIE_SECURE = getattr(settings, 'ASTAKOS_COOKIE_SECURE', True)

IM_STATIC_URL = getattr(settings, 'ASTAKOS_IM_STATIC_URL', '/static/im/')

# If set to False and invitations not enabled newly created user will be automatically accepted
MODERATION_ENABLED = getattr(settings, 'ASTAKOS_MODERATION_ENABLED', True)

# Set baseurl
BASEURL = getattr(settings, 'ASTAKOS_BASEURL', 'http://pithos.dev.grnet.gr')

# Set service name
SITENAME = getattr(settings, 'ASTAKOS_SITENAME', 'GRNET Cloud')

# Set recaptcha keys
RECAPTCHA_PUBLIC_KEY = getattr(settings, 'ASTAKOS_RECAPTCHA_PUBLIC_KEY', '')
RECAPTCHA_PRIVATE_KEY = getattr(settings, 'ASTAKOS_RECAPTCHA_PRIVATE_KEY', '')
RECAPTCHA_OPTIONS = getattr(settings, 'ASTAKOS_RECAPTCHA_OPTIONS',
                            {'theme': 'custom', 'custom_theme_widget': 'okeanos_recaptcha'})
RECAPTCHA_USE_SSL = getattr(settings, 'ASTAKOS_RECAPTCHA_USE_SSL', True)
RECAPTCHA_ENABLED = getattr(settings, 'ASTAKOS_RECAPTCHA_ENABLED', True)

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
GROUP_CREATION_SUBJECT = getattr(settings, 'ASTAKOS_GROUP_CREATION_SUBJECT',
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

# Set the quota holder component URI
QUOTA_HOLDER_URL = getattr(settings, 'ASTAKOS_QUOTA_HOLDER_URL', '')

# Set the cloud service properties
SERVICES = getattr(settings, 'ASTAKOS_SERVICES', {
    'cyclades': {
        'url': 'https://node1.example.com/ui/',
        'resources': [{
            'name':'vm',
            'group':'compute',
            'uplimit':2,
            'desc': 'Number of virtual machines'
            },{
            'name':'disk',
            'group':'compute',
            'uplimit':30*1024*1024*1024,
            'unit':'bytes',
            'desc': 'Virtual machine disk size'
            },{
            'name':'cpu',
            'group':'compute',
            'uplimit':6,
            'desc': 'Number of virtual machine processors'
            },{
            'name':'ram',
            'group':'compute',
            'uplimit':6*1024*1024*1024,
            'unit':'bytes',
            'desc': 'Virtual machines'
            },{
            'name':'network.private',
            'group':'network',
            'uplimit':1,
            'desc': 'Private networks'
            }
        ]
    },
    'pithos+': {
        'url': 'https://node2.example.com/ui/',
        'resources':[{
            'name':'diskspace',
            'group':'storage',
            'uplimit':5 * 1024 * 1024 * 1024,
            'unit':'bytes',
            'desc': 'Pithos account diskspace'
            }]
    }
})

# Set the billing URI
AQUARIUM_URL = getattr(settings, 'ASTAKOS_AQUARIUM_URL', '')

# Set how many objects should be displayed per page
PAGINATE_BY = getattr(settings, 'ASTAKOS_PAGINATE_BY', 8)

# Set how many objects should be displayed per page in show all groups page
PAGINATE_BY_ALL = getattr(settings, 'ASTAKOS_PAGINATE_BY_ALL', 15)

# Enforce token renewal on password change/reset
NEWPASSWD_INVALIDATE_TOKEN = getattr(
    settings, 'ASTAKOS_NEWPASSWD_INVALIDATE_TOKEN', True)


RESOURCES_PRESENTATION_DATA = getattr(
    settings, 'ASTAKOS_RESOURCES_PRESENTATION_DATA', {
        'groups': {
             'compute': {
                'help_text':'group compute help text',
                'is_abbreviation':False,
                'report_desc':'',
                 'verbose_name':'compute', 
            },
            'storage': {
                'help_text':'group storage help text',
                'is_abbreviation':False,
                'report_desc':'',
                 'verbose_name':'storage', 
            },
        },
        'resources': {
            'pithos+.diskspace': {
                'help_text':'resource pithos+.diskspace help text',
                'is_abbreviation':False,
                'report_desc':'Pithos+ Diskspace',
                'placeholder':'eg. 10GB',
                'verbose_name':'diskspace', 
            },
            'cyclades.vm': {
                'help_text':'resource cyclades.vm help text resource cyclades.vm help text resource cyclades.vm help text resource cyclades.vm help text',
                'is_abbreviation':True,
                'report_desc':'Virtual Machines',
                'placeholder':'eg. 2',
                'verbose_name':'vm', 
            },
            'cyclades.disk': {
                'help_text':'resource cyclades.disk help text',
                'is_abbreviation':False,
                'report_desc':'Disk',
                'placeholder':'eg. 5GB, 2GB etc',
                'verbose_name':'disk'
            },
            'cyclades.ram': {
                'help_text':'resource cyclades.ram help text',
                'is_abbreviation':True,
                'report_desc':'RAM',
                'placeholder':'eg. 4GB',
                'verbose_name':'ram'
            },
            'cyclades.cpu': {
                'help_text':'resource cyclades.cpu help text',
                'is_abbreviation':True,
                'report_desc':'CPUs',
                'placeholder':'eg. 1',
                'verbose_name':'cpu'
            },
            'cyclades.network.private': {
                'help_text':'resource cyclades.network.private help text',
                'is_abbreviation':False,
                'report_desc':'Network',
                'placeholder':'eg. 1',
                'verbose_name':'private network'
            }
        
        }
        
    })

# Permit local account migration
ENABLE_LOCAL_ACCOUNT_MIGRATION = getattr(settings, 'ASTAKOS_ENABLE_LOCAL_ACCOUNT_MIGRATION', True)
