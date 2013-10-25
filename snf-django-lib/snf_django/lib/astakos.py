# Copyright 2011, 2012, 2013 GRNET S.A. All rights reserved.
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

import logging

from astakosclient import AstakosClient
from astakosclient.errors import (Unauthorized, NoUUID, NoUserName,
                                  AstakosClientException)


def user_for_token(token, astakos_auth_url, logger=None):
    if token is None:
        return None
    client = AstakosClient(token, astakos_auth_url,
                           retry=2, use_pool=True, logger=logger)
    try:
        return client.authenticate()
    except Unauthorized:
        return None


def get_user(request, astakos_auth_url, fallback_token=None, logger=None):
    request.user = None
    request.user_uniq = None

    # Try to find token in a parameter or in a request header.
    user = user_for_token(
        request.GET.get('X-Auth-Token'), astakos_auth_url, logger)
    if not user:
        user = user_for_token(
            request.META.get('HTTP_X_AUTH_TOKEN'), astakos_auth_url, logger)
    if not user:
        user = user_for_token(
            fallback_token, astakos_auth_url, logger)
    if not user:
        return None

    request.user_uniq = user['access']['user']['id']
    request.user = user
    return user


class UserCache(object):
    """uuid<->displayname user 'cache'"""

    def __init__(self, astakos_auth_url, astakos_token,
                 split=100, logger=None):
        if logger is None:
            logger = logging.getLogger(__name__)
        self.logger = logger

        self.astakos = AstakosClient(astakos_token, astakos_auth_url,
                                     retry=2, use_pool=True, logger=logger)
        self.users = {}

        self.split = split
        assert(self.split > 0), "split must be positive"

    def fetch_names(self, uuid_list):
        total = len(uuid_list)
        split = self.split
        count = 0

        for start in range(0, total, split):
            end = start + split
            try:
                names = \
                    self.astakos.service_get_usernames(uuid_list[start:end])
                count += len(names)

                self.users.update(names)
            except AstakosClientException:
                pass
            except Exception as err:
                self.logger.error("Unexpected error while fetching "
                                  "user display names: %s" % repr(err))

        diff = (total - count)
        assert(diff >= 0), "fetched more displaynames than requested"

        if diff:
            self.logger.debug("Failed to fetch %d displaynames", diff)

    def get_uuid(self, name):
        uuid = name

        if not name in self.users:
            try:
                uuid = self.astakos.service_get_uuid(name)
            except NoUUID:
                self.logger.debug("Failed to fetch uuid for %s", name)
            except AstakosClientException:
                pass
            except Exception as err:
                self.logger.error("Unexpected error while fetching "
                                  "user uuid %s: %s" % (name, repr(err)))
            finally:
                self.users[name] = uuid

        return self.users[name]

    def get_name(self, uuid):
        name = "-"

        if not uuid in self.users:
            try:
                name = self.astakos.service_get_username(uuid)
            except NoUserName:
                self.logger.debug("Failed to fetch display name for %s", uuid)
            except AstakosClientException:
                pass
            except Exception as err:
                self.logger.error("Unexpected error while fetching "
                                  "user displayname %s: %s"
                                  % (uuid, repr(err)))
            finally:
                self.users[uuid] = name

        return self.users[uuid]
