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

import logging
import socket

from random import randint
from smtplib import SMTPException
from urllib import quote
from functools import wraps

from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import logout as auth_logout
from django.utils.http import urlencode
from django.http import HttpResponseRedirect

from astakos.im.models import AstakosUser, Invitation
from astakos.im.backends import get_backend
from astakos.im.util import get_context, get_current_site, prepare_response
from astakos.im.forms import *
from astakos.im.settings import DEFAULT_CONTACT_EMAIL, DEFAULT_FROM_EMAIL, COOKIE_NAME, IM_MODULES

def render_response(template, tab=None, status=200, context_instance=None, **kwargs):
    """
    Calls ``django.template.loader.render_to_string`` with an additional ``tab``
    keyword argument and returns an ``django.http.HttpResponse`` with the
    specified ``status``.
    """
    if tab is None:
        tab = template.partition('_')[0].partition('.html')[0]
    kwargs.setdefault('tab', tab)
    html = render_to_string(template, kwargs, context_instance=context_instance)
    return HttpResponse(html, status=status)


def requires_anonymous(func):
    """
    Decorator checkes whether the request.user is Anonymous and in that case
    redirects to `logout`.
    """
    @wraps(func)
    def wrapper(request, *args):
        if not request.user.is_anonymous():
            next = urlencode({'next': request.build_absolute_uri()})
            login_uri = reverse(logout) + '?' + next
            return HttpResponseRedirect(login_uri)
        return func(request, *args)
    return wrapper

def index(request, login_template_name='im/login.html', profile_template_name='im/profile.html', extra_context={}):
    """
    If there is logged on user renders the profile page otherwise renders login page.
    
    **Arguments**
    
    ``login_template_name``
        A custom login template to use. This is optional; if not specified,
        this will default to ``im/login.html``.
    
    ``profile_template_name``
        A custom profile template to use. This is optional; if not specified,
        this will default to ``im/profile.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
    **Template:**
    
    im/profile.html or im/login.html or ``template_name`` keyword argument.
    
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
    sitename, sitedomain = get_current_site(request, use_https=request.is_secure())
    subject = _('Invitation to %s' % sitename)
    baseurl = request.build_absolute_uri('/').rstrip('/')
    url = '%s%s?code=%d' % (baseurl, reverse('astakos.im.views.signup'), inv.code)
    message = render_to_string('im/invitation.txt', {
                'invitation': inv,
                'url': url,
                'baseurl': baseurl,
                'service': sitename,
                'support': DEFAULT_CONTACT_EMAIL % sitename.lower()})
    sender = DEFAULT_FROM_EMAIL % sitename
    send_mail(subject, message, sender, [inv.username])
    logging.info('Sent invitation %s', inv)

@login_required
@transaction.commit_manually
def invite(request, template_name='im/invitations.html', extra_context={}):
    """
    Allows a user to invite somebody else.
    
    In case of GET request renders a form for providing the invitee information.
    In case of POST checks whether the user has not run out of invitations and then
    sends an invitation email to singup to the service.
    
    The view uses commit_manually decorator in order to ensure the number of the
    user invitations is going to be updated only if the email has been successfully sent.
    
    If the user isn't logged in, redirects to settings.ASTAKOS_LOGIN_URL.
    
    **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``im/invitations.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
    **Template:**
    
    im/invitations.html or ``template_name`` keyword argument.
    
    **Settings:**
    
    The view expectes the following settings are defined:
    
    * LOGIN_URL: login uri
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
            invitation = Invitation(inviter=inviter,
                                    username=username,
                                    code=code,
                                    realname=realname)
            invitation.save()
            
            try:
                baseurl = request.build_absolute_uri('/').rstrip('/')
                _send_invitation(request, baseurl, invitation)
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
    
    sent = [{'email': inv.username,
             'realname': inv.realname,
             'is_consumed': inv.is_consumed}
             for inv in inviter.invitations_sent.all()]
    kwargs = {'inviter': inviter,
              'sent':sent}
    context = get_context(request, extra_context, **kwargs)
    return render_response(template_name,
                           context_instance = context)

@login_required
def edit_profile(request, template_name='im/profile.html', extra_context={}):
    """
    Allows a user to edit his/her profile.
    
    In case of GET request renders a form for displaying the user information.
    In case of POST updates the user informantion and redirects to ``next``
    url parameter if exists.
    
    If the user isn't logged in, redirects to settings.ASTAKOS_LOGIN_URL.  
    
    **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``im/profile.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
    **Template:**
    
    im/profile.html or ``template_name`` keyword argument.
    
    **Settings:**
    
    The view expectes the following settings are defined:
    
    * LOGIN_URL: login uri
    """
    form = ProfileForm(instance=request.user)
    extra_context['next'] = request.GET.get('next')
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            try:
                form.save()
                next = request.POST.get('next')
                if next:
                    return redirect(next)
                msg = _('Profile has been updated successfully')
                messages.add_message(request, messages.SUCCESS, msg)
            except ValueError, ve:
                messages.add_message(request, messages.ERROR, ve)
    return render_response(template_name,
                           form = form,
                           context_instance = get_context(request,
                                                          extra_context,
                                                          user=request.user))

