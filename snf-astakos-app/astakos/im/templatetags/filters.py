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

import calendar
import datetime
import math

from collections import defaultdict

from django import template
from django.core.paginator import Paginator, EmptyPage
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe
from django.template import defaultfilters

from synnefo.lib.ordereddict import OrderedDict
from synnefo.util import units

from astakos.im import settings
from astakos.im.models import ProjectResourceGrant, Project
from astakos.im.views import util as views_util
from astakos.im import util
from astakos.im import presentation
from astakos.im.models import AstakosUser

from astakos.im import quotas

register = template.Library()

DELIM = ','


def _is_inf(value):
    try:
        return value == units.PRACTICALLY_INFINITE
    except:
        return False


@register.filter
def monthssince(joined_date):
    now = datetime.datetime.now()
    date = datetime.datetime(
        year=joined_date.year, month=joined_date.month, day=1)
    months = []

    month = date.month
    year = date.year
    timestamp = calendar.timegm(date.utctimetuple())

    while date < now:
        months.append((year, month, timestamp))

        if date.month < 12:
            month = date.month + 1
            year = date.year
        else:
            month = 1
            year = date.year + 1

        date = datetime.datetime(year=year, month=month, day=1)
        timestamp = calendar.timegm(date.utctimetuple())

    return months


@register.filter
def to_unicode(s):
    return unicode(s)


@register.filter
def to_string(s):
    return str(s)


@register.filter
def lookup(d, key):
    try:
        return d.get(key)
    except:
        return


@register.filter
def lookup_uni(d, key):
    return d.get(unicode(key))


@register.filter
def dkeys(d):
    return d.keys()


@register.filter
def month_name(month_number):
    return calendar.month_name[month_number]


@register.filter
def todate(value, arg=''):
    secs = int(value) / 1000
    return datetime.datetime.fromtimestamp(secs)


# @register.filter
# def rcut(value, chars='/'):
#     return value.rstrip(chars)


@register.filter
def paginate(l, args):
    l = l or []
    page, delim, sorting = args.partition(DELIM)
    if sorting:
        if isinstance(l, QuerySet):
            l = l.order_by(sorting)
        elif isinstance(l, list):
            default = ''
            if sorting.endswith('_date'):
                default = datetime.datetime.utcfromtimestamp(0)
            l.sort(key=lambda i: getattr(i, sorting)
                   if getattr(i, sorting) else default)
    paginator = Paginator(l, settings.PAGINATE_BY)
    try:
        paginator.len
    except AttributeError:
        paginator._count = len(list(l))

    try:
        page_number = int(page)
    except ValueError:
        if page == 'last':
            page_number = paginator.num_pages
        else:
            page_number = 1
    try:
        page = paginator.page(page_number)
    except EmptyPage:
        page = paginator.page(1)
    return page


@register.filter
def concat(str1, str2):
    if not str2:
        return str(str1)
    return '%s%s%s' % (str1, DELIM, str2)


@register.filter
def items(d):
    if isinstance(d, defaultdict):
        return d.iteritems()
    return d


@register.filter
def get_value_after_dot(value):
    return value.split(".")[1]

# @register.filter
# def strip_http(value):
#     return value.replace('http://','')[:-1]


@register.filter
def truncatename(v, max=18, append="..."):
    util.truncatename(v, max, append)


@register.filter
def selected_resource_groups(project_or_app):
    if not project_or_app:
        return []

    grants = project_or_app.resource_set
    resources = grants.values_list('resource__name', flat=True)
    return map(lambda r: r.split(".")[0], resources)


@register.filter
def resource_grants(project_or_app):
    try:
        grants = project_or_app.resource_set
        grants = grants.values_list(
            'resource__name', 'member_capacity', 'project_capacity')
        return dict((e[0], {'member':e[1], 'project':e[2]}) for e in grants)
    except:
        return {}


def get_resource_grant(project_or_app, rname, capacity_for):
    if project_or_app is None:
        return None

    resource_set = project_or_app.resource_set
    if not resource_set.filter(resource__name=rname).count():
        return None

    resource = resource_set.get(resource__name=rname)
    return getattr(resource, '%s_capacity' % capacity_for)


@register.filter
def get_member_resource_grant_value(project_or_app, rname):
    return get_resource_grant(project_or_app, rname, "member")


@register.filter
def get_project_resource_grant_value(project_or_app, rname):
    return get_resource_grant(project_or_app, rname, "project")


@register.filter
def resource_diff(r, member_or_project):
    if not hasattr(r, 'display_project_diff'):
        return ''

    project, member = r.display_project_diff()
    diff = dict(zip(['project', 'member'],
                     r.display_project_diff())).get(member_or_project)

    diff_disp = ''
    if diff != '':
        diff_disp = "(%s)" % diff
    tpl = '<span class="policy-diff %s">%s</span>'
    cls = 'red' if diff.startswith("-") else 'green'
    return mark_safe(tpl % (cls, diff_disp))


@register.filter
def sorted_resources(resources_set):
    return views_util.sorted_resources(resources_set)


@register.filter
def display_resource_usage_for_project(resource, project):
    usage_map = presentation.USAGE_TAG_MAP
    quota = quotas.get_project_quota(project).get(resource.name, None)

    if not quota:
        return "No usage"

    cls = ''
    usage = quota['project_usage']
    limit = quota['project_limit']

    if limit == 0 and usage == 0:
        return "--"

    usage_perc = "%d" % ((float(usage) / limit) * 100) if limit else "100"
    _keys = usage_map.keys()
    _keys.reverse()
    closest = filter(lambda x: int(x) <= int(usage_perc), _keys)[0]
    cls = usage_map[closest]

    usage_display = units.show(usage, resource.unit)
    usage_perc_display = "%s%%" % usage_perc

    resp = """<span class="%s policy-diff">%s (%s)</span>""" % \
            (cls, usage_perc_display, usage_display)
    return mark_safe(resp)


