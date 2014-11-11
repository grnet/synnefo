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

import re
_VALID_MAC_RE = re.compile("^([0-9a-f]{2}:){5}[0-9a-f]{2}$", re.I)


def validate_mac(mac):
    """Validate a MAC address and return normalized form."""

    if not _VALID_MAC_RE.match(mac):
        raise InvalidMacAddress("Invalid MAC address '%s'" % mac)

    return mac.lower()


class InvalidMacAddress(Exception):
    pass
