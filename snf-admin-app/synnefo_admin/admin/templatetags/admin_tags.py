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
#

from importlib import import_module
from collections import OrderedDict
from django import template
import logging

import django_filters

import synnefo_admin.admin.projects.utils as project_utils
import synnefo_admin.admin.users.utils as user_utils
from synnefo_admin.admin import utils
mod = import_module('astakos.im.management.commands.project-show')

register = template.Library()

status_map = {}
status_map['vm'] = {
    'BUILD': 'warning',
    'PENDING': 'warning',
    'ERROR': 'danger',
    'STOPPED': 'info',
    'STARTED': 'success',
    'ACTIVE': 'success',
    'DESTROYED': 'inverse'
}
status_map['volume'] = {
    'AVAILABLE': 'success',
    'IN_USE': 'success',
    'DELETING': 'warning',
    'ERROR': 'danger',
    'ERROR_DELETING': 'danger',
    'ERROR_RESTORING': 'danger',
}
status_map['network'] = {
    'ACTIVE': 'success',
    'ERROR': 'danger',
}
status_map['project'] = {
    'PENDING': 'warning',
    'ACTIVE': 'success',
    'DENIED': 'danger',
    'DELETED': 'danger',
    'SUSPENDED': 'warning',
}
status_map['application'] = status_map['project']
status_map['application']['APPROVED'] = 'success'


def get_status_from_instance(inst):
    """Generic function to get the status of any instance."""
    try:
        return inst.state_display()
    except AttributeError:
        pass

    try:
        return inst.status_display
    except AttributeError:
        pass

    try:
        return inst.operstate
    except AttributeError:
        pass

    try:
        return inst.state
    except AttributeError:
        pass

    return inst.status


@register.filter(is_safe=True)
def status_label(inst):
    """Return a span label styled based on the instance's current status"""
    inst_type = utils.get_type_from_instance(inst)
    state = get_status_from_instance(inst).upper()
    state_cls = 'info'

    if inst_type == 'user':
        if not inst.email_verified or not inst.moderated:
            state_cls = 'warning'
        elif inst.is_rejected:
            state_cls = 'danger'
        elif inst.is_active:
            state_cls = 'success'
        elif not inst.is_active:
            state_cls = 'inverse'
    else:
        state_cls = status_map[inst_type].get(state, 'info')

    label_cls = "label label-%s" % state_cls

    if inst_type in ["project", "application"]:
        name = inst_type.capitalize() + " Status: "
    else:
        name = ""

    deleted_label = ""
    if getattr(inst, 'deleted', False):
        deleted_label = '<span class="label label-danger">Deleted</span>'
    return '%s\n<span class="%s">%s%s</span>' % (deleted_label, label_cls,
                                                 name, state)


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
    elif type == "ip_log":
        return "IP History"
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


@register.filter()
def details_url(inst, target):
    """Get a url for the details of an instance's field."""
    # Get instance type and import the appropriate utilities module.
    inst_type = utils.get_type_from_instance(inst)
    mod = import_module("synnefo_admin.admin.{}s.utils".format(inst_type))

    # Call the details_href function for the provided target.
    func = getattr(mod, "get_{}_details_href".format(target), None)
    if func:
        return func(inst)
    else:
        raise Exception("Wrong target name: {}".format(target))


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
def get_groups(user):
    return user_utils.get_user_groups(user)


@register.filter
def verbify(action):
    """Create verb from action name.

    If action has more than one words, then we keep the first one which, by
    convention, will be a verb.
    """
    return action.split()[0].capitalize()


@register.filter
def get_project_members(project):
    members, _ = mod.members_fields(project)
    return members


@register.filter
def get_project_stats(project):
    """Create a dictionary with a summary for a project's stats."""
    limit = project_utils.get_project_quota_category(project, "limit")
    usage = project_utils.get_project_usage(project)
    member = project_utils.get_project_quota_category(project, "member")
    if not usage:
        usage = [(name, '-',) for name, _ in limit]

    if project.is_base:
        all_stats = zip(limit, usage)
    else:
        all_stats = zip(member, limit, usage)

    new_stats = OrderedDict()
    for row in all_stats:
        resource_name = row[0][0]
        new_stats[resource_name] = []
        for _, value in row:
            new_stats[resource_name].append(value)

    return new_stats


@register.filter
def show_auth_providers(user, category):
    """Show auth providers for a user."""
    func = getattr(user, "get_%s_auth_providers" % category)
    providers = [prov.module for prov in func()]
    if providers:
        return ", ".join(providers)
    else:
        return "None"


@register.filter
def can_apply(action, item):
    """Return if action can apply on item."""
    if action.name == "Send e-mail" and action.target != 'user':
        return False
    return action.can_apply(item)


@register.filter
def default_value(f):
    """Set default value for filters.

    By default the value is all, except for filters with "NOT" in their label.
    """
    if 'NOT' in f.label:
        return 'None'
    return 'All'


@register.filter
def present_excluded(assoc):
    """Present what are the excluded entries."""
    if assoc.type == "user":
        return "users that are not project members"
    else:
        return "deleted entries"


FILTER_NAME_ICON_MAP = {
    'vm': 'snf-pc-full',
    'user': 'snf-user-full',
    'vol': 'snf-volume-full',
    'volume': 'snf-volume-full',
    'net': 'snf-network-full',
    'network': 'snf-network-full',
    'proj': 'snf-clipboard-h',
    'project': 'snf-clipboard-h',
}


@register.filter
def label_to_icon(filter_name, filter_label):
    """
    Return a span icon based on the filter name
    If no icon is found, return filter label
    """
    icon_cls = FILTER_NAME_ICON_MAP.get(filter_name)
    if icon_cls:
        label = '<span class="%s"></span>' % icon_cls
    else:
        label = filter_label
    return label


@register.filter
def show_more_exception_message(assoc):
    """Show an extra message for an instance in the popover for "Show More"."""
    if assoc.type == "user":
        return """
</br>Alternatively, you may consult the "Members" tab of the project."""
