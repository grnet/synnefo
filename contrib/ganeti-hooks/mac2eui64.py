#!/usr/bin/env python

import sys

from IPy import IP

mac = sys.argv[1]
prefix = IP(sys.argv[2])

if prefix.version() != 6:
    print "%s is not a valid IPv6 prefix" % prefix
    sys.exit(1)

components = mac.split(":")
pfx = sys.argv[2].split("::")[0]

if len(components) != 6:
    print "%s is not a valid MAC-48 address" % mac
    sys.exit(1)

eui64 = components[:3] + [ "ff", "fe" ] + components[3:]

eui64[0] = "%02x" % (int(eui64[0], 16) ^ 0x02)

for l in range(0, len(eui64), 2):
    pfx += ":%s" % "".join(eui64[l:l+2])

print IP(pfx)

# vim: set ts=4 sts=4 sw=4 et ai :
