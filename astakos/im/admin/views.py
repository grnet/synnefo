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
from django.utils.http import urlencode
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.models import AnonymousUser
from django.contrib.sites.models import Site

from astakos.im.models import AstakosUser, Invitation
from astakos.im.util import isoformat, get_or_create_user, get_context
from astakos.im.forms import *
from astakos.im.backends import get_backend
from astakos.im.views import render_response, index
from astakos.im.admin.forms import AdminProfileForm

def requires_admin(func):
    """
    Decorator checkes whether the request.user is a superuser and if not
    redirects to login page.
    """
    @wraps(func)
    def wrapper(request, *args):
        if not settings.BYPASS_ADMIN_AUTH:
            if isinstance(request.user, AnonymousUser):
                next = urlencode({'next': request.build_absolute_uri()})
                login_uri = reverse(index) + '?' + next
                return HttpResponseRedirect(login_uri)
            if not request.user.is_superuser:
                return HttpResponse('Forbidden', status=403)
        return func(request, *args)
    return wrapper

@requires_admin
def admin(request, template_name='admin.html', extra_context={}):
    """
    Renders the admin page
    
    If the ``request.user`` is not a superuser redirects to login page.
    
   **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``admin.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
   **Template:**
    
    admin.html or ``template_name`` keyword argument.
    
   **Template Context:**
    
    The template context is extended by:
    
    * tab: the name of the active tab
    * stats: dictionary containing the number of all and prending users
    """
    stats = {}
    stats['users'] = AstakosUser.objects.count()
    stats['pending'] = AstakosUser.objects.filter(is_active = False).count()
    
    invitations = Invitation.objects.all()
    stats['invitations'] = invitations.count()
    stats['invitations_consumed'] = invitations.filter(is_consumed=True).count()
    
    kwargs = {'tab': 'home', 'stats': stats}
    context = get_context(request, extra_context,**kwargs)
    return render_response(template_name, context_instance = context)

@requires_admin
def users_list(request, template_name='users_list.html', extra_context={}):
    """
    Displays the list of all users.
    
    If the ``request.user`` is not a superuser redirects to login page.
    
   **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``users_list.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
   **Template:**
    
    users_list.html or ``template_name`` keyword argument.
    
   **Template Context:**
    
    The template context is extended by:
    
    * users: list of users fitting in current page
    * filter: search key
    * pages: the number of pages
    * prev: the previous page
    * next: the current page
    
   **Settings:**
    
    * ADMIN_PAGE_LIMIT: Show these many users per page in admin interface
    """
    users = AstakosUser.objects.order_by('id')
    
    filter = request.GET.get('filter', '')
    if filter:
        if filter.startswith('-'):
            users = users.exclude(username__icontains=filter[1:])
        else:
            users = users.filter(username__icontains=filter)
    
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
    offset = max(0, page - 1) * settings.ADMIN_PAGE_LIMIT
    limit = offset + settings.ADMIN_PAGE_LIMIT
    
    npages = int(ceil(1.0 * users.count() / settings.ADMIN_PAGE_LIMIT))
    prev = page - 1 if page > 1 else None
    next = page + 1 if page < npages else None
    
    kwargs = {'users':users[offset:limit],
              'filter':filter,
              'pages':range(1, npages + 1),
              'prev':prev,
              'next':next}
    context = get_context(request, extra_context,**kwargs)
    return render_response(template_name, context_instance = context)

@requires_admin
def users_info(request, user_id, template_name='users_info.html', extra_context={}):
    """
    Displays the specific user profile.
    
    If the ``request.user`` is not a superuser redirects to login page.
    
   **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``users_info.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
   **Template:**
    
    users_info.html or ``template_name`` keyword argument.
    
   **Template Context:**
    
    The template context is extended by:
    
    * user: the user instance identified by ``user_id`` keyword argument
    """
    if not extra_context:
        extra_context = {}
    user = AstakosUser.objects.get(id=user_id)
    return render_response(template_name,
                           form = AdminProfileForm(instance=user),
                           context_instance = get_context(request, extra_context))

