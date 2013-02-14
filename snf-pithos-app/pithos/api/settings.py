#coding=utf8
from django.conf import settings

# Set local users, or a remote host. To disable local users set them to None.
sample_users = {
    '0000': 'test',
    '0001': 'verigak',
    '0002': 'chazapis',
    '0003': 'gtsouk',
    '0004': 'papagian',
    '0005': 'louridas',
    '0006': 'chstath',
    '0007': 'pkanavos',
    '0008': 'mvasilak',
    '0009': 'διογένης'
}

# Set to False if pithos running in the same machine with the identity management
PROXY_USER_SERVICES = getattr(settings, 'PITHOS_PROXY_USER_SERVICES', True)

USER_CATALOG_URL = getattr(settings, 'PITHOS_USER_CATALOG_URL',
                           'http://127.0.0.1:8000/user_catalogs/')
USER_FEEDBACK_URL = getattr(settings, 'PITHOS_USER_FEEDBACK_URL',
                            'http://127.0.0.1:8000/feedback/')
USER_LOGIN_URL = getattr(settings, 'PITHOS_USER_LOGIN_URL',
                         'http://127.0.0.1:8000/login/')
AUTHENTICATION_URL = getattr(settings, 'PITHOS_AUTHENTICATION_URL',
                             'http://localhost:8000/im/authenticate/')
AUTHENTICATION_USERS = getattr(settings, 'PITHOS_AUTHENTICATION_USERS', {})

TRANSLATE_UUIDS = getattr(settings, 'PITHOS_TRANSLATE_UUIDS', False)

COOKIE_NAME = getattr(settings, 'ASTAKOS_COOKIE_NAME', '_pithos2_a')

# SQLAlchemy (choose SQLite/MySQL/PostgreSQL).
BACKEND_DB_MODULE = getattr(
    settings, 'PITHOS_BACKEND_DB_MODULE', 'pithos.backends.lib.sqlalchemy')
BACKEND_DB_CONNECTION = getattr(settings, 'PITHOS_BACKEND_DB_CONNECTION',
                                'sqlite:////tmp/pithos-backend.db')

# Block storage.
BACKEND_BLOCK_MODULE = getattr(
    settings, 'PITHOS_BACKEND_BLOCK_MODULE', 'pithos.backends.lib.hashfiler')
BACKEND_BLOCK_PATH = getattr(
    settings, 'PITHOS_BACKEND_BLOCK_PATH', '/tmp/pithos-data/')
BACKEND_BLOCK_UMASK = getattr(settings, 'PITHOS_BACKEND_BLOCK_UMASK', 0o022)

# Queue for billing.
BACKEND_QUEUE_MODULE = getattr(settings, 'PITHOS_BACKEND_QUEUE_MODULE',
                               None)  # Example: 'pithos.backends.lib.rabbitmq'
BACKEND_QUEUE_HOSTS = getattr(settings, 'PITHOS_BACKEND_QUEUE_HOSTS', None) # Example: "['amqp://guest:guest@localhost:5672']"
BACKEND_QUEUE_EXCHANGE = getattr(settings, 'PITHOS_BACKEND_QUEUE_EXCHANGE', 'pithos')

# Default setting for new accounts.
BACKEND_QUOTA = getattr(
    settings, 'PITHOS_BACKEND_QUOTA', 50 * 1024 * 1024 * 1024)
BACKEND_VERSIONING = getattr(settings, 'PITHOS_BACKEND_VERSIONING', 'auto')
BACKEND_FREE_VERSIONING = getattr(settings, 'PITHOS_BACKEND_FREE_VERSIONING', True)

# Set the quota holder component URI
QUOTAHOLDER_URL = getattr(settings, 'PITHOS_QUOTAHOLDER_URL', '')
QUOTAHOLDER_TOKEN = getattr(settings, 'PITHOS_QUOTAHOLDER_TOKEN', '')

# Update object checksums when using hashmaps.
UPDATE_MD5 = getattr(settings, 'PITHOS_UPDATE_MD5', True)

# Service Token acquired by identity provider.
SERVICE_TOKEN = getattr(settings, 'PITHOS_SERVICE_TOKEN', '')

RADOS_STORAGE = getattr(settings, 'PITHOS_RADOS_STORAGE', False)
RADOS_POOL_BLOCKS= getattr(settings, 'PITHOS_RADOS_POOL_BLOCKS', 'blocks')
RADOS_POOL_MAPS = getattr(settings, 'PITHOS_RADOS_POOL_MAPS', 'maps')
