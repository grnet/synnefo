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
from datetime import datetime, timedelta
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import password_change
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.db.utils import IntegrityError
from django.forms.fields import URLField
from django.http import (HttpResponse, HttpResponseBadRequest,
                         HttpResponseForbidden, HttpResponseRedirect,
                         HttpResponseBadRequest, Http404)
from django.shortcuts import redirect
from django.template import RequestContext, loader as template_loader
from django.utils.http import urlencode
from django.utils.translation import ugettext as _
from django.views.generic.create_update import (create_object, delete_object,
                                                get_model_and_form_class)
from django.views.generic.list_detail import object_list, object_detail
from django.http import HttpResponseBadRequest
from django.core.xheaders import populate_xheaders

from astakos.im.models import (AstakosUser, ApprovalTerms, AstakosGroup,
                               Resource, EmailChange, GroupKind, Membership,
                               AstakosGroupQuota, RESOURCE_SEPARATOR)
from django.views.decorators.http import require_http_methods

from astakos.im.activation_backends import get_backend, SimpleBackend
from astakos.im.util import get_context, prepare_response, set_cookie, get_query
from astakos.im.forms import (LoginForm, InvitationForm, ProfileForm,
                              FeedbackForm, SignApprovalTermsForm,
                              ExtendedPasswordChangeForm, EmailChangeForm,
                              AstakosGroupCreationForm, AstakosGroupSearchForm,
                              AstakosGroupUpdateForm, AddGroupMembersForm,
                              AstakosGroupSortForm, MembersSortForm,
                              TimelineForm, PickResourceForm,
                              AstakosGroupCreationSummaryForm)
from astakos.im.functions import (send_feedback, SendMailError,
                                  logout as auth_logout,
                                  activate as activate_func,
                                  switch_account_to_shibboleth,
                                  send_group_creation_notification,
                                  SendNotificationError)
from astakos.im.endpoints.quotaholder import timeline_charge
from astakos.im.settings import (COOKIE_NAME, COOKIE_DOMAIN, LOGOUT_NEXT,
                                 LOGGING_LEVEL, PAGINATE_BY)
from astakos.im.tasks import request_billing
from astakos.im.api.callpoint import AstakosCallpoint

import astakos.im.messages as astakos_messages

logger = logging.getLogger(__name__)


DB_REPLACE_GROUP_SCHEME = """REPLACE(REPLACE("auth_group".name, 'http://', ''),
                                     'https://', '')"""

callpoint = AstakosCallpoint()

def render_response(template, tab=None, status=200, reset_cookie=False,
                    context_instance=None, **kwargs):
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
        if request.user.is_authenticated() and not request.user.signed_terms:
            params = urlencode({'next': request.build_absolute_uri(),
                                'show_form': ''})
            terms_uri = reverse('latest_terms') + '?' + params
            return HttpResponseRedirect(terms_uri)
        return func(request, *args, **kwargs)
    return wrapper


@require_http_methods(["GET", "POST"])
@signed_terms_required
def index(request, login_template_name='im/login.html', extra_context=None):
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
                           login_form=LoginForm(request=request),
                           context_instance=get_context(request, extra_context))


@require_http_methods(["GET", "POST"])
@login_required
@signed_terms_required
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
    * ASTAKOS_DEFAULT_CONTACT_EMAIL: service support email
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
                    email = form.cleaned_data.get('username')
                    realname = form.cleaned_data.get('realname')
                    inviter.invite(email, realname)
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
                msg = _(astakos_messages.PROFILE_UPDATED)
                messages.success(request, msg)
            except ValueError, ve:
                messages.success(request, ve)
    elif request.method == "GET":
        if not request.user.is_verified:
            request.user.is_verified = True
            request.user.save()
    return render_response(template_name,
                           reset_cookie=reset_cookie,
                           profile_form=form,
                           context_instance=get_context(request,
                                                        extra_context))