@requires_admin
def users_modify(request, user_id, template_name='users_info.html', extra_context={}):
    """
    Update the specific user information. Upon success redirects to ``user_info`` view.
    
    If the ``request.user`` is not a superuser redirects to login page.
    """
    form = AdminProfileForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect(users_info, user.id, template_name, extra_context)
    return render_response(template_name,
                           form = form,
                           context_instance = get_context(request, extra_context))

@requires_admin
def users_delete(request, user_id):
    """
    Deletes the specified user
    
    If the ``request.user`` is not a superuser redirects to login page.
    """
    user = AstakosUser.objects.get(id=user_id)
    user.delete()
    return redirect(users_list)

@requires_admin
def pending_users(request, template_name='pending_users.html', extra_context={}):
    """
    Displays the list of the pending users.
    
    If the ``request.user`` is not a superuser redirects to login page.
    
   **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``users_list.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
   **Template:**
    
    pending_users.html or ``template_name`` keyword argument.
    
   **Template Context:**
    
    The template context is extended by:
    
    * users: list of pending users fitting in current page
    * filter: search key
    * pages: the number of pages
    * prev: the previous page
    * next: the current page
    
   **Settings:**
    
    * ADMIN_PAGE_LIMIT: Show these many users per page in admin interface
    """
    users = AstakosUser.objects.order_by('id')
    
    users = users.filter(is_active = False)
    
    filter = request.GET.get('filter', '')
    if filter:
        if filter.startswith('-'):
            users = users.exclude(username__icontains=filter[1:])
        else:
            users = users.filter(username__icontains=filter)
    
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
    offset = max(0, page - 1) * settings.ADMIN_PAGE_LIMIT
    limit = offset + settings.ADMIN_PAGE_LIMIT
    
    npages = int(ceil(1.0 * users.count() / settings.ADMIN_PAGE_LIMIT))
    prev = page - 1 if page > 1 else None
    next = page + 1 if page < npages else None
    kwargs = {'users':users[offset:limit],
              'filter':filter,
              'pages':range(1, npages + 1),
              'page':page,
              'prev':prev,
              'next':next}
    return render_response(template_name,
                            context_instance = get_context(request, extra_context,**kwargs))

def _send_greeting(request, user, template_name):
    url = reverse('astakos.im.views.index')
    subject = _('Welcome to %s' %settings.SERVICE_NAME)
    site = Site.objects.get_current()
    baseurl = request.build_absolute_uri('/').rstrip('/')
    message = render_to_string(template_name, {
                'user': user,
                'url': url,
                'baseurl': baseurl,
                'site_name': site.name,
                'support': settings.DEFAULT_CONTACT_EMAIL})
    sender = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, sender, [user.email])
    logging.info('Sent greeting %s', user)

@requires_admin
@transaction.commit_manually
def users_activate(request, user_id, template_name='pending_users.html', extra_context={}, email_template_name='welcome_email.txt'):
    """
    Activates the specific user and sends an email. Upon success renders the
    ``template_name`` keyword argument if exists else renders ``pending_users.html``.
    
    If the ``request.user`` is not a superuser redirects to login page.
    
   **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``users_list.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
   **Templates:**
    
    pending_users.html or ``template_name`` keyword argument.
    welcome_email.txt or ``email_template_name`` keyword argument.
    
   **Template Context:**
    
    The template context is extended by:
    
    * users: list of pending users fitting in current page
    * filter: search key
    * pages: the number of pages
    * prev: the previous page
    * next: the current page
    """
    user = AstakosUser.objects.get(id=user_id)
    user.is_active = True
    user.save()
    status = messages.SUCCESS
    try:
        _send_greeting(request, user, email_template_name)
        message = _('Greeting sent to %s' % user.email)
        transaction.commit()
    except (SMTPException, socket.error) as e:
        status = messages.ERROR
        name = 'strerror'
        message = getattr(e, name) if hasattr(e, name) else e
        transaction.rollback()
    messages.add_message(request, status, message)
    
    users = AstakosUser.objects.order_by('id')
    users = users.filter(is_active = False)
    
    try:
        page = int(request.POST.get('page', 1))
    except ValueError:
        page = 1
    offset = max(0, page - 1) * settings.ADMIN_PAGE_LIMIT
    limit = offset + settings.ADMIN_PAGE_LIMIT
    
    npages = int(ceil(1.0 * users.count() / settings.ADMIN_PAGE_LIMIT))
    prev = page - 1 if page > 1 else None
    next = page + 1 if page < npages else None
    kwargs = {'users':users[offset:limit],
              'filter':'',
              'pages':range(1, npages + 1),
              'page':page,
              'prev':prev,
              'next':next}
    return render_response(template_name,
                           context_instance = get_context(request, extra_context,**kwargs))

