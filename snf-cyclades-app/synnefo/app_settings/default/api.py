# -*- coding: utf-8 -*-
#
# API configuration
#####################


DEBUG = False

# Top-level URL for deployment. Numerous other URLs depend on this.
APP_INSTALL_URL = "https://host:port"

# The API implementation needs to accept and return absolute references
# to its resources. Thus, it needs to know its public URL.
API_ROOT_URL = APP_INSTALL_URL + '/api'

# The API will return HTTP Bad Request if the ?changes-since
# parameter refers to a point in time more than POLL_LIMIT seconds ago.
POLL_LIMIT = 3600

#
# Network Configuration
#

# Synnefo assigns this link id to NICs connected on the public network.
# An IP pool should be associated with this link by the Ganeti administrator.
GANETI_PUBLIC_NETWORK = 'snf-1'
GANETI_PRIVATE_BRIDGE = 'br2990'
# This link id is assigned to NICs that should be isolated from anything else
# (e.g., right before the NIC gets deleted).
# This value is also hardcoded in a fixture in db/fixtures/initial_data.json.
GANETI_NULL_LINK = 'snf_public'

# The pool of private network links to use is
# $GANETI_LINK_PREFIX{1..$GANETI_MAX_LINK_NUMBER}.
#
# The prefix to use for private network links.
GANETI_LINK_PREFIX = 'prv'
# The number of private network links to use.
GANETI_MAX_LINK_NUMBER = 100
# The first mac prefix to use
GANETI_BASE_MAC_PREFIX = 'aa:00:01'
# The number of mac prefixes to use.
GANETI_MAX_MAC_PREFIX_NUMBER = 4096

# Firewalling
GANETI_FIREWALL_ENABLED_TAG = 'synnefo:network:0:protected'
GANETI_FIREWALL_DISABLED_TAG = 'synnefo:network:0:unprotected'
GANETI_FIREWALL_PROTECTED_TAG = 'synnefo:network:0:limited'


# The default firewall profile that will be in effect if no tags are defined
DEFAULT_FIREWALL_PROFILE = 'DISABLED'

# our REST API would prefer to be explicit about trailing slashes
APPEND_SLASH = False

# Ignore disk size specified by flavor, always build the
# machine with a 4GB (in the case of Windows: 14GB) disk.
# This setting is helpful in development setups.
#
IGNORE_FLAVOR_DISK_SIZES = False

# Quota
#
# Maximum number of VMs a user is allowed to have.
MAX_VMS_PER_USER = 3

# Override maximum number of VMs for specific users.
# e.g. VMS_USER_QUOTA = {'user1@grnet.gr': 5, 'user2@grnet.gr': 10}
VMS_USER_QUOTA = {}

# Maximum number of networks a user is allowed to have.
MAX_NETWORKS_PER_USER = 5

# Override maximum number of private networks for specific users.
# e.g. NETWORKS_USER_QUOTA = {'user1@grnet.gr': 5, 'user2@grnet.gr': 10}
NETWORKS_USER_QUOTA = {}

# URL templates for the stat graphs.
# The API implementation replaces '%s' with the encrypted backend id.
# FIXME: For now we do not encrypt the backend id.
CPU_BAR_GRAPH_URL = 'http://stats.okeanos.grnet.gr/%s/cpu-bar.png'
CPU_TIMESERIES_GRAPH_URL = 'http://stats.okeanos.grnet.gr/%s/cpu-ts.png'
NET_BAR_GRAPH_URL = 'http://stats.okeanos.grnet.gr/%s/net-bar.png'
NET_TIMESERIES_GRAPH_URL = 'http://stats.okeanos.grnet.gr/%s/net-ts.png'

# Recommended refresh period for server stats
STATS_REFRESH_PERIOD = 60

# The maximum number of file path/content pairs that can be supplied on server
# build
MAX_PERSONALITY = 5

# The maximum size, in bytes, for each personality file
MAX_PERSONALITY_SIZE = 10240

# Available storage types to be used as disk templates
GANETI_DISK_TEMPLATES = ('blockdev', 'diskless', 'drbd', 'file', 'plain',
                         'rbd',  'sharedfile')
DEFAULT_GANETI_DISK_TEMPLATE = 'drbd'

# The URL of an astakos instance that will be used for user authentication
ASTAKOS_URL = 'https://astakos.okeanos.grnet.gr/im/authenticate'

# Key for password encryption-decryption. After changing this setting, synnefo
# will be unable to decrypt all existing Backend passwords. You will need to
# store again the new password by using 'snf-manage backend-modify'
ENCRYPTION_KEY= "Password Encryption Key"
