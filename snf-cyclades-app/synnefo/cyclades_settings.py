# Copyright 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from django.conf import settings
from synnefo.lib import join_urls, parse_base_url
from synnefo.util.keypath import get_path, set_path
from synnefo.api.services import cyclades_services as vanilla_cyclades_services
from synnefo.lib.services import fill_endpoints
from astakosclient import AstakosClient

from copy import deepcopy


# --------------------------------------------------------------------
# Process Cyclades settings

BASE_URL = getattr(settings, 'CYCLADES_BASE_URL',
                   'https://compute.example.synnefo.org/compute/')
BASE_HOST, BASE_PATH = parse_base_url(BASE_URL)
SERVICE_TOKEN = getattr(settings, 'CYCLADES_SERVICE_TOKEN', "")

CUSTOMIZE_SERVICES = getattr(settings, 'CYCLADES_CUSTOMIZE_SERVICES', ())
cyclades_services = deepcopy(vanilla_cyclades_services)
fill_endpoints(cyclades_services, BASE_URL)
for path, value in CUSTOMIZE_SERVICES:
    set_path(cyclades_services, path, value, createpath=True)

COMPUTE_PREFIX = get_path(cyclades_services, 'cyclades_compute.prefix')
VMAPI_PREFIX = get_path(cyclades_services, 'cyclades_vmapi.prefix')
PLANKTON_PREFIX = get_path(cyclades_services, 'cyclades_plankton.prefix')
HELPDESK_PREFIX = get_path(cyclades_services, 'cyclades_helpdesk.prefix')
UI_PREFIX = get_path(cyclades_services, 'cyclades_ui.prefix')
USERDATA_PREFIX = get_path(cyclades_services, 'cyclades_userdata.prefix')
ADMIN_PREFIX = get_path(cyclades_services, 'cyclades_admin.prefix')

COMPUTE_ROOT_URL = join_urls(BASE_URL, COMPUTE_PREFIX)


# --------------------------------------------------------------------
# Process Astakos settings

ASTAKOS_AUTH_URL = getattr(
    settings, 'ASTAKOS_AUTH_URL',
    'https://accounts.example.synnefo.org/astakos/identity/v2.0')


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
# Define ASTAKOS_UI_URL and ASTAKOS_ACCOUNT_URL as LazyAstakosUrl
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
