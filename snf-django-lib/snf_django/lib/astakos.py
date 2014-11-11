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
