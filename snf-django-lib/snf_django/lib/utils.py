# Copyright (C) 2010-2016 GRNET S.A.
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

from astakosclient import AstakosClient
from django.conf import settings


def get_token(request):
    """Get the Authentication Token of a request."""
    token = request.GET.get("X-Auth-Token", None)
    if not token:
        token = request.META.get("HTTP_X_AUTH_TOKEN", None)
    return token


def get_client_ip(request):
    """Get the IP of the actual client that triggered the request"""
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', None)
    if client_ip:
        # Keep just the client's IP here and not all proxy history
        client_ip = client_ip.split(',')[0].strip()
    else:
        client_ip = request.META.get('REMOTE_ADDR', None)

    return client_ip


def retrieve_user(token, astakos_auth_url, logger=None, client_ip=None):
    """Return user_info retrieved from astakos for the given token"""
    astakos_url = astakos_auth_url
    if astakos_url is None:
        try:
            astakos_url = settings.ASTAKOS_AUTH_URL
        except AttributeError:
            if logger:
                logger.error("Cannot authenticate without having"
                             " an Astakos Authentication URL")
            raise

    if not token:
        return None

    headers = None
    if client_ip:
        headers = {'X-Client-IP': client_ip}

    astakos = AstakosClient(token, astakos_url, use_pool=True, retry=2,
                            logger=logger, headers=headers)
    user_info = astakos.authenticate()

    return user_info
