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
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.forms import UserCreationForm

#from astakos.im.openid_store import PithosOpenIDStore
from astakos.im.models import AstakosUser, Invitation
from astakos.im.util import isoformat, get_context
from astakos.im.backends import get_backend
from astakos.im.forms import ProfileForm, FeedbackForm, LoginForm

def render_response(template, tab=None, status=200, context_instance=None, **kwargs):
    """
    Calls ``django.template.loader.render_to_string`` with an additional ``tab``
    keyword argument and returns an ``django.http.HttpResponse`` with the
    specified ``status``.
    """
    if tab is None:
        tab = template.partition('_')[0]
    kwargs.setdefault('tab', tab)
    html = render_to_string(template, kwargs, context_instance=context_instance)
    return HttpResponse(html, status=status)

def index(request, login_template_name='login.html', profile_template_name='profile.html', extra_context={}):
    """
    If there is logged on user renders the profile page otherwise renders login page.
    
    **Arguments**
    
    ``login_template_name``
        A custom login template to use. This is optional; if not specified,
        this will default to ``login.html``.
    
    ``profile_template_name``
        A custom profile template to use. This is optional; if not specified,
        this will default to ``login.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
    **Template:**
    
    index.html or ``template_name`` keyword argument.
    
    """
    template_name = login_template_name
    formclass = 'LoginForm'
    kwargs = {}
    if request.user.is_authenticated():
        template_name = profile_template_name
        formclass = 'ProfileForm'
        kwargs.update({'instance':request.user})
    return render_response(template_name,
                           form = globals()[formclass](**kwargs),
                           context_instance = get_context(request, extra_context))

def _generate_invitation_code():
    while True:
        code = randint(1, 2L**63 - 1)
        try:
            Invitation.objects.get(code=code)
            # An invitation with this code already exists, try again
        except Invitation.DoesNotExist:
            return code

def _send_invitation(request, baseurl, inv):
    site = Site.objects.get_current()
    subject = _('Invitation to %s' % site.name)
    url = settings.SIGNUP_TARGET % (baseurl, inv.code, quote(site.domain))
    message = render_to_string('invitation.txt', {
                'invitation': inv,
                'url': url,
                'baseurl': baseurl,
                'service': site.name,
                'support': settings.DEFAULT_CONTACT_EMAIL % site.name.lower()})
    sender = settings.DEFAULT_FROM_EMAIL % site.name
    send_mail(subject, message, sender, [inv.username])
    logging.info('Sent invitation %s', inv)

@login_required
@transaction.commit_manually
def invite(request, template_name='invitations.html', extra_context={}):
    """
    Allows a user to invite somebody else.
    
    In case of GET request renders a form for providing the invitee information.
    In case of POST checks whether the user has not run out of invitations and then
    sends an invitation email to singup to the service.
    
    The view uses commit_manually decorator in order to ensure the number of the
    user invitations is going to be updated only if the email has been successfully sent.
    
    If the user isn't logged in, redirects to settings.LOGIN_URL.
    
    **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``invitations.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
    **Template:**
    
    invitations.html or ``template_name`` keyword argument.
    
    **Settings:**
    
    The view expectes the following settings are defined:
    
    * LOGIN_URL: login uri
    * SIGNUP_TARGET: Where users should signup with their invitation code
    * DEFAULT_CONTACT_EMAIL: service support email
    * DEFAULT_FROM_EMAIL: from email
    """
    status = None
    message = None
    inviter = AstakosUser.objects.get(username = request.user.username)
    
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
                baseurl = request.build_absolute_uri('/').rstrip('/')
                _send_invitation(request, baseurl, invitation)
                if created:
                    inviter.invitations = max(0, inviter.invitations - 1)
                    inviter.save()
                status = messages.SUCCESS
                message = _('Invitation sent to %s' % username)
                transaction.commit()
            except (SMTPException, socket.error) as e:
                status = messages.ERROR
                message = getattr(e, 'strerror', '')
                transaction.rollback()
        else:
            status = messages.ERROR
            message = _('No invitations left')
    messages.add_message(request, status, message)
    
    if request.GET.get('format') == 'json':
        sent = [{'email': inv.username,
                 'realname': inv.realname,
                 'is_accepted': inv.is_accepted}
                    for inv in inviter.invitations_sent.all()]
        rep = {'invitations': inviter.invitations, 'sent': sent}
        return HttpResponse(json.dumps(rep))
    
    kwargs = {'user': inviter}
    context = get_context(request, extra_context, **kwargs)
    return render_response(template_name,
                           context_instance = context)

