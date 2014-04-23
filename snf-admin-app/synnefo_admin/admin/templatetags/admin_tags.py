# Copyright 2012, 2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

from django import template
from astakos.logic import users
import logging

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


def check_state(user, state):
    """Check if user is in the given state.

    The return value is boolean
    """
    if state == 'activated':
        return user.is_active
    elif state == 'accepted':
        return user.moderated and not user.is_rejected
    elif state == 'rejected':
        return user.is_rejected
    elif state == 'verified':
        return user.email_verified
    elif state == 'moderated':
        return user.moderated
register.filter('check_state', check_state)


@register.filter
def get_state(user):
    """Get the user state.

    The user state can be Active/Inactive/Pending Moderation/Pending
    Verification. The user can never be in two states in the same time.
    """
    if user.is_active:
        return "Active"
    elif user.moderated:
        return "Inactive"
    elif user.email_verified:
        return "Pending Moderation"
    else:
        return "Pending Verification"


@register.filter
def get_state_list(user):
    """Get a space separated list of states that the user is in.

    The list is returned as a string, in order to be used in html tags
    """
    state_list = ','
    for state in ['activated', 'accepted', 'rejected', 'verified']:
        if check_state(user, state):
            state_list += state + ','

    return state_list


def check_operation(user, op):
    """Check if an opearation can apply to a user.

    The return value is boolean.
    """
    if op == 'activate':
        return users.check_activate(user)
    elif op == 'deactivate':
        return users.check_deactivate(user)
    elif op == 'accept':
        return users.check_accept(user)
    elif op == 'reject':
        return users.check_reject(user)
    elif op == 'verify':
        return users.check_verify(user)
    elif op == 'contact':
        return True
    else:
        return False
register.filter('check_operation', check_operation)


@register.filter
def get_user_operation_list(user):
    """Get a space separated list of operations that apply to a user.

    The list is returned as a string, in order to be used in html tags
    """
    op_list = ','
    for op in ['activate', 'deactivate', 'accept', 'reject', 'verify',
               'contact']:
        if check_operation(user, op):
            op_list += op + ','

    return op_list


@register.filter
def get_vm_operation_list(vm):
    """Get a space separated list of operations that apply to a vm.

    The list is returned as a string, in order to be used in html tags
    """
    op_list = ['start', 'shutdown', 'destroy', 'suspend', 'release',
               'reassign', 'contact']

    return op_list


@register.filter
def display_list_type(type):
    """Display the type of an item list in a human readable way."""
    if type == "user":
        return "Users"
    elif type == "project":
        return "Projects"
    elif type == "quota":
        return "Quotas"
    elif type == "vm":
        return "Virtual Machines"
    elif type == "network":
        return "Networks"
    else:
        return "Unknown type"


@register.filter
def admin_debug(var):
    """Print in the log a value."""
    logging.info("Template debugging: %s", var)
    return var


@register.filter
def get_details_template(type):
    """Get the correct template for the provided item."""
    template = 'admin/_' + type + '_details.html'
    logging.info("Requested the %s", template)
    return template


@register.filter
def get_index_template(type):
    """Get the correct template for the provided item."""
    template = 'admin/_' + type + '_row.html'
    logging.info("Requested the %s", template)
    return template
