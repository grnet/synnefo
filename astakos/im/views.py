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

import json
import logging
import socket
import csv
import sys

from datetime import datetime
from functools import wraps
from math import ceil
from random import randint
from smtplib import SMTPException
from hashlib import new as newhasher
from urllib import quote

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.utils.http import urlencode
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

#from astakos.im.openid_store import PithosOpenIDStore
from astakos.im.models import AstakosUser, Invitation
from astakos.im.util import isoformat, get_or_create_user, get_context
from astakos.im.forms import *
from astakos.im.backends import get_backend

def render_response(template, tab=None, status=200, context_instance=None, **kwargs):
    if tab is None:
        tab = template.partition('_')[0]
    kwargs.setdefault('tab', tab)
    html = render_to_string(template, kwargs, context_instance=context_instance)
    return HttpResponse(html, status=status)

def requires_login(func):
    @wraps(func)
    def wrapper(request, *args):
        if not settings.BYPASS_ADMIN_AUTH:
            if not request.user:
                next = urlencode({'next': request.build_absolute_uri()})
                login_uri = reverse(index) + '?' + next
                return HttpResponseRedirect(login_uri)
        return func(request, *args)
    return wrapper

def index(request, template_name='index.html', extra_context={}):
    print '#', get_context(request, extra_context)
    return render_response(template_name,
                           form = LoginForm(),
                           context_instance = get_context(request, extra_context))

def _generate_invitation_code():
    while True:
        code = randint(1, 2L**63 - 1)
        try:
            Invitation.objects.get(code=code)
            # An invitation with this code already exists, try again
        except Invitation.DoesNotExist:
            return code

def _send_invitation(baseurl, inv):
    url = settings.SIGNUP_TARGET % (baseurl, inv.code, quote(baseurl))
    subject = _('Invitation to Pithos')
    message = render_to_string('invitation.txt', {
                'invitation': inv,
                'url': url,
                'baseurl': baseurl,
                'service': settings.SERVICE_NAME,
                'support': settings.DEFAULT_CONTACT_EMAIL})
    sender = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, sender, [inv.username])
    logging.info('Sent invitation %s', inv)

@requires_login
def invite(request, template_name='invitations.html', extra_context={}):
    status = None
    message = None
    inviter = request.user

    if request.method == 'POST':
        username = request.POST.get('uniq')
        realname = request.POST.get('realname')
        
        if inviter.invitations > 0:
            code = _generate_invitation_code()
            invitation, created = Invitation.objects.get_or_create(
                inviter=inviter,
                username=username,
                defaults={'code': code, 'realname': realname})
            
            try:
                _send_invitation(request.build_absolute_uri('/').rstrip('/'), invitation)
                if created:
                    inviter.invitations = max(0, inviter.invitations - 1)
                    inviter.save()
                status = 'success'
                message = _('Invitation sent to %s' % username)
            except (SMTPException, socket.error) as e:
                status = 'error'
                message = getattr(e, 'strerror', '')
        else:
            status = 'error'
            message = _('No invitations left')

    if request.GET.get('format') == 'json':
        sent = [{'email': inv.username,
                 'realname': inv.realname,
                 'is_accepted': inv.is_accepted}
                    for inv in inviter.invitations_sent.all()]
        rep = {'invitations': inviter.invitations, 'sent': sent}
        return HttpResponse(json.dumps(rep))
    
    kwargs = {'user': inviter, 'status': status, 'message': message}
    context = get_context(request, extra_context, **kwargs)
    return render_response(template_name,
                           context_instance = context)

def _send_password(baseurl, user):
    url = settings.PASSWORD_RESET_TARGET % (baseurl,
                                            quote(user.username),
                                            quote(baseurl))
    message = render_to_string('password.txt', {
            'user': user,
            'url': url,
            'baseurl': baseurl,
            'service': settings.SERVICE_NAME,
            'support': settings.DEFAULT_CONTACT_EMAIL})
    sender = settings.DEFAULT_FROM_EMAIL
    send_mail('Pithos password recovering', message, sender, [user.email])
    logging.info('Sent password %s', user)

def reclaim_password(request, template_name='reclaim.html', extra_context={}):
    if request.method == 'GET':
        return render_response(template_name,
                               context_instance = get_context(request, extra_context))
    elif request.method == 'POST':
        username = request.POST.get('username')
        try:
            user = AstakosUser.objects.get(username=username)
            try:
                _send_password(request.build_absolute_uri('/').rstrip('/'), user)
                status = 'success'
                message = _('Password reset sent to %s' % user.email)
                user.is_active = False
                user.save()
            except (SMTPException, socket.error) as e:
                status = 'error'
                name = 'strerror'
                message = getattr(e, name) if hasattr(e, name) else e
        except AstakosUser.DoesNotExist:
            status = 'error'
            message = 'Username does not exist'
        
        kwargs = {'status': status, 'message': message}
        return render_response(template_name,
                                context_instance = get_context(request, extra_context, **kwargs))

@requires_login
def users_profile(request, template_name='users_profile.html', extra_context={}):
    try:
        user = AstakosUser.objects.get(username=request.user)
    except AstakosUser.DoesNotExist:
        token = request.GET.get('auth', None)
        user = AstakosUser.objects.get(auth_token=token)
    return render_response(template_name,
                           context_instance = get_context(request,
                                                          extra_context,
                                                          user=user))

@requires_login
def users_edit(request, template_name='users_profile.html', extra_context={}):
    try:
        user = AstakosUser.objects.get(username=request.user)
    except AstakosUser.DoesNotExist:
        token = request.POST.get('auth', None)
        #users = AstakosUser.objects.all()
        user = AstakosUser.objects.get(auth_token=token)
    user.first_name = request.POST.get('first_name')
    user.last_name = request.POST.get('last_name')
    user.affiliation = request.POST.get('affiliation')
    user.is_verified = True
    user.save()
    next = request.POST.get('next')
    if next:
        return redirect(next)
    
    status = 'success'
    message = _('Profile has been updated')
    return render_response(template_name,
                           context_instance = get_context(request, extra_context, **kwargs))
    
def signup(request, template_name='signup.html', extra_context={}, backend=None, success_url = None):
    if not backend:
        backend = get_backend()
    if request.method == 'GET':
        try:
            form = backend.get_signup_form(request)
            return render_response(template_name,
                               form=form,
                               context_instance = get_context(request, extra_context))
        except Exception, e:
            return _on_failure(e, template_name=template_name)
    elif request.method == 'POST':
        try:
            form = backend.get_signup_form(request)
            if not form.is_valid():
                return render_response(template_name,
                                       form = form,
                                       context_instance = get_context(request, extra_context))
            status, message = backend.signup(request, form, success_url)
            next = request.POST.get('next')
            if next:
                return redirect(next)
            return _info(status, message)
        except Exception, e:
            return _on_failure(e, template_name=template_name)

def _info(status, message, template_name='base.html'):
    html = render_to_string(template_name, {
            'status': status,
            'message': message})
    response = HttpResponse(html)
    return response

def _on_success(message, template_name='base.html'):
    return _info('success', message, template_name)
    
def _on_failure(message, template_name='base.html'):
    return _info('error', message, template_name)
