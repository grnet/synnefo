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
import inflect

engine = inflect.engine()

from urllib import quote

from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_http_methods
from django.utils import simplejson as json
from django.template import RequestContext

from synnefo_branding import utils as branding
from synnefo_branding import settings as branding_settings

from synnefo.lib import join_urls

import astakos.im.messages as astakos_messages

from astakos.im import activation_backends
from astakos.im.models import AstakosUser, ApprovalTerms, EmailChange, \
    AstakosUserAuthProvider, PendingThirdPartyUser, Component
from astakos.im.util import get_context, prepare_response, get_query, \
    restrict_next
from astakos.im.forms import LoginForm, InvitationForm, FeedbackForm, \
    SignApprovalTermsForm, EmailChangeForm
from astakos.im.forms import ExtendedProfileForm as ProfileForm
from synnefo.lib.services import get_public_endpoint
from astakos.im.functions import send_feedback, logout as auth_logout, \
    invite as invite_func
from astakos.im import settings
from astakos.im import presentation
from astakos.im import auth_providers as auth
from astakos.im import quotas
from astakos.im.views.util import render_response, _resources_catalog
from astakos.im.views.decorators import cookie_fix, signed_terms_required,\
    required_auth_methods_assigned, valid_astakos_user_required, login_required

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
@cookie_fix
@signed_terms_required
def login(request, template_name='im/login.html', extra_context=None):
    """
    Renders login page.

    **Arguments**

    ``template_name``
        A custom login template to use. This is optional; if not specified,
        this will default to ``im/login.html``.

    ``extra_context``
        An dictionary of variables to add to the template context.
    """

    extra_context = extra_context or {}

    third_party_token = request.GET.get('key', False)
    if third_party_token:
        messages.info(request, astakos_messages.AUTH_PROVIDER_LOGIN_TO_ADD)

    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('landing'))

    return render_response(
        template_name,
        login_form=LoginForm(request=request),
        context_instance=get_context(request, extra_context)
    )


@require_http_methods(["GET", "POST"])
@cookie_fix
@signed_terms_required
def index(request, authenticated_redirect='landing',
          anonymous_redirect='login', extra_context=None):
    """
    If user is authenticated redirect to ``authenticated_redirect`` url.
    Otherwise redirects to ``anonymous_redirect`` url.

    """
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse(authenticated_redirect))
    return HttpResponseRedirect(reverse(anonymous_redirect))


@require_http_methods(["POST"])
@cookie_fix
@valid_astakos_user_required
def update_token(request):
    """
    Update api token view.
    """
    user = request.user
    user.renew_token()
    user.save()
    messages.success(request, astakos_messages.TOKEN_UPDATED)
    return HttpResponseRedirect(reverse('api_access'))


