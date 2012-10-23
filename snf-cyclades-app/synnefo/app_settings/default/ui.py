# -*- coding: utf-8 -*-
#
# UI settings
###################

from synnefo.settings.default.admins import *

# API URL
COMPUTE_API_URL = '/api/v1.1'

# base url for ui static files
# if not set, defaults to MEDIA_URL + 'snf-<latest_ui_version>/'
UI_MEDIA_URL = '/static/ui/static/snf/'

# UI requests to the API layer time out after that many milliseconds
TIMEOUT = 10 * 1000

# A list of suggested server tags (server metadata keys)
DEFAULT_KEYWORDS = ["OS", "Role", "Location", "Owner"]

# A list of allowed icons for OS Images
IMAGE_ICONS = ["redhat", "ubuntu", "debian", "windows", "gentoo", "archlinux",
               "centos", "fedora", "freebsd", "netbsd", "openbsd", "slackware",
               "suse", "kubuntu"]

# How often should the UI request changes from the API
UI_UPDATE_INTERVAL = 5000

# Milieconds to increase the interval after UI_UPDATE_INTERVAL_INCREASE_AFTER_CALLS_COUNT calls
# of recurrent api requests
UI_UPDATE_INTERVAL_INCREASE = UI_UPDATE_INTERVAL / 4
UI_UPDATE_INTERVAL_INCREASE_AFTER_CALLS_COUNT = 4

# Maximum update interval
UI_UPDATE_INTERVAL_MAX = UI_UPDATE_INTERVAL * 3

# Fast update interval
UI_UPDATE_INTERVAL_FAST = UI_UPDATE_INTERVAL / 2

# Miliseconds to remove from the previous server response time used in
# consecutive API calls (aligning changes-since attribute).
UI_CHANGES_SINCE_ALIGNMENT = 0

# List of emails used for sending the feedback messages to (following the ADMINS format)
FEEDBACK_CONTACTS = (
    # ('Contact Name', 'contact_email@domain.com'),
)

# Email from which the feedback emails will be sent from
FEEDBACK_EMAIL_FROM = DEFAULT_FROM_EMAIL

# URL to redirect not authenticated users
UI_LOGIN_URL = "/im/login"

# URL to redirect user to when he logs out from the ui
UI_LOGOUT_URL = "/im/logout"

# Cookie name to retrieve authentication data from
UI_AUTH_COOKIE_NAME = '_pithos2_a'

# Flavor options that we provide to the user as predefined
# cpu/ram/disk combinations on vm create wizard
VM_CREATE_SUGGESTED_FLAVORS = {
    'small': {
        'cpu': 1,
        'ram': 1024,
        'disk': 20,
        'disk_template': 'drbd'
    },
    'medium': {
        'cpu': 2,
        'ram': 2048,
        'disk': 30,
        'disk_template': 'drbd'

    },
    'large': {
        'cpu': 4,
        'ram': 4096,
        'disk': 40,
        'disk_template': 'drbd'

    }
}

# A list of metadata keys to clone from image
# to the virtual machine on its creation.
VM_IMAGE_COMMON_METADATA = ["OS", "loginname", "logindomain", "users", "remote"]

# A list of suggested vm roles to display to user on create wizard
VM_CREATE_SUGGESTED_ROLES = ["Database server", "File server", "Mail server", "Web server", "Proxy"]

# Template to be used for suggesting the user a default name for newly created
# vms. {0} gets replaced by the image OS value
VM_CREATE_NAME_TPL = "My {0} server"

# Name/description metadata for the available flavor disk templates
# Dict key is the disk_template value as stored in database
UI_FLAVORS_DISK_TEMPLATES_INFO = {
    'drbd': {'name': 'DRBD',
             'description': 'DRBD storage.'},
}


#######################
# UI BEHAVIOUR SETTINGS
#######################

# Whether to increase the time of recurrent requests (networks/vms update) if
# window loses its focus
UI_DELAY_ON_BLUR = False

# Whether not visible vm views will update their content if vm changes
UI_UPDATE_HIDDEN_VIEWS = False

# After how many timeouts of reccurent ajax requests to display the timeout
# error overlay
UI_SKIP_TIMEOUTS = 1

# Whether UI should display error overlay for all Javascript exceptions
UI_HANDLE_WINDOW_EXCEPTIONS = True

# A list of os names that support ssh public key assignment
UI_SUPPORT_SSH_OS_LIST = ['debian', 'fedora', 'okeanos', 'ubuntu', 'kubuntu',
                          'centos', 'archlinux']

# OS/username map to identify default user name for the specified os
UI_OS_DEFAULT_USER_MAP = {
    'debian':'root', 'fedora': 'root', 'okeanos': 'root',
    'ubuntu': 'root', 'kubuntu': 'root', 'centos': 'root',
    'windows': 'Administrator'
}

##########################
# UI NETWORK VIEW SETTINGS
##########################

# Available network types for use to choose when creating a private network
# If only one set, no select options will be displayed
UI_NETWORK_AVAILABLE_NETWORK_TYPES = {'PRIVATE_FILTERED': 'mac-filtering'}

# Suggested private networks to let the user choose from when creating a private
# network with dhcp enabled
UI_NETWORK_AVAILABLE_SUBNETS = ['10.0.0.1/24', '192.168.1.1/24']

# Whether to display already connected vm's to the network connect overlay
UI_NETWORK_ALLOW_DUPLICATE_VM_NICS = False

# Whether to display destroy action on private networks that contain vms. If
# set to True, destroy action will only get displayed if user disconnect all
# virtual machines from the network.
UI_NETWORK_STRICT_DESTROY = True


###############
# UI EXTENSIONS
###############

# Glance images API endpoint
UI_GLANCE_API_URL = '/plankton'

# Whether or not UI should display images from the Glance API
# set in UI_GLANCE_API_URL, if setting is set to False, ui will
# request images from Compute API
UI_ENABLE_GLANCE = True

# a dict of image owner ids and their associate name
# to be displayed on images list
UI_SYSTEM_IMAGES_OWNERS = {
    'admin@synnefo.gr': 'system',
    'images@synnefo.gr': 'system'
}