@register.filter
def is_pending_app(app):
    if not app:
        return False
    return app.state in [app.PENDING]


@register.filter
def is_denied_app(app):
    if not app:
        return False
    return app.state in [app.DENIED]


def _member_policy_formatter(form_or_app, value, changed, mapping):
    if changed:
        changed = defaultfilters.title(mapping.get(changed))
    value = defaultfilters.title(mapping.get(value))
    return value, changed, None, None


def _owner_formatter(form_or_app, value, changed):
    if not changed:
        changed_name = None
    else:
        changed_name = changed.realname
    return value.realname if value else None, changed_name, None, None


def _owner_admin_formatter(form_or_app, value, changed):
    if not changed:
        changed_name = None
    else:
        changed_name = changed.realname + " (%s)" % changed.email
    return value.realname + " (%s)" % value.email if value else None, changed_name, None, None


def _owner_owner_formatter(form_or_app, value, changed):
    if not changed:
        changed_name = None
    else:
        changed_name = changed.realname
    return "Me", changed_name, None, None


MODIFICATION_FORMATTERS = {
    'member_policy': _member_policy_formatter,
    'owner': _owner_formatter,
    'owner_admin': _owner_admin_formatter,
    'owner_owner': _owner_owner_formatter
}


@register.filter
def display_modification_param(form_or_app, param, formatter=None):
    formatter_name = None
    if "," in param:
        param, formatter_name = param.split(",", 1)

    project_attr = param

    if hasattr(form_or_app, 'instance'):
        # form
        project = Project.objects.get(pk=form_or_app.instance.pk)
        app_value = form_or_app.cleaned_data[param]
        project_value = getattr(project, project_attr)
    else:
        # app
        project = form_or_app.chain
        app_value = getattr(form_or_app, project_attr)
        project_value = getattr(project, project_attr)
        if app_value == None:
            app_value = project_value

    formatter_params = {}

    if param == "member_join_policy":
        formatter_name = 'member_policy'
        formatter_params = {'mapping':
                            presentation.PROJECT_MEMBER_JOIN_POLICIES}

    if param == "member_leave_policy":
        formatter_name = 'member_policy'
        formatter_params = {'mapping':
                            presentation.PROJECT_MEMBER_LEAVE_POLICIES}

    changed = False
    changed_cls = "gray details"
    if project_value != app_value:
        changed = project_value

    if not formatter and formatter_name:
        formatter = MODIFICATION_FORMATTERS.get(formatter_name)

    changed_prefix = "<span>current: </span>"
    if formatter:
        app_value, changed, cls, prefix = formatter(form_or_app,
                                            app_value, changed,
                                            **formatter_params)
        if cls:
            changed_cls = cls

        if prefix:
            changed_prefix = prefix

    tpl = """%(value)s"""
    if changed:
        tpl += """<span class="policy-diff %(changed_cls)s">""" + \
               """%(changed_prefix)s%(changed)s</span>"""

    if not app_value:
        app_value = "(not set)"

    return mark_safe(tpl % {
        'value': app_value,
        'changed': changed,
        'changed_cls': changed_cls,
        'changed_prefix': changed_prefix
    })


@register.filter
def display_modification_param_diff(form_or_app, param):
    def formatter(form_or_app, value, changed):
        if changed in [None, False]:
            if _is_inf(value):
                value = "Unlimited"
            return value, changed, None, " "

        to_inf = _is_inf(value)
        from_inf = _is_inf(changed)

        diff = value - changed
        sign = "+"
        cls = "green"
        if diff < 0:
            sign = "-"
            diff = abs(diff)
            cls = "red"

        if diff != 5:
            if from_inf or to_inf:
                if from_inf:
                    changed = "Unlimited"
                diff = "from %s" % changed
            else:
                diff = sign + str(diff)
            changed = "(%s)" % (diff,)
        else:
            changed = None

        if to_inf:
            value = "Unlimited"
        return value, changed, cls, " "

    return display_modification_param(form_or_app, param, formatter)


@register.filter
def display_date_modification_param(form_or_app, params):
    param, date_format = params.split(",", 1)

    def formatter(form_or_app, value, changed):
        if changed not in [None, False]:
            changed = defaultfilters.date(changed, date_format)
        formatted_value = defaultfilters.date(value, date_format)
        return formatted_value, changed, None, None

    return display_modification_param(form_or_app, param, formatter)


@register.filter
def inf_display(value):
    if value == units.PRACTICALLY_INFINITE:
        return 'Unlimited'
    return value


@register.filter
def inf_value_display(value):
    if value == units.PRACTICALLY_INFINITE:
        return 'Unlimited'
    return value


@register.filter
def project_name_for_user(project, user):
    return project.display_name_for_user(user)


@register.filter
def owner_by_uuid(uuid):
    try:
        user = AstakosUser.objects.get(uuid=uuid)
        return "%s %s (%s)" % (user.first_name, user.last_name, user.email)
    except AstakosUser.DoesNotExist:
        return uuid


@register.filter
def format_inf(value):
    if _is_inf(value):
        return "Unlimited"
    return value
