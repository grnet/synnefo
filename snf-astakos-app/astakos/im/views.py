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

from smtplib import SMTPException
from urllib import quote
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import password_change
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.db.utils import IntegrityError
from django.forms.fields import URLField
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, \
    HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.utils.http import urlencode
from django.utils.translation import ugettext as _
from django.views.generic.create_update import *
from django.views.generic.list_detail import *

from astakos.im.models import AstakosUser, Invitation, ApprovalTerms, AstakosGroup, Resource
from astakos.im.activation_backends import get_backend, SimpleBackend
from astakos.im.util import get_context, prepare_response, set_cookie, get_query
from astakos.im.forms import *
from astakos.im.functions import send_greeting, send_feedback, SendMailError, \
    invite as invite_func, logout as auth_logout, activate as activate_func, \
    switch_account_to_shibboleth, send_admin_notification, SendNotificationError
from astakos.im.settings import DEFAULT_CONTACT_EMAIL, DEFAULT_FROM_EMAIL, COOKIE_NAME, COOKIE_DOMAIN, IM_MODULES, SITENAME, LOGOUT_NEXT, LOGGING_LEVEL

logger = logging.getLogger(__name__)

def render_response(template, tab=None, status=200, reset_cookie=False, context_instance=None, **kwargs):
    """
    Calls ``django.template.loader.render_to_string`` with an additional ``tab``
    keyword argument and returns an ``django.http.HttpResponse`` with the
    specified ``status``.
    """
    if tab is None:
        tab = template.partition('_')[0].partition('.html')[0]
    kwargs.setdefault('tab', tab)
    html = render_to_string(template, kwargs, context_instance=context_instance)
    response = HttpResponse(html, status=status)
    if reset_cookie:
        set_cookie(response, context_instance['request'].user)
    return response


def requires_anonymous(func):
    """
    Decorator checkes whether the request.user is not Anonymous and in that case
    redirects to `logout`.
    """
    @wraps(func)
    def wrapper(request, *args):
        if not request.user.is_anonymous():
            next = urlencode({'next': request.build_absolute_uri()})
            logout_uri = reverse(logout) + '?' + next
            return HttpResponseRedirect(logout_uri)
        return func(request, *args)
    return wrapper

def signed_terms_required(func):
    """
    Decorator checkes whether the request.user is Anonymous and in that case
    redirects to `logout`.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated() and not request.user.signed_terms():
            params = urlencode({'next': request.build_absolute_uri(),
                              'show_form':''})
            terms_uri = reverse('latest_terms') + '?' + params
            return HttpResponseRedirect(terms_uri)
        return func(request, *args, **kwargs)
    return wrapper

@signed_terms_required
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
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('edit_profile'))
    return render_response(template_name,
                           login_form = LoginForm(request=request),
                           context_instance = get_context(request, extra_context))

@login_required
@signed_terms_required
@transaction.commit_manually
def invite(request, template_name='im/invitations.html', extra_context={}):
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
        this will default to ``im/invitations.html``.

    ``extra_context``
        An dictionary of variables to add to the template context.

    **Template:**

    im/invitations.html or ``template_name`` keyword argument.

    **Settings:**

    The view expectes the following settings are defined:

    * LOGIN_URL: login uri
    * ASTAKOS_DEFAULT_CONTACT_EMAIL: service support email
    * ASTAKOS_DEFAULT_FROM_EMAIL: from email
    """
    status = None
    message = None
    form = InvitationForm()
    
    inviter = request.user
    if request.method == 'POST':
        form = InvitationForm(request.POST)
        if inviter.invitations > 0:
            if form.is_valid():
                try:
                    invitation = form.save()
                    invite_func(invitation, inviter)
                    message = _('Invitation sent to %s' % invitation.username)
                    messages.success(request, message)
                except SendMailError, e:
                    message = e.message
                    messages.error(request, message)
                    transaction.rollback()
                except BaseException, e:
                    message = _('Something went wrong.')
                    messages.error(request, message)
                    logger.exception(e)
                    transaction.rollback()
                else:
                    transaction.commit()
        else:
            message = _('No invitations left')
            messages.error(request, message)

    sent = [{'email': inv.username,
             'realname': inv.realname,
             'is_consumed': inv.is_consumed}
             for inv in request.user.invitations_sent.all()]
    kwargs = {'inviter': inviter,
              'sent':sent}
    context = get_context(request, extra_context, **kwargs)
    return render_response(template_name,
                           invitation_form = form,
                           context_instance = context)

