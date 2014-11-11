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
#

from IPy import IP

# Adapted from NFDHCPD's mac2eui64 utility, repository commit:feca7bb95


def mac2eui64(mac, prefixstr):
    try:
        prefix = IP(prefixstr)
    except ValueError:
        raise Exception("Invalid IPv6 prefix '%s'" % prefixstr)

    if prefix.version() != 6:
        raise Exception("%s is not a valid IPv6 prefix" % prefixstr)

    if prefix.prefixlen() != 64:
        raise Exception("Cannot generate an EUI-64 address on a non-64 subnet")

    mac_parts = mac.split(":")
    pfx_parts = prefix.net().strFullsize().split(":")

    if len(mac_parts) != 6:
        raise Exception("%s is not a valid MAC-48 address" % mac)

    eui64 = mac_parts[:3] + ["ff", "fe"] + mac_parts[3:]

    eui64[0] = "%02x" % (int(eui64[0], 16) ^ 0x02)

    ip = ":".join(pfx_parts[:4])
    for l in range(0, len(eui64), 2):
        ip += ":%s" % "".join(eui64[l:l + 2])

    return IP(ip).strCompressed()

# vim: set ts=4 sts=4 sw=4 et ai :