@require_http_methods(["GET", "POST"])
@cookie_fix
@valid_astakos_user_required
@transaction.commit_manually
def invite(request, template_name='im/invitations.html', extra_context=None):
    """
    Allows a user to invite somebody else.

    In case of GET request renders a form for providing the invitee
    information.
    In case of POST checks whether the user has not run out of invitations and
    then sends an invitation email to singup to the service.

    The view uses commit_manually decorator in order to ensure the number of
    the user invitations is going to be updated only if the email has been
    successfully sent.

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
                    invite_func(inviter, email, realname)
                    message = _(astakos_messages.INVITATION_SENT) % locals()
                    messages.success(request, message)
                except Exception, e:
                    transaction.rollback()
                    raise
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
@required_auth_methods_assigned()
@login_required
@cookie_fix
@signed_terms_required
def api_access_config(request, template_name='im/api_access_config.html',
                      content_type='text/plain', extra_context=None,
                      filename='.kamakirc'):

    if settings.KAMAKI_CONFIG_CLOUD_NAME:
        cloud_name = settings.KAMAKI_CONFIG_CLOUD_NAME
    else:
        cloud_name = branding_settings.SERVICE_NAME.replace(' ', '_').lower()

    url = get_public_endpoint(settings.astakos_services, 'identity')

    context = {
        'user': request.user,
        'services': Component.catalog(),
        'token_url': url,
        'cloud_name': cloud_name
    }

    extra_context = extra_context or {}
    context.update(extra_context)
    content = branding.render_to_string(template_name, context,
                                        RequestContext(request))
    response = HttpResponse(content_type=content_type)
    response.status_code = 200
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    response.content = content
    return response


@required_auth_methods_assigned()
@login_required
@cookie_fix
@signed_terms_required
def api_access(request, template_name='im/api_access.html',
               extra_context=None):
    """
    API access view.
    """
    context = {}

    url = get_public_endpoint(settings.astakos_services, 'identity')
    context['services'] = Component.catalog()
    context['token_url'] = url
    context['user'] = request.user
    context['client_url'] = settings.API_CLIENT_URL

    if extra_context:
        context.update(extra_context)
    context_instance = get_context(request, context)
    return render_response(template_name,
                           context_instance=context_instance)


@require_http_methods(["GET", "POST"])
@required_auth_methods_assigned(allow_access=True)
@login_required
@cookie_fix
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
                    domain=settings.COOKIE_DOMAIN
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
    user_providers = request.user.get_enabled_auth_providers()
    user_disabled_providers = request.user.get_disabled_auth_providers()

    # providers that user can add
    user_available_providers = request.user.get_available_auth_providers()

    extra_context['services'] = Component.catalog().values()
    return render_response(template_name,
                           profile_form=form,
                           user_providers=user_providers,
                           user_disabled_providers=user_disabled_providers,
                           user_available_providers=user_available_providers,
                           context_instance=get_context(request,
                                                        extra_context))


@transaction.commit_manually
@require_http_methods(["GET", "POST"])
@cookie_fix
def signup(request, template_name='im/signup.html', on_success='index',
           extra_context=None, activation_backend=None):
    """
    Allows a user to create a local account.

    In case of GET request renders a form for entering the user information.
    In case of POST handles the signup.

    The user activation will be delegated to the backend specified by the
    ``activation_backend`` keyword argument if present, otherwise to the
    ``astakos.im.activation_backends.InvitationBackend`` if
    settings.ASTAKOS_INVITATIONS_ENABLED is True or
    ``astakos.im.activation_backends.SimpleBackend`` if not (see
    activation_backends);

    Upon successful user creation, if ``next`` url parameter is present the
    user is redirected there otherwise renders the same page with a success
    message.

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
        logger.info("%s already signed in, redirect to index",
                    request.user.log_display)
        transaction.rollback()
        return HttpResponseRedirect(reverse('index'))

    provider = get_query(request).get('provider', 'local')
    if not auth.get_provider(provider).get_create_policy:
        logger.error("%s provider not available for signup", provider)
        transaction.rollback()
        raise PermissionDenied

    instance = None

    # user registered using third party provider
    third_party_token = request.REQUEST.get('third_party_token', None)
    unverified = None
    if third_party_token:
        # retreive third party entry. This was created right after the initial
        # third party provider handshake.
        pending = get_object_or_404(PendingThirdPartyUser,
                                    token=third_party_token)

        provider = pending.provider

        # clone third party instance into the corresponding AstakosUser
        instance = pending.get_user_instance()
        get_unverified = AstakosUserAuthProvider.objects.unverified

        # check existing unverified entries
        unverified = get_unverified(pending.provider,
                                    identifier=pending.third_party_identifier)

        if unverified and request.method == 'GET':
            messages.warning(request, unverified.get_pending_registration_msg)
            if unverified.user.moderated:
                messages.warning(request,
                                 unverified.get_pending_resend_activation_msg)
            else:
                messages.warning(request,
                                 unverified.get_pending_moderation_msg)

    # prepare activation backend based on current request
    if not activation_backend:
        activation_backend = activation_backends.get_backend()

    form_kwargs = {'instance': instance}
    if third_party_token:
        form_kwargs['third_party_token'] = third_party_token

    form = activation_backend.get_signup_form(
        provider, None, **form_kwargs)

    if request.method == 'POST':
        form = activation_backend.get_signup_form(
            provider,
            request.POST,
            **form_kwargs)

        if form.is_valid():
            commited = False
            try:
                user = form.save(commit=False)

                # delete previously unverified accounts
                if AstakosUser.objects.user_exists(user.email):
                    AstakosUser.objects.get_by_identifier(user.email).delete()

                # store_user so that user auth providers get initialized
                form.store_user(user, request)
                result = activation_backend.handle_registration(user)
                if result.status == \
                        activation_backend.Result.PENDING_MODERATION:
                    # user should be warned that his account is not active yet
                    status = messages.WARNING
                else:
                    status = messages.SUCCESS
                message = result.message
                activation_backend.send_result_notifications(result, user)

                # commit user entry
                transaction.commit()
                # commited flag
                # in case an exception get raised from this point
                commited = True

                if user and user.is_active:
                    # activation backend directly activated the user
                    # log him in
                    next = request.POST.get('next', '')
                    response = prepare_response(request, user, next=next)
                    return response

                messages.add_message(request, status, message)
                return HttpResponseRedirect(reverse(on_success))
            except Exception, e:
                if not commited:
                    transaction.rollback()
                raise
    else:
        transaction.commit()

    return render_response(
        template_name,
        signup_form=form,
        third_party_token=third_party_token,
        provider=provider,
        context_instance=get_context(request, extra_context))


