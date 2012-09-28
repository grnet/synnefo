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

from django import template
from django.core.paginator import Paginator, InvalidPage
from django.db.models.query import QuerySet

from astakos.im.settings import PAGINATE_BY

register = template.Library()

DELIM = ','

@register.filter
def monthssince(joined_date):
    now = datetime.datetime.now()
    date = datetime.datetime(year=joined_date.year, month=joined_date.month, day=1)
    months = []
    
    month = date.month
    year = date.year
    timestamp=calendar.timegm( date.utctimetuple() )
    
    while date < now:
        months.append((year, month, timestamp))
        
        if date.month < 12:
            month = date.month + 1
            year = date.year
        else:
            month = 1
            year = date.year + 1
            
        date = datetime.datetime(year=year, month=month, day=1)
        timestamp=calendar.timegm( date.utctimetuple() )
        
    return months
    
@register.filter
def lookup(d, key):
    return d.get(key)


@register.filter
def dkeys(d):
    return d.keys()


@register.filter
def month_name(month_number):
    return calendar.month_name[month_number]
    

@register.filter
def todate(value, arg = ''):
    secs = int(value) / 1000
    return datetime.datetime.fromtimestamp(secs)


@register.filter
def rcut(value, chars = '/'):
    return value.rstrip(chars)

@register.filter
def paginate(l, args):
    page, delim, sorting = args.partition(DELIM)
    if sorting:
        if isinstance(l, QuerySet):
            l = l.order_by(sorting)
        elif isinstance(l, list):
            default = ''
            if sorting.endswith('_date'):
                default = datetime.datetime.utcfromtimestamp(0)
            l.sort(key=lambda i: getattr(i, sorting) \
                        if getattr(i, sorting) else default)
            
    paginator = Paginator(l, PAGINATE_BY)
    
    try:
        page_number = int(page)
    except ValueError:
        if page == 'last':
            page_number = paginator.num_pages
        else:
            page_number = 1
    page = globals()['page'] = paginator.page(page_number)
    return page

@register.filter
def concat(str1, str2):
    if not str2:
        return str(str1)
    return '%s%s%s' % (str1, DELIM, str2)