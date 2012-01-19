# -*- coding: utf-8 -*-
#
# Plankton configuration
########################

from os.path import join

# Backend settings
PITHOS_ROOT = '/srv/pithos'
BACKEND_DB_CONNECTION = 'sqlite:///' + join(PITHOS_ROOT, 'backend.db')
BACKEND_BLOCK_PATH = join(PITHOS_ROOT, 'data/')

# The Pithos container where images will be stored by default
DEFAULT_PLANKTON_CONTAINER = 'images'

ALLOWED_DISK_FORMATS = ('diskdump', 'dump', 'extdump', 'lvm', 'ntfsclone',
                        'ntfsdump')
ALLOWED_CONTAINER_FORMATS = ('aki', 'ari', 'ami', 'bare', 'ovf')

DEFAULT_DISK_FORMAT = 'dump'
DEFAULT_CONTAINER_FORMAT = 'bare'

# The owner of the images that will be marked as "system images" by the UI
SYSTEM_IMAGES_OWNER = 'okeanos'
