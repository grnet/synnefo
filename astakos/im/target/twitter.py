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

# This is based on the docs at: https://github.com/simplegeo/python-oauth2

import oauth2 as oauth
import urlparse

from django.http import HttpResponse
from django.utils import simplejson as json
from django.contrib import messages

from astakos.im.util import get_context, prepare_response
from astakos.im.models import AstakosUser, Invitation
from astakos.im.views import render_response, requires_anonymous
from astakos.im.forms import LocalUserCreationForm, ThirdPartyUserCreationForm
from astakos.im.faults import BadRequest
from astakos.im.backends import get_backend
from astakos.im.settings import TWITTER_KEY, TWITTER_SECRET, INVITATIONS_ENABLED, IM_MODULES

# It's probably a good idea to put your consumer's OAuth token and
# OAuth secret into your project's settings. 
consumer = oauth.Consumer(TWITTER_KEY, TWITTER_SECRET)
client = oauth.Client(consumer)

request_token_url = 'http://twitter.com/oauth/request_token'
access_token_url = 'http://twitter.com/oauth/access_token'

# This is the slightly different URL used to authenticate/authorize.
authenticate_url = 'http://twitter.com/oauth/authenticate'

@requires_anonymous
def login(request, extra_context={}):
    # store invitation code and email
    request.session['email'] = request.GET.get('email')
    request.session['invitation_code'] = request.GET.get('code')

    # Step 1. Get a request token from Twitter.
    resp, content = client.request(request_token_url, "GET")
    if resp['status'] != '200':
        raise Exception("Invalid response from Twitter.")
    request_token = dict(urlparse.parse_qsl(content))
    if request.GET.get('next'):
        request_token['next'] = request.GET['next']
    
    # Step 2. Store the request token in a session for later use.
    response = HttpResponse()
    request.session['Twitter-Request-Token'] = value=json.dumps(request_token)
    
    # Step 3. Redirect the user to the authentication URL.
    url = "%s?oauth_token=%s" % (authenticate_url, request_token['oauth_token'])
    response['Location'] = url
    response.status_code = 302
    
    return response

@requires_anonymous
def authenticated(request, backend=None, login_template='im/login.html', on_signup_failure='im/signup.html', on_signup_success='im/signup_complete.html', extra_context={}):
    # Step 1. Use the request token in the session to build a new client.
    data = request.session.get('Twitter-Request-Token')
    if not data:
        raise Exception("Request token cookie not found.")
    del request.session['Twitter-Request-Token']
    
    request_token = json.loads(data)
    if not hasattr(request_token, '__getitem__'):
        raise BadRequest('Invalid data formating')
    try:
        token = oauth.Token(request_token['oauth_token'],
                            request_token['oauth_token_secret'])
    except:
        raise BadRequest('Invalid request token cookie formatting')
    client = oauth.Client(consumer, token)
    
    # Step 2. Request the authorized access token from Twitter.
    resp, content = client.request(access_token_url, "GET")
    if resp['status'] != '200':
        raise Exception("Invalid response from Twitter.")
    
    """
    This is what you'll get back from Twitter. Note that it includes the
    user's user_id and screen_name.
    {
        'oauth_token_secret': 'IcJXPiJh8be3BjDWW50uCY31chyhsMHEhqJVsphC3M',
        'user_id': '120889797', 
        'oauth_token': '120889797-H5zNnM3qE0iFoTTpNEHIz3noL9FKzXiOxwtnyVOD',
        'screen_name': 'heyismysiteup'
    }
    """
    access_token = dict(urlparse.parse_qsl(content))
    
    # Step 3. Lookup the user or create them if they don't exist.
    
    # When creating the user I just use their screen_name@twitter.com
    # for their email and the oauth_token_secret for their password.
    # These two things will likely never be used. Alternatively, you 
    # can prompt them for their email here. Either way, the password 
    # should never be used.
    screen_name = access_token['screen_name']
    next = request_token.get('next')
    
    # check first if user with that email is registered
    # and if not create one
    user = None
    email = request.session.pop('email')
    
    if email: # signup mode
        if not reserved_screen_name(screen_name): 
            try:
                user = AstakosUser.objects.get(email = email)
            except AstakosUser.DoesNotExist, e:
                # register a new user
                post_data = {'provider':'Twitter', 'affiliation':'twitter',
                                'third_party_identifier':screen_name}
                form = ThirdPartyUserCreationForm({'email':email})
                return create_user(request, form, backend, post_data, next, on_signup_failure, on_signup_success, extra_context)
        else:
            status = messages.ERROR
            message = '%s@twitter is already registered' % screen_name
            messages.add_message(request, messages.ERROR, message)
            prefix = 'Invited' if request.session['invitation_code'] else ''
            suffix  = 'UserCreationForm'
            for provider in IM_MODULES:
                main = provider.capitalize() if provider == 'local' else 'ThirdParty'
                formclass = '%s%s%s' % (prefix, main, suffix)
                extra_context['%s_form' % provider] = globals()[formclass]()
            return render_response(on_signup_failure,
                                   context_instance=get_context(request, extra_context))
    else: # login mode
        try:
            user = AstakosUser.objects.get(third_party_identifier = screen_name,
                                           provider = 'Twitter')
        except AstakosUser.DoesNotExist:
            messages.add_message(request, messages.ERROR, 'Not registered user')
        if user and user.is_active:
            return prepare_response(request, user, next)
        elif user and not user.is_active:
            messages.add_message(request, messages.ERROR, 'Inactive account: %s' % user.email)
    return render_response(login_template,
                   form = LocalUserCreationForm(),
                   context_instance=get_context(request, extra_context))

