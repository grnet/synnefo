#!/usr/bin/env python

import os
import collectd

from glob import glob


def read_int(file):
    f = open(file, "r")
    try:
        val = int(f.read())
    except ValueError:
        val = None
    finally:
        f.close()

    return val


def netstats(data=None):
    for dir in glob("/var/run/ganeti/kvm-hypervisor/nic/*"):
        if not os.path.isdir(dir):
            continue

        hostname = os.path.basename(dir)

        for nic in glob(os.path.join(dir, "*")):
            try:
                idx = int(os.path.basename(nic))
            except ValueError:
                continue
            with open(nic) as nicfile:
                try:
                    iface = nicfile.readline().strip()
                except EnvironmentError:
                    continue

            if not os.path.isdir("/sys/class/net/%s" % iface):
                continue

            bytes_in = read_int("/sys/class/net/%s/statistics/rx_bytes"
                                % iface)
            bytes_out = read_int("/sys/class/net/%s/statistics/tx_bytes"
                                 % iface)

            vl = collectd.Values(type="derive")
            vl.host = hostname
            vl.plugin = "interface"
            vl.type = "if_octets"
            vl.type_instance = "eth%d" % idx
            vl.dispatch(values=[bytes_out, bytes_in])

collectd.register_read(netstats)

# vim: set ts=4 sts=4 et sw=4 :
