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

# Maximum allowed network size for private networks.
MAX_CIDR_BLOCK = 22
# Name of the network in Ganeti corresponding to the default public network.
# All created VMs will obtain an IP from this network.
GANETI_PUBLIC_NETWORK = 'snf-net-1'

# The first mac prefix to use
MAC_POOL_BASE = 'aa:00:0'
MAC_POOL_LIMIT = 65536

ENABLED_NETWORKS = ['PUBLIC_ROUTED',
                    'PRIVATE_MAC_FILTERED',
                    'PRIVATE_PHYSICAL_VLAN']
                    # CUSTOM_ROUTED,
                    # CUSTOM_BRIDGED,

# Settings for PUBLIC_ROUTED network:
# -----------------------------------
# In this case VMCs act as routers that forward the traffic to/from VMs, based
# on the defined routing table($PUBLIC_ROUTED_ROUTING_TABLE) and ip rules, that
# exist in every node, implenting an IP-less routed and proxy-arp setup.
# (This value is also hardcoded in fixture db/fixtures/initial_data.json)
PUBLIC_ROUTED_ROUTING_TABLE = 'snf_public'
PUBLIC_ROUTED_TAGS = ['ip-less-routed']

# Boolean value indicating whether synnefo would hold a Pool and allocate IP
# addresses. If this setting is set to False, IP pool management will be
# delegated to Ganeti. If machines have been created with this option as False,
# you must run network reconciliation after turning it to True.
PUBLIC_ROUTED_USE_POOL = True

# Settings for PRIVATE_MAC_FILTERED network:
# ------------------------------------------
# All networks of this type are bridged to the same bridge. Isolation between
# networks is achieved by assigning a unique MAC-prefix to each network and
# filtering packets via ebtables.
PRIVATE_MAC_FILTERED_BRIDGE = 'br0'
PRIVATE_MAC_FILTERED_TAGS = ['private-filtered']

# Settings for PRIVATE_PHSICAL_VLAN network:
# ------------------------------------------
# Each network of this type is mapped to an isolated physical VLAN, which must
# be preconfigured in the backend. Each vlan corresponds to a bridge named
# $PRIVATE_PHYSICAL_VLAN_PREFIX{1..$PRIVATE_PHYSICAL_VLAN_MAX_NUMBER} (e.g. prv5)
# VirtualMachine's taps are eventually bridged to the corresponding bridge.
PRIVATE_PHYSICAL_VLAN_BRIDGE_PREFIX = 'prv'
# The max limit of physical vlan pool
PRIVATE_PHYSICAL_VLAN_MAX_NUMBER = 100
PRIVATE_PHYSICAL_VLAN_TAGS = ['physical-vlan']


# Settings for CUSTOM_ROUTED:
# ---------------------------
# Same as PUBLIC_ROUTED but with custom values
CUSTOM_ROUTED_ROUTING_TABLE = 'custom_routing_table'
CUSTOM_ROUTED_TAGS = []

# Settings for CUSTOM_BRIDGED:
# ---------------------------
# Same as PRIVATE_BRIDGED but with custom values
CUSTOM_BRIDGED_BRIDGE = 'custom_bridge'
CUSTOM_BRIDGED_TAGS = []

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
# Use ext_<provider_name> to map specific provider for `ext` disk template.
GANETI_DISK_TEMPLATES = ('blockdev', 'diskless', 'drbd', 'file', 'plain',
                         'rbd',  'sharedfile')
DEFAULT_GANETI_DISK_TEMPLATE = 'drbd'

# The URL of an astakos instance that will be used for user authentication
ASTAKOS_URL = 'https://astakos.okeanos.grnet.gr/im/authenticate'

# Key for password encryption-decryption. After changing this setting, synnefo
# will be unable to decrypt all existing Backend passwords. You will need to
# store again the new password by using 'snf-manage backend-modify'.
# SECRET_ENCRYPTION_KEY may up to 32 bytes. Keys bigger than 32 bytes are not
# supported.
SECRET_ENCRYPTION_KEY= "Password Encryption Key"
