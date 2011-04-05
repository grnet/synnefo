#
#

# Copyright (c) 2010 GRNET SA
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.

import d3des
from struct import pack, unpack

RFB_AUTH_SUCCESS = 0
RFB_AUTH_ERROR = 1
RFB_AUTHTYPE_VNC = 2
RFB_AUTHTYPE_NONE = 1
RFB_AUTHTYPE_ERROR = 0
RFB_SUPPORTED_AUTHTYPES = [RFB_AUTHTYPE_NONE, RFB_AUTHTYPE_VNC]
RFB_VERSION_3_8 = "RFB 003.008"
RFB_VERSION_3_7 = "RFB 003.007"
RFB_VERSION_3_3 = "RFB 003.003"
RFB_VALID_VERSIONS = [
#    RFB_VERSION_3_3,
#    RFB_VERSION_3_7,
    RFB_VERSION_3_8,
]

class RfbError(Exception):
    pass

def check_version(version):
    return version.strip()[:11] in RFB_VALID_VERSIONS

def make_auth_request(*auth_methods):
    auth_methods = set(auth_methods)
    for method in auth_methods:
        if method not in RFB_SUPPORTED_AUTHTYPES:
            raise RfbError("Unsupported authentication type: %d" % method)
    return pack('B' + 'B' * len(auth_methods), len(auth_methods), *auth_methods)

def parse_auth_request(request):
    length = unpack('B', request[0])[0]
    if length == 0:
        return []
    return unpack('B' * length, request[1:])

def parse_client_authtype(authtype):
    return unpack('B', authtype[0])[0]

def from_u32(val):
    return unpack('>L', val)[0]

def to_u32(val):
    return pack('>L', val)

def from_u8(val):
    return unpack('B', val)[0]

def to_u8(val):
    return pack('B', val)

def check_password(challenge, response, password):
    return d3des.generate_response((password + '\0' * 8 )[:8],
                                   challenge) == response
