# Copyright 2012, 2013 GRNET S.A. All rights reserved.
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

from django.db.models import Sum, Count

from synnefo.db.models import VirtualMachine, Network
from synnefo.quotas import Quotaholder, ASTAKOS_TOKEN


def get_db_holdings(users=None):
    """Get holdings from Cyclades DB."""
    holdings = {}

    vms = VirtualMachine.objects.filter(deleted=False)
    networks = Network.objects.filter(deleted=False)

    if users:
        assert(type(users) is list)
        vms = vms.filter(userid__in=users)
        networks = networks.filter(userid__in=users)

    # Get resources related with VMs
    vm_resources = vms.values("userid").annotate(num=Count("id"),
                                                 ram=Sum("flavor__ram"),
                                                 cpu=Sum("flavor__cpu"),
                                                 disk=Sum("flavor__disk"))
    for vm_res in vm_resources:
        user = vm_res['userid']
        res = {"vm": vm_res["num"],
               "cpu": vm_res["cpu"],
               "disk": 1073741824 * vm_res["disk"],
               "ram": 1048576 * vm_res["ram"]}
        holdings[user] = res

    # Get resources related with networks
    net_resources = networks.values("userid")\
                            .annotate(num=Count("id"))
    for net_res in net_resources:
        user = net_res['userid']
        if user not in holdings:
            holdings[user] = {}
        holdings[user]["network.private"] = net_res["num"]

    return holdings


def get_quotaholder_holdings(user=None):
    """Get quotas from Quotaholder for all Cyclades resources.

    Returns quotas for all users, unless a single user is specified.
    """
    qh = Quotaholder.get()
    return qh.get_service_quotas(ASTAKOS_TOKEN, user)


def transform_quotas(quotas):
    d = {}
    for resource, counters in quotas.iteritems():
        res = resource.replace("cyclades.", "")
        available = counters['available']
        limit = counters['limit']
        used = counters['used']
        used_max = limit - available
        d[res] = (used, used_max)
    return d