@transaction.commit_manually
@require_http_methods(["GET", "POST"])
def signup(request, template_name='im/signup.html', on_success='im/signup_complete.html', extra_context=None, backend=None):
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
                        msg = 'Additional email: %s saved for user %s.' % (
                            additional_email, user.email)
                        logger.log(LOGGING_LEVEL, msg)
                if user and user.is_active:
                    next = request.POST.get('next', '')
                    response = prepare_response(request, user, next=next)
                    transaction.commit()
                    return response
                messages.add_message(request, status, message)
                transaction.commit()
                return render_response(on_success,
                                       context_instance=get_context(request, extra_context))
            except SendMailError, e:
                message = e.message
                messages.error(request, message)
                transaction.rollback()
            except BaseException, e:
                message = _(astakos_messages.GENERIC_ERROR)
                messages.error(request, message)
                logger.exception(e)
                transaction.rollback()
    return render_response(template_name,
                           signup_form=form,
                           provider=provider,
                           context_instance=get_context(request, extra_context))


@require_http_methods(["GET", "POST"])
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
                messages.error(request, message)
            else:
                message = _(astakos_messages.FEEDBACK_SENT)
                messages.success(request, message)
    return render_response(template_name,
                           feedback_form=form,
                           context_instance=get_context(request, extra_context))


