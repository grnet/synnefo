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

from synnefo.lib import join_urls
from django.conf import settings


ASTAKOS_VIEWS_URL = join_urls(cyclades.ASTAKOS_BASE_URL,
                              cyclades.ASTAKOS_VIEWS_PREFIX)

ASTAKOS_ACCOUNTS_URL = join_urls(cyclades.ASTAKOS_BASE_URL,
                                 cyclades.ASTAKOS_ACCOUNTS_PREFIX)
if cyclades.PROXY_USER_SERVICES:
    ASTAKOS_ACCOUNTS_URL = join_urls('/', cyclades.BASE_ASTAKOS_PROXY_PATH,
                                     cyclades.ASTAKOS_ACCOUNTS_PREFIX)


BASE_PATH = cyclades.BASE_PATH
if not BASE_PATH.startswith("/"):
    BASE_PATH = "/" + BASE_PATH

ACCOUNTS_URL = getattr(settings, 'CYCLADES_UI_ACCOUNTS_URL',
                       join_urls(ASTAKOS_ACCOUNTS_URL))
USER_CATALOG_URL = getattr(settings, 'CYCLADES_UI_USER_CATALOG_URL',
                           join_urls(ACCOUNTS_URL, 'user_catalogs'))
FEEDBACK_URL = getattr(settings, 'CYCLADES_UI_FEEDBACK_URL',
                       join_urls(ACCOUNTS_URL, 'feedback'))
COMPUTE_URL = getattr(settings, 'CYCLADES_UI_COMPUTE_URL',
                      join_urls(BASE_PATH, cyclades.COMPUTE_PREFIX,
                                'v1.1'))
GLANCE_URL = getattr(settings, 'CYCLADES_UI_GLANCE_URL',
                     join_urls(BASE_PATH, cyclades.PLANKTON_PREFIX))
USERDATA_URL = getattr(settings, 'CYCLADES_UI_USERDATA_URL',
                       join_urls(BASE_PATH, cyclades.USERDATA_PREFIX))
LOGIN_URL = getattr(settings, 'CYCLADES_UI_LOGIN_URL',
                    join_urls(cyclades.ASTAKOS_BASE_URL,
                              cyclades.ASTAKOS_VIEWS_PREFIX, 'login'))
LOGOUT_REDIRECT = getattr(settings, 'CYCLADES_UI_LOGOUT_REDIRECT', LOGIN_URL)
