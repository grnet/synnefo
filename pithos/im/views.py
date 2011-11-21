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

from datetime import datetime
from functools import wraps
from math import ceil
from random import randint
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.http import urlencode
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from urllib import quote

from pithos.im.models import User, Invitation
from pithos.im.util import isoformat


def render_response(template, tab=None, status=200, **kwargs):
    if tab is None:
        tab = template.partition('_')[0]
    kwargs.setdefault('tab', tab)
    html = render_to_string(template, kwargs)
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


def requires_admin(func):
    @wraps(func)
    def wrapper(request, *args):
        if not settings.BYPASS_ADMIN_AUTH:
            if not request.user:
                next = urlencode({'next': request.build_absolute_uri()})
                login_uri = reverse(index) + '?' + next
                return HttpResponseRedirect(login_uri)
            if not request.user.is_admin:
                return HttpResponse('Forbidden', status=403)
        return func(request, *args)
    return wrapper


def index(request):
    kwargs = {'standard_modules':settings.IM_STANDARD_MODULES,
              'other_modules':settings.IM_OTHER_MODULES}
    return render_response('index.html',
                           next=request.GET.get('next', ''),
                           **kwargs)


@requires_admin
def admin(request):
    stats = {}
    stats['users'] = User.objects.count()
    
    invitations = Invitation.objects.all()
    stats['invitations'] = invitations.count()
    stats['invitations_accepted'] = invitations.filter(is_accepted=True).count()
    
    return render_response('admin.html', tab='home', stats=stats)


@requires_admin
def users_list(request):
    users = User.objects.order_by('id')
    
    filter = request.GET.get('filter', '')
    if filter:
        if filter.startswith('-'):
            users = users.exclude(uniq__icontains=filter[1:])
        else:
            users = users.filter(uniq__icontains=filter)
    
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
    offset = max(0, page - 1) * settings.ADMIN_PAGE_LIMIT
    limit = offset + settings.ADMIN_PAGE_LIMIT
    
    npages = int(ceil(1.0 * users.count() / settings.ADMIN_PAGE_LIMIT))
    prev = page - 1 if page > 1 else None
    next = page + 1 if page < npages else None
    return render_response('users_list.html',
                            users=users[offset:limit],
                            filter=filter,
                            pages=range(1, npages + 1),
                            page=page,
                            prev=prev,
                            next=next)
    
@requires_admin
def users_create(request):
    if request.method == 'GET':
        return render_response('users_create.html')
    if request.method == 'POST':
        user = User()
        user.uniq = request.POST.get('uniq')
        user.realname = request.POST.get('realname')
        user.is_admin = True if request.POST.get('admin') else False
        user.affiliation = request.POST.get('affiliation')
        user.quota = int(request.POST.get('quota') or 0) * (1024 ** 3)  # In GiB
        user.renew_token()
        user.save()
        return redirect(users_info, user.id)

@requires_admin
def users_info(request, user_id):
    user = User.objects.get(id=user_id)
    states = [x[0] for x in User.ACCOUNT_STATE]
    return render_response('users_info.html',
                            user=user,
                            states=states)


@requires_admin
def users_modify(request, user_id):
    user = User.objects.get(id=user_id)
    user.uniq = request.POST.get('uniq')
    user.realname = request.POST.get('realname')
    user.is_admin = True if request.POST.get('admin') else False
    user.affiliation = request.POST.get('affiliation')
    user.state = request.POST.get('state')
    user.invitations = int(request.POST.get('invitations') or 0)
    user.quota = int(request.POST.get('quota') or 0) * (1024 ** 3)  # In GiB
    user.auth_token = request.POST.get('auth_token')
    try:
        auth_token_expires = request.POST.get('auth_token_expires')
        d = datetime.strptime(auth_token_expires, '%Y-%m-%dT%H:%MZ')
        user.auth_token_expires = d
    except ValueError:
        pass
    user.save()
    return redirect(users_info, user.id)


@requires_admin
def users_delete(request, user_id):
    user = User.objects.get(id=user_id)
    user.delete()
    return redirect(users_list)


def generate_invitation_code():
    while True:
        code = randint(1, 2L**63 - 1)
        try:
            Invitation.objects.get(code=code)
            # An invitation with this code already exists, try again
        except Invitation.DoesNotExist:
            return code