@require_http_methods(["GET", "POST"])
@required_auth_methods_assigned(allow_access=True)
@login_required
@cookie_fix
@signed_terms_required
def feedback(request, template_name='im/feedback.html',
             email_template_name='im/feedback_mail.txt', extra_context=None):
    """
    Allows a user to send feedback.

    In case of GET request renders a form for providing the feedback
    information.
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
            send_feedback(msg, data, request.user, email_template_name)
            message = _(astakos_messages.FEEDBACK_SENT)
            messages.success(request, message)
            return HttpResponseRedirect(reverse('feedback'))

    return render_response(template_name,
                           feedback_form=form,
                           context_instance=get_context(request,
                                                        extra_context))


@require_http_methods(["GET"])
@cookie_fix
def logout(request, template='registration/logged_out.html',
           extra_context=None):
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
        domain=settings.COOKIE_DOMAIN
    )

    if next:
        response['Location'] = next
        response.status_code = 302
    elif settings.LOGOUT_NEXT:
        response['Location'] = settings.LOGOUT_NEXT
        response.status_code = 301
    else:
        last_provider = request.COOKIES.get(
            'astakos_last_login_method', 'local')
        provider = auth.get_provider(last_provider)
        message = provider.get_logout_success_msg
        extra = provider.get_logout_success_extra_msg
        if extra:
            message += "<br />" + extra
        messages.success(request, message)
        response['Location'] = reverse('index')
        response.status_code = 301
    return response


@require_http_methods(["GET", "POST"])
@cookie_fix
@transaction.commit_manually
def activate(request, greeting_email_template_name='im/welcome_email.txt',
             helpdesk_email_template_name='im/helpdesk_notification.txt'):
    """
    Activates the user identified by the ``auth`` request parameter, sends a
    welcome email and renews the user token.

    The view uses commit_manually decorator in order to ensure the user state
    will be updated only if the email will be send successfully.
    """
    token = request.GET.get('auth')
    next = request.GET.get('next')

    if request.user.is_authenticated():
        message = _(astakos_messages.LOGGED_IN_WARNING)
        messages.error(request, message)
        transaction.rollback()
        return HttpResponseRedirect(reverse('index'))

    try:
        user = AstakosUser.objects.get(verification_code=token)
    except AstakosUser.DoesNotExist:
        transaction.rollback()
        raise Http404

    if user.email_verified:
        message = _(astakos_messages.ACCOUNT_ALREADY_VERIFIED)
        messages.error(request, message)
        return HttpResponseRedirect(reverse('index'))

    try:
        backend = activation_backends.get_backend()
        result = backend.handle_verification(user, token)
        backend.send_result_notifications(result, user)
        next = settings.ACTIVATION_REDIRECT_URL or next
        response = HttpResponseRedirect(reverse('index'))
        if user.is_active:
            response = prepare_response(request, user, next, renew=True)
            messages.success(request, _(result.message))
        else:
            messages.warning(request, _(result.message))
    except Exception:
        transaction.rollback()
        raise
    else:
        transaction.commit()
        return response


@require_http_methods(["GET", "POST"])
@cookie_fix
def approval_terms(request, term_id=None,
                   template_name='im/approval_terms.html', extra_context=None):
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
            template_name, context_instance=get_context(request,
                                                        extra_context))

    terms = f.read()

    if request.method == 'POST':
        next = restrict_next(
            request.POST.get('next'),
            domain=settings.COOKIE_DOMAIN
        )
        if not next:
            next = reverse('index')
        form = SignApprovalTermsForm(request.POST, instance=request.user)
        if not form.is_valid():
            return render_response(template_name,
                                   terms=terms,
                                   approval_terms_form=form,
                                   context_instance=get_context(request,
                                                                extra_context))
        user = form.save()
        return HttpResponseRedirect(next)
    else:
        form = None
        if request.user.is_authenticated() and not request.user.signed_terms:
            form = SignApprovalTermsForm(instance=request.user)
        return render_response(template_name,
                               terms=terms,
                               approval_terms_form=form,
                               context_instance=get_context(request,
                                                            extra_context))


@require_http_methods(["GET", "POST"])
@cookie_fix
@transaction.commit_manually
def change_email(request, activation_key=None,
                 email_template_name='registration/email_change_email.txt',
                 form_template_name='registration/email_change_form.html',
                 confirm_template_name='registration/email_change_done.html',
                 extra_context=None):
    extra_context = extra_context or {}

    if not settings.EMAILCHANGE_ENABLED:
        raise PermissionDenied

    if activation_key:
        try:
            try:
                email_change = EmailChange.objects.get(
                    activation_key=activation_key)
            except EmailChange.DoesNotExist:
                transaction.rollback()
                logger.error("[change-email] Invalid or used activation "
                             "code, %s", activation_key)
                raise Http404

            if (
                request.user.is_authenticated() and
                request.user == email_change.user or not
                request.user.is_authenticated()
            ):
                user = EmailChange.objects.change_email(activation_key)
                msg = _(astakos_messages.EMAIL_CHANGED)
                messages.success(request, msg)
                transaction.commit()
                return HttpResponseRedirect(reverse('edit_profile'))
            else:
                logger.error("[change-email] Access from invalid user, %s %s",
                             email_change.user, request.user.log_display)
                transaction.rollback()
                raise PermissionDenied
        except ValueError, e:
            messages.error(request, e)
            transaction.rollback()
            return HttpResponseRedirect(reverse('index'))

        return render_response(confirm_template_name,
                               modified_user=user if 'user' in locals()
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
            ec = form.save(request, email_template_name, request)
        except Exception, e:
            transaction.rollback()
            raise
        else:
            msg = _(astakos_messages.EMAIL_CHANGE_REGISTERED)
            messages.success(request, msg)
            transaction.commit()
            return HttpResponseRedirect(reverse('edit_profile'))

    if request.user.email_change_is_pending():
        messages.warning(request,
                         astakos_messages.PENDING_EMAIL_CHANGE_REQUEST)

    return render_response(
        form_template_name,
        form=form,
        context_instance=get_context(request, extra_context)
    )


@cookie_fix
def send_activation(request, user_id, template_name='im/login.html',
                    extra_context=None):

    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('index'))

    extra_context = extra_context or {}
    try:
        u = AstakosUser.objects.get(id=user_id)
    except AstakosUser.DoesNotExist:
        messages.error(request, _(astakos_messages.ACCOUNT_UNKNOWN))
    else:
        if u.email_verified:
            logger.warning("[resend activation] Account already verified: %s",
                           u.log_display)

            messages.error(request,
                           _(astakos_messages.ACCOUNT_ALREADY_VERIFIED))
        else:
            activation_backend = activation_backends.get_backend()
            activation_backend.send_user_verification_email(u)
            messages.success(request, astakos_messages.ACTIVATION_SENT)

    return HttpResponseRedirect(reverse('index'))


@require_http_methods(["GET"])
@cookie_fix
@valid_astakos_user_required
def resource_usage(request):

    resources_meta = presentation.RESOURCES

    current_usage = quotas.get_user_quotas(request.user)
    current_usage = json.dumps(current_usage['system'])
    resource_catalog, resource_groups = _resources_catalog(for_usage=True)
    if resource_catalog is False:
        # on fail resource_groups contains the result object
        result = resource_groups
        messages.error(request, 'Unable to retrieve system resources: %s' %
                       result.reason)

    resource_catalog = json.dumps(resource_catalog)
    resource_groups = json.dumps(resource_groups)
    resources_order = json.dumps(resources_meta.get('resources_order'))

    return render_response('im/resource_usage.html',
                           context_instance=get_context(request),
                           resource_catalog=resource_catalog,
                           resource_groups=resource_groups,
                           resources_order=resources_order,
                           current_usage=current_usage,
                           token_cookie_name=settings.COOKIE_NAME,
                           usage_update_interval=
                           settings.USAGE_UPDATE_INTERVAL)


# TODO: action only on POST and user should confirm the removal
@require_http_methods(["POST"])
@cookie_fix
@valid_astakos_user_required
def remove_auth_provider(request, pk):
    try:
        provider = request.user.auth_providers.get(pk=int(pk)).settings
    except AstakosUserAuthProvider.DoesNotExist:
        raise Http404

    if provider.get_remove_policy:
        messages.success(request, provider.get_removed_msg)
        provider.remove_from_user()
        return HttpResponseRedirect(reverse('edit_profile'))
    else:
        raise PermissionDenied


@require_http_methods(["GET"])
@required_auth_methods_assigned(allow_access=True)
@login_required
@cookie_fix
@signed_terms_required
def landing(request):
    context = {'services': Component.catalog(orderfor='dashboard')}
    return render_response(
        'im/landing.html',
        context_instance=get_context(request), **context)


@cookie_fix
def get_menu(request, with_extra_links=False, with_signout=True):
    user = request.user
    index_url = reverse('index')

    if isinstance(user, User) and user.is_authenticated():
        l = []
        append = l.append
        item = MenuItem
        item.current_path = request.build_absolute_uri(request.path)
        append(item(url=request.build_absolute_uri(reverse('index')),
                    name=user.email))
        if with_extra_links:
            append(item(url=request.build_absolute_uri(reverse('landing')),
                        name="Overview"))
        if with_signout:
            append(item(url=request.build_absolute_uri(reverse('landing')),
                        name="Dashboard"))
        if with_extra_links:
            append(
                item(
                    url=request.build_absolute_uri(reverse('edit_profile')),
                    name="Profile"))

        if with_extra_links:
            if settings.INVITATIONS_ENABLED:
                append(item(url=request.build_absolute_uri(reverse('invite')),
                            name="Invitations"))

            append(item(url=request.build_absolute_uri(reverse('api_access')),
                        name="API access"))

            append(
                item(
                    url=request.build_absolute_uri(reverse('resource_usage')),
                    name="Usage"))

            if settings.PROJECTS_VISIBLE:
                append(
                    item(
                        url=request.build_absolute_uri(
                            reverse('project_list')),
                        name="Projects"))

            append(item(url=request.build_absolute_uri(reverse('feedback')),
                        name="Contact"))
        if with_signout:
            append(item(url=request.build_absolute_uri(reverse('logout')),
                        name="Sign out"))
    else:
        l = [{'url': request.build_absolute_uri(index_url),
              'name': _("Sign in")}]

    callback = request.GET.get('callback', None)
    data = json.dumps(tuple(l))
    mimetype = 'application/json'

    if callback:
        mimetype = 'application/javascript'
        data = '%s(%s)' % (callback, data)

    return HttpResponse(content=data, mimetype=mimetype)


class MenuItem(dict):
    current_path = ''

    def __init__(self, *args, **kwargs):
        super(MenuItem, self).__init__(*args, **kwargs)
        if kwargs.get('url') or kwargs.get('submenu'):
            self.__set_is_active__()

    def __setitem__(self, key, value):
        super(MenuItem, self).__setitem__(key, value)
        if key in ('url', 'submenu'):
            self.__set_is_active__()

    def __set_is_active__(self):
        if self.get('is_active'):
            return
        if self.current_path.startswith(self.get('url')):
            self.__setitem__('is_active', True)
        else:
            submenu = self.get('submenu', ())
            current = (i for i in submenu if i.get('url') == self.current_path)
            try:
                current_node = current.next()
                if not current_node.get('is_active'):
                    current_node.__setitem__('is_active', True)
                self.__setitem__('is_active', True)
            except StopIteration:
                return

    def __setattribute__(self, name, value):
        super(MenuItem, self).__setattribute__(name, value)
        if name == 'current_path':
            self.__set_is_active__()


def get_services(request):
    callback = request.GET.get('callback', None)
    mimetype = 'application/json'
    data = json.dumps(Component.catalog().values())

    if callback:
        # Consume session messages. When get_services is loaded from an astakos
        # page, messages should have already been consumed in the html
        # response. When get_services is loaded from another domain/service we
        # consume them here so that no stale messages to appear if user visits
        # an astakos view later on.
        # TODO: messages could be served to other services/sites in the dict
        # response of get_services and/or get_menu. Services could handle those
        # messages respectively.
        messages_list = list(messages.get_messages(request))
        mimetype = 'application/javascript'
        data = '%s(%s)' % (callback, data)

    return HttpResponse(content=data, mimetype=mimetype)
