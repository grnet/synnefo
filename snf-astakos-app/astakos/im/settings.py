from django.conf import settings

# Set the expiration time of newly created auth tokens
# to be this many hours after their creation time.
AUTH_TOKEN_DURATION = getattr(settings, 'ASTAKOS_AUTH_TOKEN_DURATION', 30 * 24)

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
# Supported modules are: 'local', 'twitter' and 'shibboleth'
IM_MODULES = getattr(settings, 'ASTAKOS_IM_MODULES', ['local'])

# Force user profile verification
FORCE_PROFILE_UPDATE = getattr(settings, 'ASTAKOS_FORCE_PROFILE_UPDATE', True)

#Enable invitations
INVITATIONS_ENABLED = getattr(settings, 'ASTAKOS_INVITATIONS_ENABLED', False)

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
PROJECT_TERMINATION_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_TERMINATION_SUBJECT',
    '%s alpha2 testing project terminated (%%(name)s)' % SITENAME)
PROJECT_SUSPENSION_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_SUSPENSION_SUBJECT',
    '%s alpha2 testing project suspended (%%(name)s)' % SITENAME)
PROJECT_MEMBERSHIP_CHANGE_SUBJECT = getattr(
    settings, 'ASTAKOS_PROJECT_MEMBERSHIP_CHANGE_SUBJECT',
    '%s alpha2 testing project membership changed (%%(name)s)' % SITENAME)

# Set the quota holder component URI
QUOTAHOLDER_URL = getattr(settings, 'ASTAKOS_QUOTAHOLDER_URL', '')
QUOTAHOLDER_TOKEN = getattr(settings, 'ASTAKOS_QUOTAHOLDER_TOKEN', '')

# Set the cloud service properties
SERVICES = getattr(settings, 'ASTAKOS_SERVICES', {
    'cyclades': {
        'url': 'https://node1.example.com/ui/',
        'resources': [{
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
            'name':'vm',
            'group':'compute',
            'uplimit':2,
            'desc': 'Number of virtual machines'
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

USAGE_UPDATE_INTERVAL = getattr(settings, 'ASTAKOS_USAGE_UPDATE_INTERVAL', 5000)

RESOURCES_PRESENTATION_DATA = getattr(
    settings, 'ASTAKOS_RESOURCES_PRESENTATION_DATA', {
        'groups': {
             'compute': {
                'help_text':'Compute resources (amount of VMs, CPUs, RAM, System disk) ',
                'is_abbreviation':False,
                'report_desc':'',
                 'verbose_name':'compute',
            },
            'storage': {
                'help_text':'Storage resources (amount of space to store files on Pithos) ',
                'is_abbreviation':False,
                'report_desc':'',
                 'verbose_name':'storage',
            },
            'network': {
                'help_text':' Network resources (amount of Private Networks)  ',
                'is_abbreviation':False,
                'report_desc':'',
                'verbose_name':'network',
            },
        },
        'resources': {
            'pithos+.diskspace': {
                'help_text':'This is the space on Pithos for storing files and VM Images. ',
                'help_text_input_each':'This is the total amount of space on Pithos that will be granted to each user of this Project ',
                'is_abbreviation':False,
                'report_desc':'Storage Space',
                'placeholder':'eg. 10GB',
                'verbose_name':'Storage Space',
            },
            'cyclades.disk': {
                'help_text':'This is the System Disk that the VMs have that run the OS ',
                'help_text_input_each':"This is the total amount of System Disk that will be granted to each user of this Project (this refers to the total System Disk of all VMs, not each VM's System Disk)  ",
                'is_abbreviation':False,
                'report_desc':'System Disk',
                'placeholder':'eg. 5GB, 2GB etc',
                'verbose_name':'System Disk'
            },
            'cyclades.ram': {
                'help_text':'RAM used by VMs ',
                'help_text_input_each':'This is the total amount of RAM that will be granted to each user of this Project (on all VMs)  ',
                'is_abbreviation':True,
                'report_desc':'RAM',
                'placeholder':'eg. 4GB',
                'verbose_name':'ram'
            },
            'cyclades.cpu': {
                'help_text':'CPUs used by VMs ',
                'help_text_input_each':'This is the total number of CPUs that will be granted to each user of this Project (on all VMs)  ',
                'is_abbreviation':True,
                'report_desc':'CPUs',
                'placeholder':'eg. 1',
                'verbose_name':'cpu'
            },
            'cyclades.vm': {
                'help_text':'These are the VMs one can create on the Cyclades UI ',
                'help_text_input_each':'This is the total number of VMs that will be granted to each user of this Project ',
                'is_abbreviation':True,
                'report_desc':'Virtual Machines',
                'placeholder':'eg. 2',
                'verbose_name':'vm',
            },
            'cyclades.network.private': {
                'help_text':'These are the Private Networks one can create on the Cyclades UI. ',
                'help_text_input_each':'This is the total number of Private Networks that will be granted to each user of this Project ',
                'is_abbreviation':False,
                'report_desc':'Private Networks',
                'placeholder':'eg. 1',
                'verbose_name':'private network'
            }

        }

    })

# Permit local account migration
ENABLE_LOCAL_ACCOUNT_MIGRATION = getattr(settings, 'ASTAKOS_ENABLE_LOCAL_ACCOUNT_MIGRATION', True)

# Strict shibboleth usage
SHIBBOLETH_REQUIRE_NAME_INFO = getattr(settings,
                                       'ASTAKOS_SHIBBOLETH_REQUIRE_NAME_INFO',
                                       False)

PROJECT_MEMBER_JOIN_POLICIES = getattr(settings,
                                'ASTAKOS_PROJECT_MEMBER_JOIN_POLICIES',
                                {1:'automatically accepted by the system',
                                 2:'accepted by the owner of the project',
                                 3:'members can not join the project'})

PROJECT_MEMBER_LEAVE_POLICIES = getattr(settings,
                                'ASTAKOS_PROJECT_MEMBER_LEAVE_POLICIES',
                                {1:'automatically accepted by the system',
                                 2:'accepted by the owner of the project',
                                 3:'members can not leave the project'})
