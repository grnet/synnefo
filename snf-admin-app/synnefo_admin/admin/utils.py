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

import functools
import logging
import inspect
from importlib import import_module

from django.views.decorators.gzip import gzip_page
from django.template import Context, Template
from django.core.urlresolvers import reverse
from django.utils.html import escape

from astakos.im.models import Resource
from synnefo.db.models import (VirtualMachine, Volume, Network, IPAddress,
                               IPAddressLog)
from astakos.im.models import AstakosUser, Project, ProjectApplication

from synnefo.util import units
from astakos.im.user_utils import send_plain as send_email
from snf_django.lib.api import faults

from synnefo_admin import admin_settings
from astakos.im import settings as astakos_settings

from .actions import get_allowed_actions, get_permitted_actions
logger = logging.getLogger(__name__)


"""A mapping between model names and Django models."""
model_dict = {
    "user": AstakosUser,
    "vm": VirtualMachine,
    "volume": Volume,
    "network": Network,
    "ip": IPAddress,
    "ip_log": IPAddressLog,
    "project": Project,
    "application": ProjectApplication,
}


def default_view():
    """Return the first registered view based on ADMIN_VIEWS.

    If the ADMIN_VIEWS dict is empty, return None.
    """
    return next(admin_settings.ADMIN_VIEWS.iterkeys(), None)


def __reverse_model_dict():
    """Create the a model dict with the class names as keys."""
    reversed_model_dict = {}
    for key, value in model_dict.iteritems():
        reversed_model_dict[value.__name__] = key
    return reversed_model_dict
reversed_model_dict = __reverse_model_dict()


def get_type_from_instance(inst):
    """Get the name for the instance class that is used in admin app."""
    inst_cls_name = inst.__class__.__name__
    return reversed_model_dict[inst_cls_name]


def admin_log(request, *argc, **kwargs):
    caller_name = inspect.stack()[1][3]
    s = "User: %s, " % request.user['access']['user']['name']
    s += "View: %s, " % caller_name

    for key, value in kwargs.iteritems():
        s += "%s: %s, " % (key.capitalize(), value)

    if caller_name == "admin_actions":
        logging.info(s)
    else:
        logging.debug(s)


def conditionally_gzip_page(func):
    """Decorator to gzip response of unpaginated json requests."""
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        display_length = getattr(request.REQUEST, 'iDisplayLength', None)
        if not display_length or display_length > 0:
            return func(request, *args, **kwargs)
        else:
            return gzip_page(func)(request, *args, **kwargs)
    return wrapper


def get_resource(name):
    r = cached_resources.get(name, None)
    if not r:
        r = Resource.objects.get(name=name)
        cached_resources[name] = r
    return r
cached_resources = {}


def is_resource_useful(resource, limit):
    """Simple function to check if the resource is useful to show.

    Values that have infinite or zero limits are discarded.
    """
    displayed_limit = units.show(limit, resource.unit)
    if limit == 0 or displayed_limit == 'inf':
        return False
    return True


def get_actions(target, user=None, inst=None):
    """Generic function for getting actions for various targets.

    Note: this function will import the action module for the target, which
    means that it may be slow.
    """
    if target in ['quota', 'nic', 'ip_log']:
        return None

    mod = import_module('synnefo_admin.admin.resources.%ss.actions' % target)
    actions = mod.cached_actions
    if inst:
        return get_allowed_actions(actions, inst, user)
    else:
        return get_permitted_actions(actions, user)


def update_actions_rbac(actions):
    """Add allowed groups to actions dictionary from settings.

    Read the settings file to find the allowed groups for this action.
    """
    for op, action in actions.iteritems():
        target = action.target
        groups = []
        try:
            groups = admin_settings.ADMIN_RBAC[target][op]
        except KeyError:
            pass

        action.allowed_groups = groups


