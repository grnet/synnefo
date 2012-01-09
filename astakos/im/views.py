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

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.shortcuts import render_to_response
from django.utils.http import urlencode
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.forms import Form
from django.forms.formsets import formset_factory
#from openid.consumer.consumer import Consumer, \
#    SUCCESS, CANCEL, FAILURE, SETUP_NEEDED

from hashlib import new as newhasher

from urllib import quote

#from astakos.im.openid_store import PithosOpenIDStore
from astakos.im.models import User, Invitation
from astakos.im.util import isoformat
from astakos.im.forms import *

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
    kwargs = {'im_modules':settings.IM_MODULES,
              'other_modules':settings.IM_MODULES[1:]}
    return render_response('index.html',
                           next=request.GET.get('next', ''),
                           **kwargs)


@requires_admin
def admin(request):
    stats = {}
    stats['users'] = User.objects.count()
    stats['pending'] = User.objects.filter(state = 'PENDING').count()
    
    invitations = Invitation.objects.all()
    stats['invitations'] = invitations.count()
    stats['invitations_consumed'] = invitations.filter(is_consumed=True).count()
    
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

@requires_admin
def pending_users(request):
    users = User.objects.order_by('id')
    
    users = users.filter(state = 'PENDING')
    
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
    offset = max(0, page - 1) * settings.ADMIN_PAGE_LIMIT
    limit = offset + settings.ADMIN_PAGE_LIMIT
    
    npages = int(ceil(1.0 * users.count() / settings.ADMIN_PAGE_LIMIT))
    prev = page - 1 if page > 1 else None
    next = page + 1 if page < npages else None
    return render_response('pending_users.html',
                            users=users[offset:limit],
                            filter=filter,
                            pages=range(1, npages + 1),
                            page=page,
                            prev=prev,
                            next=next)

def send_greeting(baseurl, user):
    url = baseurl
    subject = _('Welcome to Pithos')
    message = render_to_string('welcome.txt', {
                'user': user,
                'url': url,
                'baseurl': baseurl,
                'service': settings.SERVICE_NAME,
                'support': settings.DEFAULT_CONTACT_EMAIL})
    sender = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, sender, [user.email])
    logging.info('Sent greeting %s', user)

@requires_admin
def users_activate(request, user_id):
    user = User.objects.get(id=user_id)
    user.state = 'ACTIVE'
    status = 'success'
    try:
        send_greeting(request.build_absolute_uri('/').rstrip('/'), user)
        message = _('Greeting sent to %s' % user.email)
        user.save()
    except (SMTPException, socket.error) as e:
        status = 'error'
        name = 'strerror'
        message = getattr(e, name) if hasattr(e, name) else e
    
    users = User.objects.order_by('id')
    users = users.filter(state = 'PENDING')
    
    try:
        page = int(request.POST.get('page', 1))
    except ValueError:
        page = 1
    offset = max(0, page - 1) * settings.ADMIN_PAGE_LIMIT
    limit = offset + settings.ADMIN_PAGE_LIMIT
    
    npages = int(ceil(1.0 * users.count() / settings.ADMIN_PAGE_LIMIT))
    prev = page - 1 if page > 1 else None
    next = page + 1 if page < npages else None
    return render_response('pending_users.html',
                            users=users[offset:limit],
                            filter=filter,
                            pages=range(1, npages + 1),
                            page=page,
                            prev=prev,
                            next=next,
                            message=message)

def generate_invitation_code():
    while True:
        code = randint(1, 2L**63 - 1)
        try:
            Invitation.objects.get(code=code)
            # An invitation with this code already exists, try again
        except Invitation.DoesNotExist:
            return code


def send_invitation(baseurl, inv):
    url = settings.SIGNUP_TARGET % (baseurl, inv.code, quote(baseurl))
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

@requires_admin
def invitations_list(request):
    invitations = Invitation.objects.order_by('id')
    
    filter = request.GET.get('filter', '')
    if filter:
        if filter.startswith('-'):
            invitations = invitations.exclude(uniq__icontains=filter[1:])
        else:
            invitations = invitations.filter(uniq__icontains=filter)
    
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
    offset = max(0, page - 1) * settings.ADMIN_PAGE_LIMIT
    limit = offset + settings.ADMIN_PAGE_LIMIT
    
    npages = int(ceil(1.0 * invitations.count() / settings.ADMIN_PAGE_LIMIT))
    prev = page - 1 if page > 1 else None
    next = page + 1 if page < npages else None
    return render_response('invitations_list.html',
                            invitations=invitations[offset:limit],
                            filter=filter,
                            pages=range(1, npages + 1),
                            page=page,
                            prev=prev,
                            next=next)

