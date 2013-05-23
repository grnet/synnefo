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

BASE_URL = getattr(settings, 'CYCLADES_BASE_URL',
                   'https://compute.example.synnefo.org/compute/')
BASE_HOST, BASE_PATH = parse_base_url(BASE_URL)

ASTAKOS_BASE_URL = getattr(settings, 'ASTAKOS_BASE_URL',
                           'https://accounts.example.synnefo.org/astakos/')
ASTAKOS_BASE_HOST, ASTAKOS_BASE_PATH = parse_base_url(ASTAKOS_BASE_URL)

COMPUTE_PREFIX = getattr(settings, 'CYCLADES_COMPUTE_PREFIX', 'compute')
VMAPI_PREFIX = getattr(settings, 'CYCLADES_VMAPI_PREFIX', 'vmapi')
PLANKTON_PREFIX = getattr(settings, 'CYCLADES_PLANKTON_PREFIX', 'plankton')
HELPDESK_PREFIX = getattr(settings, 'CYCLADES_HELPDESK_PREFIX', 'helpdesk')

# The API implementation needs to accept and return absolute references
# to its resources. Thus, it needs to know its public URL.
COMPUTE_ROOT_URL = join_urls(BASE_URL, COMPUTE_PREFIX)

BASE_ASTAKOS_PROXY_PATH = getattr(settings,
                                  'CYCLADES_BASE_ASTAKOS_PROXY_PATH',
                                  ASTAKOS_BASE_PATH)
BASE_ASTAKOS_PROXY_PATH = join_urls(BASE_PATH, BASE_ASTAKOS_PROXY_PATH)
BASE_ASTAKOS_PROXY_PATH = BASE_ASTAKOS_PROXY_PATH.strip('/')

ASTAKOS_ACCOUNTS_PREFIX = getattr(settings,
                             'ASTAKOS_ACCOUNTS_PREFIX', 'accounts').strip('/')

ASTAKOS_VIEWS_PREFIX = getattr(settings,
                               'ASTAKOS_VIEWS_PREFIX', 'im').strip('/')

ASTAKOS_KEYSTONE_PREFIX = getattr(settings,
                                  'ASTAKOS_KEYSTONE_PREFIX',
                                  'keystone').strip('/')

PROXY_USER_SERVICES = getattr(settings, 'CYCLADES_PROXY_USER_SERVICES', True)
