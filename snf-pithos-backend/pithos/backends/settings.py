# SQLAlchemy (choose SQLite/MySQL/PostgreSQL).
from os.path import join

BACKEND_PATH = '/usr/share/synnefo/pithos'
BACKEND_DB_MODULE = 'pithos.backends.lib.sqlalchemy'

BACKEND_DB_CONNECTION = 'sqlite:////' + BACKEND_PATH + '/pithos-backend.db'

# Block storage.
BACKEND_BLOCK_MODULE = 'pithos.backends.lib.hashfiler'
BACKEND_BLOCK_PATH = join(BACKEND_PATH, 'data/')

# Default setting for new accounts.
BACKEND_QUOTA = 50 * 1024 * 1024 * 1024
BACKEND_VERSIONING = 'auto'
