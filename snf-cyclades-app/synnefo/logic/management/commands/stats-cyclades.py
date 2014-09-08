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

from __future__ import division
import sys
import operator
import json

from optparse import make_option
from collections import defaultdict

from snf_django.management.utils import pprint_table, parse_bool

from snf_django.management.commands import SynnefoCommand, CommandError
from synnefo.management.common import get_resource
from synnefo.admin import stats as statistics
from synnefo.util import units


class Command(SynnefoCommand):
    help = "Get available statistics about the Cyclades service"
    can_import_settings = True

    command_option_list = (
        make_option("--backend",
                    dest="backend",
                    help="Include statistics only for this backend"),
        make_option("--clusters",
                    dest="clusters",
                    default="True",
                    metavar="True|False",
                    choices=["True", "False"],
                    help="Include statistics about clusters (default=True)"),
        make_option("--cluster-details",
                    dest="cluster_details",
                    default="True",
                    metavar="True|False",
                    choices=["True", "False"],
                    help="Include detail statistics about each Ganeti cluster"
                         " (default=True)"),
        make_option("--servers",
                    dest="servers",
                    default="True",
                    metavar="True|False",
                    choices=["True", "False"],
                    help="Include statistics about servers (default=True)"),
        make_option("--ip-pools",
                    dest="ip_pools",
                    default="True",
                    metavar="True|False",
                    choices=["True", "False"],
                    help="Include statistics about public IPv4 allocation"
                         " pools (default=True)"),
        make_option("--networks",
                    dest="networks",
                    default="True",
                    metavar="True|False",
                    choices=["True", "False"],
                    help="Include statistics about networks (default=True)"),
        make_option("--images",
                    dest="images",
                    default="True",
                    metavar="True|False",
                    choices=["True", "False"],
                    help="Include statistics about images (default=True)"),
        make_option("--json-file",
                    dest="json_file",
                    help="Pretty print statistics from a JSON file."),
    )

    def handle(self, *args, **options):
        if options["backend"] is not None:
            backend = get_resource("backend", options["backend"])
        else:
            backend = None

        clusters = parse_bool(options["clusters"])
        servers = parse_bool(options["servers"])
        images = parse_bool(options["images"])
        if backend is None:
            ip_pools = parse_bool(options["ip_pools"])
            networks = parse_bool(options["networks"])
        else:
            ip_pools = False
            networks = False

        if options["json_file"] is None:
            stats = statistics.get_cyclades_stats(backend, clusters, servers,
                                                  ip_pools, networks, images)
        else:
            with open(options["json_file"]) as data_file:
                stats = json.load(data_file)

        output_format = options["output_format"]
        if output_format == "json":
            self.stdout.write(json.dumps(stats, indent=4) + "\n")
        elif output_format == "pretty":
            cluster_details = parse_bool(options["cluster_details"])
            pretty_print_stats(stats, self.stdout,
                               cluster_details=cluster_details)
        else:
            raise CommandError("Output format '%s' not supported." %
                               output_format)