@require_http_methods(["GET", "POST"])
@signed_terms_required
def logout(request, template='registration/logged_out.html', extra_context=None):
    """
    Wraps `django.contrib.auth.logout` and delete the cookie.
    """
    response = HttpResponse()
    if request.user.is_authenticated():
        email = request.user.email
        auth_logout(request)
        response.delete_cookie(COOKIE_NAME, path='/', domain=COOKIE_DOMAIN)
        msg = 'Cookie deleted for %s' % email
        logger.log(LOGGING_LEVEL, msg)
    next = request.GET.get('next')
    if next:
        response['Location'] = next
        response.status_code = 302
        return response
    elif LOGOUT_NEXT:
        response['Location'] = LOGOUT_NEXT
        response.status_code = 301
        return response
    messages.success(request, _(astakos_messages.LOGOUT_SUCCESS))
    context = get_context(request, extra_context)
    response.write(
        template_loader.render_to_string(template, context_instance=context))
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
        local_user = AstakosUser.objects.get(
            ~Q(id=user.id),
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
            message = _(astakos_messages.GENERIC_ERROR)
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
            message = _(astakos_messages.GENERIC_ERROR)
            messages.error(request, message)
            logger.exception(e)
            transaction.rollback()
            return index(request)


@require_http_methods(["GET", "POST"])
def approval_terms(request, term_id=None, template_name='im/approval_terms.html', extra_context=None):
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
    f = open(term.location, 'r')
    terms = f.read()

    if request.method == 'POST':
        next = request.POST.get('next')
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
@signed_terms_required
def change_password(request):
    return password_change(request,
                           post_change_redirect=reverse('edit_profile'),
                           password_change_form=ExtendedPasswordChangeForm)


@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
@transaction.commit_manually
def change_email(request, activation_key=None,
                 email_template_name='registration/email_change_email.txt',
                 form_template_name='registration/email_change_form.html',
                 confirm_template_name='registration/email_change_done.html',
                 extra_context=None):
    if activation_key:
        try:
            user = EmailChange.objects.change_email(activation_key)
            if request.user.is_authenticated() and request.user == user:
                msg = _(astakos_messages.EMAIL_CHANGED)
                messages.success(request, msg)
                auth_logout(request)
                response = prepare_response(request, user)
                transaction.commit()
                return response
        except ValueError, e:
            messages.error(request, e)
        return render_response(confirm_template_name,
                               modified_user=user if 'user' in locals(
                               ) else None,
                               context_instance=get_context(request,
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
            msg = _(astakos_messages.PENDING_EMAIL_CHANGE_REQUEST)
            messages.error(request, msg)
        else:
            msg = _(astakos_messages.EMAIL_CHANGE_REGISTERED)
            messages.success(request, msg)
            transaction.commit()
    return render_response(form_template_name,
                           form=form,
                           context_instance=get_context(request,
                                                        extra_context))



resource_presentation = {
       'compute': {
            'help_text':'group compute help text',
            'is_abbreviation':False,
            'report_desc':''
        },
        'storage': {
            'help_text':'group storage help text',
            'is_abbreviation':False,
            'report_desc':''
        },
        'pithos+.diskspace': {
            'help_text':'resource pithos+.diskspace help text',
            'is_abbreviation':False,
            'report_desc':'Pithos+ Diskspace',
            'placeholder':'eg. 10GB'
        },
        'cyclades.vm': {
            'help_text':'resource cyclades.vm help text resource cyclades.vm help text resource cyclades.vm help text resource cyclades.vm help text',
            'is_abbreviation':True,
            'report_desc':'Virtual Machines',
            'placeholder':'eg. 2'
        },
        'cyclades.disksize': {
            'help_text':'resource cyclades.disksize help text',
            'is_abbreviation':False,
            'report_desc':'Disksize',
            'placeholder':'eg. 5GB'
        },
        'cyclades.disk': {
            'help_text':'resource cyclades.disk help text',
            'is_abbreviation':False,
            'report_desc':'Disk',
            'placeholder':'eg. 5GB'    
        },
        'cyclades.ram': {
            'help_text':'resource cyclades.ram help text',
            'is_abbreviation':True,
            'report_desc':'RAM',
            'placeholder':'eg. 4GB'
        },
        'cyclades.cpu': {
            'help_text':'resource cyclades.cpu help text',
            'is_abbreviation':True,
            'report_desc':'CPUs',
            'placeholder':'eg. 1'
        },
        'cyclades.network.private': {
            'help_text':'resource cyclades.network.private help text',
            'is_abbreviation':False,
            'report_desc':'Network',
            'placeholder':'eg. 1'
        }
    }

@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def group_add(request, kind_name='default'):
    result = callpoint.list_resources()
    resource_catalog = {'resources':defaultdict(defaultdict),
                        'groups':defaultdict(list)}
    if result.is_success:
        for r in result.data:
            service = r.get('service', '')
            name = r.get('name', '')
            group = r.get('group', '')
            unit = r.get('unit', '')
            fullname = '%s%s%s' % (service, RESOURCE_SEPARATOR, name)
            resource_catalog['resources'][fullname] = dict(unit=unit)
            resource_catalog['groups'][group].append(fullname)
        
        resource_catalog = dict(resource_catalog)
        for k, v in resource_catalog.iteritems():
            resource_catalog[k] = dict(v)
    else:
        messages.error(
            request,
            'Unable to retrieve system resources: %s' % result.reason
    )
    
    try:
        kind = GroupKind.objects.get(name=kind_name)
    except:
        return HttpResponseBadRequest(_(astakos_messages.GROUPKIND_UNKNOWN))
    
    

    post_save_redirect = '/im/group/%(id)s/'
    context_processors = None
    model, form_class = get_model_and_form_class(
        model=None,
        form_class=AstakosGroupCreationForm
    )
    
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            return render_response(
                template='im/astakosgroup_form_summary.html',
                context_instance=get_context(request),
                form = AstakosGroupCreationSummaryForm(form.cleaned_data),
                policies = form.policies(),
                resource_catalog=resource_catalog,
                resource_presentation=resource_presentation
            )
    else:
        now = datetime.now()
        data = {
            'kind': kind
        }
        form = form_class(data)

    # Create the template, context, response
    template_name = "%s/%s_form.html" % (
        model._meta.app_label,
        model._meta.object_name.lower()
    )
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        'form': form,
        'kind': kind,
        'resource_catalog':resource_catalog,
        'resource_presentation':resource_presentation,
    }, context_processors)
    return HttpResponse(t.render(c))


#@require_http_methods(["POST"])
@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def group_add_complete(request):
    model = AstakosGroup
    form = AstakosGroupCreationSummaryForm(request.POST)
    if form.is_valid():
        d = form.cleaned_data
        d['owners'] = [request.user]
        result = callpoint.create_groups((d,)).next()
        if result.is_success:
            new_object = result.data[0]
            msg = _(astakos_messages.OBJECT_CREATED) %\
                {"verbose_name": model._meta.verbose_name}
            messages.success(request, msg, fail_silently=True)
            
            # send notification
            try:
                send_group_creation_notification(
                    template_name='im/group_creation_notification.txt',
                    dictionary={
                        'group': new_object,
                        'owner': request.user,
                        'policies': d.get('policies', [])
                    }
                )
            except SendNotificationError, e:
                messages.error(request, e, fail_silently=True)
            post_save_redirect = '/im/group/%(id)s/'
            return HttpResponseRedirect(post_save_redirect % new_object)
        else:
            msg = _(astakos_messages.OBJECT_CREATED_FAILED) %\
                {"verbose_name": model._meta.verbose_name,
                 "reason":result.reason}
            messages.error(request, msg, fail_silently=True)
    return render_response(
        template='im/astakosgroup_form_summary.html',
        context_instance=get_context(request),
        form=form)


#@require_http_methods(["GET"])
@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def group_list(request):
    none = request.user.astakos_groups.none()
    q = AstakosGroup.objects.raw("""
        SELECT auth_group.id,
        %s AS groupname,
        im_groupkind.name AS kindname,
        im_astakosgroup.*,
        owner.email AS groupowner,
        (SELECT COUNT(*) FROM im_membership
            WHERE group_id = im_astakosgroup.group_ptr_id
            AND date_joined IS NOT NULL) AS approved_members_num,
        (SELECT CASE WHEN(
                    SELECT date_joined FROM im_membership
                    WHERE group_id = im_astakosgroup.group_ptr_id
                    AND person_id = %s) IS NULL
                    THEN 0 ELSE 1 END) AS membership_status
        FROM im_astakosgroup
        INNER JOIN im_membership ON (
            im_astakosgroup.group_ptr_id = im_membership.group_id)
        INNER JOIN auth_group ON(im_astakosgroup.group_ptr_id = auth_group.id)
        INNER JOIN im_groupkind ON (im_astakosgroup.kind_id = im_groupkind.id)
        LEFT JOIN im_astakosuser_owner ON (
            im_astakosuser_owner.astakosgroup_id = im_astakosgroup.group_ptr_id)
        LEFT JOIN auth_user as owner ON (
            im_astakosuser_owner.astakosuser_id = owner.id)
        WHERE im_membership.person_id = %s
        """ % (DB_REPLACE_GROUP_SCHEME, request.user.id, request.user.id))
    d = defaultdict(list)
    
    for g in q:
        if request.user.email == g.groupowner:
            d['own'].append(g)
        else:
            d['other'].append(g)
    
    for g in q:
        d['all'].append(g)
    
    # validate sorting
    fields = ('own', 'other', 'all')
    for f in fields:
        v = globals()['%s_sorting' % f] = request.GET.get('%s_sorting' % f)
        if v:
            form = AstakosGroupSortForm({'sort_by': v})
            if not form.is_valid():
                globals()['%s_sorting' % f] = form.cleaned_data.get('sort_by')
    return object_list(request, queryset=none,
                       extra_context={'is_search': False,
                                      'all': d['all'],
                                      'mine': d['own'],
                                      'other': d['other'],
                                      'own_sorting': own_sorting,
                                      'other_sorting': other_sorting,
                                      'all_sorting': all_sorting,
                                      'own_page': request.GET.get('own_page', 1),
                                      'other_page': request.GET.get('other_page', 1),
                                      'all_page': request.GET.get('all_page', 1)
                                      })


@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def group_detail(request, group_id):
    q = AstakosGroup.objects.select_related().filter(pk=group_id)
    q = q.extra(select={
        'is_member': """SELECT CASE WHEN EXISTS(
                            SELECT id FROM im_membership
                            WHERE group_id = im_astakosgroup.group_ptr_id
                            AND person_id = %s)
                        THEN 1 ELSE 0 END""" % request.user.id,
        'is_owner': """SELECT CASE WHEN EXISTS(
                        SELECT id FROM im_astakosuser_owner
                        WHERE astakosgroup_id = im_astakosgroup.group_ptr_id
                        AND astakosuser_id = %s)
                        THEN 1 ELSE 0 END""" % request.user.id,
        'kindname': """SELECT name FROM im_groupkind
                       WHERE id = im_astakosgroup.kind_id"""})

    model = q.model
    context_processors = None
    mimetype = None
    try:
        obj = q.get()
    except AstakosGroup.DoesNotExist:
        raise Http404("No %s found matching the query" % (
            model._meta.verbose_name))

    update_form = AstakosGroupUpdateForm(instance=obj)
    addmembers_form = AddGroupMembersForm()
    if request.method == 'POST':
        update_data = {}
        addmembers_data = {}
        for k, v in request.POST.iteritems():
            if k in update_form.fields:
                update_data[k] = v
            if k in addmembers_form.fields:
                addmembers_data[k] = v
        update_data = update_data or None
        addmembers_data = addmembers_data or None
        update_form = AstakosGroupUpdateForm(update_data, instance=obj)
        addmembers_form = AddGroupMembersForm(addmembers_data)
        if update_form.is_valid():
            update_form.save()
        if addmembers_form.is_valid():
            try:
                map(obj.approve_member, addmembers_form.valid_users)
            except AssertionError:
                msg = _(astakos_messages.GROUP_MAX_PARTICIPANT_NUMBER_REACHED)
                messages.error(request, msg)
            addmembers_form = AddGroupMembersForm()

    template_name = "%s/%s_detail.html" % (
        model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        'object': obj,
    }, context_processors)

    # validate sorting
    sorting = request.GET.get('sorting')
    if sorting:
        form = MembersSortForm({'sort_by': sorting})
        if form.is_valid():
            sorting = form.cleaned_data.get('sort_by')

    extra_context = {'update_form': update_form,
                     'addmembers_form': addmembers_form,
                     'page': request.GET.get('page', 1),
                     'sorting': sorting}
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    response = HttpResponse(t.render(c), mimetype=mimetype)
    populate_xheaders(
        request, response, model, getattr(obj, obj._meta.pk.name))
    return response


