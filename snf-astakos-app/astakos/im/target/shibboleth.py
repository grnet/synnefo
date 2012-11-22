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

from django.http import HttpResponseBadRequest
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.template import RequestContext
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from urlparse import urlunsplit, urlsplit
from django.utils.http import urlencode

from astakos.im.util import prepare_response, get_context, get_invitation
from astakos.im.views import requires_anonymous, render_response
from astakos.im.settings import ENABLE_LOCAL_ACCOUNT_MIGRATION, BASEURL

from astakos.im.models import AstakosUser, PendingThirdPartyUser
from astakos.im.forms import LoginForm
from astakos.im.activation_backends import get_backend, SimpleBackend

import logging

logger = logging.getLogger(__name__)

class Tokens:
    # these are mapped by the Shibboleth SP software
    SHIB_EPPN = "HTTP_EPPN" # eduPersonPrincipalName
    SHIB_NAME = "HTTP_SHIB_INETORGPERSON_GIVENNAME"
    SHIB_SURNAME = "HTTP_SHIB_PERSON_SURNAME"
    SHIB_CN = "HTTP_SHIB_PERSON_COMMONNAME"
    SHIB_DISPLAYNAME = "HTTP_SHIB_INETORGPERSON_DISPLAYNAME"
    SHIB_EP_AFFILIATION = "HTTP_SHIB_EP_AFFILIATION"
    SHIB_SESSION_ID = "HTTP_SHIB_SESSION_ID"
    SHIB_MAIL = "HTTP_SHIB_MAIL"

@require_http_methods(["GET", "POST"])
@requires_anonymous
def login(
    request,
    login_template='im/login.html',
    signup_template='im/third_party_check_local.html',
    extra_context=None
):
    extra_context = extra_context or {}

    tokens = request.META
    
    try:
        eppn = tokens.get(Tokens.SHIB_EPPN)
        if not eppn:
            raise KeyError(_('Missing unique token in request'))
        if Tokens.SHIB_DISPLAYNAME in tokens:
            realname = tokens[Tokens.SHIB_DISPLAYNAME]
        elif Tokens.SHIB_CN in tokens:
            realname = tokens[Tokens.SHIB_CN]
        elif Tokens.SHIB_NAME in tokens and Tokens.SHIB_SURNAME in tokens:
            realname = tokens[Tokens.SHIB_NAME] + ' ' + tokens[Tokens.SHIB_SURNAME]
        else:
            raise KeyError(_('Missing user name in request'))
    except KeyError, e:
        extra_context['login_form'] = LoginForm(request=request)
        messages.error(request, e)
        return render_response(
            login_template,
            context_instance=get_context(request, extra_context)
        )
    
    affiliation = tokens.get(Tokens.SHIB_EP_AFFILIATION, '')
    email = tokens.get(Tokens.SHIB_MAIL, '')
    
    try:
        user = AstakosUser.objects.get(
            provider='shibboleth',
            third_party_identifier=eppn
        )
        if user.is_active:
            return prepare_response(request,
                                    user,
                                    request.GET.get('next'),
                                    'renew' in request.GET)
        elif not user.activation_sent:
            message = _('Your request is pending activation')
            messages.error(request, message)
        else:
            urls = {}
            urls['send_activation'] = reverse(
                'send_activation',
                kwargs={'user_id':user.id}
            )
            urls['signup'] = reverse(
                'shibboleth_signup',
                args= [user.username]
            )   
            message = _(
                'You have not followed the activation link. \
                <a href="%(send_activation)s">Resend activation email?</a> or \
                <a href="%(signup)s">Provide new email?</a>' % urls
            )
            messages.error(request, message)
        return render_response(login_template,
                               login_form = LoginForm(request=request),
                               context_instance=RequestContext(request))
    except AstakosUser.DoesNotExist, e:
        # First time
        try:
            user, created = PendingThirdPartyUser.objects.get_or_create(
                third_party_identifier=eppn,
                provider='shibboleth',
                defaults=dict(
                    realname=realname,
                    affiliation=affiliation,
                    email=email
                )
            )
            user.save()
        except BaseException, e:
            logger.exception(e)
            template = login_template
            extra_context['login_form'] = LoginForm(request=request)
            messages.error(request, _('Something went wrong.'))
        else:
            if not ENABLE_LOCAL_ACCOUNT_MIGRATION:
                url = reverse(
                    'shibboleth_signup',
                    args= [user.username]
                )
                return HttpResponseRedirect(url)
            else:
                template = signup_template
                extra_context['username'] = user.username
        
        extra_context['provider']='shibboleth'
        return render_response(
            template,
            context_instance=get_context(request, extra_context)
        )

@require_http_methods(["GET"])
@requires_anonymous
def signup(
    request,
    username,
    backend=None,
    on_creation_template='im/third_party_registration.html',
    extra_context=None
):
    extra_context = extra_context or {}
    if not username:
        return HttpResponseBadRequest(_('Missing key parameter.'))
    try:
        pending = PendingThirdPartyUser.objects.get(username=username)
    except PendingThirdPartyUser.DoesNotExist:
        try:
            user = AstakosUser.objects.get(username=username)
        except AstakosUser.DoesNotExist:
            return HttpResponseBadRequest(_('Invalid key.'))
    else:
        d = pending.__dict__
        d.pop('_state', None)
        d.pop('id', None)
        user = AstakosUser(**d)
    try:
        backend = backend or get_backend(request)
    except ImproperlyConfigured, e:
        messages.error(request, e)
    else:
        extra_context['form'] = backend.get_signup_form(
            provider='shibboleth',
            instance=user
        )
    extra_context['provider']='shibboleth'
    return render_response(
            on_creation_template,
            context_instance=get_context(request, extra_context)
    )