@requires_admin
def invitations_export(request):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=invitations.csv'

    writer = csv.writer(response)
    writer.writerow(['ID',
                     'Uniq',
                     'Real Name',
                     'Code',
                     'Inviter Uniq',
                     'Inviter Real Name',
                     'Is_accepted',
                     'Created',
                     'Accepted',])
    invitations = Invitation.objects.order_by('id')
    for inv in invitations:
        writer.writerow([inv.id,
                         inv.uniq.encode("utf-8"),
                         inv.realname.encode("utf-8"),
                         inv.code,
                         inv.inviter.uniq.encode("utf-8"),
                         inv.inviter.realname.encode("utf-8"),
                         inv.is_accepted,
                         inv.created,
                         inv.accepted])

    return response


@requires_admin
def users_export(request):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=users.csv'

    writer = csv.writer(response)
    writer.writerow(['ID',
                     'Uniq',
                     'Real Name',
                     'Admin',
                     'Affiliation',
                     'State',
                     'Quota (GiB)',
                     'Updated',])
    users = User.objects.order_by('id')
    for u in users:
        writer.writerow([u.id,
                         u.uniq.encode("utf-8"),
                         u.realname.encode("utf-8"),
                         u.is_admin,
                         u.affiliation.encode("utf-8"),
                         u.state.encode("utf-8"),
                         u.quota,
                         u.updated])

    return response

@requires_admin
def users_create(request):
    if request.method == 'GET':
        return render_response('users_local_create.html')
    if request.method == 'POST':
        user = User()
        user.uniq = request.POST.get('uniq')
        user.realname = request.POST.get('realname')
        user.is_admin = True if request.POST.get('admin') else False
        user.affiliation = request.POST.get('affiliation')
        user.quota = int(request.POST.get('quota') or 0) * (1024 ** 3)  # In GiB
        user.renew_token()
        user.provider = 'local'
        user.save()
        return redirect(users_info, user.id)

@requires_login
def users_profile(request):
    next = request.GET.get('next')
    try:
        user = User.objects.get(uniq=request.user)
    except User.DoesNotExist:
        user = User.objects.get(auth_token=request.GET.get('auth', None))
    states = [x[0] for x in User.ACCOUNT_STATE]
    return render_response('users_profile.html',
                            user=user,
                            states=states,
                            next=next)

@requires_login
def users_edit(request):
    try:
        user = User.objects.get(uniq=request.user)
    except User.DoesNotExist:
        token = request.POST.get('auth', None)
        users = User.objects.all()
        user = User.objects.get(auth_token=token)
    user.realname = request.POST.get('realname')
    user.affiliation = request.POST.get('affiliation')
    user.is_verified = True
    user.save()
    next = request.POST.get('next')
    if next:
        return redirect(next)
    
    status = 'success'
    message = _('Profile has been updated')
    html = render_to_string('users_profile.html', {
            'user': user,
            'status': status,
            'message': message})
    return HttpResponse(html)
    
def signup(request):
    if request.method == 'GET':
        kwargs = {'im_modules':settings.IM_MODULES,
                  'next':request.GET.get('next', ''),
                  'code':request.GET.get('code', '')}
        return render_response('signup.html', **kwargs)
    elif request.method == 'POST':
        provider = request.POST.get('choice')
        if not provider:
            return on_failure(_('No provider selected'), template='signup.html')
        
        kwargs = {'code':request.POST.get('code', ''),
                  'next':request.POST.get('next', '')}
        url = '%s%s?' %(reverse('astakos.im.views.register'), provider)
        for k,v in kwargs.items():
            if v:
                url = '%s%s=%s&' %(url, k, v)
        return redirect(url)

def render_registration(provider, code='', next=''):
    initial_data = {'provider':provider}
    if settings.INVITATIONS_ENABLED and code:
        try:
            print '#', type(code), code
            invitation = Invitation.objects.get(code=code)
            if invitation.is_consumed:
                return HttpResponseBadRequest('Invitation has beeen used')
            initial_data.update({'uniq':invitation.uniq,
                                 'email':invitation.uniq,
                                 'realname':invitation.realname})
            try:
                inviter = User.objects.get(uniq=invitation.inviter)
                initial_data['inviter'] = inviter.realname
            except User.DoesNotExist:
                pass
        except Invitation.DoesNotExist:
            return on_failure(_('Wrong invitation code'), template='register.html')
    
    prefix = 'Invited' if code else ''
    formclassname = '%s%sRegisterForm' %(prefix, provider.capitalize())
    formclass_ = getattr(sys.modules['astakos.im.forms'], formclassname)
    RegisterFormSet = formset_factory(formclass_, extra=0)
    formset = RegisterFormSet(initial=[initial_data])
    return render_response('register.html',
                           formset=formset,
                           next=next,
                           filter=filter,
                           code=code)

def is_preaccepted(user):
    if user.invitation and not user.invitation.is_consumed:
        return True
    
    return False

def should_send_verification():
    if not settings.INVITATIONS_ENABLED:
        return True    
    return False