@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def group_search(request, extra_context=None, **kwargs):
    q = request.GET.get('q')
    sorting = request.GET.get('sorting')
    if request.method == 'GET':
        form = AstakosGroupSearchForm({'q': q} if q else None)
    else:
        form = AstakosGroupSearchForm(get_query(request))
        if form.is_valid():
            q = form.cleaned_data['q'].strip()
    if q:
        queryset = AstakosGroup.objects.select_related()
        queryset = queryset.filter(name__contains=q)
        queryset = queryset.filter(approval_date__isnull=False)
        queryset = queryset.extra(select={
                                  'groupname': DB_REPLACE_GROUP_SCHEME,
                                  'kindname': "im_groupkind.name",
                                  'approved_members_num': """
                    SELECT COUNT(*) FROM im_membership
                    WHERE group_id = im_astakosgroup.group_ptr_id
                    AND date_joined IS NOT NULL""",
                                  'membership_approval_date': """
                    SELECT date_joined FROM im_membership
                    WHERE group_id = im_astakosgroup.group_ptr_id
                    AND person_id = %s""" % request.user.id,
                                  'is_member': """
                    SELECT CASE WHEN EXISTS(
                    SELECT date_joined FROM im_membership
                    WHERE group_id = im_astakosgroup.group_ptr_id
                    AND person_id = %s)
                    THEN 1 ELSE 0 END""" % request.user.id,
                                  'is_owner': """
                    SELECT CASE WHEN EXISTS(
                    SELECT id FROM im_astakosuser_owner
                    WHERE astakosgroup_id = im_astakosgroup.group_ptr_id
                    AND astakosuser_id = %s)
                    THEN 1 ELSE 0 END""" % request.user.id})
        if sorting:
            # TODO check sorting value
            queryset = queryset.order_by(sorting)
    else:
        queryset = AstakosGroup.objects.none()
    return object_list(
        request,
        queryset,
        paginate_by=PAGINATE_BY,
        page=request.GET.get('page') or 1,
        template_name='im/astakosgroup_list.html',
        extra_context=dict(form=form,
                           is_search=True,
                           q=q,
                           sorting=sorting))


