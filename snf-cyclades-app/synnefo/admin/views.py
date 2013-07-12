# Copyright 2013 GRNET S.A. All rights reserved.
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

import logging
from django import http
from django.utils import simplejson as json
from synnefo.db.models import VirtualMachine, Network
from django.db.models import Count, Sum
from snf_django.lib import api
from copy import copy


log = logging.getLogger(__name__)


@api.api_method(http_method='GET', user_required=False, token_required=False,
                logger=log, serializations=['json'])
@api.allow_jsonp()
def get_stats(request):
    stats = get_statistics()
    data = json.dumps(stats)
    return http.HttpResponse(data, status=200, content_type='application/json')


def get_statistics():
    # VirtualMachines
    vm_objects = VirtualMachine.objects
    servers = vm_objects.values("deleted", "operstate")\
                        .annotate(count=Count("id"),
                                  cpu=Sum("flavor__cpu"),
                                  ram=Sum("flavor__ram"),
                                  disk=Sum("flavor__disk"))
    zero_stats = {"count": 0, "cpu": 0, "ram": 0, "disk": 0}
    server_stats = {}
    for state in VirtualMachine.RSAPI_STATE_FROM_OPER_STATE.values():
        server_stats[state] = copy(zero_stats)

    for stats in servers:
        deleted = stats.pop("deleted")
        operstate = stats.pop("operstate")
        state = VirtualMachine.RSAPI_STATE_FROM_OPER_STATE.get(operstate)
        if deleted:
            for key in zero_stats.keys():
                server_stats["DELETED"][key] += stats.get(key, 0)
        elif state:
            for key in zero_stats.keys():
                server_stats[state][key] += stats.get(key, 0)

    #Networks
    net_objects = Network.objects
    networks = net_objects.values("deleted", "state")\
                          .annotate(count=Count("id"))
    zero_stats = {"count": 0}
    network_stats = {}
    for state in Network.RSAPI_STATE_FROM_OPER_STATE.values():
        network_stats[state] = copy(zero_stats)

    for stats in networks:
        deleted = stats.pop("deleted")
        state = stats.pop("state")
        state = Network.RSAPI_STATE_FROM_OPER_STATE.get(state)
        if deleted:
            for key in zero_stats.keys():
                network_stats["DELETED"][key] += stats.get(key, 0)
        elif state:
            for key in zero_stats.keys():
                network_stats[state][key] += stats.get(key, 0)

    statistics = {"servers": server_stats,
                  "networks": network_stats}
    return statistics