@requires_admin
def invitations_list(request, template_name='invitations_list.html', extra_context={}):
    """
    Displays a list with the Invitations.
    
    If the ``request.user`` is not a superuser redirects to login page.
    
   **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``invitations_list.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
   **Templates:**
    
    invitations_list.html or ``template_name`` keyword argument.
    
   **Template Context:**
    
    The template context is extended by:
    
    * invitations: list of invitations fitting in current page
    * filter: search key
    * pages: the number of pages
    * prev: the previous page
    * next: the current page
    """
    invitations = Invitation.objects.order_by('id')
    
    filter = request.GET.get('filter', '')
    if filter:
        if filter.startswith('-'):
            invitations = invitations.exclude(username__icontains=filter[1:])
        else:
            invitations = invitations.filter(username__icontains=filter)
    
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1
    offset = max(0, page - 1) * settings.ADMIN_PAGE_LIMIT
    limit = offset + settings.ADMIN_PAGE_LIMIT
    
    npages = int(ceil(1.0 * invitations.count() / settings.ADMIN_PAGE_LIMIT))
    prev = page - 1 if page > 1 else None
    next = page + 1 if page < npages else None
    kwargs = {'invitations':invitations[offset:limit],
              'filter':filter,
              'pages':range(1, npages + 1),
              'page':page,
              'prev':prev,
              'next':next}
    return render_response(template_name,
                           context_instance = get_context(request, extra_context,**kwargs))

@requires_admin
def invitations_export(request):
    """
    Exports the invitation list in csv file.
    """
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=invitations.csv'

    writer = csv.writer(response)
    writer.writerow(['ID',
                     'Username',
                     'Real Name',
                     'Code',
                     'Inviter username',
                     'Inviter Real Name',
                     'Is_accepted',
                     'Created',
                     'Accepted',])
    invitations = Invitation.objects.order_by('id')
    for inv in invitations:
        
        writer.writerow([inv.id,
                         inv.username.encode("utf-8"),
                         inv.realname.encode("utf-8"),
                         inv.code,
                         inv.inviter.username.encode("utf-8"),
                         inv.inviter.realname.encode("utf-8"),
                         inv.is_accepted,
                         inv.created,
                         inv.accepted])

    return response


@requires_admin
def users_export(request):
    """
    Exports the user list in csv file.
    """
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=users.csv'

    writer = csv.writer(response)
    writer.writerow(['ID',
                     'Username',
                     'Real Name',
                     'Admin',
                     'Affiliation',
                     'Is active?',
                     'Quota (GiB)',
                     'Updated',])
    users = AstakosUser.objects.order_by('id')
    for u in users:
        writer.writerow([u.id,
                         u.username.encode("utf-8"),
                         u.realname.encode("utf-8"),
                         u.is_superuser,
                         u.affiliation.encode("utf-8"),
                         u.is_active,
                         u.quota,
                         u.updated])

    return response

@requires_admin
def users_create(request, template_name='users_create.html', extra_context={}):
    """
    Creates a user. Upon success redirect to ``users_info`` view.
    
   **Arguments**
    
    ``template_name``
        A custom template to use. This is optional; if not specified,
        this will default to ``users_create.html``.
    
    ``extra_context``
        An dictionary of variables to add to the template context.
    
   **Templates:**
    
    users_create.html or ``template_name`` keyword argument.
    """
    if request.method == 'GET':
        return render_response(template_name,
                               context_instance=get_context(request, extra_context))
    if request.method == 'POST':
        user = AstakosUser()
        user.username = request.POST.get('username')
        user.email = request.POST.get('email')
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.is_superuser = True if request.POST.get('admin') else False
        user.affiliation = request.POST.get('affiliation')
        user.quota = int(request.POST.get('quota') or 0) * (1024**3)  # In GiB
        user.renew_token()
        user.provider = 'local'
        user.save()
        return redirect(users_info, user.id)