@require_http_methods(["GET", "POST"])
@signed_terms_required
@login_required
def group_all(request, extra_context=None, **kwargs):
    q = AstakosGroup.objects.select_related()
    q = q.filter(approval_date__isnull=False)
    q = q.extra(select={
                'groupname': DB_REPLACE_GROUP_SCHEME,
                'kindname': "im_groupkind.name",
                'approved_members_num': """
                    SELECT COUNT(*) FROM im_membership
                    WHERE group_id = im_astakosgroup.group_ptr_id
                    AND date_joined IS NOT NULL""",
                'membership_approval_date': """
                    SELECT date_joined FROM im_membership
                    WHERE group_id = im_astakosgroup.group_ptr_id
                    AND person_id = %s""" % request.user.id,
                'is_member': """
                    SELECT CASE WHEN EXISTS(
                    SELECT date_joined FROM im_membership
                    WHERE group_id = im_astakosgroup.group_ptr_id
                    AND person_id = %s)
                    THEN 1 ELSE 0 END""" % request.user.id})
    sorting = request.GET.get('sorting')
    if sorting:
        # TODO check sorting value
        q = q.order_by(sorting)
    return object_list(
        request,
        q,
        paginate_by=PAGINATE_BY,
        page=request.GET.get('page') or 1,
        template_name='im/astakosgroup_list.html',
        extra_context=dict(form=AstakosGroupSearchForm(),
                           is_search=True,
                           sorting=sorting))


