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

from traceback import format_exc
from time import time, mktime
from urllib import quote
from urlparse import urlparse

from django.conf import settings
from django.http import HttpResponse
from django.utils import simplejson as json
from django.core.urlresolvers import reverse

from astakos.im.faults import BadRequest, Unauthorized, InternalServerError
from astakos.im.models import AstakosUser
from astakos.im.settings import CLOUD_SERVICES, INVITATIONS_ENABLED

def render_fault(request, fault):
    if isinstance(fault, InternalServerError) and settings.DEBUG:
        fault.details = format_exc(fault)

    request.serialization = 'text'
    data = fault.message + '\n'
    if fault.details:
        data += '\n' + fault.details
    response = HttpResponse(data, status=fault.code)
    response['Content-Length'] = len(response.content)
    return response

def authenticate(request):
    # Normal Response Codes: 204
    # Error Response Codes: internalServerError (500)
    #                       badRequest (400)
    #                       unauthorised (401)
    try:
        if request.method != 'GET':
            raise BadRequest('Method not allowed.')
        x_auth_token = request.META.get('HTTP_X_AUTH_TOKEN')
        if not x_auth_token:
            return render_fault(request, BadRequest('Missing X-Auth-Token'))

        try:
            user = AstakosUser.objects.get(auth_token=x_auth_token)
        except AstakosUser.DoesNotExist, e:
            return render_fault(request, Unauthorized('Invalid X-Auth-Token'))

        # Check if the is active.
        if not user.is_active:
            return render_fault(request, Unauthorized('User inactive'))

        # Check if the token has expired.
        if (time() - mktime(user.auth_token_expires.timetuple())) > 0:
            return render_fault(request, Unauthorized('Authentication expired'))

        response = HttpResponse()
        response.status=204
        user_info = {'username':user.username,
                     'uniq':user.email,
                     'auth_token':user.auth_token,
                     'auth_token_created':user.auth_token_created.isoformat(),
                     'auth_token_expires':user.auth_token_expires.isoformat()}
        response.content = json.dumps(user_info)
        response['Content-Type'] = 'application/json; charset=UTF-8'
        response['Content-Length'] = len(response.content)
        return response
    except BaseException, e:
        fault = InternalServerError('Unexpected error')
        return render_fault(request, fault)

def get_services(request):
    if request.method != 'GET':
        raise BadRequest('Method not allowed.')

    callback = request.GET.get('callback', None)
    data = json.dumps(CLOUD_SERVICES)
    mimetype = 'application/json'

    if callback:
        mimetype = 'application/javascript'
        data = '%s(%s)' % (callback, data)

    return HttpResponse(content=data, mimetype=mimetype)

def get_menu(request):
    if request.method != 'GET':
        raise BadRequest('Method not allowed.')
    location = request.GET.get('location', '')
    absolute = lambda (url): request.build_absolute_uri(url)
    index_url = absolute(reverse('astakos.im.views.index'))
    if urlparse(location).query.rfind('next=') == -1:
        index_url = '%s?next=%s' % (index_url, quote(location))
    l = [{ 'url': index_url, 'name': "login..."}]
    if request.user.is_authenticated():
        l = []
        l.append({ 'url': absolute(reverse('astakos.im.views.edit_profile')),
                  'name': request.user.email})
        l.append({ 'url': absolute(reverse('astakos.im.views.edit_profile')),
                  'name': "view your profile..." })
        if request.user.password:
            l.append({ 'url': absolute(reverse('password_change')),
                      'name': "change your password..." })
        if INVITATIONS_ENABLED:
            l.append({ 'url': absolute(reverse('astakos.im.views.invite')),
                      'name': "invite some friends..." })
        l.append({ 'url': absolute(reverse('astakos.im.views.send_feedback')),
                  'name': "feedback..." })
        l.append({ 'url': absolute(reverse('astakos.im.views.logout')),
                  'name': "logout..."})

    callback = request.GET.get('callback', None)
    data = json.dumps(tuple(l))
    mimetype = 'application/json'

    if callback:
        mimetype = 'application/javascript'
        data = '%s(%s)' % (callback, data)

    return HttpResponse(content=data, mimetype=mimetype)