def send_invitation(baseurl, inv):
    url = settings.INVITATION_LOGIN_TARGET % (baseurl, inv.code, quote(baseurl))
    subject = _('Invitation to Pithos')
    message = render_to_string('invitation.txt', {
                'invitation': inv,
                'url': url,
                'baseurl': baseurl,
                'service': settings.SERVICE_NAME,
                'support': settings.DEFAULT_CONTACT_EMAIL})
    sender = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, sender, [inv.uniq])
    logging.info('Sent invitation %s', inv)


@requires_login
def invite(request):
    status = None
    message = None
    inviter = request.user

    if request.method == 'POST':
        uniq = request.POST.get('uniq')
        realname = request.POST.get('realname')
        
        if inviter.invitations > 0:
            code = generate_invitation_code()
            invitation, created = Invitation.objects.get_or_create(
                inviter=inviter,
                uniq=uniq,
                defaults={'code': code, 'realname': realname})
            
            try:
                send_invitation(request.build_absolute_uri('/').rstrip('/'), invitation)
                if created:
                    inviter.invitations = max(0, inviter.invitations - 1)
                    inviter.save()
                status = 'success'
                message = _('Invitation sent to %s' % uniq)
            except (SMTPException, socket.error) as e:
                status = 'error'
                message = getattr(e, 'strerror', '')
        else:
            status = 'error'
            message = _('No invitations left')

    if request.GET.get('format') == 'json':
        sent = [{'email': inv.uniq,
                 'realname': inv.realname,
                 'is_accepted': inv.is_accepted}
                    for inv in inviter.invitations_sent.all()]
        rep = {'invitations': inviter.invitations, 'sent': sent}
        return HttpResponse(json.dumps(rep))
    
    html = render_to_string('invitations.html', {
            'user': inviter,
            'status': status,
            'message': message})
    return HttpResponse(html)

def send_verification(baseurl, user):
    url = settings.ACTIVATION_LOGIN_TARGET % (baseurl,
                                              quote(user.auth_token),
                                              quote(baseurl))
    message = render_to_string('activation.txt', {
            'user': user,
            'url': url,
            'baseurl': baseurl,
            'service': settings.SERVICE_NAME,
            'support': settings.DEFAULT_CONTACT_EMAIL})
    sender = settings.DEFAULT_FROM_EMAIL
    send_mail('Pithos account activation', message, sender, [user.email])
    logging.info('Sent activation %s', user)

def local_create(request):
    if request.method == 'GET':
        return render_response('local_create.html')
    elif request.method == 'POST':
        username = request.POST.get('uniq')
        realname = request.POST.get('realname')
        email = request.POST.get('email')
        password = request.POST.get('password')
        status = 'success'
        cookie_value = None
        if not username:
            status = 'error'
            message = 'No username provided'
        elif not password:
            status = 'error'
            message = 'No password provided'
        elif not email:
            status = 'error'
            message = 'No email provided'
        
        if status == 'success':
            username = '%s@local' % username
            try:
                user = User.objects.get(uniq=username)
                status = 'error'
                message = 'Username is not available'
            except User.DoesNotExist:
                user = User()
                user.uniq = username 
                user.realname = realname
                user.email = request.POST.get('email')
                user.password = request.POST.get('password')
                user.is_admin = False
                user.quota = 0
                user.state = 'UNVERIFIED'
                user.level = 1
                user.renew_token()
                try:
                    send_verification(request.build_absolute_uri('/').rstrip('/'), user)
                    message = _('Verification sent to %s' % user.email)
                    user.save()
                except (SMTPException, socket.error) as e:
                    status = 'error'
                    name = 'strerror'
                    message = getattr(e, name) if hasattr(e, name) else e
        
        html = render_to_string('local_create.html', {
                'status': status,
                'message': message})
        response = HttpResponse(html)
        return response

def send_password(baseurl, user):
    url = settings.PASSWORD_RESET_TARGET % (baseurl,
                                            quote(user.uniq),
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

def reclaim_password(request):
    if request.method == 'GET':
        return render_response('reclaim.html')
    elif request.method == 'POST':
        username = request.POST.get('uniq')
        username = '%s@local' % username
        try:
            user = User.objects.get(uniq=username)
            try:
                send_password(request.build_absolute_uri('/').rstrip('/'), user)
                status = 'success'
                message = _('Password reset sent to %s' % user.email)
                user.status = 'UNVERIFIED'
                user.save()
            except (SMTPException, socket.error) as e:
                status = 'error'
                name = 'strerror'
                message = getattr(e, name) if hasattr(e, name) else e
        except User.DoesNotExist:
            status = 'error'
            message = 'Username does not exist'
        
        html = render_to_string('reclaim.html', {
                'status': status,
                'message': message})
        return HttpResponse(html)
