# -*- coding: utf-8 -*-
#
# Plankton configuration
########################

# Backend settings
BACKEND_DB_CONNECTION = 'sqlite:////usr/share/synnefo/pithos/backend.db'
PITHOS_BACKEND_POOL_SIZE = 8

# Backend block module settings
PITHOS_BACKEND_BLOCK_MODULE = 'pithos.backends.lib.hashfiler'
PITHOS_BACKEND_BLOCK_KWARGS = {}

# The Pithos container where images will be stored by default
DEFAULT_PLANKTON_CONTAINER = 'images'

ALLOWED_DISK_FORMATS = ('diskdump', 'extdump', 'ntfsdump')
DEFAULT_DISK_FORMAT = 'diskdump'

ALLOWED_CONTAINER_FORMATS = ('aki', 'ari', 'ami', 'bare', 'ovf')
DEFAULT_CONTAINER_FORMAT = 'bare'

# The owner of the images that will be marked as "system images" by the UI
SYSTEM_IMAGES_OWNER = 'okeanos'

# Archipelago Configuration File
PITHOS_BACKEND_ARCHIPELAGO_CONF = '/etc/archipelago/archipelago.conf'

# Archipelagp xseg pool size
PITHOS_BACKEND_XSEG_POOL_SIZE = 8

# The maximum interval (in seconds) for consequent backend object map checks
PITHOS_BACKEND_MAP_CHECK_INTERVAL = 1

#The maximum allowed number of image metadata
PITHOS_RESOURCE_MAX_METADATA = 32
