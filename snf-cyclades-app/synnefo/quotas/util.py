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

from django.db.models import Sum, Count, Q

from synnefo.db.models import VirtualMachine, Network, IPAddress, Volume
from synnefo.quotas import Quotaholder
from collections import defaultdict

QuotaDict = lambda: defaultdict(lambda: defaultdict(dict))

MiB = 2 ** 20
GiB = 2 ** 30


def get_db_holdings(user=None, project=None, for_users=True):
    """Get per user or per project holdings from Cyclades DB."""

    if for_users is False and user is not None:
        raise ValueError(
            "Computing per project holdings; setting a user is meaningless.")
    holdings = QuotaDict()

    vms = VirtualMachine.objects.filter(deleted=False)
    networks = Network.objects.filter(deleted=False)
    floating_ips = IPAddress.objects.filter(deleted=False, floating_ip=True)
    volumes = Volume.objects.filter(deleted=False)

    if for_users and user is not None:
        vms = vms.filter(userid=user)
        networks = networks.filter(userid=user)
        floating_ips = floating_ips.filter(userid=user)
        volumes = volumes.filter(userid=user)

    if project is not None:
        vms = vms.filter(project=project)
        networks = networks.filter(project=project)
        floating_ips = floating_ips.filter(project=project)
        volumes = volumes.filter(project=project)

    values = ["project"]
    if for_users:
        values.append("userid")

    vm_resources = vms.values(*values)\
        .annotate(num=Count("id"),
                  total_ram=Sum("flavor__ram"),
                  total_cpu=Sum("flavor__cpu"))
    for vm_res in vm_resources.iterator():
        project = vm_res['project']
        res = {"cyclades.vm": vm_res["num"],
               "cyclades.total_cpu": vm_res["total_cpu"],
               "cyclades.total_ram": vm_res["total_ram"] * MiB}
        pholdings = holdings[vm_res['userid']] if for_users else holdings
        pholdings[project] = res

    vm_active_resources = vms.values(*values)\
        .filter(Q(operstate="STARTED") | Q(operstate="BUILD") |
                Q(operstate="ERROR"))\
        .annotate(ram=Sum("flavor__ram"),
                  cpu=Sum("flavor__cpu"))

    for vm_res in vm_active_resources.iterator():
        project = vm_res['project']
        pholdings = holdings[vm_res['userid']] if for_users else holdings
        pholdings[project]["cyclades.cpu"] = vm_res["cpu"]
        pholdings[project]["cyclades.ram"] = vm_res["ram"] * MiB

    # Get disk resource
    disk_resources = volumes.values(*values).annotate(Sum("size"))
    for disk_res in disk_resources.iterator():
        project = disk_res['project']
        pholdings = (holdings[disk_res['userid']]
                     if for_users else holdings)
        pholdings[project]["cyclades.disk"] = disk_res["size__sum"] * GiB

    # Get resources related with networks
    net_resources = networks.values(*values)\
                            .annotate(num=Count("id"))

    for net_res in net_resources.iterator():
        project = net_res['project']
        if project is None:
            continue
        pholdings = holdings[net_res['userid']] if for_users else holdings
        pholdings[project]["cyclades.network.private"] = net_res["num"]

    floating_ips_resources = floating_ips.values(*values)\
                                         .annotate(num=Count("id"))

    for floating_ip_res in floating_ips_resources.iterator():
        project = floating_ip_res["project"]
        pholdings = (holdings[floating_ip_res["userid"]]
                     if for_users else holdings)
        pholdings[project]["cyclades.floating_ip"] = \
            floating_ip_res["num"]

    return holdings


def get_quotaholder_holdings(user=None):
    """Get quotas from Quotaholder for all Cyclades resources.

    Returns quotas for all users, unless a single user is specified.
    """
    qh = Quotaholder.get()
    return qh.service_get_quotas(user)


def get_qh_users_holdings(users=None, projects=None):
    qh = Quotaholder.get()
    return qh.service_get_quotas(user=users, project_id=projects)


def get_qh_project_holdings(projects=None):
    qh = Quotaholder.get()
    return qh.service_get_project_quotas(project_id=projects)


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