def pprint_clusters(clusters, stdout, detail=True):
    t_backend_cnt, t_vms = 0, 0
    t_nodes_cnt, t_vm_cap_cnt, t_offline_cnt, t_drained_cnt = 0, 0, 0, 0
    t_cpu = 0
    t_mused, t_mtotal = 0, 0
    t_dused, t_dtotal = 0, 0
    t_vcpu, t_vram, t_vdisk = 0, 0, 0
    for cluster_name, c_info in sorted(clusters.items()):
        t_backend_cnt += 1
        node_table = []
        c_nodes_cnt, c_vm_cap_cnt, c_offline_cnt, c_drained_cnt = 0, 0, 0, 0
        c_cpu = 0
        c_mfree, c_mused, c_mtotal = 0, 0, 0
        c_dfree, c_dused, c_dtotal = 0, 0, 0
        for node_name, n_info in sorted(c_info["nodes"].items()):
            c_nodes_cnt += 1
            if not n_info["vm_capable"]:
                continue
            c_vm_cap_cnt += 1
            drained, offline = n_info["drained"], n_info["offline"]
            state = "online"
            if c_info["offline"]:
                state = "offline"
            if c_info["drained"]:
                state += " (drained)"
            cpu = n_info["cpu"]
            ram, disk = n_info["ram"], n_info["disk"]
            mfree, mtotal = int(ram["free"]), int(ram["total"])
            mused = mtotal - mfree
            dfree, dtotal = int(disk["free"]), int(disk["total"])
            dused = dtotal - dfree
            if offline:
                c_offline_cnt += 1
            if drained:
                c_drained_cnt += 1
            c_mtotal += mtotal
            c_dtotal += dtotal
            if not offline:
                c_cpu += cpu
                c_mfree += mfree
                c_mused += mused
                c_dfree += dfree
                c_dused += dused
            mpercentage = ("%.2f%%" % (100 * mused / mtotal))\
                if mtotal != 0 else "-"
            dpercentage = ("%.2f%%" % (100 * dused / dtotal))\
                if dtotal != 0 else "-"
            node_table.append((node_name, state, n_info["instances"], cpu,
                               "%s/%s %s" % (units.show(mused, "bytes"),
                                             units.show(mtotal, "bytes"),
                                             mpercentage),
                               "%s/%s %s" % (units.show(dused, "bytes"),
                                             units.show(dtotal, "bytes"),
                                             dpercentage),))
        state = "online"
        if c_info["offline"]:
            state = "offline"
        if c_info["drained"]:
            state += " (drained)"
        virtual_cpu = c_info["virtual_cpu"]
        virtual_ram = c_info["virtual_ram"]
        virtual_disk = c_info["virtual_disk"]
        if not c_info["offline"]:
            t_cpu += c_cpu
            t_mused += c_mused
            t_mtotal += c_mtotal
            t_dused += c_dused
            t_dtotal += c_dtotal
            t_vcpu += virtual_cpu
            t_vdisk += virtual_disk
            t_vram += virtual_ram
            t_nodes_cnt += c_nodes_cnt
            t_vm_cap_cnt += c_vm_cap_cnt
            t_offline_cnt += c_offline_cnt
            t_drained_cnt += c_drained_cnt
            t_vms += int(c_info["virtual_servers"])
        if not detail:
            continue
        cluster_table = (
            ("Name", cluster_name),
            ("State", state),
            ("Nodes", "Total: %s, VM Capable: %s, Drained %s Offline: %s" %
                      (c_nodes_cnt, c_vm_cap_cnt, c_drained_cnt,
                       c_offline_cnt)),
            ("Disk Templates", ", ".join(c_info["disk_templates"])),
            ("Hypervisor", c_info["hypervisor"]),
            ("Instances", c_info["virtual_servers"]),
            ("Virtual CPUs", virtual_cpu),
            ("Physical CPUs", c_cpu),
            ("V/P CPUs", ("%.2f%%" % (100 * virtual_cpu / c_cpu))),
            ("Virtual RAM", units.show(virtual_ram, "bytes")),
            ("Physical RAM (used/total)",
                "%s/%s %s%%" % (units.show(c_mused, "bytes"),
                                units.show(c_mtotal, "bytes"),
                                ("%.2f%%" % (100 * c_mused / c_mtotal)
                                    if c_mtotal != 0 else "-"))),
            ("V/P used RAM", ("%.2f%%" % (100 * virtual_ram / c_mused)
                              if c_mused != 0 else "-")),
            ("V/P total RAM", ("%.2f%%" % (100 * virtual_ram / c_mtotal)
                               if c_mtotal != 0 else "-")),
            ("Virtual disk", units.show(virtual_disk, "bytes")),
            ("Physical Disk (used/total)",
                "%s/%s %s%%" % (units.show(c_dused, "bytes"),
                                units.show(c_dtotal, "bytes"),
                                ("%.2f%%" % (100 * c_dused/c_dtotal)
                                 if c_dtotal != 0 else "-"))),
            ("V/P used disk", ("%.2f%%" % (100 * virtual_disk / c_dused)
                               if c_dused != 0 else "-")),
            ("V/P total disk", ("%.2f%%" % (100 * virtual_disk / c_dtotal)
                                if c_dtotal != 0 else "-")),
        )
        pprint_table(stdout, cluster_table, headers=None, separator=" | ",
                     title="Statistics for backend %s" % cluster_name)
        headers = ("Node Name", "State", "VMs",
                   "CPUs", "RAM (used/total)", "Disk (used/total)")
        pprint_table(stdout, node_table, headers, separator=" | ",
                     title="Statistics per node for backend %s" % cluster_name)

    total_table = (
        ("Backend", t_backend_cnt),
        ("Nodes", "Total: %s, VM Capable: %s, Drained %s Offline: %s" %
                  (t_nodes_cnt, t_vm_cap_cnt, t_drained_cnt, t_offline_cnt)),
        ("Instances", t_vms),
        ("Virtual CPUs", t_vcpu),
        ("Physical CPUs", t_cpu),
        ("V/P CPUs", ("%.2f%%" % (100 * t_vcpu / t_cpu))),
        ("Virtual RAM", units.show(t_vram, "bytes")),
        ("Physical RAM (used/total)", "%s/%s %s%%" %
            (units.show(t_mused, "bytes"), units.show(t_mtotal, "bytes"),
             ("%.2f%%" % (100 * t_mused/t_mtotal) if t_mtotal != 0 else "-"))),
        ("V/P used RAM", ("%.2f%%" % (100 * t_vram / t_mused)
                          if t_mused != 0 else "-")),
        ("V/P total RAM", ("%.2f%%" % (100 * t_vram / t_mtotal)
                           if t_mtotal != 0 else "-")),
        ("Virtual disk", units.show(t_vdisk, "bytes")),
        ("Physical Disk (used/total)",
            "%s/%s %s%%" % (units.show(t_dused, "bytes"),
                            units.show(t_dtotal, "bytes"),
                            ("%.2f%%" % (100 * t_dused/t_dtotal)
                             if t_dtotal != 0 else "-"))),
        ("V/P used disk", ("%.2f%%" % (100 * t_vdisk / t_dused)
                           if t_dused != 0 else "-")),
        ("V/P total disk", ("%.2f%%" % (100 * t_vdisk / t_dtotal)
                            if t_dtotal != 0 else "-")),
    )

    if len(clusters) > 1:
        stdout.write("\n")
        pprint_table(stdout, total_table, headers=None, separator=" | ",
                     title="Statistics for all backends")


