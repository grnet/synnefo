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

from synnefo.db.models import VirtualMachine, Network, IPAddress
from synnefo.quotas import Quotaholder
from collections import defaultdict

QuotaDict = lambda: defaultdict(lambda: defaultdict(dict))

MiB = 2 ** 20
GiB = 2 ** 30


def get_db_holdings(user=None, project=None):
    """Get holdings from Cyclades DB."""
    holdings = QuotaDict()

    vms = VirtualMachine.objects.filter(deleted=False)
    networks = Network.objects.filter(deleted=False)
    floating_ips = IPAddress.objects.filter(deleted=False, floating_ip=True)

    if user is not None:
        vms = vms.filter(userid=user)
        networks = networks.filter(userid=user)
        floating_ips = floating_ips.filter(userid=user)

    if project is not None:
        vms = vms.filter(project=project)
        networks = networks.filter(project=project)
        floating_ips = floating_ips.filter(project=project)

    # Get resources related with VMs
    vm_resources = vms.values("userid", "project")\
        .annotate(num=Count("id"),
                  total_ram=Sum("flavor__ram"),
                  total_cpu=Sum("flavor__cpu"),
                  disk=Sum("flavor__disk"))

    for vm_res in vm_resources.iterator():
        user = vm_res['userid']
        project = vm_res['project']
        res = {"cyclades.vm": vm_res["num"],
               "cyclades.total_cpu": vm_res["total_cpu"],
               "cyclades.disk": vm_res["disk"] * GiB,
               "cyclades.total_ram": vm_res["total_ram"] * MiB}
        holdings[user][project] = res

    vm_active_resources = vms.values("userid", "project")\
        .filter(Q(operstate="STARTED") | Q(operstate="BUILD") |
                Q(operstate="ERROR"))\
        .annotate(ram=Sum("flavor__ram"),
                  cpu=Sum("flavor__cpu"))

    for vm_res in vm_active_resources.iterator():
        user = vm_res['userid']
        project = vm_res['project']
        holdings[user][project]["cyclades.cpu"] = vm_res["cpu"]
        holdings[user][project]["cyclades.ram"] = vm_res["ram"] * MiB

    # Get resources related with networks
    net_resources = networks.values("userid", "project")\
                            .annotate(num=Count("id"))

    for net_res in net_resources.iterator():
        user = net_res['userid']
        if user is None:
            continue
        project = net_res['project']
        holdings[user][project]["cyclades.network.private"] = net_res["num"]

    floating_ips_resources = floating_ips.values("userid", "project")\
                                         .annotate(num=Count("id"))

    for floating_ip_res in floating_ips_resources.iterator():
        user = floating_ip_res["userid"]
        project = floating_ip_res["project"]
        holdings[user][project]["cyclades.floating_ip"] = \
            floating_ip_res["num"]

    return holdings


def get_db_project_holdings(project=None):
    """Get holdings from Cyclades DB."""
    holdings = QuotaDict()

    vms = VirtualMachine.objects.filter(deleted=False)
    networks = Network.objects.filter(deleted=False)
    floating_ips = IPAddress.objects.filter(deleted=False, floating_ip=True)

    if project is not None:
        vms = vms.filter(project=project)
        networks = networks.filter(project=project)
        floating_ips = floating_ips.filter(project=project)

    # Get resources related with VMs
    vm_resources = vms.values("project")\
        .annotate(num=Count("id"),
                  total_ram=Sum("flavor__ram"),
                  total_cpu=Sum("flavor__cpu"),
                  disk=Sum("flavor__disk"))

    for vm_res in vm_resources.iterator():
        project = vm_res['project']
        res = {"cyclades.vm": vm_res["num"],
               "cyclades.total_cpu": vm_res["total_cpu"],
               "cyclades.disk": vm_res["disk"] * GiB,
               "cyclades.total_ram": vm_res["total_ram"] * MiB}
        holdings[project] = res

    vm_active_resources = vms.values("project")\
        .filter(Q(operstate="STARTED") | Q(operstate="BUILD") |
                Q(operstate="ERROR"))\
        .annotate(ram=Sum("flavor__ram"),
                  cpu=Sum("flavor__cpu"))

    for vm_res in vm_active_resources.iterator():
        project = vm_res['project']
        holdings[project]["cyclades.cpu"] = vm_res["cpu"]
        holdings[project]["cyclades.ram"] = vm_res["ram"] * MiB

    # Get resources related with networks
    net_resources = networks.values("project").annotate(num=Count("id"))

    for net_res in net_resources.iterator():
        project = net_res['project']
        if project is None:
            continue
        holdings[project]["cyclades.network.private"] = net_res["num"]

    floating_ips_resources = floating_ips.values("project")\
        .annotate(num=Count("id"))

    for floating_ip_res in floating_ips_resources.iterator():
        project = floating_ip_res["project"]
        holdings[project]["cyclades.floating_ip"] = floating_ip_res["num"]

    return holdings


def get_quotaholder_holdings(user=None):
    """Get quotas from Quotaholder for all Cyclades resources.

    Returns quotas for all users, unless a single user is specified.
    """
    qh = Quotaholder.get()
    return qh.service_get_quotas(user)


def get_qh_users_holdings(users=None):
    qh = Quotaholder.get()
    if users is None or len(users) != 1:
        req = None
    else:
        req = users[0]
    quotas = qh.service_get_quotas(req)

    if users is None:
        return quotas

    qs = {}
    for user in users:
        try:
            qs[user] = quotas[user]
        except KeyError:
            pass
    return qs


def get_qh_project_holdings(projects=None):
    qh = Quotaholder.get()
    if projects is None or len(projects) != 1:
        req = None
    else:
        req = projects[0]
    quotas = qh.service_get_project_quotas(req)

    if projects is None:
        return quotas

    qs = {}
    for project in projects:
        try:
            qs[project] = quotas[project]
        except KeyError:
            pass
    return qs


def transform_quotas(quotas):
    d = {}
    for resource, counters in quotas.iteritems():
        used = counters['usage']
        limit = counters['limit']
        pending = counters['pending']
        d[resource] = (used, limit, pending)
    return d


def transform_project_quotas(quotas):
    d = {}
    for resource, counters in quotas.iteritems():
        used = counters['project_usage']
        limit = counters['project_limit']
        pending = counters['project_pending']
        d[resource] = (used, limit, pending)
    return d
