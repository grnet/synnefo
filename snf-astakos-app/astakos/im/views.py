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
import calendar
import inflect

engine = inflect.engine()

from urllib import quote
from functools import wraps
from datetime import datetime
from synnefo.lib.ordereddict import OrderedDict

from django_tables2 import RequestConfig

from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.utils import IntegrityError
from django.http import (
    HttpResponse, HttpResponseBadRequest,
    HttpResponseForbidden, HttpResponseRedirect,
    HttpResponseBadRequest, Http404)
from django.shortcuts import redirect
from django.template import RequestContext, loader as template_loader
from django.utils.http import urlencode
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.views.generic.create_update import (
    apply_extra_context, lookup_object, delete_object, get_model_and_form_class)
from django.views.generic.list_detail import object_list, object_detail
from django.core.xheaders import populate_xheaders
from django.core.exceptions import ValidationError, PermissionDenied
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.utils import simplejson as json

import astakos.im.messages as astakos_messages

from astakos.im.activation_backends import get_backend, SimpleBackend
from astakos.im import tables
from astakos.im.models import (
    AstakosUser, ApprovalTerms,
    EmailChange, RESOURCE_SEPARATOR,
    AstakosUserAuthProvider, PendingThirdPartyUser,
    PendingMembershipError,
    ProjectApplication, ProjectMembership, Project)
from astakos.im.util import (
    get_context, prepare_response, get_query, restrict_next)
from astakos.im.forms import (
    LoginForm, InvitationForm,
    FeedbackForm, SignApprovalTermsForm,
    EmailChangeForm,
    ProjectApplicationForm, ProjectSortForm,
    AddProjectMembersForm, ProjectSearchForm,
    ProjectMembersSortForm)
from astakos.im.forms import ExtendedProfileForm as ProfileForm
from astakos.im.functions import (
    send_feedback, SendMailError,
    logout as auth_logout,
    activate as activate_func,
    invite,
    send_activation as send_activation_func,
    SendNotificationError,
    accept_membership, reject_membership, remove_membership, cancel_membership,
    leave_project, join_project, enroll_member, can_join_request, can_leave_request,
    get_related_project_id, get_by_chain_or_404,
    approve_application, deny_application,
    cancel_application, dismiss_application)
from astakos.im.settings import (
    COOKIE_DOMAIN, LOGOUT_NEXT,
    LOGGING_LEVEL, PAGINATE_BY,
    RESOURCES_PRESENTATION_DATA, PAGINATE_BY_ALL,
    ACTIVATION_REDIRECT_URL,
    MODERATION_ENABLED)
from astakos.im.api import get_services_dict
from astakos.im import settings as astakos_settings
from astakos.im.api.callpoint import AstakosCallpoint
from astakos.im import auth_providers
from astakos.im.project_xctx import project_transaction_context
from astakos.im.retry_xctx import RetryException

logger = logging.getLogger(__name__)

callpoint = AstakosCallpoint()

def render_response(template, tab=None, status=200, context_instance=None, **kwargs):
    """
    Calls ``django.template.loader.render_to_string`` with an additional ``tab``
    keyword argument and returns an ``django.http.HttpResponse`` with the
    specified ``status``.
    """
    if tab is None:
        tab = template.partition('_')[0].partition('.html')[0]
    kwargs.setdefault('tab', tab)
    html = template_loader.render_to_string(
        template, kwargs, context_instance=context_instance)
    response = HttpResponse(html, status=status)
    return response

def requires_auth_provider(provider_id, **perms):
    """
    """
    def decorator(func, *args, **kwargs):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            provider = auth_providers.get_provider(provider_id)

            if not provider or not provider.is_active():
                raise PermissionDenied

            if provider:
                for pkey, value in perms.iteritems():
                    attr = 'is_available_for_%s' % pkey.lower()
                    if getattr(provider, attr)() != value:
                        #TODO: add session message
                        return HttpResponseRedirect(reverse('login'))
            return func(request, *args)
        return wrapper
    return decorator


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
    Decorator checks whether the request.user is Anonymous and in that case
    redirects to `logout`.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated() and not request.user.signed_terms:
            params = urlencode({'next': request.build_absolute_uri(),
                                'show_form': ''})
            terms_uri = reverse('latest_terms') + '?' + params
            return HttpResponseRedirect(terms_uri)
        return func(request, *args, **kwargs)
    return wrapper


def required_auth_methods_assigned(only_warn=False):
    """
    Decorator that checks whether the request.user has all required auth providers
    assigned.
    """
    required_providers = auth_providers.REQUIRED_PROVIDERS.keys()

    def decorator(func):
        if not required_providers:
            return func

        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated():
                for required in required_providers:
                    if not request.user.has_auth_provider(required):
                        provider = auth_providers.get_provider(required)
                        if only_warn:
                            messages.error(request,
                                           _(astakos_messages.AUTH_PROVIDER_REQUIRED  % {
                                               'provider': provider.get_title_display}))
                        else:
                            return HttpResponseRedirect(reverse('edit_profile'))
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def valid_astakos_user_required(func):
    return signed_terms_required(required_auth_methods_assigned()(login_required(func)))


