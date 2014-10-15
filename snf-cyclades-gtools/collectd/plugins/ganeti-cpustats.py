#!/usr/bin/env python

import os
import collectd

from glob import glob


def get_vcpus(pid):
    """Get a KVM instance vCPU count by looking at its fd's"""
    vcpus = 0
    for fd in glob("/proc/%d/fd/*" % pid):
        # XXX: sad but trueeeeeeeeeeee
        if os.readlink(fd) == "anon_inode:kvm-vcpu":
            vcpus += 1
    return vcpus


def cpustats(data=None):
    for file in glob("/var/run/ganeti/kvm-hypervisor/pid/*"):
        instance = os.path.basename(file)
        try:
            pid = int(open(file, "r").read())
            proc = open("/proc/%d/stat" % pid, "r")
            cputime = [int(proc.readline().split()[42])]
        except EnvironmentError:
            continue
        vcpus = get_vcpus(pid)
        proc.close()

        if vcpus == 0:
            continue

        vl = collectd.Values(type="derive")
        vl.host = instance
        vl.plugin = "cpu"
        vl.type = "virt_cpu_total"
        total = sum(cputime) * 100 / (vcpus * os.sysconf("SC_CLK_TCK"))
        vl.dispatch(values=[total])

collectd.register_read(cpustats)

# vim: set ts=4 sts=4 et sw=4 :
