# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

from django.conf import settings
from synnefo.lib import join_urls, parse_base_url
from synnefo.api.services import cyclades_services as vanilla_cyclades_services
from synnefo.lib.services import fill_endpoints
from astakosclient import AstakosClient

from copy import deepcopy


logger = logging.getLogger(__name__)

# --------------------------------------------------------------------
# Process Cyclades settings

BASE_URL = getattr(settings, 'CYCLADES_BASE_URL',
                   'https://compute.example.synnefo.org/compute/')
BASE_HOST, BASE_PATH = parse_base_url(BASE_URL)
SERVICE_TOKEN = getattr(settings, 'CYCLADES_SERVICE_TOKEN', "")

cyclades_services = deepcopy(vanilla_cyclades_services)
fill_endpoints(cyclades_services, BASE_URL)

COMPUTE_PREFIX = cyclades_services['cyclades_compute']['prefix']
NETWORK_PREFIX = cyclades_services['cyclades_network']['prefix']
VMAPI_PREFIX = cyclades_services['cyclades_vmapi']['prefix']
PLANKTON_PREFIX = cyclades_services['cyclades_plankton']['prefix']
HELPDESK_PREFIX = cyclades_services['cyclades_helpdesk']['prefix']
UI_PREFIX = cyclades_services['cyclades_ui']['prefix']
USERDATA_PREFIX = cyclades_services['cyclades_userdata']['prefix']
ADMIN_PREFIX = cyclades_services['cyclades_admin']['prefix']
VOLUME_PREFIX = cyclades_services['cyclades_volume']['prefix']

COMPUTE_ROOT_URL = join_urls(BASE_URL, COMPUTE_PREFIX)


# --------------------------------------------------------------------
# Process Astakos settings

ASTAKOS_AUTH_URL = getattr(
    settings, 'ASTAKOS_AUTH_URL',
    'https://accounts.example.synnefo.org/astakos/identity/v2.0')


# --------------------------------------
# Define a LazyAstakosUrl
# This is used to define ASTAKOS_ACCOUNT_URL and
# ASTAKOS_UI_URL and should never be used as is.
class LazyAstakosUrl(object):
    def __init__(self, endpoints_name):
        self.endpoints_name = endpoints_name

    def __str__(self):
        if not hasattr(self, 'str'):
            try:
                astakos_client = \
                    AstakosClient(SERVICE_TOKEN, ASTAKOS_AUTH_URL)
                self.str = getattr(astakos_client, self.endpoints_name)
            except Exception as excpt:
                logger.exception(
                    "Could not retrieve endpoints from Astakos url %s: %s",
                    ASTAKOS_AUTH_URL, excpt)
                return ""
        return self.str

# --------------------------------------
# Define ASTAKOS_UI_URL and ASTAKOS_ACCOUNT_URL as LazyAstakosUrl
# These are used to define the proxy paths.
# These have to be resolved lazily (by the proxy function) so
# they should not be used as is.
ASTAKOS_ACCOUNT_URL = LazyAstakosUrl('account_url')
ASTAKOS_UI_URL = LazyAstakosUrl('ui_url')

# --------------------------------------
# Define Astakos prefixes
ASTAKOS_PROXY_PREFIX = getattr(settings, 'CYCLADES_PROXY_PREFIX', '_astakos')
ASTAKOS_AUTH_PREFIX = join_urls('/', ASTAKOS_PROXY_PREFIX, 'identity')
ASTAKOS_ACCOUNT_PREFIX = join_urls('/', ASTAKOS_PROXY_PREFIX, 'account')
ASTAKOS_UI_PREFIX = join_urls('/', ASTAKOS_PROXY_PREFIX, 'ui')

# --------------------------------------
# Define Astakos proxy paths
ASTAKOS_AUTH_PROXY_PATH = join_urls(BASE_PATH, ASTAKOS_AUTH_PREFIX)
ASTAKOS_ACCOUNT_PROXY_PATH = join_urls(BASE_PATH, ASTAKOS_ACCOUNT_PREFIX)
ASTAKOS_UI_PROXY_PATH = join_urls(BASE_PATH, ASTAKOS_UI_PREFIX)