@require_http_methods(["GET", "POST"])
@signed_terms_required
def index(request, login_template_name='im/login.html', profile_template_name='im/profile.html', extra_context=None):
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
    extra_context = extra_context or {}
    template_name = login_template_name
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('astakos.im.views.edit_profile'))

    third_party_token = request.GET.get('key', False)
    if third_party_token:
        messages.info(request, astakos_messages.AUTH_PROVIDER_LOGIN_TO_ADD)

    return render_response(
        template_name,
        login_form = LoginForm(request=request),
        context_instance = get_context(request, extra_context)
    )


@require_http_methods(["POST"])
@valid_astakos_user_required
def update_token(request):
    """
    Update api token view.
    """
    user = request.user
    user.renew_token()
    user.save()
    messages.success(request, astakos_messages.TOKEN_UPDATED)
    return HttpResponseRedirect(reverse('edit_profile'))


@require_http_methods(["GET", "POST"])
@valid_astakos_user_required
@transaction.commit_manually
def invite(request, template_name='im/invitations.html', extra_context=None):
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
    """
    extra_context = extra_context or {}
    status = None
    message = None
    form = InvitationForm()

    inviter = request.user
    if request.method == 'POST':
        form = InvitationForm(request.POST)
        if inviter.invitations > 0:
            if form.is_valid():
                try:
                    email = form.cleaned_data.get('username')
                    realname = form.cleaned_data.get('realname')
                    invite(inviter, email, realname)
                    message = _(astakos_messages.INVITATION_SENT) % locals()
                    messages.success(request, message)
                except SendMailError, e:
                    message = e.message
                    messages.error(request, message)
                    transaction.rollback()
                except BaseException, e:
                    message = _(astakos_messages.GENERIC_ERROR)
                    messages.error(request, message)
                    logger.exception(e)
                    transaction.rollback()
                else:
                    transaction.commit()
        else:
            message = _(astakos_messages.MAX_INVITATION_NUMBER_REACHED)
            messages.error(request, message)

    sent = [{'email': inv.username,
             'realname': inv.realname,
             'is_consumed': inv.is_consumed}
            for inv in request.user.invitations_sent.all()]
    kwargs = {'inviter': inviter,
              'sent': sent}
    context = get_context(request, extra_context, **kwargs)
    return render_response(template_name,
                           invitation_form=form,
                           context_instance=context)


@require_http_methods(["GET", "POST"])
@required_auth_methods_assigned(only_warn=True)
@login_required
@signed_terms_required
def edit_profile(request, template_name='im/profile.html', extra_context=None):
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
    extra_context = extra_context or {}
    form = ProfileForm(
        instance=request.user,
        session_key=request.session.session_key
    )
    extra_context['next'] = request.GET.get('next')
    if request.method == 'POST':
        form = ProfileForm(
            request.POST,
            instance=request.user,
            session_key=request.session.session_key
        )
        if form.is_valid():
            try:
                prev_token = request.user.auth_token
                user = form.save(request=request)
                next = restrict_next(
                    request.POST.get('next'),
                    domain=COOKIE_DOMAIN
                )
                msg = _(astakos_messages.PROFILE_UPDATED)
                messages.success(request, msg)

                if form.email_changed:
                    msg = _(astakos_messages.EMAIL_CHANGE_REGISTERED)
                    messages.success(request, msg)
                if form.password_changed:
                    msg = _(astakos_messages.PASSWORD_CHANGED)
                    messages.success(request, msg)

                if next:
                    return redirect(next)
                else:
                    return redirect(reverse('edit_profile'))
            except ValueError, ve:
                messages.success(request, ve)
    elif request.method == "GET":
        request.user.is_verified = True
        request.user.save()

    # existing providers
    user_providers = request.user.get_active_auth_providers()

    # providers that user can add
    user_available_providers = request.user.get_available_auth_providers()

    extra_context['services'] = get_services_dict()
    return render_response(template_name,
                           profile_form = form,
                           user_providers = user_providers,
                           user_available_providers = user_available_providers,
                           context_instance = get_context(request,
                                                          extra_context))


@transaction.commit_manually
@require_http_methods(["GET", "POST"])
def signup(request, template_name='im/signup.html', on_success='index', extra_context=None, backend=None):
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

    ``extra_context``
        An dictionary of variables to add to the template context.

    ``on_success``
        Resolvable view name to redirect on registration success.

    **Template:**

    im/signup.html or ``template_name`` keyword argument.
    """
    extra_context = extra_context or {}
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('edit_profile'))

    provider = get_query(request).get('provider', 'local')
    if not auth_providers.get_provider(provider).is_available_for_create():
        raise PermissionDenied

    id = get_query(request).get('id')
    try:
        instance = AstakosUser.objects.get(id=id) if id else None
    except AstakosUser.DoesNotExist:
        instance = None

    third_party_token = request.REQUEST.get('third_party_token', None)
    if third_party_token:
        pending = get_object_or_404(PendingThirdPartyUser,
                                    token=third_party_token)
        provider = pending.provider
        instance = pending.get_user_instance()

    try:
        if not backend:
            backend = get_backend(request)
        form = backend.get_signup_form(provider, instance)
    except Exception, e:
        form = SimpleBackend(request).get_signup_form(provider)
        messages.error(request, e)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save(commit=False)

            # delete previously unverified accounts
            if AstakosUser.objects.user_exists(user.email):
                AstakosUser.objects.get_by_identifier(user.email).delete()

            try:
                result = backend.handle_activation(user)
                status = messages.SUCCESS
                message = result.message

                form.store_user(user, request)

                if 'additional_email' in form.cleaned_data:
                    additional_email = form.cleaned_data['additional_email']
                    if additional_email != user.email:
                        user.additionalmail_set.create(email=additional_email)
                        msg = 'Additional email: %s saved for user %s.' % (
                            additional_email,
                            user.email
                        )
                        logger._log(LOGGING_LEVEL, msg, [])

                if user and user.is_active:
                    next = request.POST.get('next', '')
                    response = prepare_response(request, user, next=next)
                    transaction.commit()
                    return response

                transaction.commit()
                messages.add_message(request, status, message)
                return HttpResponseRedirect(reverse(on_success))

            except SendMailError, e:
                logger.exception(e)
                status = messages.ERROR
                message = e.message
                messages.error(request, message)
                transaction.rollback()
            except BaseException, e:
                logger.exception(e)
                message = _(astakos_messages.GENERIC_ERROR)
                messages.error(request, message)
                logger.exception(e)
                transaction.rollback()

    return render_response(template_name,
                           signup_form=form,
                           third_party_token=third_party_token,
                           provider=provider,
                           context_instance=get_context(request, extra_context))