def assert_valid_contact_request(request):
    """Check if the request is a valid contact request.

    In order to be a valid contact request, it should contain a POST dictionary
    and the following fields: sender, subject, text. If any of the above are
    missing, raise BadRequest with the appropriate message.
    """
    if not hasattr(request, 'POST'):
        raise faults.BadRequest(
            "Contact request does not have a POST dictionary.")

    required_fields = ['sender', 'subject', 'text']
    error_fields = set(required_fields) - set(request.POST.keys())

    if error_fields:
        error_fields = ', '.join(error_fields)
        error_msg = "Contact request does not have the following fields: {}"
        raise faults.BadRequest(error_msg.format(error_fields))


class CustomSender(object):

    """Context manager for setting and restoring the SERVER_EMAIL setting."""

    def __init__(self, sender):
        """Store the default and the provided sender."""
        self.custom_sender = sender
        self.default_sender = astakos_settings.SERVER_EMAIL

    def __enter__(self):
        """Use the provided sender as default."""
        astakos_settings.SERVER_EMAIL = self.custom_sender

    def __exit__(self, exc_type, exc_value, traceback):
        """Restore default sender."""
        astakos_settings.SERVER_EMAIL = self.default_sender


def render_email(user, request):
    """Render an email and return its subject and body.

    This function takes as arguments a QueryDict and a user. The user will
    serve as the target of the mail. The QueryDict should contain a `text` and
    `subject` attribute that will be used as the body and subject of the mail
    respectively.

    The email can optionally be customized with user information. If the user
    has provided any one of the following variables:

        {{ full_name }}, {{ first_name }}, {{ last_name }}, {{ email }}

    then they will be rendered appropriately.
    """
    c = Context({'full_name': user.realname,
                 'first_name': user.first_name,
                 'last_name': user.last_name,
                 'email': user.email, })

    # Render the mail body
    t = Template(request['text'])
    body = t.render(c)

    # Render the mail subject
    t = Template(request['subject'])
    subject = t.render(c)
    return subject, body


def send_admin_email(user, request):
    """Use request to render an email and send it to a user."""
    assert_valid_contact_request(request)
    subject, body = render_email(user, request.POST)
    sender = request.POST.get('sender')
    send_email(user, sender=sender, subject=subject, template_name=None,
               text=body)


def create_details_href(type, name, id):
    """Create an href (name + url) for an item."""
    name = escape(name)
    url = reverse('admin-details', args=[type, id])
    if type == 'user':
        href = '<a href=%s>%s (%s)</a>' % (url, name, id)
    elif type == 'ip':
        href = '<a href=%s>%s</a>' % (url, name)
    else:
        href = '<a href=%s>%s (id:%s)</a>' % (url, name, id)
    return href


def _filter_public_ip_log(qs):
    network_ids = Network.objects.filter(public=True).values('id')
    return qs.filter(network_id__in=network_ids)


def filter_public_ip_log(assoc):
    if assoc.type == 'ip_log':
        assoc.qs = _filter_public_ip_log(assoc.qs)
        assoc.total = assoc.count_total()


def filter_distinct(assoc):
    if hasattr(assoc, 'qs'):
        assoc.qs = assoc.qs.distinct()


def exclude_deleted(assoc):
    """Exclude deleted items."""
    if (admin_settings.ADMIN_SHOW_DELETED_ASSOCIATED_ITEMS or
            not hasattr(assoc, 'qs')):
        return

    if assoc.type in ['vm', 'volume', 'network', 'ip']:
        assoc.qs = assoc.qs.exclude(deleted=True)
    elif assoc.type == 'nic':
        assoc.qs = assoc.qs.exclude(machine__deleted=True)

    assoc.excluded = assoc.total - assoc.qs.count()


def order_by_newest(assoc):
    ord = getattr(assoc, 'order_by', None)
    if ord:
        assoc.qs = assoc.qs.order_by(ord)


def limit_shown(assoc):
    limit = admin_settings.ADMIN_LIMIT_ASSOCIATED_ITEMS_PER_CATEGORY
    assoc.items = assoc.items[:limit]
    assoc.showing = assoc.count_items()


def customize_details_context(context):
    """Perform generic customizations on the detail context."""
    for assoc in context['associations_list']:
        filter_public_ip_log(assoc)
        filter_distinct(assoc)
        exclude_deleted(assoc)
        order_by_newest(assoc)
        limit_shown(assoc)
