# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from astakosclient import AstakosClient
from astakosclient.errors import Unauthorized


def user_for_token(client, token, usage=False):
    if not token:
        return None

    try:
        return client.get_user_info(token, usage=True)
    except Unauthorized:
        return None


def get_user(request, astakos_url, fallback_token=None,
             usage=False, logger=None):
    request.user = None
    request.user_uniq = None

    client = AstakosClient(astakos_url, retry=2, use_pool=True, logger=logger)
    # Try to find token in a parameter or in a request header.
    user = user_for_token(client, request.GET.get('X-Auth-Token'), usage=usage)
    if not user:
        user = user_for_token(client,
                              request.META.get('HTTP_X_AUTH_TOKEN'),
                              usage=usage)
    if not user:
        user = user_for_token(client, fallback_token, usage=usage)
    if not user:
        return None

    # use user uuid, instead of email, keep email/displayname reference
    # to user_id
    request.user_uniq = user['uuid']
    request.user = user
    request.user_id = user.get('displayname')
    return user


class UserCache(object):
    """uuid<->displayname user 'cache'"""

    def __init__(self, astakos_url, astakos_token, split=100, logger=None):
        self.astakos = AstakosClient(astakos_url, retry=2,
                                     use_pool=True, logger=logger)
        self.astakos_token = astakos_token
        self.users = {}

        self.split = split
        assert(self.split > 0), "split must be positive"

    def fetch_names(self, uuid_list):
        total = len(uuid_list)
        split = self.split

        for start in range(0, total, split):
            end = start + split
            try:
                names = self.astakos.service_get_usernames(
                    self.astakos_token, uuid_list[start:end])
                self.users.update(names)
            except:
                pass

    def get_uuid(self, name):
        if not name in self.users:
            try:
                self.users[name] = \
                    self.astakos.service_get_uuid(
                        self.astakos_token, name)
            except:
                self.users[name] = name

        return self.users[name]

    def get_name(self, uuid):
        """Do the uuid-to-email resolving"""

        if not uuid in self.users:
            try:
                self.users[uuid] = \
                    self.astakos.service_get_username(
                        self.astakos_token, uuid)
            except:
                self.users[uuid] = "-"

        return self.users[uuid]
