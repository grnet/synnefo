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

import time
from synnefo.db.models import VirtualMachine, IPAddress, NetworkInterface
from synnefo.logic import servers
from synnefo.logic import ips as logic_ips
from synnefo.logic import backend


MiB = 2 ** 20
GiB = 2 ** 30


def _partition_by(f, l, convert=None):
    if convert is None:
        convert = lambda x: x
    d = {}
    for x in l:
        group = f(x)
        group_l = d.get(group, [])
        group_l.append(convert(x))
        d[group] = group_l
    return d


CHANGE = {
    "cyclades.ram": lambda vm: vm.flavor.ram * MiB,
    "cyclades.cpu": lambda vm: vm.flavor.cpu,
    "cyclades.vm": lambda vm: 1,
    "cyclades.total_ram": lambda vm: vm.flavor.ram * MiB,
    "cyclades.total_cpu": lambda vm: vm.flavor.cpu,
    "cyclades.disk": lambda vm: vm.flavor.disk * GiB,
    "cyclades.floating_ip": lambda vm: 1,
    }


def wait_server_job(server):
    jobID = server.task_job_id
    client = server.get_client()
    status, error = backend.wait_for_job(client, jobID)
    if status != "success":
        raise ValueError(error)


VM_SORT_LEVEL = {
    "ERROR": 4,
    "BUILD": 3,
    "STOPPED": 2,
    "STARTED": 1,
    "RESIZE": 1,
    "DESTROYED": 0,
    }


def sort_vms():
    def f(vm):
        level = VM_SORT_LEVEL[vm.operstate]
        return (level, vm.id)
    return f


def handle_stop_active(viol_id, resource, vms, diff, actions):
    vm_actions = actions["vm"]
    vms = [vm for vm in vms if vm.operstate in ["STARTED", "BUILD", "ERROR"]]
    vms = sorted(vms, key=sort_vms(), reverse=True)
    for vm in vms:
        if diff < 1:
            break
        diff -= CHANGE[resource](vm)
        if vm_actions.get(vm.id) is None:
            action = "REMOVE" if vm.operstate == "ERROR" else "SHUTDOWN"
            vm_actions[vm.id] = viol_id, vm.operstate, vm.backend_id, action


def handle_destroy(viol_id, resource, vms, diff, actions):
    vm_actions = actions["vm"]
    vms = sorted(vms, key=sort_vms(), reverse=True)
    for vm in vms:
        if diff < 1:
            break
        diff -= CHANGE[resource](vm)
        vm_actions[vm.id] = viol_id, vm.operstate, vm.backend_id, "REMOVE"


def _state_after_action(vm, action):
    if action == "REMOVE":
        return "ERROR"  # highest
    if action == "SHUTDOWN":
        return "STOPPED"
    return vm.operstate  # no action


def _maybe_action(tpl):
    if tpl is None:
        return None
    return tpl[-1]


def sort_ips(vm_actions):
    def f(ip):
        if not ip.in_use():
            level = 5
        else:
            machine = ip.nic.machine
            action = _maybe_action(vm_actions.get(machine.id))
            level = VM_SORT_LEVEL[_state_after_action(machine, action)]
        return (level, ip.id)
    return f


def handle_floating_ip(viol_id, resource, ips, diff, actions):
    vm_actions = actions.get("vm", {})
    ip_actions = actions["floating_ip"]
    ips = sorted(ips, key=sort_ips(vm_actions), reverse=True)
    for ip in ips:
        if diff < 1:
            break
        diff -= CHANGE[resource](ip)
        state = "USED" if ip.in_use() else "FREE"
        if ip.nic and ip.nic.machine:
            backend_id = ip.nic.machine.backend_id
        else:
            backend_id = None
        ip_actions[ip.id] = viol_id, state, backend_id, "REMOVE"


def get_vms(users=None, projects=None):
    vms = VirtualMachine.objects.filter(deleted=False).\
        select_related("flavor").order_by('-id')
    if users is not None:
        vms = vms.filter(userid__in=users)
    if projects is not None:
        vms = vms.filter(project__in=projects)

    vmsdict = _partition_by(lambda vm: vm.project, vms)
    for project, projectdict in vmsdict.iteritems():
        vmsdict[project] = _partition_by(lambda vm: vm.userid, projectdict)
    return vmsdict


