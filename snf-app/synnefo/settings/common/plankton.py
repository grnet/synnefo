# -*- coding: utf-8 -*-
#
# Plankton configuration
########################

from os.path import join

PITHOS_ROOT = '/usr/share/pithos'
BACKEND_DB_MODULE = 'pithos.backends.lib.sqlalchemy'
BACKEND_DB_CONNECTION = 'sqlite:///' + join(PITHOS_ROOT, 'backend.db')
BACKEND_BLOCK_MODULE = 'pithos.backends.lib.hashfiler'
BACKEND_BLOCK_PATH = join(PITHOS_ROOT, 'data/')

# Default setting for new accounts.
DEFAULT_QUOTA = 50 * 1024 * 1024 * 1024
DEFAULT_VERSIONING = 'auto'

PITHOS_IMAGE_CONTAINER = 'images'

ALLOWED_DISK_FORMATS = ('diskdump', 'dump', 'extdump', 'lvm', 'ntfsclone',
        'ntfsdump')
ALLOWED_CONTAINER_FORMATS = ('aki', 'ari', 'ami', 'bare', 'ovf')

DEFAULT_DISK_FORMAT = 'dump'
DEFAULT_CONTAINER_FORMAT = 'bare'