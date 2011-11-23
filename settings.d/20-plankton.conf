# -*- coding: utf-8 -*-
#
# Plankton configuration
########################

PITHOS_ROOT = os.path.join(PROJECT_PATH, 'pithos')
BACKEND_DB_MODULE = 'pithos.backends.lib.sqlalchemy'
BACKEND_DB_CONNECTION = 'sqlite:///' + os.path.join(PITHOS_ROOT, 'backend.db')
BACKEND_BLOCK_MODULE = 'pithos.backends.lib.hashfiler'
BACKEND_BLOCK_PATH = os.path.join(PITHOS_ROOT, 'data/')

# Default setting for new accounts.
DEFAULT_QUOTA = 50 * 1024 * 1024 * 1024
DEFAULT_VERSIONING = 'auto'

PITHOS_IMAGE_CONTAINER = 'images'

IMAGE_STORES = ('file', 'pithos')
IMAGE_DISK_FORMATS = ('aki', 'ari', 'ami', 'raw', 'iso', 'vhd', 'vdi', 'qcow2')
IMAGE_CONTAINER_FORMATS = ('aki', 'ari', 'ami', 'bare', 'ovf')

DEFAULT_IMAGE_STORE = 'pithos'
DEFAULT_DISK_FORMAT = 'iso'
DEFAULT_CONTAINER_FORMAT = 'ovf'