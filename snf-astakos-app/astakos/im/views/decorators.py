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

from functools import wraps

from django.utils.http import urlquote
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.decorators import available_attrs
from django.utils.http import urlencode

from astakos.im import auth_providers as auth
from astakos.im.cookie import CookieHandler

REDIRECT_FIELD_NAME = 'next'


def user_passes_test(test_func, login_url=None,
                     redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    if not login_url:
        from django.conf import settings
        login_url = settings.LOGIN_URL

    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            path = urlquote(request.get_full_path())
            tup = reverse('login'), redirect_field_name, path
            return HttpResponseRedirect('%s?%s=%s' % tup)
        return wraps(view_func,
                     assigned=available_attrs(view_func))(_wrapped_view)
    return decorator


def login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME,
                   login_url=None):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated(),
        redirect_field_name=redirect_field_name,

    )
    if function:
        return actual_decorator(function)
    return actual_decorator


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
    View requires specified authentication module to be enabled in
    ASTAKOS_IM_MODULES setting.
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