@login_required
@signed_terms_required
def edit_profile(request, template_name='im/profile.html', extra_context={}):
    """
    Allows a user to edit his/her profile.

    In case of GET request renders a form for displaying the user information.
    In case of POST updates the user informantion and redirects to ``next``
    url parameter if exists.

    If the user isn't logged in, redirects to settings.LOGIN_URL.

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
    reset_cookie = False
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            try:
                prev_token = request.user.auth_token
                user = form.save()
                reset_cookie = user.auth_token != prev_token
                form = ProfileForm(instance=user)
                next = request.POST.get('next')
                if next:
                    return redirect(next)
                msg = _('Profile has been updated successfully')
                messages.success(request, msg)
            except ValueError, ve:
                messages.success(request, ve)
    elif request.method == "GET":
        if not request.user.is_verified:
            request.user.is_verified = True
            request.user.save()
    return render_response(template_name,
                           reset_cookie = reset_cookie,
                           profile_form = form,
                           context_instance = get_context(request,
                                                          extra_context))

def signup(request, template_name='im/signup.html', on_success='im/signup_complete.html', extra_context={}, backend=None):
    """
    Allows a user to create a local account.

    In case of GET request renders a form for entering the user information.
    In case of POST handles the signup.

    The user activation will be delegated to the backend specified by the ``backend`` keyword argument
    if present, otherwise to the ``astakos.im.activation_backends.InvitationBackend``
    if settings.ASTAKOS_INVITATIONS_ENABLED is True or ``astakos.im.activation_backends.SimpleBackend`` if not
    (see activation_backends);
    
    Upon successful user creation, if ``next`` url parameter is present the user is redirected there
    otherwise renders the same page with a success message.
    
    On unsuccessful creation, renders ``template_name`` with an error message.
    
    **Arguments**
    
    ``template_name``
        A custom template to render. This is optional;
        if not specified, this will default to ``im/signup.html``.

    ``on_success``
        A custom template to render in case of success. This is optional;
        if not specified, this will default to ``im/signup_complete.html``.

    ``extra_context``
        An dictionary of variables to add to the template context.

    **Template:**
    
    im/signup.html or ``template_name`` keyword argument.
    im/signup_complete.html or ``on_success`` keyword argument. 
    """
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('edit_profile'))
    
    provider = get_query(request).get('provider', 'local')
    try:
        if not backend:
            backend = get_backend(request)
        form = backend.get_signup_form(provider)
    except Exception, e:
        form = SimpleBackend(request).get_signup_form(provider)
        messages.error(request, e)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save(commit=False)
            try:
                result = backend.handle_activation(user)
                status = messages.SUCCESS
                message = result.message
                user.save()
                if 'additional_email' in form.cleaned_data:
                    additional_email = form.cleaned_data['additional_email']
                    if additional_email != user.email:
                        user.additionalmail_set.create(email=additional_email)
                        msg = 'Additional email: %s saved for user %s.' % (additional_email, user.email)
                        logger._log(LOGGING_LEVEL, msg, [])
                if user and user.is_active:
                    next = request.POST.get('next', '')
                    return prepare_response(request, user, next=next)
                messages.add_message(request, status, message)
                return render_response(on_success,
                                       context_instance=get_context(request, extra_context))
            except SendMailError, e:
                message = e.message
                messages.error(request, message)
            except BaseException, e:
                message = _('Something went wrong.')
                messages.error(request, message)
                logger.exception(e)
    return render_response(template_name,
                           signup_form = form,
                           provider = provider,
                           context_instance=get_context(request, extra_context))

@login_required
@signed_terms_required
def feedback(request, template_name='im/feedback.html', email_template_name='im/feedback_mail.txt', extra_context={}):
    """
    Allows a user to send feedback.

    In case of GET request renders a form for providing the feedback information.
    In case of POST sends an email to support team.

    If the user isn't logged in, redirects to settings.LOGIN_URL.

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
    * ASTAKOS_DEFAULT_CONTACT_EMAIL: List of feedback recipients
    """
    if request.method == 'GET':
        form = FeedbackForm()
    if request.method == 'POST':
        if not request.user:
            return HttpResponse('Unauthorized', status=401)

        form = FeedbackForm(request.POST)
        if form.is_valid():
            msg = form.cleaned_data['feedback_msg']
            data = form.cleaned_data['feedback_data']
            try:
                send_feedback(msg, data, request.user, email_template_name)
            except SendMailError, e:
                status = messages.ERROR
                messages.error(request, message)
            else:
                message = _('Feedback successfully sent')
                messages.succeess(request, message)
    return render_response(template_name,
                           feedback_form = form,
                           context_instance = get_context(request, extra_context))

@signed_terms_required
def logout(request, template='registration/logged_out.html', extra_context={}):
    """
    Wraps `django.contrib.auth.logout` and delete the cookie.
    """
    response = HttpResponse()
    if request.user.is_authenticated():
        email = request.user.email
        auth_logout(request)
        response.delete_cookie(COOKIE_NAME, path='/', domain=COOKIE_DOMAIN)
        msg = 'Cookie deleted for %s' % email
        logger._log(LOGGING_LEVEL, msg, [])
    next = request.GET.get('next')
    if next:
        response['Location'] = next
        response.status_code = 302
        return response
    elif LOGOUT_NEXT:
        response['Location'] = LOGOUT_NEXT
        response.status_code = 301
        return response
    messages.success(request, _('You have successfully logged out.'))
    context = get_context(request, extra_context)
    response.write(render_to_string(template, context_instance=context))
    return response

@transaction.commit_manually
def activate(request, greeting_email_template_name='im/welcome_email.txt', helpdesk_email_template_name='im/helpdesk_notification.txt'):
    """
    Activates the user identified by the ``auth`` request parameter, sends a welcome email
    and renews the user token.

    The view uses commit_manually decorator in order to ensure the user state will be updated
    only if the email will be send successfully.
    """
    token = request.GET.get('auth')
    next = request.GET.get('next')
    try:
        user = AstakosUser.objects.get(auth_token=token)
    except AstakosUser.DoesNotExist:
        return HttpResponseBadRequest(_('No such user'))
    
    if user.is_active:
        message = _('Account already active.')
        messages.error(request, message)
        return index(request)
        
    try:
        local_user = AstakosUser.objects.get(
            ~Q(id = user.id),
            email=user.email,
            is_active=True
        )
    except AstakosUser.DoesNotExist:
        try:
            activate_func(
                user,
                greeting_email_template_name,
                helpdesk_email_template_name,
                verify_email=True
            )
            response = prepare_response(request, user, next, renew=True)
            transaction.commit()
            return response
        except SendMailError, e:
            message = e.message
            messages.error(request, message)
            transaction.rollback()
            return index(request)
        except BaseException, e:
            message = _('Something went wrong.')
            messages.error(request, message)
            logger.exception(e)
            transaction.rollback()
            return index(request)
    else:
        try:
            user = switch_account_to_shibboleth(
                user,
                local_user,
                greeting_email_template_name
            )
            response = prepare_response(request, user, next, renew=True)
            transaction.commit()
            return response
        except SendMailError, e:
            message = e.message
            messages.error(request, message)
            transaction.rollback()
            return index(request)
        except BaseException, e:
            message = _('Something went wrong.')
            messages.error(request, message)
            logger.exception(e)
            transaction.rollback()
            return index(request)

def approval_terms(request, term_id=None, template_name='im/approval_terms.html', extra_context={}):
    term = None
    terms = None
    if not term_id:
        try:
            term = ApprovalTerms.objects.order_by('-id')[0]
        except IndexError:
            pass
    else:
        try:
             term = ApprovalTerms.objects.get(id=term_id)
        except ApprovalTermDoesNotExist, e:
            pass

    if not term:
        return HttpResponseRedirect(reverse('index'))
    f = open(term.location, 'r')
    terms = f.read()

    if request.method == 'POST':
        next = request.POST.get('next')
        if not next:
            next = reverse('index')
        form = SignApprovalTermsForm(request.POST, instance=request.user)
        if not form.is_valid():
            return render_response(template_name,
                           terms = terms,
                           approval_terms_form = form,
                           context_instance = get_context(request, extra_context))
        user = form.save()
        return HttpResponseRedirect(next)
    else:
        form = None
        if request.user.is_authenticated() and not request.user.signed_terms():
            form = SignApprovalTermsForm(instance=request.user)
        return render_response(template_name,
                               terms = terms,
                               approval_terms_form = form,
                               context_instance = get_context(request, extra_context))

@signed_terms_required
def change_password(request):
    return password_change(request,
                            post_change_redirect=reverse('edit_profile'),
                            password_change_form=ExtendedPasswordChangeForm)

@signed_terms_required
@login_required
@transaction.commit_manually
def change_email(request, activation_key=None,
                 email_template_name='registration/email_change_email.txt',
                 form_template_name='registration/email_change_form.html',
                 confirm_template_name='registration/email_change_done.html',
                 extra_context={}):
    if activation_key:
        try:
            user = EmailChange.objects.change_email(activation_key)
            if request.user.is_authenticated() and request.user == user:
                msg = _('Email changed successfully.')
                messages.success(request, msg)
                auth_logout(request)
                response = prepare_response(request, user)
                transaction.commit()
                return response
        except ValueError, e:
            messages.error(request, e)
        return render_response(confirm_template_name,
                               modified_user = user if 'user' in locals() else None,
                               context_instance = get_context(request,
                                                              extra_context))
    
    if not request.user.is_authenticated():
        path = quote(request.get_full_path())
        url = request.build_absolute_uri(reverse('index'))
        return HttpResponseRedirect(url + '?next=' + path)
    form = EmailChangeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            ec = form.save(email_template_name, request)
        except SendMailError, e:
            msg = e
            messages.error(request, msg)
            transaction.rollback()
        except IntegrityError, e:
            msg = _('There is already a pending change email request.')
            messages.error(request, msg)
        else:
            msg = _('Change email request has been registered succefully.\
                    You are going to receive a verification email in the new address.')
            messages.success(request, msg)
            transaction.commit()
    return render_response(form_template_name,
                           form = form,
                           context_instance = get_context(request,
                                                          extra_context))

@signed_terms_required
@login_required
def group_add(request, kind_name='default'):
    try:
        kind = GroupKind.objects.get(name = kind_name)
    except:
        return HttpResponseBadRequest(_('No such group kind'))
    
    template_loader=loader
    post_save_redirect='/im/group/%(id)s/'
    context_processors=None
    model, form_class = get_model_and_form_class(
        model=None,
        form_class=AstakosGroupCreationForm
    )
    resources = dict( (str(r.id), r) for r in Resource.objects.select_related().all() )
    policies = []
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, resources=resources)
        if form.is_valid():
            new_object = form.save()
            
            # save owner
            new_object.owners = [request.user]
            
            # save quota policies
            for (rid, limit) in form.resources():
                try:
                    r = resources[rid]
                except KeyError, e:
                    logger.exception(e)
                    # TODO Should I stay or should I go???
                    continue
                else:
                    new_object.astakosgroupquota_set.create(
                        resource = r,
                        limit = limit
                    )
                policies.append('%s %d' % (r, limit))
            msg = _("The %(verbose_name)s was created successfully.") %\
                                    {"verbose_name": model._meta.verbose_name}
            messages.success(request, msg, fail_silently=True)
            
            # send notification
            try:
                send_admin_notification(
                    template_name='im/group_creation_notification.txt',
                    dictionary={
                        'group':new_object,
                        'owner':request.user,
                        'policies':policies,
                    },
                    subject='%s alpha2 testing group creation notification' % SITENAME
                )
            except SendNotificationError, e:
                messages.error(request, e, fail_silently=True)
            return redirect(post_save_redirect, new_object)
    else:
        now = datetime.now()
        data = {
            'kind':kind,
            'issue_date':now,
            'expiration_date':now + timedelta(days=30)
        }
        form = form_class(data, resources=resources)

    # Create the template, context, response
    template_name = "%s/%s_form.html" % (
        model._meta.app_label,
        model._meta.object_name.lower()
    )
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        'form': form
    }, context_processors)
    return HttpResponse(t.render(c))

@signed_terms_required
@login_required
def group_list(request):
    list = request.user.astakos_groups.select_related().all()
    return object_list(request, queryset=list)

@signed_terms_required
@login_required
def group_detail(request, group_id):
    try:
        group = AstakosGroup.objects.select_related().get(id=group_id)
    except AstakosGroup.DoesNotExist:
        return HttpResponseBadRequest(_('Invalid group.'))
    return object_detail(request,
         AstakosGroup.objects.all(),
         object_id=group_id,
         extra_context = {'quota':group.quota}
    )

@signed_terms_required
@login_required
def group_approval_request(request, group_id):
    return HttpResponse()

@signed_terms_required
@login_required
def group_search(request, extra_context={}, **kwargs):
    join_forms = {}
    if request.method == 'GET':
        form = AstakosGroupSearchForm()
    else:
        form = AstakosGroupSearchForm(get_query(request))
        if form.is_valid():
            q = form.cleaned_data['q'].strip()
            q = URLField().to_python(q)
            queryset = AstakosGroup.objects.select_related().filter(name=q)
            f = MembershipCreationForm
            for g in queryset:
                join_forms[g.name] = f(
                    dict(
                        group=g,
                        person=request.user,
                        date_requested=datetime.now().strftime("%d/%m/%Y")
                    )
                )
            return object_list(
                request,
                queryset,
                template_name='im/astakosgroup_list.html',
                extra_context=dict(
                    form=form,
                    is_search=True,
                    join_forms=join_forms
                )
            )
    return render_response(
        template='im/astakosgroup_list.html',
        form = form,
        context_instance=get_context(request)
    )

@signed_terms_required
@login_required
def group_join(request, group_id):
    return create_object(
        request,
        model=Membership,
        template_name='im/astakosgroup_list.html',
        post_save_redirect = reverse(
            'group_detail',
            kwargs=dict(group_id=group_id)
        )
    )

@signed_terms_required
@login_required
def group_leave(request, group_id):
    try:
        m = Membership.objects.select_related().get(
            group__id=group_id,
            person=request.user
        )
    except Membership.DoesNotExist:
        return HttpResponseBadRequest(_('Invalid membership.'))
    if request.user in m.group.owner.all():
        return HttpResponseForbidden(_('Owner can not leave the group.'))
    return delete_object(
        request,
        model=Membership,
        object_id = m.id,
        template_name='im/astakosgroup_list.html',
        post_delete_redirect = reverse(
            'group_detail',
            kwargs=dict(group_id=group_id)
        )
    )

def handle_membership():
    def decorator(func):
        @wraps(func)
        def wrapper(request, group_id, user_id):
            try:
                m = Membership.objects.select_related().get(
                    group__id=group_id,
                    person__id=user_id
                )
            except Membership.DoesNotExist:
                return HttpResponseBadRequest(_('Invalid membership.'))
            else:
                if request.user not in m.group.owner.all():
                    return HttpResponseForbidden(_('User is not a group owner.'))
                func(request, m)
                return render_response(
                    template='im/astakosgroup_detail.html',
                    context_instance=get_context(request),
                    object=m.group,
                    quota=m.group.quota,
                    more_policies=m.group.has_undefined_policies
                )
        return wrapper
    return decorator

@signed_terms_required
@login_required
@handle_membership()
def approve_member(request, membership):
    try:
        membership.approve()
        realname = membership.person.realname
        msg = _('%s has been successfully joined the group.' % realname)
        messages.success(request, msg)
    except BaseException, e:
        logger.exception(e)
        msg = _('Something went wrong during %s\'s approval.' % realname)
        messages.error(request, msg)
    
@signed_terms_required
@login_required
@handle_membership()
def disapprove_member(request, membership):
    try:
        membership.disapprove()
        realname = membership.person.realname
        msg = _('%s has been successfully removed from the group.' % realname)
        messages.success(request, msg)
    except BaseException, e:
        logger.exception(e)
        msg = _('Something went wrong during %s\'s disapproval.' % realname)
        messages.error(request, msg)

@signed_terms_required
@login_required
def resource_list(request):
    return render_response(
        template='im/astakosuserquota_list.html',
        context_instance=get_context(request),
        quota=request.user.quota
    )