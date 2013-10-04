#coding=utf8
from django.conf import settings
from synnefo.lib import parse_base_url, join_urls
from synnefo.lib.services import fill_endpoints
from synnefo.util.keypath import get_path
from pithos.api.services import pithos_services as vanilla_pithos_services
from astakosclient import AstakosClient

from copy import deepcopy


# --------------------------------------------------------------------
# Process Pithos settings

# Top-level URL for Pithos. Must set.
BASE_URL = getattr(settings, 'PITHOS_BASE_URL',
                   "https://object-store.example.synnefo.org/pithos/")
# Service Token acquired by identity provider.
SERVICE_TOKEN = getattr(settings, 'PITHOS_SERVICE_TOKEN', '')

BASE_HOST, BASE_PATH = parse_base_url(BASE_URL)

pithos_services = deepcopy(vanilla_pithos_services)
fill_endpoints(pithos_services, BASE_URL)
PITHOS_PREFIX = get_path(pithos_services, 'pithos_object-store.prefix')
PUBLIC_PREFIX = get_path(pithos_services, 'pithos_public.prefix')
UI_PREFIX = get_path(pithos_services, 'pithos_ui.prefix')

COOKIE_NAME = getattr(settings, 'PITHOS_ASTAKOS_COOKIE_NAME', '_pithos2_a')


# --------------------------------------------------------------------
# Process Astakos settings

ASTAKOS_AUTH_URL = getattr(
    settings, 'ASTAKOS_AUTH_URL',
    'https://accounts.example.synnefo.org/astakos/identity/v2.0/')

ASTAKOSCLIENT_POOLSIZE = \
    getattr(settings, 'PITHOS_ASTAKOSCLIENT_POOLSIZE', 200)


# --------------------------------------
# Define a LazyAstakosUrl
class LazyAstakosUrl(object):
    def __init__(self, endpoints_name):
        self.endpoints_name = endpoints_name

    def __str__(self):
        if not hasattr(self, 'str'):
            try:
                astakos_client = \
                    AstakosClient(SERVICE_TOKEN, ASTAKOS_AUTH_URL)
                self.str = getattr(astakos_client, self.endpoints_name)
            except:
                return None
        return self.str

# --------------------------------------
# Define ASTAKOS_ACCOUNT_URL and ASTAKOS_UR_URL as LazyAstakosUrl
ASTAKOS_ACCOUNT_URL = LazyAstakosUrl('account_url')
ASTAKOS_UI_URL = LazyAstakosUrl('ui_url')

# --------------------------------------
# Define Astakos prefixes
ASTAKOS_PROXY_PREFIX = getattr(settings, 'PITHOS_PROXY_PREFIX', '_astakos')
ASTAKOS_AUTH_PREFIX = join_urls('/', ASTAKOS_PROXY_PREFIX, 'identity')
ASTAKOS_ACCOUNT_PREFIX = join_urls('/', ASTAKOS_PROXY_PREFIX, 'account')
ASTAKOS_UI_PREFIX = join_urls('/', ASTAKOS_PROXY_PREFIX, 'ui')

# --------------------------------------
# Define Astakos proxy paths
ASTAKOS_AUTH_PROXY_PATH = join_urls(BASE_PATH, ASTAKOS_AUTH_PREFIX)
ASTAKOS_ACCOUNT_PROXY_PATH = join_urls(BASE_PATH, ASTAKOS_ACCOUNT_PREFIX)
ASTAKOS_UI_PROXY_PATH = join_urls(BASE_PATH, ASTAKOS_UI_PREFIX)

# Astakos login URL to redirect if the user information is missing
LOGIN_URL = join_urls(ASTAKOS_UI_PROXY_PATH, 'login')


# --------------------------------------------------------------------
# Backend settings

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
BACKEND_QUEUE_MODULE = getattr(settings, 'PITHOS_BACKEND_QUEUE_MODULE', None)
# Example: 'pithos.backends.lib.rabbitmq'

BACKEND_QUEUE_HOSTS = getattr(settings, 'PITHOS_BACKEND_QUEUE_HOSTS', None)
# Example: "['amqp://guest:guest@localhost:5672']"

BACKEND_QUEUE_EXCHANGE = getattr(settings, 'PITHOS_BACKEND_QUEUE_EXCHANGE',
                                 'pithos')

# Default setting for new accounts.
BACKEND_ACCOUNT_QUOTA = getattr(
    settings, 'PITHOS_BACKEND_ACCOUNT_QUOTA', 50 * 1024 * 1024 * 1024)
BACKEND_CONTAINER_QUOTA = getattr(
    settings, 'PITHOS_BACKEND_CONTAINER_QUOTA', 0)
BACKEND_VERSIONING = getattr(settings, 'PITHOS_BACKEND_VERSIONING', 'auto')
BACKEND_FREE_VERSIONING = getattr(settings, 'PITHOS_BACKEND_FREE_VERSIONING',
                                  True)

# Enable backend pooling
BACKEND_POOL_ENABLED = getattr(settings, 'PITHOS_BACKEND_POOL_ENABLED', True)

# Default backend pool size
BACKEND_POOL_SIZE = getattr(settings, 'PITHOS_BACKEND_POOL_SIZE', 5)

# Update object checksums.
UPDATE_MD5 = getattr(settings, 'PITHOS_UPDATE_MD5', False)

RADOS_STORAGE = getattr(settings, 'PITHOS_RADOS_STORAGE', False)
RADOS_POOL_BLOCKS = getattr(settings, 'PITHOS_RADOS_POOL_BLOCKS', 'blocks')
RADOS_POOL_MAPS = getattr(settings, 'PITHOS_RADOS_POOL_MAPS', 'maps')

# This enables a ui compatibility layer for the introduction of UUIDs in
# identity management.  WARNING: Setting to True will break your installation.
TRANSLATE_UUIDS = getattr(settings, 'PITHOS_TRANSLATE_UUIDS', False)

# Set how many random bytes to use for constructing the URL
# of Pithos public files
PUBLIC_URL_SECURITY = getattr(settings, 'PITHOS_PUBLIC_URL_SECURITY', 16)
# Set the alphabet to use for constructing the URL of Pithos public files
PUBLIC_URL_ALPHABET = getattr(
    settings,
    'PITHOS_PUBLIC_URL_ALPHABET',
    '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')

# The maximum number or items returned by the listing api methods
API_LIST_LIMIT = getattr(settings, 'PITHOS_API_LIST_LIMIT', 10000)

# The backend block size
BACKEND_BLOCK_SIZE = getattr(
    settings, 'PITHOS_BACKEND_BLOCK_SIZE', 4 * 1024 * 1024)

# The backend block hash algorithm
BACKEND_HASH_ALGORITHM = getattr(
    settings, 'PITHOS_BACKEND_HASH_ALGORITHM', 'sha256')
