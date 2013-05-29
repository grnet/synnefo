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

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.http import urlencode

from astakos.im import auth_providers as auth
from astakos.im.cookie import CookieHandler


def cookie_fix(func):
    """
    Decorator checks whether the request.user conforms
    with the astakos cookie and if not it fixes it.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        cookie = CookieHandler(request)
        if not cookie.is_valid:
            # redirect to request path to set/delete the cookie
            response = HttpResponse(status=302)
            response['Location'] = request.get_full_path()
            cookie.fix(response)
            return response

        response = func(request, *args, **kwargs)

        # if the user authentication status has changed during the processing
        # set/delete the cookie appropriately
        if not cookie.is_valid:
            cookie.fix(response)
        return response
    return wrapper


def requires_auth_provider(provider_id, **perms):
    """
    """
    def decorator(func, *args, **kwargs):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            provider = auth.get_provider(provider_id)

            if not provider or not provider.is_active():
                raise PermissionDenied

            for pkey, value in perms.iteritems():
                attr = 'get_%s_policy' % pkey.lower()
                if getattr(provider, attr) != value:
                    #TODO: add session message
                    return HttpResponseRedirect(reverse('login'))
            return func(request, *args)
        return wrapper
    return decorator


def requires_anonymous(func):
    """
    Decorator checkes whether the request.user is not Anonymous and
    in that case redirects to `logout`.
    """
    @wraps(func)
    def wrapper(request, *args):
        if not request.user.is_anonymous():
            next = urlencode({'next': request.build_absolute_uri()})
            logout_uri = reverse('astakos.im.views.logout') + '?' + next
            return HttpResponseRedirect(logout_uri)
        return func(request, *args)
    return wrapper


def signed_terms_required(func):
    """
    Decorator checks whether the request.user is Anonymous and in that case
    redirects to `logout`.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated() and not request.user.signed_terms:
            params = urlencode({'next': request.build_absolute_uri(),
                                'show_form': ''})
            terms_uri = reverse('latest_terms') + '?' + params
            return HttpResponseRedirect(terms_uri)
        return func(request, *args, **kwargs)
    return wrapper


def required_auth_methods_assigned(allow_access=False):
    """
    Decorator that checks whether the request.user has all
    required auth providers assigned.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated():
                missing = request.user.missing_required_providers()
                if missing:
                    for provider in missing:
                        messages.error(request,
                                       provider.get_required_msg)
                    if not allow_access:
                        return HttpResponseRedirect(reverse('edit_profile'))
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def valid_astakos_user_required(func):
    return signed_terms_required(
        required_auth_methods_assigned()(login_required(func)))