#@require_http_methods(["POST"])
@require_http_methods(["POST", "GET"])
@signed_terms_required
@login_required
def group_join(request, group_id):
    m = Membership(group_id=group_id,
                   person=request.user,
                   date_requested=datetime.now())
    try:
        m.save()
        post_save_redirect = reverse(
            'group_detail',
            kwargs=dict(group_id=group_id))
        return HttpResponseRedirect(post_save_redirect)
    except IntegrityError, e:
        logger.exception(e)
        msg = _(astakos_messages.GROUP_JOIN_FAILURE)
        messages.error(request, msg)
        return group_search(request)


@require_http_methods(["POST"])
@signed_terms_required
@login_required
def group_leave(request, group_id):
    try:
        m = Membership.objects.select_related().get(
            group__id=group_id,
            person=request.user)
    except Membership.DoesNotExist:
        return HttpResponseBadRequest(_(astakos_messages.NOT_A_MEMBER))
    if request.user in m.group.owner.all():
        return HttpResponseForbidden(_(astakos_messages.OWNER_CANNOT_LEAVE_GROUP))
    return delete_object(
        request,
        model=Membership,
        object_id=m.id,
        template_name='im/astakosgroup_list.html',
        post_delete_redirect=reverse(
            'group_detail',
            kwargs=dict(group_id=group_id)))


def handle_membership(func):
    @wraps(func)
    def wrapper(request, group_id, user_id):
        try:
            m = Membership.objects.select_related().get(
                group__id=group_id,
                person__id=user_id)
        except Membership.DoesNotExist:
            return HttpResponseBadRequest(_(astakos_messages.NOT_MEMBER))
        else:
            if request.user not in m.group.owner.all():
                return HttpResponseForbidden(_(astakos_messages.NOT_OWNER))
            func(request, m)
            return group_detail(request, group_id)
    return wrapper


#@require_http_methods(["POST"])
@require_http_methods(["POST", "GET"])
@signed_terms_required
@login_required
@handle_membership
def approve_member(request, membership):
    try:
        membership.approve()
        realname = membership.person.realname
        msg = _(astakos_messages.MEMBER_JOINED_GROUP) % locals()
        messages.success(request, msg)
    except AssertionError:
        msg = _(astakos_messages.GROUP_MAX_PARTICIPANT_NUMBER_REACHED)
        messages.error(request, msg)
    except BaseException, e:
        logger.exception(e)
        realname = membership.person.realname
        msg = _(astakos_messages.GENERIC_ERROR)
        messages.error(request, msg)


@signed_terms_required
@login_required
@handle_membership
def disapprove_member(request, membership):
    try:
        membership.disapprove()
        realname = membership.person.realname
        msg = MEMBER_REMOVED % realname
        messages.success(request, msg)
    except BaseException, e:
        logger.exception(e)
        msg = _(astakos_messages.GENERIC_ERROR)
        messages.error(request, msg)