def pprint_servers(servers, stdout):
    # Print server stats per state
    per_state = []
    for state, stats in sorted(servers.items()):
        count = stats["count"]
        cpu = reduce(operator.add,
                     [int(k) * int(v) for k, v in stats["cpu"].items()], 0)
        ram = reduce(operator.add,
                     [int(k) * int(v) for k, v in stats["ram"].items()], 0)
        disk = 0
        for disk_template, disk_stats in stats["disk"].items():
            disk = reduce(operator.add,
                          [int(k) * int(v) for k, v in disk_stats.items()],
                          disk)
        per_state.append((state, count, cpu, units.show(ram, "bytes", "auto"),
                          units.show(disk, "bytes", "auto")))
    headers = ("State", "Servers", "CPUs", "RAM", "Disk")
    pprint_table(stdout, per_state, headers, separator=" | ",
                 title="Servers Per Operational State")
    stdout.write("\n")

    # Print server stats per CPU
    per_cpu = []
    cpu_stats = defaultdict(dict)
    for state, stats in servers.items():
        for cpu, cpu_cnt in stats["cpu"].items():
            cpu_stats[cpu][state] = cpu_cnt
            cpu_stats[cpu]["total"] = \
                cpu_stats[cpu].setdefault("total", 0) + int(cpu_cnt)
    for cpu, _cpu_stats in sorted(cpu_stats.items()):
        per_cpu.append((cpu, _cpu_stats["total"],
                        _cpu_stats.get("started", 0),
                        _cpu_stats.get("stopped", 0),
                        _cpu_stats.get("error", 0)))
    headers = ("CPUs", "Total", "Started", "Stopped", "Error")
    pprint_table(stdout, per_cpu, headers, separator=" | ",
                 title="Servers Per CPU")
    stdout.write("\n")

    # Print server stats per RAM
    per_ram = []
    ram_stats = defaultdict(dict)
    for state, stats in servers.items():
        for ram, ram_cnt in stats["ram"].items():
            ram_stats[ram][state] = ram_cnt
            ram_stats[ram]["total"] = \
                ram_stats[ram].setdefault("total", 0) + int(ram_cnt)
    for ram, _ram_stats in sorted(ram_stats.items()):
        per_ram.append((units.show(ram, "bytes", "auto"),
                        _ram_stats["total"],
                        _ram_stats.get("started", 0),
                        _ram_stats.get("stopped", 0),
                        _ram_stats.get("error", 0)))
    headers = ("RAM", "Total", "Started", "Stopped", "Error")
    pprint_table(stdout, per_ram, headers, separator=" | ",
                 title="Servers Per RAM")
    stdout.write("\n")

    # Print server stats per Disk Template
    per_disk_t = []
    disk_t_stats = defaultdict(dict)
    for state, stats in servers.items():
        for disk_t, disk_t_info in stats["disk"].items():
            disk_t_cnt = reduce(operator.add,
                                [v for v in disk_t_info.values()], 0)
            disk_t_stats[disk_t][state] = disk_t_cnt
            disk_t_stats[disk_t]["total"] = \
                disk_t_stats[disk_t].setdefault("total", 0) + int(disk_t_cnt)
    for disk_t, _disk_t_stats in sorted(disk_t_stats.items()):
        per_disk_t.append((disk_t, _disk_t_stats["total"],
                           _disk_t_stats.get("started", 0),
                           _disk_t_stats.get("stopped", 0),
                           _disk_t_stats.get("error", 0)))
    headers = ("Disk Template", "Total", "Started", "Stopped", "Error")
    pprint_table(stdout, per_disk_t, headers, separator=" | ",
                 title="Servers Per Disk Template")
    stdout.write("\n")

    # Print server stats per Disk Template
    per_disk_t_size = []
    disk_template_sizes = defaultdict(dict)
    disk_sizes = set()
    for state, stats in servers.items():
        for disk_t, disk_t_info in stats["disk"].items():
            if disk_t not in disk_template_sizes:
                disk_template_sizes[disk_t] = defaultdict(int)
            for disk_size, vm_count in disk_t_info.items():
                disk_sizes.add(disk_size)
                disk_template_sizes[disk_t][disk_size] += vm_count
    disk_sizes = sorted(list(disk_sizes))

    for disk_t, disk_info in disk_template_sizes.items():
        _line = [disk_t]
        for size in disk_sizes:
            _line.append(disk_info[size])
        per_disk_t_size.append(_line)
    headers = ["Disk Template"] + map(lambda x: units.show(x, "bytes"),
                                      disk_sizes)
    pprint_table(stdout, per_disk_t_size, headers, separator=" | ",
                 title="Servers per Disk Template and Disk Size")
    stdout.write("\n")

    # Print server stats per disk size
    per_disk = []
    disk_stats = defaultdict(dict)
    for state, stats in servers.items():
        for disk_t, disk_info in stats["disk"].items():
            for disk, disk_cnt in disk_info.items():
                if disk not in disk_stats:
                    disk_stats[disk] = defaultdict(dict)
                disk_stats[disk][state] = \
                    disk_stats[disk].setdefault(state, 0) + int(disk_cnt)
                disk_stats[disk]["total"] = \
                    disk_stats[disk].setdefault("total", 0) + int(disk_cnt)
    for disk, _disk_stats in sorted(disk_stats.items()):
        per_disk.append((units.show(disk, "bytes", "auto"),
                         _disk_stats["total"],
                         _disk_stats.get("started", 0),
                         _disk_stats.get("stopped", 0),
                         _disk_stats.get("error", 0)))
    headers = ("Disk Size", "Total", "Started", "Stopped", "Error")
    pprint_table(stdout, per_disk, headers, separator=" | ",
                 title="Servers Per Disk Size")
    stdout.write("\n")


