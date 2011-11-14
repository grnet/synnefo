# Copyright 2011 GRNET S.A. All rights reserved.
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

from django.conf import settings
from django.http import HttpResponse
from django.utils import simplejson as json

from pithos.im.target.util import get_or_create_user, prepare_response

# It's probably a good idea to put your consumer's OAuth token and
# OAuth secret into your project's settings. 
consumer = oauth.Consumer(settings.TWITTER_KEY, settings.TWITTER_SECRET)
client = oauth.Client(consumer)

request_token_url = 'http://twitter.com/oauth/request_token'
access_token_url = 'http://twitter.com/oauth/access_token'

# This is the slightly different URL used to authenticate/authorize.
authenticate_url = 'http://twitter.com/oauth/authenticate'

def login(request):
    # Step 1. Get a request token from Twitter.
    resp, content = client.request(request_token_url, "GET")
    if resp['status'] != '200':
        raise Exception("Invalid response from Twitter.")
    request_token = dict(urlparse.parse_qsl(content))
    if request.GET.get('next'):
        request_token['next'] = request.GET['next']
    
    # Step 2. Store the request token in a session for later use.
    response = HttpResponse()
    response.set_cookie('Twitter-Request-Token', value=json.dumps(request_token), max_age=300)
    
    # Step 3. Redirect the user to the authentication URL.
    url = "%s?oauth_token=%s" % (authenticate_url, request_token['oauth_token'])
    response['Location'] = url
    response.status_code = 302
    
    return response

def authenticated(request):
    # Step 1. Use the request token in the session to build a new client.
    data = request.COOKIES.get('Twitter-Request-Token', None)
    if not data:
        raise Exception("Request token cookie not found.")
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
    uniq = '%s@twitter.com' % access_token['screen_name']
    realname = access_token['user_id']
    
    return prepare_response(get_or_create_user(uniq, realname, 'Twitter', 0),
                            request_token.get('next'))
