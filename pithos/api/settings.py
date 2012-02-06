from django.conf import settings
from os.path import abspath, dirname, join

PROJECT_PATH = getattr(settings, 'PROJECT_PATH', dirname(dirname(abspath(__file__))))

# SQLAlchemy (choose SQLite/MySQL/PostgreSQL).
BACKEND_DB_MODULE =  getattr(settings, 'PITHOS_BACKEND_DB_MODULE', 'pithos.backends.lib.sqlalchemy')
BACKEND_DB_CONNECTION = getattr(settings, 'PITHOS_BACKEND_DB_CONNECTION', 'sqlite:///' + join(PROJECT_PATH, 'backend.db'))

# Block storage.
BACKEND_BLOCK_MODULE = getattr(settings, 'PITHOS_BACKEND_BLOCK_MODULE', 'pithos.backends.lib.hashfiler')
BACKEND_BLOCK_PATH = getattr(settings, 'PITHOS_BACKEND_BLOCK_PATH', join(PROJECT_PATH, 'data/'))

# Queue for billing.
BACKEND_QUEUE_MODULE = getattr(settings, 'PITHOS_BACKEND_QUEUE_MODULE', None) # Example: 'pithos.backends.lib.rabbitmq'
BACKEND_QUEUE_CONNECTION = getattr(settings, 'PITHOS_BACKEND_QUEUE_CONNECTION', None) # Example: 'rabbitmq://guest:guest@localhost:5672/pithos'

# Default setting for new accounts.
BACKEND_QUOTA = getattr(settings, 'PITHOS_BACKEND_QUOTA', 50 * 1024 * 1024 * 1024)
BACKEND_VERSIONING = getattr(settings, 'PITHOS_BACKEND_VERSIONING', 'auto')

