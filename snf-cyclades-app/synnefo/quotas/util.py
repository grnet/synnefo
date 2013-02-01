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

from django.db.models import Sum, Count

from synnefo.db.models import VirtualMachine, Network
from synnefo.quotas import get_quota_holder
from synnefo.lib.quotaholder.api.exception import NoEntityError


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


def get_quotaholder_holdings(users=[]):
    """Get holdings from Quotaholder.

    If the entity for the user does not exist in quotaholder, no holding
    is returned.
    """
    holdings = {}
    with get_quota_holder() as qh:
        for user in users:
            try:
                (qh_holdings, _) = \
                    qh.list_holdings(context={}, list_holdings=[(user, "1")])
                if not qh_holdings:
                    continue
                qh_holdings = qh_holdings[0]
                qh_holdings = filter(lambda x: x[1].startswith("cyclades."),
                                     qh_holdings)
                holdings[user] = dict(map(decode_holding, qh_holdings))
            except NoEntityError:
                pass
    return holdings


def decode_holding(holding):
    entity, resource, imported, exported, returned, released = holding
    res = resource.replace("cyclades.", "")
    return (res, imported - exported + returned - released)