def pprint_networks(networks, stdout):
    values = []
    for flavor, stats in sorted(networks.items()):
        active = int(stats.get("active", 0))
        error = int(stats.get("error", 0))
        values.append((flavor, active + error, active, error))
    headers = ("Flavor", "Total", "Active", "Error")
    pprint_table(stdout, values, headers, separator=" | ",
                 title="Statistics for Networks")
    stdout.write("\n")


def pprint_ip_pools(ip_pools, stdout):
    values = []
    for state, stats in sorted(ip_pools.items()):
        count = stats["count"]
        free = stats["free"]
        total = stats["total"]
        values.append((state, count, free, total))
    headers = ("State", "Number", "Free IPs", "Total IPs")
    pprint_table(stdout, values, headers, separator=" | ",
                 title="Statistics for Public IPv4 Pools")
    stdout.write("\n")


def pretty_print_stats(stats, stdout, cluster_details=True):
    newline = lambda: stdout.write("\n")

    _datetime = stats.get("datetime")
    stdout.write("datetime: %s\n" % _datetime)
    newline()

    servers = stats.get("servers")
    if servers is not None:
        pprint_servers(servers, stdout)
        newline()

    networks = stats.get("networks")
    if networks is not None:
        pprint_networks(networks, stdout)
        newline()

    ip_pools = stats.get("ip_pools")
    if ip_pools is not None:
        pprint_ip_pools(ip_pools, stdout)
        newline()

    images = stats.get("images")
    if images is not None:
        pprint_table(stdout, sorted(images.items()), separator=" | ",
                     title="Statistics for Images")
        newline()

    clusters = stats.get("clusters")
    if clusters is not None:
        pprint_clusters(clusters, stdout, detail=cluster_details)


if __name__ == "__main__":
    stats = statistics.get_cyclades_stats(clusters=True, servers=True,
                                          ip_pools=True, networks=True,
                                          images=True)
    pretty_print_stats(stats, sys.stdout)
    sys.exit(0)
