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
import  traceback

from django.conf import settings
from django.http import HttpResponse
from django.utils import simplejson as json
from django.contrib.auth import authenticate
from django.contrib import messages
from django.shortcuts import redirect

from astakos.im.target.util import prepare_response, requires_anonymous
from astakos.im.util import get_or_create_user, get_context
from astakos.im.models import AstakosUser, Invitation
from astakos.im.views import render_response, create_user
from astakos.im.backends import get_backend
from astakos.im.forms import LocalUserCreationForm, ThirdPartyUserCreationForm
from astakos.im.faults import BadRequest

# It's probably a good idea to put your consumer's OAuth token and
# OAuth secret into your project's settings. 
consumer = oauth.Consumer(settings.TWITTER_KEY, settings.TWITTER_SECRET)
client = oauth.Client(consumer)

request_token_url = 'http://twitter.com/oauth/request_token'
access_token_url = 'http://twitter.com/oauth/access_token'

# This is the slightly different URL used to authenticate/authorize.
authenticate_url = 'http://twitter.com/oauth/authenticate'

@requires_anonymous
def login(request, template_name='signup.html', extra_context={}):
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
def authenticated(request, backend=None, template_name='login.html', extra_context={}):
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
    
    # signup mode
    if email:
        if not reserved_screen_name(screen_name): 
            try:
                user = AstakosUser.objects.get(email = email)
            except AstakosUser.DoesNotExist, e:
                # register a new user
                post_data = {'provider':'Twitter', 'affiliation':'twitter',
                                'third_party_identifier':screen_name}
                form = ThirdPartyUserCreationForm({'email':email})
                return create_user(request, form, backend, post_data, next, template_name, extra_context)
        else:
            status = messages.ERROR
            message = '%s@twitter is already registered' % screen_name
            messages.add_message(request, messages.ERROR, message)
    else:
        # login mode
        try:
            user = AstakosUser.objects.get(third_party_identifier = screen_name,
                                           provider = 'Twitter')
        except AstakosUser.DoesNotExist:
            messages.add_message(request, messages.ERROR, 'Not registered user')
        if user and user.is_active:
            #in order to login the user we must call authenticate first
            user = authenticate(email=user.email, auth_token=user.auth_token)
            return prepare_response(request, user, next)
        elif user and not user.is_active:
            messages.add_message(request, messages.ERROR, 'Inactive account: %s' % user.email)
    return render_response(template_name,
                   form = LocalUserCreationForm(),
                   context_instance=get_context(request, extra_context))

def reserved_screen_name(screen_name):
    try:
        AstakosUser.objects.get(provider='Twitter',
                                third_party_identifier=screen_name)
        return True
    except AstakosUser.DoesNotExist, e:
        return False