@login_required
def edit_profile(request, template_name='profile.html', extra_context={}):
    """
    Allows a user to edit his/her profile.
    
    In case of GET request renders a form for displaying the user information.
    In case of POST updates the user informantion.
    
    If the user isn't logged in, redirects to settings.LOGIN_URL.  
    
    **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``profile.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
    **Template:**
    
    profile.html or ``template_name`` keyword argument.
    """
    try:
        user = AstakosUser.objects.get(username=request.user)
        form = ProfileForm(instance=user)
    except AstakosUser.DoesNotExist:
        token = request.GET.get('auth', None)
        user = AstakosUser.objects.get(auth_token=token)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            try:
                form.save()
                msg = _('Profile has been updated successfully')
                messages.add_message(request, messages.SUCCESS, msg)
            except ValueError, ve:
                messages.add_message(request, messages.ERROR, ve)
    return render_response(template_name,
                           form = form,
                           context_instance = get_context(request,
                                                          extra_context,
                                                          user=user))

@transaction.commit_manually
def signup(request, template_name='signup.html', extra_context={}, backend=None):
    """
    Allows a user to create a local account.
    
    In case of GET request renders a form for providing the user information.
    In case of POST handles the signup.
    
    The user activation will be delegated to the backend specified by the ``backend`` keyword argument
    if present, otherwise to the ``astakos.im.backends.InvitationBackend``
    if settings.INVITATIONS_ENABLED is True or ``astakos.im.backends.SimpleBackend`` if not
    (see backends);
    
    Upon successful user creation if ``next`` url parameter is present the user is redirected there
    otherwise renders the same page with a success message.
    
    On unsuccessful creation, renders the same page with an error message.
    
    The view uses commit_manually decorator in order to ensure the user will be created
    only if the procedure has been completed successfully.
    
    **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``signup.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
    **Template:**
    
    signup.html or ``template_name`` keyword argument.
    """
    try:
        if not backend:
            backend = get_backend(request)
        form = backend.get_signup_form()
        if request.method == 'POST':
            if form.is_valid():
                status, message = backend.signup(form)
                # rollback in case of error
                if status == messages.ERROR:
                    transaction.rollback()
                else:
                    transaction.commit()
                    next = request.POST.get('next')
                    if next:
                        return redirect(next)
                messages.add_message(request, status, message)
    except Invitation.DoesNotExist, e:
        messages.add_message(request, messages.ERROR, e)
    return render_response(template_name,
                           form = form if 'form' in locals() else UserCreationForm(),
                           context_instance=get_context(request, extra_context))

@login_required
def send_feedback(request, template_name='feedback.html', email_template_name='feedback_mail.txt', extra_context={}):
    """
    Allows a user to send feedback.
    
    In case of GET request renders a form for providing the feedback information.
    In case of POST sends an email to support team.
    
    If the user isn't logged in, redirects to settings.LOGIN_URL.  
    
    **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``feedback.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
    **Template:**
    
    signup.html or ``template_name`` keyword argument.
    
    **Settings:**
    
    * DEFAULT_CONTACT_EMAIL: List of feedback recipients
    """
    if request.method == 'GET':
        form = FeedbackForm()
    if request.method == 'POST':
        if not request.user:
            return HttpResponse('Unauthorized', status=401)
        
        form = FeedbackForm(request.POST)
        if form.is_valid():
            site = Site.objects.get_current()
            subject = _("Feedback from %s" % site.name)
            from_email = request.user.email
            recipient_list = [settings.DEFAULT_CONTACT_EMAIL]
            content = render_to_string(email_template_name, {
                        'message': form.cleaned_data('feedback_msg'),
                        'data': form.cleaned_data('feedback_data'),
                        'request': request})
            
            send_mail(subject, content, from_email, recipient_list)
            
            resp = json.dumps({'status': 'send'})
            return HttpResponse(resp)
    return render_response(template_name,
                           form = form,
                           context_instance = get_context(request, extra_context))