def get_floating_ips(users=None, projects=None):
    ips = IPAddress.objects.filter(deleted=False, floating_ip=True).\
        select_related("nic__machine")
    if users is not None:
        ips = ips.filter(userid__in=users)
    if projects is not None:
        ips = ips.filter(project__in=projects)

    ipsdict = _partition_by(lambda ip: ip.project, ips)
    for project, projectdict in ipsdict.iteritems():
        ipsdict[project] = _partition_by(lambda ip: ip.userid, projectdict)
    return ipsdict


def get_actual_resources(resource_type, users=None, projects=None):
    ACTUAL_RESOURCES = {
        "vm": get_vms,
        "floating_ip": get_floating_ips,
        }
    return ACTUAL_RESOURCES[resource_type](users=users, projects=projects)


def skip_check(obj, to_check=None, excluded=None):
    return (to_check is not None and obj not in to_check or
            excluded is not None and obj in excluded)


def pick_project_resources(project_dict, users=None, excluded_users=None):
    resources = []
    for user, user_resources in project_dict.iteritems():
        if skip_check(user, users, excluded_users):
            continue
        resources += user_resources
    return resources


VM_ACTION = {
    "REMOVE": servers.destroy,
    "SHUTDOWN": servers.stop,
}


def apply_to_vm(action, vm_id, shutdown_timeout):
    try:
        vm = VirtualMachine.objects.select_for_update().get(id=vm_id)
        VM_ACTION[action](vm, shutdown_timeout=shutdown_timeout)
        return True
    except BaseException:
        return False


def allow_operation(backend_id, opcount, maxops):
    if backend_id is None or maxops is None:
        return True
    backend_ops = opcount.get(backend_id, 0)
    if backend_ops >= maxops:
        return False
    opcount[backend_id] = backend_ops + 1
    return True


def perform_vm_actions(actions, opcount, maxops=None, fix=False, options={}):
    log = []
    for vm_id, (viol_id, state, backend_id, vm_action) in actions.iteritems():
        if not allow_operation(backend_id, opcount, maxops):
            continue
        data = ("vm", vm_id, state, backend_id, vm_action, viol_id)
        if fix:
            r = apply_to_vm(vm_action, vm_id, options.get("shutdown_timeout"))
            data += ("DONE" if r else "FAILED",)
        log.append(data)
    return log


def wait_for_ip(ip_id):
    for i in range(100):
        ip = IPAddress.objects.get(id=ip_id)
        if ip.nic_id is None:
            objs = IPAddress.objects.select_for_update()
            return objs.get(id=ip_id)
        time.sleep(1)
    raise ValueError(
        "Floating_ip %s: Waiting for port delete timed out." % ip_id)


def remove_ip(ip_id):
    try:
        ip = IPAddress.objects.select_for_update().get(id=ip_id)
        port_id = ip.nic_id
        if port_id:
            objs = NetworkInterface.objects.select_for_update()
            port = objs.get(id=port_id)
            servers.delete_port(port)
            if port.machine:
                wait_server_job(port.machine)
            ip = wait_for_ip(ip_id)
        logic_ips.delete_floating_ip(ip)
        return True
    except BaseException:
        return False


def perform_floating_ip_actions(actions, opcount, maxops=None, fix=False,
                                options={}):
    log = []
    for ip_id, (viol_id, state, backend_id, ip_action) in actions.iteritems():
        if not allow_operation(backend_id, opcount, maxops):
            continue
        data = ("floating_ip", ip_id, state, backend_id, ip_action, viol_id)
        if ip_action == "REMOVE":
            if fix:
                r = remove_ip(ip_id)
                data += ("DONE" if r else "FAILED",)
        log.append(data)
    return log


def perform_actions(actions, maxops=None, fix=False, options={}):
    ACTION_HANDLING = [
        ("floating_ip", perform_floating_ip_actions),
        ("vm", perform_vm_actions),
        ]

    opcount = {}
    logs = []
    for resource_type, handler in ACTION_HANDLING:
        t_actions = actions.get(resource_type, {})
        log = handler(t_actions, opcount, maxops=maxops, fix=fix,
                      options=options)
        logs += log
    return logs


# It is important to check resources in this order, especially
# floating_ip after vm resources.
RESOURCE_HANDLING = [
    ("cyclades.cpu", handle_stop_active, "vm"),
    ("cyclades.ram", handle_stop_active, "vm"),
    ("cyclades.total_cpu", handle_destroy, "vm"),
    ("cyclades.total_ram", handle_destroy, "vm"),
    ("cyclades.disk", handle_destroy, "vm"),
    ("cyclades.vm", handle_destroy, "vm"),
    ("cyclades.floating_ip", handle_floating_ip, "floating_ip"),
    ]