def signup(request, on_failure='im/signup.html', on_success='im/signup_complete.html', extra_context={}, backend=None):
    """
    Allows a user to create a local account.
    
    In case of GET request renders a form for providing the user information.
    In case of POST handles the signup.
    
    The user activation will be delegated to the backend specified by the ``backend`` keyword argument
    if present, otherwise to the ``astakos.im.backends.InvitationBackend``
    if settings.ASTAKOS_INVITATIONS_ENABLED is True or ``astakos.im.backends.SimpleBackend`` if not
    (see backends);
    
    Upon successful user creation if ``next`` url parameter is present the user is redirected there
    otherwise renders the same page with a success message.
    
    On unsuccessful creation, renders the same page with an error message.
    
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
        for provider in IM_MODULES:
            extra_context['%s_form' % provider] = backend.get_signup_form(provider)
        if request.method == 'POST':
            provider = request.POST.get('provider')
            next = request.POST.get('next', '')
            form = extra_context['%s_form' % provider]
            if form.is_valid():
                if provider != 'local':
                    url = reverse('astakos.im.target.%s.login' % provider)
                    url = '%s?email=%s&next=%s' % (url, form.data['email'], next)
                    if backend.invitation:
                        url = '%s&code=%s' % (url, backend.invitation.code)
                    return redirect(url)
                else:
                    status, message, user = backend.signup(form)
                    if user and user.is_active:
                        return prepare_response(request, user, next=next)
                    messages.add_message(request, status, message)
                    return render_response(on_success,
                           context_instance=get_context(request, extra_context))
    except (Invitation.DoesNotExist, ValueError), e:
        messages.add_message(request, messages.ERROR, e)
        for provider in IM_MODULES:
            main = provider.capitalize() if provider == 'local' else 'ThirdParty'
            formclass = '%sUserCreationForm' % main
            extra_context['%s_form' % provider] = globals()[formclass]()
    return render_response(on_failure,
                           context_instance=get_context(request, extra_context))

@login_required
def send_feedback(request, template_name='im/feedback.html', email_template_name='im/feedback_mail.txt', extra_context={}):
    """
    Allows a user to send feedback.
    
    In case of GET request renders a form for providing the feedback information.
    In case of POST sends an email to support team.
    
    If the user isn't logged in, redirects to settings.ASTAKOS_LOGIN_URL.  
    
    **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``im/feedback.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
    **Template:**
    
    im/signup.html or ``template_name`` keyword argument.
    
    **Settings:**
    
    * LOGIN_URL: login uri
    * DEFAULT_CONTACT_EMAIL: List of feedback recipients
    """
    if request.method == 'GET':
        form = FeedbackForm()
    if request.method == 'POST':
        if not request.user:
            return HttpResponse('Unauthorized', status=401)
        
        form = FeedbackForm(request.POST)
        if form.is_valid():
            sitename, sitedomain = get_current_site(request, use_https=request.is_secure())
            subject = _("Feedback from %s" % sitename)
            from_email = request.user.email
            recipient_list = [DEFAULT_CONTACT_EMAIL % sitename.lower()]
            content = render_to_string(email_template_name, {
                        'message': form.cleaned_data['feedback_msg'],
                        'data': form.cleaned_data['feedback_data'],
                        'request': request})
            
            try:
                send_mail(subject, content, from_email, recipient_list)
                message = _('Feedback successfully sent')
                status = messages.SUCCESS
            except (SMTPException, socket.error) as e:
                status = messages.ERROR
                message = getattr(e, 'strerror', '')
            messages.add_message(request, status, message)
    return render_response(template_name,
                           form = form,
                           context_instance = get_context(request, extra_context))

def logout(request, template='registration/logged_out.html', extra_context={}):
    """
    Wraps `django.contrib.auth.logout` and delete the cookie.
    """
    auth_logout(request)
    response = HttpResponse()
    response.delete_cookie(COOKIE_NAME)
    next = request.GET.get('next')
    if next:
        response['Location'] = next
        response.status_code = 302
        return response
    context = get_context(request, extra_context)
    response.write(render_to_string(template, context_instance=context))
    return response

def activate(request):
    """
    Activates the user identified by the ``auth`` request parameter
    """
    token = request.GET.get('auth')
    next = request.GET.get('next')
    try:
        user = AstakosUser.objects.get(auth_token=token)
    except AstakosUser.DoesNotExist:
        return HttpResponseBadRequest('No such user')
    
    user.is_active = True
    user.save()
    return prepare_response(request, user, next, renew=True)