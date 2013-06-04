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
from synnefo.util.keypath import get_path
from synnefo.api.services import cyclades_services as vanilla_cyclades_services
from synnefo.lib.services import fill_endpoints
from astakosclient import astakos_services as vanilla_astakos_services

from copy import deepcopy


# Process Cyclades settings

BASE_URL = getattr(settings, 'CYCLADES_BASE_URL',
                   'https://compute.example.synnefo.org/compute/')
BASE_HOST, BASE_PATH = parse_base_url(BASE_URL)

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

COMPUTE_ROOT_URL = join_urls(BASE_URL, COMPUTE_PREFIX)


# Process Astakos settings

ASTAKOS_BASE_URL = getattr(settings, 'ASTAKOS_BASE_URL',
                           'https://accounts.example.synnefo.org/astakos/')
ASTAKOS_BASE_HOST, ASTAKOS_BASE_PATH = parse_base_url(ASTAKOS_BASE_URL)

# Patch astakosclient directly, otherwise it will not see any customization
#astakos_services = deepcopy(vanilla_astakos_services)
CUSTOMIZE_ASTAKOS_SERVICES = \
        getattr(settings, 'CYCLADES_CUSTOMIZE_ASTAKOS_SERVICES', ())

astakos_services = deepcopy(vanilla_astakos_services)
fill_endpoints(astakos_services, ASTAKOS_BASE_URL)
for path, value in CUSTOMIZE_ASTAKOS_SERVICES:
    set_path(astakos_services, path, value, createpath=True)

ASTAKOS_ACCOUNTS_PREFIX = get_path(astakos_services, 'astakos_account.prefix')
ASTAKOS_VIEWS_PREFIX = get_path(astakos_services, 'astakos_ui.prefix')
ASTAKOS_KEYSTONE_PREFIX = get_path(astakos_services, 'astakos_keystone.prefix')


# Proxy Astakos settings

BASE_ASTAKOS_PROXY_PATH = getattr(settings,
                                  'CYCLADES_BASE_ASTAKOS_PROXY_PATH',
                                  ASTAKOS_BASE_PATH)
BASE_ASTAKOS_PROXY_PATH = join_urls(BASE_PATH, BASE_ASTAKOS_PROXY_PATH)
BASE_ASTAKOS_PROXY_PATH = BASE_ASTAKOS_PROXY_PATH.strip('/')

PROXY_USER_SERVICES = getattr(settings, 'CYCLADES_PROXY_USER_SERVICES', True)
