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
