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

try:
    from django.core.servers.basehttp import is_hop_by_hop
except ImportError:
    # Removed in Django 1.4
    _hop_headers = {
        'connection': 1, 'keep-alive': 1, 'proxy-authenticate': 1,
        'proxy-authorization': 1, 'te': 1, 'trailers': 1,
        'transfer-encoding': 1, 'upgrade': 1
    }

    def is_hop_by_hop(header_name):
        """Return true if 'header_name' is an HTTP/1.1 "Hop-by-Hop" header"""
        return header_name.lower() in _hop_headers


# Headers which don't get prefixed with HTTP_ but should get forwarded
ALLOWED_PLAIN_HTTP_HEADERS = ['CONTENT_TYPE']

def fix_header(k, v):
    prefix = 'HTTP_'
    if k.startswith(prefix):
        k = k[len(prefix):].title().replace('_', '-')

    if k in ALLOWED_PLAIN_HTTP_HEADERS:
        k = k.title().replace('_', '-')

    return k, v


def forward_header(k):
    return k.upper() not in ['HOST', 'CONTENT_LENGTH'] and \
        not is_hop_by_hop(k) and not '.' in k
