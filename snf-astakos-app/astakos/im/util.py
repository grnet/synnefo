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

import logging
import time
import urllib

from urlparse import urlparse
from datetime import tzinfo, timedelta

from django.http import HttpResponse, HttpResponseBadRequest, urlencode
from django.template import RequestContext
from django.contrib.auth import authenticate
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.encoding import iri_to_uri
from django.utils.translation import ugettext as _

from astakos.im.models import AstakosUser, Invitation
from astakos.im.user_utils import login
from astakos.im import settings

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


def epoch(dt):
    return int(time.mktime(dt.timetuple()) * 1000)


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
    Utility method to validate that provided url is safe to be used as the
    redirect location of an http redirect response. The method parses the
    provided url and identifies if it conforms CORS against provided domain
    AND url scheme matches any of the schemes in `allowed_schemes` parameter.
    If verirication succeeds sanitized safe url is returned. Consider using
    the method's result in the response location header and not the originally
    provided url. If verification fails the method returns None.

    >>> print restrict_next('/im/feedback', '.okeanos.grnet.gr')
    /im/feedback
    >>> print restrict_next('pithos.okeanos.grnet.gr/im/feedback',
    ...                     '.okeanos.grnet.gr')
    //pithos.okeanos.grnet.gr/im/feedback
    >>> print restrict_next('https://pithos.okeanos.grnet.gr/im/feedback',
    ...                     '.okeanos.grnet.gr')
    https://pithos.okeanos.grnet.gr/im/feedback
    >>> print restrict_next('pithos://127.0.0.1', '.okeanos.grnet.gr')
    None
    >>> print restrict_next('pithos://127.0.0.1', '.okeanos.grnet.gr',
    ...                     allowed_schemes=('pithos'))
    None
    >>> print restrict_next('pithos://127.0.0.1', '127.0.0.1',
    ...                     allowed_schemes=('pithos'))
    pithos://127.0.0.1
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
    >>> print restrict_next('node1.example.com', allowed_schemes=('pithos',))
    None
    >>> print restrict_next('pithos://localhost', 'localhost',
    ...                     allowed_schemes=('pithos',))
    pithos://localhost
    """
    if not url:
        return None

    parts = urlparse(url, scheme='http')
    if not parts.netloc and not parts.path.startswith('/'):
        # fix url if does not conforms RFC 1808
        url = '//%s' % url
        parts = urlparse(url, scheme='http')

    if not domain and not allowed_schemes:
        return url

    # domain validation
    if domain:
        if not parts.netloc:
            return url
        if parts.netloc.endswith(domain):
            return url
        else:
            return None

    # scheme validation
    if allowed_schemes:
        if parts.scheme in allowed_schemes:
            return url

    return None


def restrict_reverse(*args, **kwargs):
    """
    Like reverse, with an additional restrict_next call to the reverse result.
    """
    domain = kwargs.pop('restrict_domain', settings.COOKIE_DOMAIN)
    url = reverse(*args, **kwargs)
    return restrict_next(url, domain=domain)


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
    renew = renew or user.token_expired()
    if renew:
        user.renew_token(
            flush_sessions=True,
            current_key=request.session.session_key
        )
        try:
            user.save()
        except ValidationError, e:
            return HttpResponseBadRequest(e)

    next = restrict_next(next, domain=settings.COOKIE_DOMAIN)

    if settings.FORCE_PROFILE_UPDATE and \
            not user.is_verified and not user.is_superuser:
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
        next = settings.LOGIN_SUCCESS_URL

    response['Location'] = iri_to_uri(next)
    response.status_code = 302
    return response


def reserved_email(email):
    return AstakosUser.objects.user_exists(email)


def reserved_verified_email(email):
    return AstakosUser.objects.verified_user_exists(email)


def get_query(request):
    try:
        return request.__getattribute__(request.method)
    except AttributeError:
        return {}


def get_properties(obj):
    def get_class_attr(_class, attr):
        try:
            return getattr(_class, attr)
        except AttributeError:
            return

    return (i for i in vars(obj.__class__)
            if isinstance(get_class_attr(obj.__class__, i), property))


def model_to_dict(obj, exclude=None, include_empty=True):
    '''
        serialize model object to dict with related objects

        author: Vadym Zakovinko <vp@zakovinko.com>
        date: January 31, 2011
        http://djangosnippets.org/snippets/2342/
    '''

    if exclude is None:
        exclude = ['AutoField', 'ForeignKey', 'OneToOneField']
    tree = {}
    for field_name in obj._meta.get_all_field_names():
        try:
            field = getattr(obj, field_name)
        except (ObjectDoesNotExist, AttributeError):
            continue

        if field.__class__.__name__ in ['RelatedManager',
                                        'ManyRelatedManager']:
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
    properties = list(get_properties(obj))
    for p in properties:
        tree[p] = getattr(obj, p)
    tree['str_repr'] = obj.__str__()

    return tree


def login_url(request):
    attrs = {}
    for attr in ['login', 'key', 'code']:
        val = request.REQUEST.get(attr, None)
        if val:
            attrs[attr] = val
    return "%s?%s" % (reverse('login'), urllib.urlencode(attrs))


def redirect_back(request, default='index'):
    """
    Redirect back to referer if safe and possible.
    """
    referer = request.META.get('HTTP_REFERER')

    safedomain = settings.BASE_URL.replace("https://", "").replace(
        "http://", "")
    safe = restrict_next(referer, safedomain)
    # avoid redirect loop
    loops = referer == request.get_full_path()
    if referer and safe and not loops:
        return redirect(referer)
    return redirect(reverse(default))


def truncatename(v, max=18, append="..."):
    length = len(v)
    if length > max:
        return v[:max] + append
    else:
        return v
