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

from django.db.models import Sum, Count, Q

from synnefo.db.models import VirtualMachine, Network, FloatingIP
from synnefo.quotas import Quotaholder, ASTAKOS_TOKEN


def get_db_holdings(user=None):
    """Get holdings from Cyclades DB."""
    holdings = {}

    vms = VirtualMachine.objects.filter(deleted=False)
    networks = Network.objects.filter(deleted=False)
    floating_ips = FloatingIP.objects.filter(deleted=False)

    if user is not None:
        vms = vms.filter(userid=user)
        networks = networks.filter(userid=user)
        floating_ips = floating_ips.filter(userid=user)

    # Get resources related with VMs
    vm_resources = vms.values("userid").annotate(num=Count("id"),
                                                 ram=Sum("flavor__ram"),
                                                 cpu=Sum("flavor__cpu"),
                                                 disk=Sum("flavor__disk"))
    vm_active_resources = \
        vms.values("userid")\
           .filter(Q(operstate="STARTED") | Q(operstate="BUILD") |
                   Q(operstate="ERROR"))\
           .annotate(active_ram=Sum("flavor__ram"),
                     active_cpu=Sum("flavor__cpu"))

    for vm_res in vm_resources.iterator():
        user = vm_res['userid']
        res = {"cyclades.vm": vm_res["num"],
               "cyclades.cpu": vm_res["cpu"],
               "cyclades.disk": 1073741824 * vm_res["disk"],
               "cyclades.ram": 1048576 * vm_res["ram"]}
        holdings[user] = res

    for vm_res in vm_active_resources.iterator():
        user = vm_res['userid']
        holdings[user]["cyclades.active_cpu"] = vm_res["active_cpu"]
        holdings[user]["cyclades.active_ram"] = 1048576 * vm_res["active_ram"]

    # Get resources related with networks
    net_resources = networks.values("userid")\
                            .annotate(num=Count("id"))
    for net_res in net_resources.iterator():
        user = net_res['userid']
        holdings.setdefault(user, {})
        holdings[user]["cyclades.network.private"] = net_res["num"]

    floating_ips_resources = floating_ips.values("userid")\
                                         .annotate(num=Count("id"))
    for floating_ip_res in floating_ips_resources.iterator():
        user = floating_ip_res["userid"]
        holdings.setdefault(user, {})
        holdings[user]["cyclades.floating_ip"] = floating_ip_res["num"]

    return holdings


def get_quotaholder_holdings(user=None):
    """Get quotas from Quotaholder for all Cyclades resources.

    Returns quotas for all users, unless a single user is specified.
    """
    qh = Quotaholder.get()
    return qh.service_get_quotas(ASTAKOS_TOKEN, user)


def transform_quotas(quotas):
    d = {}
    for resource, counters in quotas.iteritems():
        used = counters['usage']
        limit = counters['limit']
        pending = counters['pending']
        d[resource] = (used, limit, pending)
    return d