def reserved_screen_name(screen_name):
    try:
        AstakosUser.objects.get(provider='Twitter',
                                third_party_identifier=screen_name)
        return True
    except AstakosUser.DoesNotExist, e:
        return False

def create_user(request, form, backend=None, post_data={}, next = None, on_failure='im/signup.html', on_success='im/signup_complete.html', extra_context={}): 
    """
    Create a user.
    
    The user activation will be delegated to the backend specified by the ``backend`` keyword argument
    if present, otherwise to the ``astakos.im.backends.InvitationBackend``
    if settings.ASTAKOS_INVITATIONS_ENABLED is True or ``astakos.im.backends.SimpleBackend`` if not
    (see backends);
    
    Upon successful user creation if ``next`` url parameter is present the user is redirected there
    otherwise renders the ``on_success`` template (if exists) or im/signup_complete.html.
    
    On unsuccessful creation, renders the ``on_failure`` template (if exists) or im/signup.html with an error message.
    
    **Arguments**
    
    ``on_failure``
        A custom template to render in case of failure. This is optional;
        if not specified, this will default to ``im/signup.html``.
    
    ``on_success``
        A custom template to render in case of success. This is optional;
        if not specified, this will default to ``im/signup_complete.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
    **Template:**
    
    im/signup.html or ``on_failure`` keyword argument.
    im/signup_complete.html or ``on_success`` keyword argument.
    """
    try:
        if not backend:
            backend = get_backend(request)
        if form.is_valid():
            status, message, user = backend.signup(form)
            if status == messages.SUCCESS:
                for k,v in post_data.items():
                    setattr(user,k, v)
                user.save()
                if user.is_active:
                    return prepare_response(request, user, next=next)
            messages.add_message(request, status, message)
            return render_response(on_success,
                                   context_instance=get_context(request, extra_context))
        else:
            messages.add_message(request, messages.ERROR, form.errors)
    except (Invitation.DoesNotExist, ValueError), e:
        messages.add_message(request, messages.ERROR, e)
    for provider in IM_MODULES:
        extra_context['%s_form' % provider] = backend.get_signup_form(provider)
    return render_response(on_failure,
                           form = LocalUserCreationForm(),
                           context_instance=get_context(request, extra_context))