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
#

import synnefo.cyclades_settings as cyclades
from synnefo.cyclades_settings import cyclades_services, astakos_services

from synnefo.lib import join_urls
from synnefo.lib.services import get_public_endpoint

from django.conf import settings

BASE_PATH = cyclades.BASE_PATH
if not BASE_PATH.startswith("/"):
    BASE_PATH = "/" + BASE_PATH

GLANCE_URL = get_public_endpoint(cyclades_services, 'image', 'v1.0')
COMPUTE_URL = get_public_endpoint(cyclades_services, 'compute', 'v2.0')
USERDATA_URL = get_public_endpoint(cyclades_services, 'cyclades_userdata', '')
ASTAKOS_UI_URL = get_public_endpoint(astakos_services, 'astakos_ui', '')

if cyclades.PROXY_USER_SERVICES:
    ACCOUNT_URL = join_urls('/', cyclades.BASE_ASTAKOS_PROXY_PATH,
                            cyclades.ASTAKOS_ACCOUNTS_PREFIX, 'v1.0')
else:
    ACCOUNT_URL = get_public_endpoint(astakos_services, 'account', 'v1.0')


USER_CATALOG_URL = join_urls(ACCOUNT_URL, 'user_catalogs')
FEEDBACK_URL = join_urls(ACCOUNT_URL, 'feedback')

LOGIN_URL = join_urls(ASTAKOS_UI_URL, 'login')
LOGOUT_REDIRECT = LOGIN_URL
