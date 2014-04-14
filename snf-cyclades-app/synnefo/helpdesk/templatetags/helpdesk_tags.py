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

from django import template

register = template.Library()


@register.filter(name="vm_public_ip")
def vm_public_ip(vm):
    """
    Identify if vm is connected to ``public`` network and return the ipv4
    address
    """
    try:
        return vm.nics.filter(network__public=True)[0].ipv4_address
    except IndexError:
        return "No public ip"


VM_STATE_CSS_MAP = {
        'BUILD': 'warning',
        'PENDING': 'warning',
        'ERROR': 'important',
        'STOPPED': 'notice',
        'STARTED': 'success',
        'ACTIVE': 'success',
        'DESTROYED': 'inverse'
}


@register.filter(name="object_status_badge", is_safe=True)
def object_status_badge(vm_or_net):
    """
    Return a span badge styled based on the vm current status
    """
    state = vm_or_net.operstate if hasattr(vm_or_net, 'operstate') else \
        vm_or_net.state
    state_cls = VM_STATE_CSS_MAP.get(state, 'notice')
    badge_cls = "badge badge-%s" % state_cls

    deleted_badge = ""
    if vm_or_net.deleted:
        deleted_badge = '<span class="badge badge-important">Deleted</span>'
    return '%s\n<span class="%s">%s</span>' % (deleted_badge, badge_cls, state)


@register.filter(name="network_deleted_badge", is_safe=True)
def network_deleted_badge(network):
    """
    Return a span badge styled based on the vm current status
    """
    deleted_badge = ""
    if network.deleted:
        deleted_badge = '<span class="badge badge-important">Deleted</span>'
    return deleted_badge


@register.filter(name="get_os", is_safe=True)
def get_os(vm):
    try:
        return vm.metadata.filter(meta_key="OS").get().meta_value
    except:
        return "unknown"


@register.filter(name="network_vms", is_safe=True)
def network_vms(network, account, show_deleted=False):
    vms = []
    nics = network.nics.filter(machine__userid=account)
    if not show_deleted:
        nics = nics.filter(machine__deleted=False).distinct()
    for nic in nics:
        vms.append(nic.machine)
    return vms


@register.filter(name="network_nics")
def network_nics(network, account, show_deleted=False):
    vms = []
    nics = network.nics.filter(machine__userid=account)
    if not show_deleted:
        nics = nics.filter(machine__deleted=False).distinct()
    return nics


@register.filter(name="backend_info", is_safe=True)
def backend_info(vm):
    content = ""
    backend = vm.backend
    excluded = ['password_hash', 'hash', 'username']
    if not vm.backend:
        content = "No backend"
        return content

    for field in vm.backend._meta.fields:
        if field.name in excluded:
            continue
        content += '<dt>Backend ' + field.name + '</dt><dd>' + \
                   str(getattr(backend, field.name)) + '</dd>'
    return content
