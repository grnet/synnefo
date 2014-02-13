# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import calendar
import datetime
import math

from collections import defaultdict

from django import template
from django.core.paginator import Paginator, EmptyPage
from django.db.models.query import QuerySet
from django.utils.safestring import mark_safe

from synnefo.lib.ordereddict import OrderedDict

from astakos.im import settings
from astakos.im.models import ProjectResourceGrant
from astakos.im.views import util as views_util
from astakos.im import util

register = template.Library()

DELIM = ','


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
    tpl = '<span class="policy-diff %s">(%s)</span>'
    cls = 'red' if diff.startswith("-") else 'green'
    return mark_safe(tpl % (cls, diff))


@register.filter
def sorted_resources(resources_set):
    return views_util.sorted_resources(resources_set)


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
