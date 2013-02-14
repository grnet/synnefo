# -*- coding: utf-8 -*-
#
# Plankton configuration
########################

# Backend settings
BACKEND_DB_CONNECTION = 'sqlite:////usr/share/synnefo/pithos/backend.db'
BACKEND_BLOCK_PATH = '/usr/share/synnefo/pithos/data/'

# The Pithos container where images will be stored by default
DEFAULT_PLANKTON_CONTAINER = 'images'

ALLOWED_DISK_FORMATS = ('diskdump', 'extdump', 'ntfsdump')
DEFAULT_DISK_FORMAT = 'diskdump'

ALLOWED_CONTAINER_FORMATS = ('aki', 'ari', 'ami', 'bare', 'ovf')
DEFAULT_CONTAINER_FORMAT = 'bare'

# The owner of the images that will be marked as "system images" by the UI
SYSTEM_IMAGES_OWNER = 'okeanos'

# If true, this enables a ui compatibility layer for the introduction of UUIDs
# in identity management. WARNING: Setting to True will break your installation.
TRANSLATE_UUIDS = False