def register(request, provider):
    print '---', request
    code = request.GET.get('code')
    next = request.GET.get('next')
    if request.method == 'GET':
        code = request.GET.get('code', '')
        next = request.GET.get('next', '')
        if provider not in settings.IM_MODULES:
            return on_failure(_('Invalid provider'))
        return render_registration(provider, code, next)
    elif request.method == 'POST':
        provider = request.POST.get('form-0-provider')
        inviter = request.POST.get('form-0-inviter')
        
        #instantiate the form
        prefix = 'Invited' if inviter else ''
        formclassname = '%sRegisterForm' %(provider.capitalize())
        formclass_ = getattr(sys.modules['astakos.im.forms'], formclassname)
        RegisterFormSet = formset_factory(formclass_, extra=0)
        formset = RegisterFormSet(request.POST)
        if not formset.is_valid():
            return render_to_response('register.html',
                                      {'formset':formset,
                                       'code':code,
                                       'next':next}) 
        
        user = User()
        for form in formset.forms:
            for field in form.fields:
                if hasattr(user, field):
                    setattr(user, field, form.cleaned_data[field])
            break
        
        if user.openidurl:
            redirect_url = reverse('astakos.im.views.create')
            return ask_openid(request, 
                        user.openidurl,
                        redirect_url,
                        'signup')
        
        #save hashed password
        if user.password:
            hasher = newhasher('sha256')
            hasher.update(user.password)
            user.password = hasher.hexdigest() 
            
        user.renew_token()
        
        if is_preaccepted(user):
            user.state = 'ACTIVE'
            user.save()
            url = reverse('astakos.im.views.index')
            return redirect(url)
        
        status = 'success'
        if should_send_verification():
            try:
                send_verification(request.build_absolute_uri('/').rstrip('/'), user)
                message = _('Verification sent to %s' % user.email)
                user.save()
            except (SMTPException, socket.error) as e:
                status = 'error'
                name = 'strerror'
                message = getattr(e, name) if hasattr(e, name) else e
        else:
            user.save()
            message = _('Registration completed. You will receive an email upon your account\'s activation')
        
        return info(status, message)

#def discover_extensions(openid_url):
#    service = discover(openid_url)
#    use_ax = False
#    use_sreg = False
#    for endpoint in service[1]:
#        if not use_sreg:
#            use_sreg = sreg.supportsSReg(endpoint)
#        if not use_ax:
#            use_ax = endpoint.usesExtension("http://openid.net/srv/ax/1.0")
#        if use_ax and use_sreg: break
#    return use_ax, use_sreg
#
#def ask_openid(request, openid_url, redirect_to, on_failure=None):
#    """ basic function to ask openid and return response """
#    on_failure = on_failure or signin_failure
#    sreg_req = None
#    ax_req = None
#    
#    trust_root = getattr(
#        settings, 'OPENID_TRUST_ROOT', request.build_absolute_uri() + '/'
#    )
#    request.session = {}
#    consumer = Consumer(request.session, PithosOpenIDStore())
#    try:
#        auth_request = consumer.begin(openid_url)
#    except DiscoveryFailure:
#        msg = _("The OpenID %s was invalid") % openid_url
#        return on_failure(request, msg)
#    
#     get capabilities
#    use_ax, use_sreg = discover_extensions(openid_url)
#    if use_sreg:
#         set sreg extension
#         we always ask for nickname and email
#        sreg_attrs = getattr(settings, 'OPENID_SREG', {})
#        sreg_attrs.update({ "optional": ['nickname', 'email'] })
#        sreg_req = sreg.SRegRequest(**sreg_attrs)
#    if use_ax:
#         set ax extension
#         we always ask for nickname and email
#        ax_req = ax.FetchRequest()
#        ax_req.add(ax.AttrInfo('http://schema.openid.net/contact/email', 
#                                alias='email', required=True))
#        ax_req.add(ax.AttrInfo('http://schema.openid.net/namePerson/friendly', 
#                                alias='nickname', required=True))
#                      
#         add custom ax attrs          
#        ax_attrs = getattr(settings, 'OPENID_AX', [])
#        for attr in ax_attrs:
#            if len(attr) == 2:
#                ax_req.add(ax.AttrInfo(attr[0], required=alias[1]))
#            else:
#                ax_req.add(ax.AttrInfo(attr[0]))
#       
#    if sreg_req is not None:
#        auth_request.addExtension(sreg_req)
#    if ax_req is not None:
#        auth_request.addExtension(ax_req)
#    
#    redirect_url = auth_request.redirectURL(trust_root, redirect_to)
#    return HttpResponseRedirect(redirect_url)

def info(status, message, template='base.html'):
    html = render_to_string(template, {
            'status': status,
            'message': message})
    response = HttpResponse(html)
    return response

def on_success(message, template='base.html'):
    return info('success', message)
    
def on_failure(message, template='base.html'):
    return info('error', message)
