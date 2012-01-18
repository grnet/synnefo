# SQLAlchemy (choose SQLite/MySQL/PostgreSQL).
BACKEND_DB_MODULE = 'pithos.backends.lib.sqlalchemy'
BACKEND_DB_CONNECTION = 'sqlite:///' + join(PROJECT_PATH, 'backend.db')

# Block storage.
BACKEND_BLOCK_MODULE = 'pithos.backends.lib.hashfiler'
BACKEND_BLOCK_PATH = join(PROJECT_PATH, 'data/')

# Default setting for new accounts.
BACKEND_QUOTA = 50 * 1024 * 1024 * 1024
BACKEND_VERSIONING = 'auto'
