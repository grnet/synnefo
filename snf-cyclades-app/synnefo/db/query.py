# Copyright 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

from synnefo.db.models import IPAddress


def get_server_ips(server, for_update=False):
    ips = IPAddress.objects.select_related("subnet")
    ips = ips.filter(nic__machine=server, deleted=False)
    if for_update:
        ips = ips.select_for_update()
    return ips


def get_server_active_ips(server, for_update=False):
    ips = get_server_ips(server, for_update=for_update)
    return ips.filter(nic__state="ACTIVE")


def get_server_public_ip(server, version=4):
    ips = get_server_active_ips(server)
    try:
        public_ips = ips.filter(network__public=True,
                                subnet__ipversion=version)
        return public_ips[0].address
    except IndexError:
        return None


def get_floating_ips(for_update=False):
    ips = IPAddress.objects.select_related("subnet")
    ips = ips.filter(floating_ip=True, deleted=False)
    if for_update:
        ips = ips.select_for_update()
    return ips


def get_server_floating_ips(server, for_update=False):
    floating_ips = get_floating_ips(for_update=for_update)
    return floating_ips.filter(nic__machine=server)


def get_server_floating_ip(server, address, for_update=False):
    server_fips = get_server_floating_ips(server, for_update=for_update)
    return server_fips.get(address=address)


def get_user_floating_ip(userid, address, for_update=False):
    fips = get_floating_ips(for_update=for_update)
    return fips.get(userid=userid, address=address)
