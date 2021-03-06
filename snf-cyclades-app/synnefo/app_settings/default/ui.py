# -*- coding: utf-8 -*-
#
# UI settings
###################

# API URL
#COMPUTE_API_URL = '/api/v1.1'

# base url for ui static files
# if not set, defaults to MEDIA_URL + 'snf-<latest_ui_version>/'
UI_MEDIA_URL = '/static/ui/static/snf/'

# UI requests to the API layer time out after that many milliseconds
TIMEOUT = 10 * 1000

# A list of suggested server tags (server metadata keys)
DEFAULT_KEYWORDS = ["OS", "Role", "Location", "Owner"]

# A list of allowed icons for OS Images
IMAGE_ICONS = ["rhel", "ubuntu", "debian", "windows", "gentoo", "archlinux",
               "centos", "fedora", "freebsd", "netbsd", "openbsd", "slackware",
               "sles", "opensuse", "kubuntu", "oraclelinux", "coreos",
               "scientificlinux"]

# How often should the UI request changes from the API
UI_UPDATE_INTERVAL = 5000

# Milieconds to increase the interval after
# UI_UPDATE_INTERVAL_INCREASE_AFTER_CALLS_COUNT calls
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

# How often to check for user usage changes
UI_QUOTAS_UPDATE_INTERVAL = 10000

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
VM_IMAGE_COMMON_METADATA = ["OS", "loginname", "logindomain", "users",
                            "remote"]

# A list of suggested vm roles to display to user on create wizard
VM_CREATE_SUGGESTED_ROLES = ["Database server", "File server", "Mail server",
                             "Web server", "Proxy"]

# Template to be used for suggesting the user a default name for newly created
# vms. {0} gets replaced by the image OS value
VM_CREATE_NAME_TPL = "My {0} server"

# Template to use to build vm hostname
UI_VM_HOSTNAME_FORMAT = 'snf-%(id)s.vm.synnefo.org'

# Name/description metadata for the available flavor disk templates
# Dict key is the disk_template value as stored in database
UI_FLAVORS_DISK_TEMPLATES_INFO = {
    'drbd': {'name': 'DRBD',
             'description': 'DRBD storage.'},
}

# Override default connect prompt messages. The setting gets appended to the
# ui default values so you only need to modify parameters you need to alter.
#
# Indicative format:
# {
#    '<browser os1>': {
#        '<vm os family1>': ['top message....', 'bottom message'],
#        '<vm os family 2>': ['top message....', 'bottom message'],
#        'ssh_message': 'ssh %(user)s@%(hostname)s'
# }
#
# you may use the following parameters to format ssh_message:
#
# * server_id: the database pk of the vm
# * ip_address: the ipv4 address of the public vm nic
# * hostname: vm hostname
# * user: vm username
#
# you may assign a callable python object to the ssh_message, if so the above
# parameters get passed as arguments to the provided object.
UI_CONNECT_PROMPT_MESSAGES = {}

# extend rdp file content. May be a string with format parameters similar to
# those used in UI_CONNECT_PROMPT_MESSAGES `ssh_message` or a callable object.
UI_EXTRA_RDP_CONTENT = None


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
    'debian': 'root', 'fedora': 'root', 'okeanos': 'root',
    'ubuntu': 'root', 'kubuntu': 'root', 'centos': 'root',
    'windows': 'Administrator'
}

##########################
# UI NETWORK VIEW SETTINGS
##########################

# Available network types for use to choose when creating a private network
# If only one set, no select options will be displayed
UI_NETWORK_AVAILABLE_NETWORK_TYPES = {'MAC_FILTERED': 'mac-filtering'}

# Suggested private networks to let the user choose from when creating a
# private network with dhcp enabled
UI_NETWORK_AVAILABLE_SUBNETS = ['10.0.0.0/24', '192.168.0.0/24']

# UI will use this setting to find an available network subnet if user requests
# automatic subnet selection.
UI_AUTOMATIC_NETWORK_RANGE_FORMAT = "192.168.%d.0/24"

# Whether to display already connected vm's to the network connect overlay
UI_NETWORK_ALLOW_DUPLICATE_VM_NICS = False

# Whether to display destroy action on private networks that contain vms. If
# set to True, destroy action will only get displayed if user disconnect all
# virtual machines from the network.
UI_NETWORK_STRICT_DESTROY = True

# Whether or not to group public networks nics in a single network view
UI_GROUP_PUBLIC_NETWORKS = True


###############
# UI EXTENSIONS
###############

# Whether or not UI should display images from the Glance API
# set in UI_GLANCE_API_URL, if setting is set to False, ui will
# request images from Compute API
UI_ENABLE_GLANCE = True

# a dict of image owner ids and their associate name
# to be displayed on images list
UI_SYSTEM_IMAGES_OWNERS = {
    'admin@synnefo.org': 'system',
    'images@synnefo.org': 'system'
}

## A list of user uuids. Images owned by users in this list will incur extra
## handling and be sectioned accordingly in image list view based on the
## LISTING_SECTION property if set.
UI_IMAGE_LISTING_USERS = []