@require_http_methods(["GET", "POST"])
@required_auth_methods_assigned(only_warn=True)
@login_required
@signed_terms_required
def feedback(request, template_name='im/feedback.html', email_template_name='im/feedback_mail.txt', extra_context=None):
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
    """
    extra_context = extra_context or {}
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
                messages.error(request, message)
            else:
                message = _(astakos_messages.FEEDBACK_SENT)
                messages.success(request, message)
    return render_response(template_name,
                           feedback_form=form,
                           context_instance=get_context(request, extra_context))


@require_http_methods(["GET"])
@signed_terms_required
def logout(request, template='registration/logged_out.html', extra_context=None):
    """
    Wraps `django.contrib.auth.logout`.
    """
    extra_context = extra_context or {}
    response = HttpResponse()
    if request.user.is_authenticated():
        email = request.user.email
        auth_logout(request)
    else:
        response['Location'] = reverse('index')
        response.status_code = 301
        return response

    next = restrict_next(
        request.GET.get('next'),
        domain=COOKIE_DOMAIN
    )

    if next:
        response['Location'] = next
        response.status_code = 302
    elif LOGOUT_NEXT:
        response['Location'] = LOGOUT_NEXT
        response.status_code = 301
    else:
        message = _(astakos_messages.LOGOUT_SUCCESS)
        last_provider = request.COOKIES.get('astakos_last_login_method', None)
        if last_provider:
            provider = auth_providers.get_provider(last_provider)
            extra_message = provider.get_logout_message_display
            if extra_message:
                message += '<br />' + extra_message
        messages.add_message(request, messages.SUCCESS, mark_safe(message))
        response['Location'] = reverse('index')
        response.status_code = 301
    return response


@require_http_methods(["GET", "POST"])
@transaction.commit_manually
def activate(request, greeting_email_template_name='im/welcome_email.txt',
             helpdesk_email_template_name='im/helpdesk_notification.txt'):
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
        return HttpResponseBadRequest(_(astakos_messages.ACCOUNT_UNKNOWN))

    if user.is_active:
        message = _(astakos_messages.ACCOUNT_ALREADY_ACTIVE)
        messages.error(request, message)
        return index(request)

    try:
        activate_func(user, greeting_email_template_name,
                      helpdesk_email_template_name, verify_email=True)
        messages.success(request, _(astakos_messages.ACCOUNT_ACTIVATED))
        next = ACTIVATION_REDIRECT_URL or next
        response = prepare_response(request, user, next, renew=True)
        transaction.commit()
        return response
    except SendMailError, e:
        message = e.message
        messages.add_message(request, messages.ERROR, message)
        transaction.rollback()
        return index(request)
    except BaseException, e:
        status = messages.ERROR
        message = _(astakos_messages.GENERIC_ERROR)
        messages.add_message(request, messages.ERROR, message)
        logger.exception(e)
        transaction.rollback()
        return index(request)


@require_http_methods(["GET", "POST"])
def approval_terms(request, term_id=None, template_name='im/approval_terms.html', extra_context=None):
    extra_context = extra_context or {}
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
        except ApprovalTerms.DoesNotExist, e:
            pass

    if not term:
        messages.error(request, _(astakos_messages.NO_APPROVAL_TERMS))
        return HttpResponseRedirect(reverse('index'))
    try:
        f = open(term.location, 'r')
    except IOError:
        messages.error(request, _(astakos_messages.GENERIC_ERROR))
        return render_response(
            template_name, context_instance=get_context(request, extra_context))

    terms = f.read()

    if request.method == 'POST':
        next = restrict_next(
            request.POST.get('next'),
            domain=COOKIE_DOMAIN
        )
        if not next:
            next = reverse('index')
        form = SignApprovalTermsForm(request.POST, instance=request.user)
        if not form.is_valid():
            return render_response(template_name,
                                   terms=terms,
                                   approval_terms_form=form,
                                   context_instance=get_context(request, extra_context))
        user = form.save()
        return HttpResponseRedirect(next)
    else:
        form = None
        if request.user.is_authenticated() and not request.user.signed_terms:
            form = SignApprovalTermsForm(instance=request.user)
        return render_response(template_name,
                               terms=terms,
                               approval_terms_form=form,
                               context_instance=get_context(request, extra_context))


@require_http_methods(["GET", "POST"])
@transaction.commit_manually
def change_email(request, activation_key=None,
                 email_template_name='registration/email_change_email.txt',
                 form_template_name='registration/email_change_form.html',
                 confirm_template_name='registration/email_change_done.html',
                 extra_context=None):
    extra_context = extra_context or {}


    if not astakos_settings.EMAILCHANGE_ENABLED:
        raise PermissionDenied

    if activation_key:
        try:
            user = EmailChange.objects.change_email(activation_key)
            if request.user.is_authenticated() and request.user == user or not \
                    request.user.is_authenticated():
                msg = _(astakos_messages.EMAIL_CHANGED)
                messages.success(request, msg)
                transaction.commit()
                return HttpResponseRedirect(reverse('edit_profile'))
        except ValueError, e:
            messages.error(request, e)
            transaction.rollback()
            return HttpResponseRedirect(reverse('index'))

        return render_response(confirm_template_name,
                               modified_user=user if 'user' in locals() \
                               else None, context_instance=get_context(request,
                                                            extra_context))

    if not request.user.is_authenticated():
        path = quote(request.get_full_path())
        url = request.build_absolute_uri(reverse('index'))
        return HttpResponseRedirect(url + '?next=' + path)

    # clean up expired email changes
    if request.user.email_change_is_pending():
        change = request.user.emailchanges.get()
        if change.activation_key_expired():
            change.delete()
            transaction.commit()
            return HttpResponseRedirect(reverse('email_change'))

    form = EmailChangeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            ec = form.save(email_template_name, request)
        except SendMailError, e:
            msg = e
            messages.error(request, msg)
            transaction.rollback()
            return HttpResponseRedirect(reverse('edit_profile'))
        else:
            msg = _(astakos_messages.EMAIL_CHANGE_REGISTERED)
            messages.success(request, msg)
            transaction.commit()
            return HttpResponseRedirect(reverse('edit_profile'))

    if request.user.email_change_is_pending():
        messages.warning(request, astakos_messages.PENDING_EMAIL_CHANGE_REQUEST)

    return render_response(
        form_template_name,
        form=form,
        context_instance=get_context(request, extra_context)
    )


def send_activation(request, user_id, template_name='im/login.html', extra_context=None):

    if request.user.is_authenticated():
        messages.error(request, _(astakos_messages.ALREADY_LOGGED_IN))
        return HttpResponseRedirect(reverse('edit_profile'))

    # TODO: check if moderation is only enabled for local login
    if astakos_settings.MODERATION_ENABLED:
        raise PermissionDenied

    extra_context = extra_context or {}
    try:
        u = AstakosUser.objects.get(id=user_id)
    except AstakosUser.DoesNotExist:
        messages.error(request, _(astakos_messages.ACCOUNT_UNKNOWN))
    else:
        try:
            send_activation_func(u)
            msg = _(astakos_messages.ACTIVATION_SENT)
            messages.success(request, msg)
        except SendMailError, e:
            messages.error(request, e)

    return HttpResponseRedirect(reverse('index'))


@require_http_methods(["GET"])
@valid_astakos_user_required
def resource_usage(request):

    def with_class(entry):
         entry['load_class'] = 'red'
         max_value = float(entry['maxValue'])
         curr_value = float(entry['currValue'])
         entry['ratio_limited']= 0
         if max_value > 0 :
             entry['ratio'] = (curr_value / max_value) * 100
         else:
             entry['ratio'] = 0
         if entry['ratio'] < 66:
             entry['load_class'] = 'yellow'
         if entry['ratio'] < 33:
             entry['load_class'] = 'green'
         if entry['ratio']<0:
             entry['ratio'] = 0
         if entry['ratio']>100:
             entry['ratio_limited'] = 100
         else:
             entry['ratio_limited'] = entry['ratio']
         return entry

    def pluralize(entry):
        entry['plural'] = engine.plural(entry.get('name'))
        return entry

    resource_usage = None
    result = callpoint.get_user_usage(request.user.id)
    if result.is_success:
        resource_usage = result.data
        backenddata = map(with_class, result.data)
        backenddata = map(pluralize , backenddata)
    else:
        messages.error(request, result.reason)
        backenddata = []
        resource_usage = []

    if request.REQUEST.get('json', None):
        return HttpResponse(json.dumps(backenddata),
                            mimetype="application/json")

    return render_response('im/resource_usage.html',
                           context_instance=get_context(request),
                           resource_usage=backenddata,
                           usage_update_interval=astakos_settings.USAGE_UPDATE_INTERVAL,
                           result=result)

# TODO: action only on POST and user should confirm the removal
@require_http_methods(["GET", "POST"])
@login_required
@signed_terms_required
def remove_auth_provider(request, pk):
    try:
        provider = request.user.auth_providers.get(pk=pk)
    except AstakosUserAuthProvider.DoesNotExist:
        raise Http404

    if provider.can_remove():
        provider.delete()
        message = astakos_messages.AUTH_PROVIDER_REMOVED % \
                            provider.settings.get_method_prompt_display
        messages.success(request, message)
        return HttpResponseRedirect(reverse('edit_profile'))
    else:
        raise PermissionDenied


def how_it_works(request):
    return render_response(
        'im/how_it_works.html',
        context_instance=get_context(request))

@project_transaction_context()
def _create_object(request, model=None, template_name=None,
        template_loader=template_loader, extra_context=None, post_save_redirect=None,
        login_required=False, context_processors=None, form_class=None,
        msg=None, ctx=None):
    """
    Based of django.views.generic.create_update.create_object which displays a
    summary page before creating the object.
    """
    response = None

    if extra_context is None: extra_context = {}
    if login_required and not request.user.is_authenticated():
        return redirect_to_login(request.path)
    try:

        model, form_class = get_model_and_form_class(model, form_class)
        extra_context['edit'] = 0
        if request.method == 'POST':
            form = form_class(request.POST, request.FILES)
            if form.is_valid():
                verify = request.GET.get('verify')
                edit = request.GET.get('edit')
                if verify == '1':
                    extra_context['show_form'] = False
                    extra_context['form_data'] = form.cleaned_data
                elif edit == '1':
                    extra_context['show_form'] = True
                else:
                    new_object = form.save()
                    if not msg:
                        msg = _("The %(verbose_name)s was created successfully.")
                    msg = msg % model._meta.__dict__
                    messages.success(request, msg, fail_silently=True)
                    response = redirect(post_save_redirect, new_object)
        else:
            form = form_class()
    except BaseException, e:
        logger.exception(e)
        messages.error(request, _(astakos_messages.GENERIC_ERROR))
        if ctx:
            ctx.mark_rollback()
    finally:
        if response == None:
            # Create the template, context, response
            if not template_name:
                template_name = "%s/%s_form.html" %\
                     (model._meta.app_label, model._meta.object_name.lower())
            t = template_loader.get_template(template_name)
            c = RequestContext(request, {
                'form': form
            }, context_processors)
            apply_extra_context(extra_context, c)
            response = HttpResponse(t.render(c))
        return response

@project_transaction_context()
def _update_object(request, model=None, object_id=None, slug=None,
        slug_field='slug', template_name=None, template_loader=template_loader,
        extra_context=None, post_save_redirect=None, login_required=False,
        context_processors=None, template_object_name='object',
        form_class=None, msg=None, ctx=None):
    """
    Based of django.views.generic.create_update.update_object which displays a
    summary page before updating the object.
    """
    response = None

    if extra_context is None: extra_context = {}
    if login_required and not request.user.is_authenticated():
        return redirect_to_login(request.path)

    try:
        model, form_class = get_model_and_form_class(model, form_class)
        obj = lookup_object(model, object_id, slug, slug_field)

        if request.method == 'POST':
            form = form_class(request.POST, request.FILES, instance=obj)
            if form.is_valid():
                verify = request.GET.get('verify')
                edit = request.GET.get('edit')
                if verify == '1':
                    extra_context['show_form'] = False
                    extra_context['form_data'] = form.cleaned_data
                elif edit == '1':
                    extra_context['show_form'] = True
                else:
                    obj = form.save()
                    if not msg:
                        msg = _("The %(verbose_name)s was created successfully.")
                    msg = msg % model._meta.__dict__
                    messages.success(request, msg, fail_silently=True)
                    response = redirect(post_save_redirect, obj)
        else:
            form = form_class(instance=obj)
    except BaseException, e:
        logger.exception(e)
        messages.error(request, _(astakos_messages.GENERIC_ERROR))
        ctx.mark_rollback()
    finally:
        if response == None:
            if not template_name:
                template_name = "%s/%s_form.html" %\
                    (model._meta.app_label, model._meta.object_name.lower())
            t = template_loader.get_template(template_name)
            c = RequestContext(request, {
                'form': form,
                template_object_name: obj,
            }, context_processors)
            apply_extra_context(extra_context, c)
            response = HttpResponse(t.render(c))
            populate_xheaders(request, response, model, getattr(obj, obj._meta.pk.attname))
        return response

@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def project_add(request):
    resource_groups = RESOURCES_PRESENTATION_DATA.get('groups', {})
    resource_catalog = ()
    result = callpoint.list_resources()
    details_fields = [
        "name", "homepage", "description","start_date","end_date", "comments"]
    membership_fields =[
        "member_join_policy", "member_leave_policy", "limit_on_members_number"]
    if not result.is_success:
        messages.error(
            request,
            'Unable to retrieve system resources: %s' % result.reason
    )
    else:
        resource_catalog = [
            [g, filter(lambda r: r.get('group', '') == g, result.data)] \
                for g in resource_groups]

    # order resources
    groups_order = RESOURCES_PRESENTATION_DATA.get('groups_order')
    resources_order = RESOURCES_PRESENTATION_DATA.get('resources_order')
    resource_catalog = sorted(resource_catalog, key=lambda g:groups_order.index(g[0]))

    resource_groups_list = sorted([(k,v) for k,v in resource_groups.items()],
                                  key=lambda f:groups_order.index(f[0]))
    resource_groups = OrderedDict(resource_groups_list)
    for index, group in enumerate(resource_catalog):
        resource_catalog[index][1] = sorted(resource_catalog[index][1],
                                            key=lambda r: resources_order.index(r['str_repr']))


    extra_context = {
        'resource_catalog':resource_catalog,
        'resource_groups':resource_groups,
        'show_form':True,
        'details_fields':details_fields,
        'membership_fields':membership_fields}
    return _create_object(
        request,
        template_name='im/projects/projectapplication_form.html',
        extra_context=extra_context,
        post_save_redirect=reverse('project_list'),
        form_class=ProjectApplicationForm,
        msg=_("The %(verbose_name)s has been received and \
                 is under consideration."))


@require_http_methods(["GET"])
@signed_terms_required
@login_required
def project_list(request):
    projects = ProjectApplication.objects.user_accessible_projects(request.user).select_related()
    table = tables.UserProjectApplicationsTable(projects, user=request.user,
                                                prefix="my_projects_")
    RequestConfig(request, paginate={"per_page": PAGINATE_BY}).configure(table)

    return object_list(
        request,
        projects,
        template_name='im/projects/project_list.html',
        extra_context={
            'is_search':False,
            'table': table,
        })


@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
@project_transaction_context()
def project_app_cancel(request, application_id, ctx=None):
    chain_id = None
    try:
        application_id = int(application_id)
        chain_id = get_related_project_id(application_id)
        cancel_application(application_id, request.user)
    except (IOError, PermissionDenied), e:
        messages.error(request, e)
    except BaseException, e:
        logger.exception(e)
        messages.error(request, _(astakos_messages.GENERIC_ERROR))
        if ctx:
            ctx.mark_rollback()
    else:
        msg = _(astakos_messages.APPLICATION_CANCELLED)
        messages.success(request, msg)

    next = request.GET.get('next')
    if not next:
        if chain_id:
            next = reverse('astakos.im.views.project_detail', args=(chain_id,))
        else:
            next = reverse('astakos.im.views.project_list')

    next = restrict_next(next, domain=COOKIE_DOMAIN)
    return redirect(next)


@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def project_modify(request, application_id):

    try:
        app = ProjectApplication.objects.get(id=application_id)
    except ProjectApplication.DoesNotExist:
        raise Http404

    user = request.user
    if not (user.owns_application(app) or user.is_project_admin(app.id)):
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    resource_groups = RESOURCES_PRESENTATION_DATA.get('groups', {})
    resource_catalog = ()
    result = callpoint.list_resources()
    details_fields = [
        "name", "homepage", "description","start_date","end_date", "comments"]
    membership_fields =[
        "member_join_policy", "member_leave_policy", "limit_on_members_number"]
    if not result.is_success:
        messages.error(
            request,
            'Unable to retrieve system resources: %s' % result.reason
    )
    else:
        resource_catalog = [
            (g, filter(lambda r: r.get('group', '') == g, result.data)) \
                for g in resource_groups]
    extra_context = {
        'resource_catalog':resource_catalog,
        'resource_groups':resource_groups,
        'show_form':True,
        'details_fields':details_fields,
        'update_form': True,
        'membership_fields':membership_fields}
    return _update_object(
        request,
        object_id=application_id,
        template_name='im/projects/projectapplication_form.html',
        extra_context=extra_context, post_save_redirect=reverse('project_list'),
        form_class=ProjectApplicationForm,
        msg = _("The %(verbose_name)s has been received and \
                    is under consideration."))


@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def project_app(request, application_id):
    return common_detail(request, application_id, project_view=False)

@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def project_detail(request, chain_id):
    return common_detail(request, chain_id)

@project_transaction_context(sync=True)
def addmembers(request, chain_id, addmembers_form, ctx=None):
    if addmembers_form.is_valid():
        try:
            chain_id = int(chain_id)
            map(lambda u: enroll_member(
                    chain_id,
                    u,
                    request_user=request.user),
                addmembers_form.valid_users)
        except (IOError, PermissionDenied), e:
            messages.error(request, e)
        except BaseException, e:
            if ctx:
                ctx.mark_rollback()
            messages.error(request, e)

def common_detail(request, chain_or_app_id, project_view=True):
    project = None
    if project_view:
        chain_id = chain_or_app_id
        if request.method == 'POST':
            addmembers_form = AddProjectMembersForm(
                request.POST,
                chain_id=int(chain_id),
                request_user=request.user)
            addmembers(request, chain_id, addmembers_form)
            if addmembers_form.is_valid():
                addmembers_form = AddProjectMembersForm()  # clear form data
        else:
            addmembers_form = AddProjectMembersForm()  # initialize form

        project, application = get_by_chain_or_404(chain_id)
        if project:
            members = project.projectmembership_set.select_related()
            members_table = tables.ProjectMembersTable(project,
                                                       members,
                                                       user=request.user,
                                                       prefix="members_")
            RequestConfig(request, paginate={"per_page": PAGINATE_BY}
                          ).configure(members_table)

        else:
            members_table = None

    else: # is application
        application_id = chain_or_app_id
        application = get_object_or_404(ProjectApplication, pk=application_id)
        members_table = None
        addmembers_form = None

    modifications_table = None

    user = request.user
    is_project_admin = user.is_project_admin(application_id=application.id)
    is_owner = user.owns_application(application)
    if not (is_owner or is_project_admin) and not project_view:
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    if (not (is_owner or is_project_admin) and project_view and
        not user.non_owner_can_view(project)):
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    following_applications = list(application.pending_modifications())
    following_applications.reverse()
    modifications_table = (
        tables.ProjectModificationApplicationsTable(following_applications,
                                                    user=request.user,
                                                    prefix="modifications_"))

    mem_display = user.membership_display(project) if project else None
    can_join_req = can_join_request(project, user) if project else False
    can_leave_req = can_leave_request(project, user) if project else False

    return object_detail(
        request,
        queryset=ProjectApplication.objects.select_related(),
        object_id=application.id,
        template_name='im/projects/project_detail.html',
        extra_context={
            'project_view': project_view,
            'addmembers_form':addmembers_form,
            'members_table': members_table,
            'owner_mode': is_owner,
            'admin_mode': is_project_admin,
            'modifications_table': modifications_table,
            'mem_display': mem_display,
            'can_join_request': can_join_req,
            'can_leave_request': can_leave_req,
            })

@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def project_search(request):
    q = request.GET.get('q', '')
    form = ProjectSearchForm()
    q = q.strip()

    if request.method == "POST":
        form = ProjectSearchForm(request.POST)
        if form.is_valid():
            q = form.cleaned_data['q'].strip()
        else:
            q = None

    if q is None:
        projects = ProjectApplication.objects.none()
    else:
        accepted_projects = request.user.projectmembership_set.filter(
            ~Q(acceptance_date__isnull=True)).values_list('project', flat=True)
        projects = ProjectApplication.objects.search_by_name(q)
        projects = projects.filter(~Q(project__last_approval_date__isnull=True))
        projects = projects.exclude(project__in=accepted_projects)

    table = tables.UserProjectApplicationsTable(projects, user=request.user,
                                                prefix="my_projects_")
    if request.method == "POST":
        table.caption = _('SEARCH RESULTS')
    else:
        table.caption = _('ALL PROJECTS')

    RequestConfig(request, paginate={"per_page": PAGINATE_BY}).configure(table)

    return object_list(
        request,
        projects,
        template_name='im/projects/project_list.html',
        extra_context={
          'form': form,
          'is_search': True,
          'q': q,
          'table': table
        })

@require_http_methods(["POST", "GET"])
@signed_terms_required
@login_required
@project_transaction_context(sync=True)
def project_join(request, chain_id, ctx=None):
    next = request.GET.get('next')
    if not next:
        next = reverse('astakos.im.views.project_detail',
                       args=(chain_id,))

    try:
        chain_id = int(chain_id)
        auto_accepted = join_project(chain_id, request.user)
        if auto_accepted:
            m = _(astakos_messages.USER_JOINED_PROJECT)
        else:
            m = _(astakos_messages.USER_JOIN_REQUEST_SUBMITTED)
        messages.success(request, m)
    except (IOError, PermissionDenied), e:
        messages.error(request, e)
    except BaseException, e:
        logger.exception(e)
        messages.error(request, _(astakos_messages.GENERIC_ERROR))
        if ctx:
            ctx.mark_rollback()
    next = restrict_next(next, domain=COOKIE_DOMAIN)
    return redirect(next)

@require_http_methods(["POST", "GET"])
@signed_terms_required
@login_required
@project_transaction_context(sync=True)
def project_leave(request, chain_id, ctx=None):
    next = request.GET.get('next')
    if not next:
        next = reverse('astakos.im.views.project_list')

    try:
        chain_id = int(chain_id)
        auto_accepted = leave_project(chain_id, request.user)
        if auto_accepted:
            m = _(astakos_messages.USER_LEFT_PROJECT)
        else:
            m = _(astakos_messages.USER_LEAVE_REQUEST_SUBMITTED)
        messages.success(request, m)
    except (IOError, PermissionDenied), e:
        messages.error(request, e)
    except PendingMembershipError as e:
        raise RetryException()
    except BaseException, e:
        logger.exception(e)
        messages.error(request, _(astakos_messages.GENERIC_ERROR))
        if ctx:
            ctx.mark_rollback()
    next = restrict_next(next, domain=COOKIE_DOMAIN)
    return redirect(next)

@require_http_methods(["POST"])
@signed_terms_required
@login_required
@project_transaction_context()
def project_cancel(request, chain_id, ctx=None):
    next = request.GET.get('next')
    if not next:
        next = reverse('astakos.im.views.project_list')

    try:
        chain_id = int(chain_id)
        cancel_membership(chain_id, request.user)
        m = _(astakos_messages.USER_REQUEST_CANCELLED)
        messages.success(request, m)
    except (IOError, PermissionDenied), e:
        messages.error(request, e)
    except PendingMembershipError as e:
        raise RetryException()
    except BaseException, e:
        logger.exception(e)
        messages.error(request, _(astakos_messages.GENERIC_ERROR))
        if ctx:
            ctx.mark_rollback()

    next = restrict_next(next, domain=COOKIE_DOMAIN)
    return redirect(next)

@require_http_methods(["POST"])
@signed_terms_required
@login_required
@project_transaction_context(sync=True)
def project_accept_member(request, chain_id, user_id, ctx=None):
    try:
        chain_id = int(chain_id)
        user_id = int(user_id)
        m = accept_membership(chain_id, user_id, request.user)
    except (IOError, PermissionDenied), e:
        messages.error(request, e)
    except PendingMembershipError as e:
        raise RetryException()
    except BaseException, e:
        logger.exception(e)
        messages.error(request, _(astakos_messages.GENERIC_ERROR))
        if ctx:
            ctx.mark_rollback()
    else:
        realname = escape(m.person.realname)
        msg = _(astakos_messages.USER_MEMBERSHIP_ACCEPTED) % locals()
        messages.success(request, msg)
    return redirect(reverse('project_detail', args=(chain_id,)))

@require_http_methods(["POST"])
@signed_terms_required
@login_required
@project_transaction_context(sync=True)
def project_remove_member(request, chain_id, user_id, ctx=None):
    try:
        chain_id = int(chain_id)
        user_id = int(user_id)
        m = remove_membership(chain_id, user_id, request.user)
    except (IOError, PermissionDenied), e:
        messages.error(request, e)
    except PendingMembershipError as e:
        raise RetryException()
    except BaseException, e:
        logger.exception(e)
        messages.error(request, _(astakos_messages.GENERIC_ERROR))
        if ctx:
            ctx.mark_rollback()
    else:
        realname = escape(m.person.realname)
        msg = _(astakos_messages.USER_LEFT_PROJECT) % locals()
        messages.success(request, msg)
    return redirect(reverse('project_detail', args=(chain_id,)))

@require_http_methods(["POST"])
@signed_terms_required
@login_required
@project_transaction_context()
def project_reject_member(request, chain_id, user_id, ctx=None):
    try:
        chain_id = int(chain_id)
        user_id = int(user_id)
        m = reject_membership(chain_id, user_id, request.user)
    except (IOError, PermissionDenied), e:
        messages.error(request, e)
    except PendingMembershipError as e:
        raise RetryException()
    except BaseException, e:
        logger.exception(e)
        messages.error(request, _(astakos_messages.GENERIC_ERROR))
        if ctx:
            ctx.mark_rollback()
    else:
        realname = escape(m.person.realname)
        msg = _(astakos_messages.USER_MEMBERSHIP_REJECTED) % locals()
        messages.success(request, msg)
    return redirect(reverse('project_detail', args=(chain_id,)))

@require_http_methods(["POST", "GET"])
@signed_terms_required
@login_required
@project_transaction_context(sync=True)
def project_app_approve(request, application_id, ctx=None):

    if not request.user.is_project_admin():
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    try:
        app = ProjectApplication.objects.get(id=application_id)
    except ProjectApplication.DoesNotExist:
        raise Http404

    approve_application(application_id)
    chain_id = get_related_project_id(application_id)
    return redirect(reverse('project_detail', args=(chain_id,)))

@require_http_methods(["POST", "GET"])
@signed_terms_required
@login_required
@project_transaction_context()
def project_app_deny(request, application_id, ctx=None):

    if not request.user.is_project_admin():
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    try:
        app = ProjectApplication.objects.get(id=application_id)
    except ProjectApplication.DoesNotExist:
        raise Http404

    deny_application(application_id)
    return redirect(reverse('project_list'))

@require_http_methods(["POST", "GET"])
@signed_terms_required
@login_required
@project_transaction_context()
def project_app_dismiss(request, application_id, ctx=None):
    try:
        app = ProjectApplication.objects.get(id=application_id)
    except ProjectApplication.DoesNotExist:
        raise Http404

    if not request.user.owns_application(app):
        m = _(astakos_messages.NOT_ALLOWED)
        raise PermissionDenied(m)

    # XXX: dismiss application also does authorization
    dismiss_application(application_id, request_user=request.user)

    chain_id = None
    chain_id = get_related_project_id(application_id)
    if chain_id:
        next = reverse('project_detail', args=(chain_id,))
    else:
        next = reverse('project_list')
    return redirect(next)


def landing(request):
    return render_response(
        'im/landing.html',
        context_instance=get_context(request))


def api_access(request):
    return render_response(
        'im/api_access.html',
        context_instance=get_context(request))
