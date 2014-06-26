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

from collections import OrderedDict
from django import template
import logging
logger = logging.getLogger(__name__)

import django_filters

import synnefo_admin.admin.projects.utils as project_utils
from astakos.im.models import AstakosUser

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


@register.filter(name="object_status_label", is_safe=True)
def object_status_label(vm_or_net):
    """
    Return a span label styled based on the vm current status
    """
    state = vm_or_net.operstate if hasattr(vm_or_net, 'operstate') else \
        vm_or_net.state
    state_cls = VM_STATE_CSS_MAP.get(state, 'notice')
    label_cls = "label label-%s" % state_cls

    deleted_label = ""
    if vm_or_net.deleted:
        deleted_label = '<span class="label label-important">Deleted</span>'
    return '%s\n<span class="%s">%s</span>' % (deleted_label, label_cls, state)


@register.filter(name="network_deleted_label", is_safe=True)
def network_deleted_label(network):
    """
    Return a span label styled based on the vm current status
    """
    deleted_label = ""
    if network.deleted:
        deleted_label = '<span class="label label-important">Deleted</span>'
    return deleted_label


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
    elif type == "nic":
        return "Network Interfaces"
    elif type == "ip":
        return "IP Addresses"
    elif type == "volume":
        return "Volumes"
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
def get_filter_template(filter):
    """Get the correct flter template according to the filter type.

    This only works for filters that are instances of django-filter's Filter.
    """
    if isinstance(filter, django_filters.NumberFilter):
        type = "number"
    elif isinstance(filter, django_filters.CharFilter):
        type = "char"
    elif isinstance(filter, django_filters.BooleanFilter):
        type = "bool"
    elif isinstance(filter, django_filters.ChoiceFilter):
        type = "choice"
    elif isinstance(filter, django_filters.MultipleChoiceFilter):
        type = "multichoice"
    else:
        raise Exception("Unknown filter type: %s", filter)
    template = 'admin/filter_' + type + '.html'
    logging.info("Requested the %s", template)
    return template


@register.filter
def id(item):
    try:
        return item['project'].uuid
    except TypeError:
        pass

    try:
        return item.uuid
    except AttributeError:
        pass

    try:
        return item.id
    except AttributeError:
        pass

    return item.pk


@register.filter
def repr(item):
    """Return the string representation of an item.

    If an item has a "realname" attribute that is not emprty, we return this.
    Else, if an item has a "name" attribute that is not empty, we return this.
    Finally, if an item has none of the above attributes, or the attributes are
    empty, return the result of the __str__ method of the item.
    """
    try:
        return item.address
    except AttributeError:
        pass

    try:
        return item['project'].realname
    except TypeError:
        pass

    try:
        if item.realname:
            return item.realname
    except AttributeError:
        pass

    try:
        if item.name:
            return item.name
    except AttributeError:
        pass

    return item.__str__()


@register.filter
def verbify(action):
    """Create verb from action name.

    If action has more than one words, then we keep the first one which, by
    convention, will be a verb.
    """
    return action.split()[0].capitalize()


@register.filter
def get_project_stats(project):
    """Create a dictionary with a summary for a project's stats."""
    stats = OrderedDict()
    if not project.is_base:
        stats['Max per member'] = \
            project_utils.display_project_resources(project, 'member')
    stats['Total'] = project_utils.display_project_resources(project, 'total')
    stats['Usage'] = project_utils.display_project_stats(project,
                                                         'project_usage')
    return stats


@register.filter
def can_apply(action, item):
    """Return if action can apply on item."""
    if action.name == "Send e-mail" and action.target != 'user':
        return False
    return action.can_apply(item)
