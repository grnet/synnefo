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

import sys
from snf_django.management.utils import pprint_table
from synnefo.lib.ordereddict import OrderedDict
from snf_django.lib.astakos import UserCache
from synnefo.settings import (CYCLADES_SERVICE_TOKEN as ASTAKOS_TOKEN,
                              ASTAKOS_AUTH_URL)
from synnefo.db.models import Backend, pooled_rapi_client
from synnefo.db.pools import bitarray_to_map

from synnefo.logic.rapi import GanetiApiError
from synnefo.logic.reconciliation import (nics_from_instance,
                                          disks_from_instance)
from synnefo.management.common import get_image


def pprint_network(network, display_mails=False, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "State of Network %s in DB" % network.id

    ucache = UserCache(ASTAKOS_AUTH_URL, ASTAKOS_TOKEN)
    userid = network.userid

    db_network = OrderedDict([
        ("name", network.name),
        ("backend-name", network.backend_id),
        ("state", network.state),
        ("userid", userid),
        ("username", ucache.get_name(userid) if display_mails else None),
        ("public", network.public),
        ("floating_ip_pool", network.floating_ip_pool),
        ("external_router", network.external_router),
        ("drained", network.drained),
        ("MAC prefix", network.mac_prefix),
        ("flavor", network.flavor),
        ("link", network.link),
        ("mode", network.mode),
        ("deleted", network.deleted),
        ("tags", "), ".join(network.backend_tag)),
        ("action", network.action)])

    pprint_table(stdout, db_network.items(), None, separator=" | ",
                 title=title)


def pprint_network_subnets(network, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "Subnets of network %s" % network.id

    subnets = list(network.subnets.values_list("id", "name", "ipversion",
                                               "cidr", "gateway", "dhcp",
                                               "deleted"))
    headers = ["ID", "Name", "Version", "CIDR", "Gateway", "DHCP",
               "Deleted"]
    pprint_table(stdout, subnets, headers, separator=" | ",
                 title=title)


def pprint_network_backends(network, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "State of Network %s in DB for each backend" % network.id
    bnets = list(network.backend_networks.values_list(
        "backend__clustername",
        "operstate", "deleted", "backendjobid",
        "backendopcode", "backendjobstatus"))
    headers = ["Backend", "State", "Deleted", "JobID", "Opcode",
               "JobStatus"]
    pprint_table(stdout, bnets, headers, separator=" | ",
                 title=title)


def pprint_network_in_ganeti(network, stdout=None):
    if stdout is None:
        stdout = sys.stdout
    for backend in Backend.objects.exclude(offline=True):
        with pooled_rapi_client(backend) as client:
            try:
                g_net = client.GetNetwork(network.backend_id)
                ip_map = g_net.pop("map")
                pprint_table(stdout, g_net.items(), None,
                             title="State of network in backend: %s" %
                                   backend.clustername)
                if network.subnet4 is not None:
                    pprint_pool(None, ip_map, 80, stdout)
            except GanetiApiError as e:
                if e.code == 404:
                    stdout.write('Network does not exist in backend %s\n' %
                                 backend.clustername)
                else:
                    raise e


def pprint_subnet_in_db(subnet, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "State of Subnet %s in DB" % subnet.id
    info = OrderedDict([("ID", subnet.id),
                        ("Network_ID", subnet.network.id),
                        # If a user names his subnet "-", what happens then?
                        ("User_ID", subnet.userid),
                        ("Name", "-" if subnet.name == "" else subnet.name),
                        ("IP_Version", subnet.ipversion),
                        ("CIDR", subnet.cidr),
                        ("Gateway", subnet.gateway),
                        ("Public", subnet.public),
                        ("DHCP/SLAAC", subnet.dhcp),
                        ("Host_Routes", subnet.host_routes),
                        ("DNS_Nameservers", subnet.dns_nameservers)])
    pprint_table(stdout, info.items(), None, separator=" | ", title=title)


def pprint_ippool(subnet, stdout=None, title=None):
    """Pretty print IP Pools of a subnet. Only IPv4 subnets have IP Pools"""

    if int(subnet.ipversion) != 4:
        return 0

    if stdout is None:
        stdout = sys.stdout

    stdout.write("IP Pools of subnet %s:\n\n" % subnet.id)

    for pool in subnet.get_ip_pools():
        size = pool.pool_size
        available = pool.available.count()
        info = OrderedDict([("First_IP", pool.return_start()),
                            ("Last_IP", pool.return_end()),
                            ("Size", size),
                            ("Available", available)])
        pprint_table(stdout, info.items(), None, separator=" | ", title=None)

        reserved = [pool.index_to_value(index)
                    for index, ip in enumerate(pool.reserved[:size])
                    if ip is False]

        if reserved != []:
            stdout.write("\nExternally Reserved IPs:\n\n")
            stdout.write(", ".join(reserved) + "\n")

        ip_sum = pool.available[:size] & pool.reserved[:size]
        pprint_pool(None, bitarray_to_map(ip_sum), 80, stdout)
        stdout.write("\n\n")


def pool_map_chunks(smap, step=64):
    for i in xrange(0, len(smap), step):
        yield smap[i:i + step]


def splitPoolMap(s, count):
    chunks = pool_map_chunks(s, count)
    acc = []
    count = 0
    for chunk in chunks:
        chunk_len = len(chunk)
        acc.append(str(count).rjust(3) + ' ' + chunk + ' ' +
                   str(count + chunk_len - 1).ljust(4))
        count += chunk_len
    return '\n' + '\n'.join(acc)


def pprint_pool(name, pool_map, step=80, stdout=None):
    if stdout is None:
        stdout = sys.stdout
    if name is not None:
        stdout.write("Pool: %s\n" % name)
    stdout.write(splitPoolMap(pool_map, count=step))
    stdout.write("\n")


def pprint_port(port, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "State of Port %s in DB" % port.id
    port = OrderedDict([
        ("id", port.id),
        ("name", port.name),
        ("userid", port.userid),
        ("server", port.machine_id),
        ("network", port.network_id),
        ("device_owner", port.device_owner),
        ("mac", port.mac),
        ("state", port.state)])

    pprint_table(stdout, port.items(), None, separator=" | ",
                 title=title)


def pprint_port_ips(port, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "IP Addresses of Port %s" % port.id
    ips = list(port.ips.values_list("address", "network_id", "subnet_id",
                                    "subnet__cidr", "floating_ip"))
    headers = ["Address", "Network", "Subnet", "CIDR", "is_floating"]
    pprint_table(stdout, ips, headers, separator=" | ",
                 title=title)


def pprint_port_in_ganeti(port, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "State of Port %s in Ganeti" % port.id

    vm = port.machine
    if vm is None:
        stdout.write("Port is not attached to any instance.\n")
        return

    client = vm.get_client()
    try:
        vm_info = client.GetInstance(vm.backend_vm_id)
    except GanetiApiError as e:
        if e.code == 404:
            stdout.write("Port seems attached to server %s, but"
                         " server does not exist in backend.\n"
                         % vm)
            return
        raise e

    nics = nics_from_instance(vm_info)
    try:
        gnt_nic = filter(lambda nic: nic.get("name") == port.backend_uuid,
                         nics)[0]
        gnt_nic["instance"] = vm_info["name"]
    except IndexError:
        stdout.write("Port %s is not attached to instance %s\n" %
                     (port.id, vm.id))
        return
    pprint_table(stdout, gnt_nic.items(), None, separator=" | ",
                 title=title)

    vm.put_client(client)


def pprint_server(server, display_mails=False, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "State of Server %s in DB" % server.id

    ucache = UserCache(ASTAKOS_AUTH_URL, ASTAKOS_TOKEN)
    userid = server.userid

    try:
        image = get_image(server.imageid, server.userid)['name']
    except:
        image = server.imageid

    server_dict = OrderedDict([
        ("id", server.id),
        ("name", server.name),
        ("userid", server.userid),
        ("username", ucache.get_name(userid) if display_mails else None),
        ("flavor_id", server.flavor_id),
        ("flavor_name", server.flavor.name),
        ("imageid", server.imageid),
        ("image_name", image),
        ("state", server.operstate),
        ("backend", server.backend),
        ("deleted", server.deleted),
        ("action", server.action),
        ("task", server.task),
        ("task_job_id", server.task_job_id),
        ("backendjobid", server.backendjobid),
        ("backendopcode", server.backendopcode),
        ("backendjobstatus", server.backendjobstatus),
        ("backend_time", server.backendtime),
        ])

    pprint_table(stdout, server_dict.items(), None, separator=" | ",
                 title=title)


def pprint_server_nics(server, stdout=None, title=None):
    if title is None:
        title = "Ports of Server %s" % server.id
    if stdout is None:
        stdout = sys.stdout

    nics = []
    for nic in server.nics.all():
        nics.append((nic.id, nic.name, nic.index, nic.mac, nic.ipv4_address,
                     nic.ipv6_address, nic.network, nic.firewall_profile,
                     nic.state))

    headers = ["ID", "Name", "Index", "MAC", "IPv4 Address", "IPv6 Address",
               "Network", "Firewall", "State"]
    pprint_table(stdout, nics, headers, separator=" | ",
                 title=title)


def pprint_server_volumes(server, stdout=None, title=None):
    if title is None:
        title = "Volumes of Server %s" % server.id
    if stdout is None:
        stdout = sys.stdout

    vols = []
    for vol in server.volumes.filter(deleted=False):
        volume_type = vol.volume_type
        vols.append((vol.id, vol.name, vol.index, vol.size,
                     volume_type.template, volume_type.provider,
                     vol.status, vol.source))

    headers = ["ID", "Name", "Index", "Size", "Template", "Provider",
               "Status", "Source"]
    pprint_table(stdout, vols, headers, separator=" | ",
                 title=title)


def pprint_server_in_ganeti(server, print_jobs=False, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "State of Server %s in Ganeti" % server.id

    client = server.get_client()
    try:
        server_info = client.GetInstance(server.backend_vm_id)
    except GanetiApiError as e:
        if e.code == 404:
            stdout.write("Server '%s' does not exist in backend '%s'\n"
                         % (server.id, server.backend.clustername))
            return
        raise e
    server.put_client(client)

    GANETI_INSTANCE_FIELDS = ('name', 'oper_state', 'admin_state', 'status',
                              'pnode', 'snode', 'network_port',
                              'disk_template', 'disk_usage',
                              'oper_ram', 'oper_vcpus', 'mtime')
    server_dict = OrderedDict([(k, server_info.get(k))
                              for k in GANETI_INSTANCE_FIELDS])

    pprint_table(stdout, server_dict.items(), None, separator=" | ",
                 title=title)
    stdout.write("\n")

    nics = nics_from_instance(server_info)
    nics_keys = ["ip", "mac", "name", "network"]
    nics_values = [[nic[key] for key in nics_keys] for nic in nics]
    pprint_table(stdout, nics_values, nics_keys, separator=" | ",
                 title="NICs of Server %s in Ganeti" % server.id)

    stdout.write("\n")
    disks = disks_from_instance(server_info)
    disks_keys = ["name", "size"]
    disks_values = [[disk[key] for key in disks_keys] for disk in disks]
    pprint_table(stdout, disks_values, disks_keys, separator=" | ",
                 title="Disks of Server %s in Ganeti" % server.id)

    if not print_jobs:
        return

    client = server.get_client()
    jobs = client.GetJobs(bulk=True)
    server_jobs = filter(
        lambda x: server.backend_vm_id in (" ".join(x.get("summary"))), jobs)

    GANETI_JOB_FIELDS = ('id', 'status', 'summary', 'opresult', 'opstatus',
                         'oplog', 'start_ts', 'end_ts')
    for server_job in server_jobs:
        stdout.write("\n")
        values = [server_job.get(k) for k in GANETI_JOB_FIELDS]
        pprint_table(stdout, zip(GANETI_JOB_FIELDS, values), None,
                     separator=" | ",
                     title="Ganeti Job %s" % server_job["id"])
    server.put_client(client)


def pprint_volume(volume, display_mails=False, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "State of volume %s in DB" % volume.id

    ucache = UserCache(ASTAKOS_AUTH_URL, ASTAKOS_TOKEN)
    userid = volume.userid

    volume_type = volume.volume_type
    volume_dict = OrderedDict([
        ("id", volume.id),
        ("size", volume.size),
        ("disk_template", volume_type.template),
        ("disk_provider", volume_type.provider),
        ("server_id", volume.machine_id),
        ("userid", volume.userid),
        ("username", ucache.get_name(userid) if display_mails else None),
        ("index", volume.index),
        ("name", volume.name),
        ("state", volume.status),
        ("delete_on_termination", volume.delete_on_termination),
        ("deleted", volume.deleted),
        ("backendjobid", volume.backendjobid),
        ])

    pprint_table(stdout, volume_dict.items(), None, separator=" | ",
                 title=title)


def pprint_volume_in_ganeti(volume, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "State of volume %s in Ganeti" % volume.id

    vm = volume.machine
    if vm is None:
        stdout.write("volume is not attached to any instance.\n")
        return

    client = vm.get_client()
    try:
        vm_info = client.GetInstance(vm.backend_vm_id)
    except GanetiApiError as e:
        if e.code == 404:
            stdout.write("Volume seems attached to server %s, but"
                         " server does not exist in backend.\n"
                         % vm)
            return
        raise e

    disks = disks_from_instance(vm_info)
    try:
        gnt_disk = filter(lambda disk:
                          disk.get("name") == volume.backend_volume_uuid,
                          disks)[0]
        gnt_disk["instance"] = vm_info["name"]
    except IndexError:
        stdout.write("Volume %s is not attached to instance %s\n" % (volume.id,
                                                                     vm.id))
        return
    pprint_table(stdout, gnt_disk.items(), None, separator=" | ",
                 title=title)

    vm.put_client(client)


def pprint_volume_type(volume_type, stdout=None, title=None):
    if stdout is None:
        stdout = sys.stdout
    if title is None:
        title = "Volume Type %s" % volume_type.id

    vtype_info = OrderedDict([
        ("name", volume_type.name),
        ("disk template", volume_type.disk_template),
        ("deleted", volume_type.deleted),
    ])

    pprint_table(stdout, vtype_info.items(), separator=" | ", title=title)
