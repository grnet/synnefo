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

import logging
import datetime
import time

from urlparse import urlparse
from datetime import tzinfo, timedelta

from django.http import HttpResponse, HttpResponseBadRequest, urlencode
from django.template import RequestContext
from django.contrib.auth import authenticate
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.translation import ugettext as _

from astakos.im.models import AstakosUser, Invitation
from astakos.im.settings import (
    COOKIE_DOMAIN, FORCE_PROFILE_UPDATE)
from astakos.im.functions import login

import astakos.im.messages as astakos_messages

logger = logging.getLogger(__name__)


class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return 'UTC'

    def dst(self, dt):
        return timedelta(0)


def isoformat(d):
    """Return an ISO8601 date string that includes a timezone."""

    return d.replace(tzinfo=UTC()).isoformat()


def epoch(datetime):
    return int(time.mktime(datetime.timetuple()) * 1000)


def get_context(request, extra_context=None, **kwargs):
    extra_context = extra_context or {}
    extra_context.update(kwargs)
    return RequestContext(request, extra_context)


def get_invitation(request):
    """
    Returns the invitation identified by the ``code``.

    Raises ValueError if the invitation is consumed or there is another account
    associated with this email.
    """
    code = request.GET.get('code')
    if request.method == 'POST':
        code = request.POST.get('code')
    if not code:
        return
    invitation = Invitation.objects.get(code=code)
    if invitation.is_consumed:
        raise ValueError(_(astakos_messages.INVITATION_CONSUMED_ERR))
    if reserved_email(invitation.username):
        email = invitation.username
        raise ValueError(_(astakos_messages.EMAIL_RESERVED) % locals())
    return invitation

def restrict_next(url, domain=None, allowed_schemes=()):
    """
    Return url if having the supplied ``domain`` (if present) or one of the ``allowed_schemes``.
    Otherwise return None.

    >>> print restrict_next('/im/feedback', '.okeanos.grnet.gr')
    /im/feedback
    >>> print restrict_next('pithos.okeanos.grnet.gr/im/feedback', '.okeanos.grnet.gr')
    //pithos.okeanos.grnet.gr/im/feedback
    >>> print restrict_next('https://pithos.okeanos.grnet.gr/im/feedback', '.okeanos.grnet.gr')
    https://pithos.okeanos.grnet.gr/im/feedback
    >>> print restrict_next('pithos://127.0.0,1', '.okeanos.grnet.gr')
    None
    >>> print restrict_next('pithos://127.0.0,1', '.okeanos.grnet.gr', allowed_schemes=('pithos'))
    pithos://127.0.0,1
    >>> print restrict_next('node1.example.com', '.okeanos.grnet.gr')
    None
    >>> print restrict_next('//node1.example.com', '.okeanos.grnet.gr')
    None
    >>> print restrict_next('https://node1.example.com', '.okeanos.grnet.gr')
    None
    >>> print restrict_next('https://node1.example.com')
    https://node1.example.com
    >>> print restrict_next('//node1.example.com')
    //node1.example.com
    >>> print restrict_next('node1.example.com')
    //node1.example.com
    """
    if not url:
        return
    parts = urlparse(url, scheme='http')
    if not parts.netloc and not parts.path.startswith('/'):
        # fix url if does not conforms RFC 1808
        url = '//%s' % url
        parts = urlparse(url, scheme='http')
    # TODO more scientific checks?
    if not parts.netloc:    # internal url
        return url
    elif not domain:
        return url
    elif parts.netloc.endswith(domain):
        return url
    elif parts.scheme in allowed_schemes:
        return url

def prepare_response(request, user, next='', renew=False):
    """Return the unique username and the token
       as 'X-Auth-User' and 'X-Auth-Token' headers,
       or redirect to the URL provided in 'next'
       with the 'user' and 'token' as parameters.

       Reissue the token even if it has not yet
       expired, if the 'renew' parameter is present
       or user has not a valid token.
    """
    renew = renew or (not user.auth_token)
    renew = renew or (user.auth_token_expires < datetime.datetime.now())
    if renew:
        user.renew_token(
            flush_sessions=True,
            current_key=request.session.session_key
        )
        try:
            user.save()
        except ValidationError, e:
            return HttpResponseBadRequest(e)

    next = restrict_next(next, domain=COOKIE_DOMAIN)

    if FORCE_PROFILE_UPDATE and not user.is_verified and not user.is_superuser:
        params = ''
        if next:
            params = '?' + urlencode({'next': next})
        next = reverse('edit_profile') + params

    response = HttpResponse()

    # authenticate before login
    user = authenticate(email=user.email, auth_token=user.auth_token)
    login(request, user)
    request.session.set_expiry(user.auth_token_expires)

    if not next:
        next = reverse('astakos.im.views.index')

    response['Location'] = next
    response.status_code = 302
    return response

class lazy_string(object):
    def __init__(self, function, *args, **kwargs):
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        if not hasattr(self, 'str'):
            self.str = self.function(*self.args, **self.kwargs)
        return self.str


def reverse_lazy(*args, **kwargs):
    return lazy_string(reverse, *args, **kwargs)


def reserved_email(email):
    return AstakosUser.objects.user_exists(email)


def get_query(request):
    try:
        return request.__getattribute__(request.method)
    except AttributeError:
        return {}


def model_to_dict(obj, exclude=['AutoField', 'ForeignKey', 'OneToOneField'],
                  include_empty=True):
    '''
        serialize model object to dict with related objects

        author: Vadym Zakovinko <vp@zakovinko.com>
        date: January 31, 2011
        http://djangosnippets.org/snippets/2342/
    '''
    tree = {}
    for field_name in obj._meta.get_all_field_names():
        try:
            field = getattr(obj, field_name)
        except (ObjectDoesNotExist, AttributeError):
            continue

        if field.__class__.__name__ in ['RelatedManager', 'ManyRelatedManager']:
            if field.model.__name__ in exclude:
                continue

            if field.__class__.__name__ == 'ManyRelatedManager':
                exclude.append(obj.__class__.__name__)
            subtree = []
            for related_obj in getattr(obj, field_name).all():
                value = model_to_dict(related_obj, exclude=exclude)
                if value or include_empty:
                    subtree.append(value)
            if subtree or include_empty:
                tree[field_name] = subtree
            continue

        field = obj._meta.get_field_by_name(field_name)[0]
        if field.__class__.__name__ in exclude:
            continue

        if field.__class__.__name__ == 'RelatedObject':
            exclude.append(field.model.__name__)
            tree[field_name] = model_to_dict(getattr(obj, field_name),
                                             exclude=exclude)
            continue

        value = getattr(obj, field_name)
        if field.__class__.__name__ == 'ForeignKey':
            value = unicode(value) if value is not None else value
        if value or include_empty:
            tree[field_name] = value

    return tree
