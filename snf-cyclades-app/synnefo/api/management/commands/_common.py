# Copyright 2012 GRNET S.A. All rights reserved.
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

import ipaddr
from datetime import datetime

from django.utils.timesince import timesince, timeuntil
from django.core.management import CommandError

from synnefo.api.util import validate_network_size
from synnefo.settings import MAX_CIDR_BLOCK


def format_bool(b):
    return 'YES' if b else 'NO'


def format_date(d):
    if not d:
        return ''

    if d < datetime.now():
        return timesince(d) + ' ago'
    else:
        return 'in ' + timeuntil(d)


def format_vm_state(vm):
    if vm.operstate == "BUILD":
        return "BUILD(" + str(vm.buildpercentage) + "%)"
    else:
        return vm.operstate


def validate_network_info(options):
    subnet = options['subnet']
    gateway = options['gateway']
    subnet6 = options['subnet6']
    gateway6 = options['gateway6']

    try:
        net = ipaddr.IPv4Network(subnet)
        prefix = net.prefixlen
        if not validate_network_size(prefix):
            raise CommandError("Unsupport network mask %d."
                               " Must be in range (%s,29] "
                               % (prefix, MAX_CIDR_BLOCK))
    except ValueError:
        raise CommandError('Malformed subnet')
    try:
        gateway and ipaddr.IPv4Address(gateway) or None
    except ValueError:
        raise CommandError('Malformed gateway')

    try:
        subnet6 and ipaddr.IPv6Network(subnet6) or None
    except ValueError:
        raise CommandError('Malformed subnet6')

    try:
        gateway6 and ipaddr.IPv6Address(gateway6) or None
    except ValueError:
        raise CommandError('Malformed gateway6')

    return subnet, gateway, subnet6, gateway6