#@require_http_methods(["GET"])
@require_http_methods(["POST", "GET"])
@signed_terms_required
@login_required
def resource_list(request):
#     if request.method == 'POST':
#         form = PickResourceForm(request.POST)
#         if form.is_valid():
#             r = form.cleaned_data.get('resource')
#             if r:
#                 groups = request.user.membership_set.only('group').filter(
#                     date_joined__isnull=False)
#                 groups = [g.group_id for g in groups]
#                 q = AstakosGroupQuota.objects.select_related().filter(
#                     resource=r, group__in=groups)
#     else:
#         form = PickResourceForm()
#         q = AstakosGroupQuota.objects.none()
#
#     return object_list(request, q,
#                        template_name='im/astakosuserquota_list.html',
#                        extra_context={'form': form, 'data':data})

    def with_class(entry):
        entry['load_class'] = 'red'
        max_value = float(entry['maxValue'])
        curr_value = float(entry['currValue'])
        if max_value > 0 :
           entry['ratio'] = (curr_value / max_value) * 100
        else: 
           entry['ratio'] = 0 
        if entry['ratio'] < 66:
            entry['load_class'] = 'yellow'
        if entry['ratio'] < 33:
            entry['load_class'] = 'green'
        return entry

    def pluralize(entry):
        entry['plural'] = engine.plural(entry.get('name'))
        return entry

    result = callpoint.get_user_status(request.user.id)
    if result.is_success:
        backenddata = map(with_class, result.data)
        data = map(pluralize, result.data)
    else:
        data = None
        messages.error(request, result.reason)
    return render_response('im/resource_list.html',
                           data=data,
                           resource_presentation=resource_presentation,
                           context_instance=get_context(request))


def group_create_list(request):
    form = PickResourceForm()
    return render_response(
        template='im/astakosgroup_create_list.html',
        context_instance=get_context(request),)


#@require_http_methods(["GET"])
@require_http_methods(["POST", "GET"])
@signed_terms_required
@login_required
def billing(request):

    today = datetime.today()
    month_last_day = calendar.monthrange(today.year, today.month)[1]
    data['resources'] = map(with_class, data['resources'])
    start = request.POST.get('datefrom', None)
    if start:
        today = datetime.fromtimestamp(int(start))
        month_last_day = calendar.monthrange(today.year, today.month)[1]

    start = datetime(today.year, today.month, 1).strftime("%s")
    end = datetime(today.year, today.month, month_last_day).strftime("%s")
    r = request_billing.apply(args=('pgerakios@grnet.gr',
                                    int(start) * 1000,
                                    int(end) * 1000))
    data = {}

    try:
        status, data = r.result
        data = _clear_billing_data(data)
        if status != 200:
            messages.error(request, _(astakos_messages.BILLING_ERROR) % status)
    except:
        messages.error(request, r.result)

    print type(start)

    return render_response(
        template='im/billing.html',
        context_instance=get_context(request),
        data=data,
        zerodate=datetime(month=1, year=1970, day=1),
        today=today,
        start=int(start),
        month_last_day=month_last_day)


def _clear_billing_data(data):

    # remove addcredits entries
    def isnotcredit(e):
        return e['serviceName'] != "addcredits"

    # separate services
    def servicefilter(service_name):
        service = service_name

        def fltr(e):
            return e['serviceName'] == service
        return fltr

    data['bill_nocredits'] = filter(isnotcredit, data['bill'])
    data['bill_vmtime'] = filter(servicefilter('vmtime'), data['bill'])
    data['bill_diskspace'] = filter(servicefilter('diskspace'), data['bill'])
    data['bill_addcredits'] = filter(servicefilter('addcredits'), data['bill'])

    return data
     
     
#@require_http_methods(["GET"])
@require_http_methods(["POST", "GET"])
@signed_terms_required
@login_required
def timeline(request):
#    data = {'entity':request.user.email}
    timeline_body = ()
    timeline_header = ()
#    form = TimelineForm(data)
    form = TimelineForm()
    if request.method == 'POST':
        data = request.POST
        form = TimelineForm(data)
        if form.is_valid():
            data = form.cleaned_data
            timeline_header = ('entity', 'resource',
                               'event name', 'event date',
                               'incremental cost', 'total cost')
            timeline_body = timeline_charge(
                data['entity'], data['resource'],
                data['start_date'], data['end_date'],
                data['details'], data['operation'])

    return render_response(template='im/timeline.html',
                           context_instance=get_context(request),
                           form=form,
                           timeline_header=timeline_header,
                           timeline_body=timeline_body)
    return data
