# Copyright (C) 2010-2014 GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import re
import synnefo.util.date as date_util

from random import random
from datetime import datetime

from django import forms
from django.utils.translation import ugettext as _
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, \
    PasswordResetForm, PasswordChangeForm, SetPasswordForm
from django.core.mail import send_mail, get_connection
from django.contrib.auth.tokens import default_token_generator
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_str
from astakos.im import transaction
from django.core import validators

from synnefo.util import units
from synnefo_branding.utils import render_to_string
from synnefo.lib import join_urls
from astakos.im.fields import EmailField, InfiniteChoiceField
from astakos.im.models import AstakosUser, EmailChange, Invitation, Resource, \
    PendingThirdPartyUser, get_latest_terms, ProjectApplication, Project
from astakos.im import presentation
from astakos.im.widgets import DummyWidget, RecaptchaWidget
from astakos.im.functions import submit_application, \
    accept_membership_project_checks, ProjectError
from astakos.im.user_utils import send_change_email

from astakos.im.util import reserved_verified_email, model_to_dict
from astakos.im import auth_providers
from astakos.im import settings
from astakos.im import auth

import astakos.im.messages as astakos_messages

import logging
import hashlib
import recaptcha.client.captcha as captcha
import re

logger = logging.getLogger(__name__)

BASE_PROJECT_NAME_REGEX = re.compile(
    r'^system:[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-'
     '[a-f0-9]{12}$')
DOMAIN_VALUE_REGEX = re.compile(
    r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$',
    re.IGNORECASE)

READ_ONLY_FIELD_MSG = ("This value is provided by your authentication provider"
                       " and cannot be changed.")

class LocalUserCreationForm(UserCreationForm):
    """
    Extends the built in UserCreationForm in several ways:

    * Adds email, first_name, last_name, recaptcha_challenge_field,
    * recaptcha_response_field field.
    * The username field isn't visible and it is assigned a generated id.
    * User created is not active.
    """
    recaptcha_challenge_field = forms.CharField(widget=DummyWidget)
    recaptcha_response_field = forms.CharField(
        widget=RecaptchaWidget, label='')
    email = EmailField()

    class Meta:
        model = AstakosUser
        fields = ("email", "first_name", "last_name",
                  "has_signed_terms", "has_signed_terms")

    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """
        request = kwargs.pop('request', None)
        provider = kwargs.pop('provider', 'local')

        # we only use LocalUserCreationForm for local provider
        if not provider == 'local':
            raise Exception('Invalid provider')

        self.ip = None
        if request:
            self.ip = request.META.get('REMOTE_ADDR',
                                       request.META.get('HTTP_X_REAL_IP',
                                                        None))

        super(LocalUserCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['email', 'first_name', 'last_name',
                                'password1', 'password2']

        if settings.RECAPTCHA_ENABLED:
            self.fields.keyOrder.extend(['recaptcha_challenge_field',
                                         'recaptcha_response_field', ])
        if get_latest_terms():
            self.fields.keyOrder.append('has_signed_terms')

        if 'has_signed_terms' in self.fields:
            # Overriding field label since we need to apply a link
            # to the terms within the label
            terms_link_html = '<a href="%s" target="_blank">%s</a>' \
                % (reverse('latest_terms'), _("the terms"))
            self.fields['has_signed_terms'].label = \
                mark_safe("I agree with %s" % terms_link_html)

    def clean_email(self):
        email = self.cleaned_data['email']
        if not email:
            raise forms.ValidationError(_(astakos_messages.REQUIRED_FIELD))
        if reserved_verified_email(email):
            raise forms.ValidationError(_(astakos_messages.EMAIL_USED))
        return email

    def clean_has_signed_terms(self):
        has_signed_terms = self.cleaned_data['has_signed_terms']
        if not has_signed_terms:
            raise forms.ValidationError(_(astakos_messages.SIGN_TERMS))
        return has_signed_terms

    def clean_recaptcha_response_field(self):
        if 'recaptcha_challenge_field' in self.cleaned_data:
            self.validate_captcha()
        return self.cleaned_data['recaptcha_response_field']

    def clean_recaptcha_challenge_field(self):
        if 'recaptcha_response_field' in self.cleaned_data:
            self.validate_captcha()
        return self.cleaned_data['recaptcha_challenge_field']

    def validate_captcha(self):
        rcf = self.cleaned_data['recaptcha_challenge_field']
        rrf = self.cleaned_data['recaptcha_response_field']
        check = captcha.submit(
            rcf, rrf, settings.RECAPTCHA_PRIVATE_KEY, self.ip)
        if not check.is_valid:
            raise forms.ValidationError(_(
                astakos_messages.CAPTCHA_VALIDATION_ERR))

    def create_user(self):
        try:
            data = self.cleaned_data
        except AttributeError:
            self.is_valid()
            data = self.cleaned_data

        user = auth.make_local_user(
            email=data['email'], password=data['password1'],
            first_name=data['first_name'], last_name=data['last_name'],
            has_signed_terms=True)
        return user


class ThirdPartyUserCreationForm(forms.ModelForm):
    email = EmailField(
        label='Contact email',
        help_text='This is needed for contact purposes. '
        'It doesn&#39;t need to be the same with the one you '
        'provided to login previously. '
    )

    ro_fields = []

    class Meta:
        model = AstakosUser
        fields = ['email', 'first_name', 'last_name', 'has_signed_terms']

    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """

        self.provider = kwargs.pop('provider', None)
        self.request = kwargs.pop('request', None)
        if not self.provider or self.provider == 'local':
            raise Exception('Invalid provider, %r' % self.provider)

        # ThirdPartyUserCreationForm should always get instantiated with
        # a third_party_token value
        self.third_party_token = kwargs.pop('third_party_token', None)
        if not self.third_party_token:
            raise Exception('ThirdPartyUserCreationForm'
                            ' requires third_party_token')

        super(ThirdPartyUserCreationForm, self).__init__(*args, **kwargs)

        if not get_latest_terms():
            del self.fields['has_signed_terms']

        if 'has_signed_terms' in self.fields:
            # Overriding field label since we need to apply a link
            # to the terms within the label
            terms_link_html = '<a href="%s" target="_blank">%s</a>' \
                % (reverse('latest_terms'), _("the terms"))
            self.fields['has_signed_terms'].label = \
                mark_safe("I agree with %s" % terms_link_html)

        auth_provider = auth_providers.get_provider(self.provider)
        user_attr_map = auth_provider.get_user_attr_map()
        for field in ['email', 'first_name', 'last_name']:
            if not user_attr_map[field][1]:
                self.ro_fields.append(field)
                self.fields[field].widget.attrs['readonly'] = True
                self.fields[field].help_text = _(READ_ONLY_FIELD_MSG)

    def clean_email(self):
        email = self.cleaned_data['email']
        if not email:
            raise forms.ValidationError(_(astakos_messages.REQUIRED_FIELD))
        if reserved_verified_email(email):
            provider_id = self.provider
            provider = auth_providers.get_provider(provider_id)
            extra_message = provider.get_add_to_existing_account_msg

            raise forms.ValidationError(mark_safe(
                _(astakos_messages.EMAIL_USED) + ' ' + extra_message))
        return email

    def clean_first_name(self):
        if 'first_name' in self.ro_fields:
            return self.initial['first_name']
        return self.cleaned_data['first_name']

    def clean_last_name(self):
        if 'last_name' in self.ro_fields:
            return self.initial['last_name']
        return self.cleaned_data['last_name']

    def clean_has_signed_terms(self):
        has_signed_terms = self.cleaned_data['has_signed_terms']
        if not has_signed_terms:
            raise forms.ValidationError(_(astakos_messages.SIGN_TERMS))
        return has_signed_terms

    def _get_pending_user(self):
        return PendingThirdPartyUser.objects.get(token=self.third_party_token)

    def create_user(self):
        try:
            data = self.cleaned_data
        except AttributeError:
            self.is_valid()
            data = self.cleaned_data

        user = auth.make_user(
            email=data["email"],
            first_name=data["first_name"], last_name=data["last_name"],
            has_signed_terms=True)
        pending = self._get_pending_user()
        provider = pending.get_provider(user)
        provider.add_to_user()
        pending.delete()
        return user


class LoginForm(AuthenticationForm):
    username = EmailField(label=_("Email"))
    recaptcha_challenge_field = forms.CharField(widget=DummyWidget)
    recaptcha_response_field = forms.CharField(
        widget=RecaptchaWidget, label='')

    def __init__(self, *args, **kwargs):
        was_limited = kwargs.get('was_limited', False)
        request = kwargs.get('request', None)
        if request:
            self.ip = request.META.get(
                'REMOTE_ADDR',
                request.META.get('HTTP_X_REAL_IP', None))

        t = ('request', 'was_limited')
        for elem in t:
            if elem in kwargs.keys():
                kwargs.pop(elem)
        super(LoginForm, self).__init__(*args, **kwargs)

        self.fields.keyOrder = ['username', 'password']
        if was_limited and settings.RECAPTCHA_ENABLED:
            self.fields.keyOrder.extend(['recaptcha_challenge_field',
                                         'recaptcha_response_field', ])

    def clean_username(self):
        return self.cleaned_data['username'].lower()

    def clean_recaptcha_response_field(self):
        if 'recaptcha_challenge_field' in self.cleaned_data:
            self.validate_captcha()
        return self.cleaned_data['recaptcha_response_field']

    def clean_recaptcha_challenge_field(self):
        if 'recaptcha_response_field' in self.cleaned_data:
            self.validate_captcha()
        return self.cleaned_data['recaptcha_challenge_field']

    def validate_captcha(self):
        rcf = self.cleaned_data['recaptcha_challenge_field']
        rrf = self.cleaned_data['recaptcha_response_field']
        check = captcha.submit(
            rcf, rrf, settings.RECAPTCHA_PRIVATE_KEY, self.ip)
        if not check.is_valid:
            raise forms.ValidationError(_(
                astakos_messages.CAPTCHA_VALIDATION_ERR))

    def clean(self):
        """
        Override default behavior in order to check user's activation later
        """
        username = self.cleaned_data.get('username')

        if username:
            try:
                user = AstakosUser.objects.get_by_identifier(username)
                if not user.has_auth_provider('local'):
                    provider = auth_providers.get_provider('local', user)
                    msg = provider.get_login_disabled_msg
                    raise forms.ValidationError(mark_safe(msg))
            except AstakosUser.DoesNotExist:
                pass

        try:
            super(LoginForm, self).clean()
        except forms.ValidationError:
            if self.user_cache is None:
                raise
            if not self.user_cache.is_active:
                msg = self.user_cache.get_inactive_message('local')
                raise forms.ValidationError(msg)
            if self.request:
                if not self.request.session.test_cookie_worked():
                    raise
        return self.cleaned_data


class ProfileForm(forms.ModelForm):
    """
    Subclass of ``ModelForm`` for permiting user to edit his/her profile.
    Most of the fields are readonly since the user is not allowed to change
    them.

    The class defines a save method which sets ``is_verified`` to True so as
    the user during the next login will not to be redirected to profile page.
    """
    email = EmailField(label='E-mail address',
                       help_text='E-mail address')
    renew = forms.BooleanField(label='Renew token', required=False)
    ro_fields = ['email']

    class Meta:
        model = AstakosUser
        fields = ('email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        self.session_key = kwargs.pop('session_key', None)
        super(ProfileForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.id:
            if not instance.can_change_first_name():
                self.ro_fields.append('first_name')
            if not instance.can_change_last_name():
                self.ro_fields.append('last_name')
            for field in self.ro_fields:
                self.fields[field].widget.attrs['readonly'] = True
                self.fields[field].help_text = _(READ_ONLY_FIELD_MSG)

    def clean_email(self):
        return self.instance.email

    def clean_first_name(self):
        if 'first_name' in self.ro_fields:
            return self.initial['first_name']
        return self.cleaned_data['first_name']

    def clean_last_name(self):
        if 'last_name' in self.ro_fields:
            return self.initial['last_name']
        return self.cleaned_data['last_name']

    def save(self, commit=True, **kwargs):
        user = super(ProfileForm, self).save(commit=False, **kwargs)
        user.is_verified = True
        if self.cleaned_data.get('renew'):
            user.renew_token(
                flush_sessions=True,
                current_key=self.session_key
            )
        if commit:
            user.save(**kwargs)
        return user


class FeedbackForm(forms.Form):
    """
    Form for writing feedback.
    """
    feedback_msg = forms.CharField(widget=forms.Textarea, label=u'Message')
    feedback_data = forms.CharField(widget=forms.HiddenInput(), label='',
                                    required=False)


class SendInvitationForm(forms.Form):
    """
    Form for sending an invitations
    """

    email = EmailField(required=True, label='Email address')
    first_name = EmailField(label='First name')
    last_name = EmailField(label='Last name')


class ExtendedPasswordResetForm(PasswordResetForm):
    """
    Extends PasswordResetForm by overriding

    save method: to pass a custom from_email in send_mail.
    clean_email: to handle local auth provider checks
    """
    def clean_email(self):
        # we override the default django auth clean_email to provide more
        # detailed messages in case of inactive users
        email = self.cleaned_data['email']
        try:
            user = AstakosUser.objects.get_by_identifier(email)
            self.users_cache = [user]
            if not user.is_active:
                if not user.has_auth_provider('local', auth_backend='astakos'):
                    provider = auth_providers.get_provider('local', user)
                    msg = mark_safe(provider.get_unusable_password_msg)
                    raise forms.ValidationError(msg)

                msg = mark_safe(user.get_inactive_message('local'))
                raise forms.ValidationError(msg)

            provider = auth_providers.get_provider('local', user)
            if not user.has_usable_password():
                msg = provider.get_unusable_password_msg
                raise forms.ValidationError(mark_safe(msg))

            if not user.can_change_password():
                msg = provider.get_cannot_change_password_msg
                raise forms.ValidationError(mark_safe(msg))

        except AstakosUser.DoesNotExist:
            raise forms.ValidationError(_(astakos_messages.EMAIL_UNKNOWN))
        return email

    def save(self, domain_override=None,
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             request=None, **kwargs):
        """
        Generates a one-use only link for resetting password and sends to the
        user.

        """
        for user in self.users_cache:
            url = user.astakosuser.get_password_reset_url(token_generator)
            url = join_urls(settings.BASE_HOST, url)
            c = {
                'email': user.email,
                'url': url,
                'site_name': settings.SITENAME,
                'user': user,
                'baseurl': settings.BASE_URL,
                'support': settings.CONTACT_EMAIL
            }
            message = render_to_string(email_template_name, c)
            from_email = settings.SERVER_EMAIL
            send_mail(_(astakos_messages.PASSWORD_RESET_EMAIL_SUBJECT),
                      message,
                      from_email,
                      [user.email],
                      connection=get_connection())


class EmailChangeForm(forms.ModelForm):

    new_email_address = EmailField()

    class Meta:
        model = EmailChange
        fields = ('new_email_address',)

    def clean_new_email_address(self):
        addr = self.cleaned_data['new_email_address']
        if reserved_verified_email(addr):
            raise forms.ValidationError(_(astakos_messages.EMAIL_USED))
        return addr

    def save(self, request,
             email_template_name='registration/email_change_email.txt',
             commit=True, **kwargs):
        ec = super(EmailChangeForm, self).save(commit=False, **kwargs)
        ec.user = request.user
        # delete pending email changes
        request.user.emailchanges.all().delete()

        activation_key = hashlib.sha1(
            str(random()) + smart_str(ec.new_email_address))
        ec.activation_key = activation_key.hexdigest()
        if commit:
            ec.save(**kwargs)
        send_change_email(ec, request, email_template_name=email_template_name)


class SignApprovalTermsForm(forms.ModelForm):

    class Meta:
        model = AstakosUser
        fields = ("has_signed_terms",)

    def __init__(self, *args, **kwargs):
        super(SignApprovalTermsForm, self).__init__(*args, **kwargs)
        self.fields['has_signed_terms'].label = _("I agree with the terms")

    def clean_has_signed_terms(self):
        has_signed_terms = self.cleaned_data['has_signed_terms']
        if not has_signed_terms:
            raise forms.ValidationError(_(astakos_messages.SIGN_TERMS))
        return has_signed_terms

    def save(self, commit=True, **kwargs):
        user = super(SignApprovalTermsForm, self).save(commit=commit, **kwargs)
        user.date_signed_terms = datetime.now()
        if commit:
            user.save(**kwargs)
        return user


class InvitationForm(forms.ModelForm):

    username = EmailField(label=_("Email"))

    def __init__(self, *args, **kwargs):
        super(InvitationForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Invitation
        fields = ('username', 'realname')

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            Invitation.objects.get(username=username)
            raise forms.ValidationError(
                _(astakos_messages.INVITATION_EMAIL_EXISTS))
        except Invitation.DoesNotExist:
            pass
        return username


class ExtendedPasswordChangeForm(PasswordChangeForm):
    """
    Extends PasswordChangeForm by enabling user
    to optionally renew also the token.
    """
    if not settings.NEWPASSWD_INVALIDATE_TOKEN:
        renew = forms.BooleanField(
            label='Renew token', required=False,
            initial=True,
            help_text='Unsetting this may result in security risk.')

    def __init__(self, user, *args, **kwargs):
        self.session_key = kwargs.pop('session_key', None)
        super(ExtendedPasswordChangeForm, self).__init__(user, *args, **kwargs)

    def save(self, commit=True, **kwargs):
        try:
            if settings.NEWPASSWD_INVALIDATE_TOKEN or \
                    self.cleaned_data.get('renew'):
                self.user.renew_token()
            self.user.flush_sessions(current_key=self.session_key)
        except AttributeError:
            # if user model does has not such methods
            pass
        return super(ExtendedPasswordChangeForm, self).save(commit=commit,
                                                            **kwargs)


class ExtendedSetPasswordForm(SetPasswordForm):
    """
    Extends SetPasswordForm by enabling user
    to optionally renew also the token.
    """
    if not settings.NEWPASSWD_INVALIDATE_TOKEN:
        renew = forms.BooleanField(
            label='Renew token',
            required=False,
            initial=True,
            help_text='Unsetting this may result in security risk.')

    def __init__(self, user, *args, **kwargs):
        super(ExtendedSetPasswordForm, self).__init__(user, *args, **kwargs)

    @transaction.commit_on_success()
    def save(self, commit=True, **kwargs):
        try:
            self.user = AstakosUser.objects.get(id=self.user.id)
            if settings.NEWPASSWD_INVALIDATE_TOKEN or \
                    self.cleaned_data.get('renew'):
                self.user.renew_token()

            provider = auth_providers.get_provider('local', self.user)
            if provider.get_add_policy:
                provider.add_to_user()

        except BaseException, e:
            logger.exception(e)
        return super(ExtendedSetPasswordForm, self).save(commit=commit,
                                                         **kwargs)


app_name_label = "Project name"
app_name_placeholder = _("myproject.mylab.ntua.gr")
app_name_validator = validators.RegexValidator(
    DOMAIN_VALUE_REGEX,
    _(astakos_messages.DOMAIN_VALUE_ERR),
    'invalid')
base_app_name_validator = validators.RegexValidator(
    BASE_PROJECT_NAME_REGEX,
    _(astakos_messages.BASE_PROJECT_NAME_ERR),
    'invalid')
app_name_help = _("""
        The project's name should be in a domain format.
        The domain shouldn't neccessarily exist in the real
        world but is helpful to imply a structure.
        e.g.: myproject.mylab.ntua.gr or
        myservice.myteam.myorganization""")
app_name_widget = forms.TextInput(
    attrs={'placeholder': app_name_placeholder})


app_home_label = "Homepage URL"
app_home_placeholder = 'myinstitution.org/myproject/'
app_home_help = _("""
        URL pointing at your project's site.
        e.g.: myinstitution.org/myproject/.
        Leave blank if there is no website.""")
app_home_widget = forms.TextInput(
    attrs={'placeholder': app_home_placeholder})

app_desc_label = _("Description")
app_desc_help = _("""
        Please provide a short but descriptive abstract of your
        project, so that anyone searching can quickly understand
        what this project is about.""")

app_comment_label = _("Comments for review (private)")
app_comment_help = _("""
        Write down any comments you may have for the reviewer
        of this application (e.g. background and rationale to
        support your request).
        The comments are strictly for the review process
        and will not be made public.""")

app_start_date_label = _("Start date")
app_start_date_help = _("""
        Provide a date when your need your project to be created,
        and members to be able to join and get resources.
        This date is only a hint to help prioritize reviews.""")

app_end_date_label = _("Termination date")
app_end_date_help = _("""
        At this date, the project will be automatically terminated
        and its resource grants revoked from all members. If you are
        not certain, it is best to start with a conservative estimation.
        You can always re-apply for an extension, if you need.""")

join_policy_label = _("Joining policy")
app_member_join_policy_help = _("""
        Select how new members are accepted into the project.""")
leave_policy_label = _("Leaving policy")
app_member_leave_policy_help = _("""
        Select how new members can leave the project.""")

max_members_label = _("Max members")
max_members_help = _("""
        Specify the maximum number of members this project may have,
        including the owner. Beyond this number, no new members
        may join the project and be granted the project resources.
        If you are not certain, it is best to start with a conservative
        limit. You can always request a raise when you need it.""")

join_policies = presentation.PROJECT_MEMBER_JOIN_POLICIES.items()
leave_policies = presentation.PROJECT_MEMBER_LEAVE_POLICIES.items()


class ProjectApplicationForm(forms.ModelForm):

    name = forms.CharField(
        label=app_name_label,
        help_text=app_name_help,
        widget=app_name_widget,
        validators=[app_name_validator])

    homepage = forms.URLField(
        label=app_home_label,
        help_text=app_home_help,
        widget=app_home_widget,
        required=False)

    description = forms.CharField(
        label=app_desc_label,
        help_text=app_desc_help,
        widget=forms.Textarea,
        required=False)

    comments = forms.CharField(
        label=app_comment_label,
        help_text=app_comment_help,
        widget=forms.Textarea,
        required=False)

    start_date = forms.DateTimeField(
        label=app_start_date_label,
        help_text=app_start_date_help,
        required=False)

    end_date = forms.DateTimeField(
        label=app_end_date_label,
        help_text=app_end_date_help)

    member_join_policy = forms.TypedChoiceField(
        label=join_policy_label,
        help_text=app_member_join_policy_help,
        initial=2,
        coerce=int,
        choices=join_policies)

    member_leave_policy = forms.TypedChoiceField(
        label=leave_policy_label,
        help_text=app_member_leave_policy_help,
        coerce=int,
        choices=leave_policies)

    limit_on_members_number = InfiniteChoiceField(
        choices=settings.PROJECT_MEMBERS_LIMIT_CHOICES,
        label=max_members_label,
        help_text=max_members_help,
        initial="Unlimited",
        required=True)

    class Meta:
        model = ProjectApplication
        fields = ('name', 'homepage', 'description',
                  'start_date', 'end_date', 'comments',
                  'member_join_policy', 'member_leave_policy',
                  'limit_on_members_number')

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')

        super(ProjectApplicationForm, self).__init__(*args, **kwargs)
        # in case of new application remove closed join policy
        if not instance:
            policies = presentation.PROJECT_MEMBER_JOIN_POLICIES.copy()
            policies.pop(3)
            self.fields['member_join_policy'].choices = policies.iteritems()
        else:
            if instance.is_base:
                name_field = self.fields['name']
                name_field.validators = [base_app_name_validator]
            if self.initial['limit_on_members_number'] == \
                                                    units.PRACTICALLY_INFINITE:
                self.initial['limit_on_members_number'] = 'Unlimited'

    def clean_limit_on_members_number(self):
        value = self.cleaned_data.get('limit_on_members_number')
        if value in ["inf", "Unlimited"]:
            return units.PRACTICALLY_INFINITE
        return value

    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if not self.instance:
            today = datetime.now()
            today = datetime(today.year, today.month, today.day)
            if start_date and (start_date - today).days < 0:
                raise forms.ValidationError(
                    _(astakos_messages.INVALID_PROJECT_START_DATE))
        return start_date

    def clean_end_date(self):
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')
        today = datetime.now()
        today = datetime(today.year, today.month, today.day)
        if end_date and (end_date - today).days < 0:
            raise forms.ValidationError(
                _(astakos_messages.INVALID_PROJECT_END_DATE))
        if start_date and (end_date - start_date).days <= 0:
            raise forms.ValidationError(
                _(astakos_messages.INCONSISTENT_PROJECT_DATES))
        return end_date

    def clean(self):
        userid = self.data.get('user', None)
        policies = self.resource_policies
        self.user = None
        if userid:
            try:
                self.user = AstakosUser.objects.get(id=userid)
            except AstakosUser.DoesNotExist:
                pass
        if not self.user:
            raise forms.ValidationError(_(astakos_messages.NO_APPLICANT))
        cleaned_data = super(ProjectApplicationForm, self).clean()
        return cleaned_data

    @property
    def resource_policies(self):
        policies = []
        append = policies.append
        resource_indexes = {}
        include_diffs = False
        is_new = self.instance and self.instance.id is None

        existing_policies = []
        existing_data = {}

        # normalize to single values dict
        data = dict()
        for key, value in self.data.iteritems():
            data[key] = value

        if not is_new:
            # User may have emptied some fields. Empty values are not handled
            # below. Fill data as if user typed "0" in field, but only
            # for resources which exist in application project and have
            # non-zero capacity (either for member or project).
            include_diffs = True
            existing_policies = self.instance.resource_set
            append_groups = set()
            for policy in existing_policies:
                cap_set = max(policy.project_capacity, policy.member_capacity)

                if not policy.resource.ui_visible:
                    continue

                rname = policy.resource.name
                group = policy.resource.group
                existing_data["%s_p_uplimit" % rname] = "0"
                existing_data["%s_m_uplimit" % rname] = "0"
                append_groups.add(group)

            for key, value in existing_data.iteritems():
                if not key in data or data.get(key, '') == '':
                    data[key] = value
            for group in append_groups:
                data["is_selected_%s" % group] = "1"

        for name, value in data.iteritems():

            if not value:
                continue

            if name.endswith('_uplimit'):
                is_project_limit = name.endswith('_p_uplimit')
                suffix = '_p_uplimit' if is_project_limit else '_m_uplimit'
                if value == 'inf' or value == 'Unlimited':
                    value = units.PRACTICALLY_INFINITE
                uplimit = value
                prefix, _suffix = name.split(suffix)

                try:
                    resource = Resource.objects.get(name=prefix)
                except Resource.DoesNotExist:
                    raise forms.ValidationError("Resource %s does not exist" %
                                                resource.name)

                # keep only resource limits for selected resource groups
                if data.get('is_selected_%s' % \
                                     resource.group, "0") == "1":
                    if not resource.ui_visible:
                        raise forms.ValidationError("Invalid resource %s" %
                                                    resource.name)
                    d = model_to_dict(resource)
                    try:
                        uplimit = long(uplimit)
                    except ValueError:
                        m = "Limit should be an integer"
                        raise forms.ValidationError(m)

                    display = units.show(uplimit, resource.unit)
                    if display == "inf":
                        display = "Unlimited"

                    handled = resource_indexes.get(prefix)

                    diff_data = None
                    if include_diffs:
                        try:
                            policy = existing_policies.get(resource=resource)
                            if is_project_limit:
                                pval = policy.project_capacity
                            else:
                                pval = policy.member_capacity

                            if pval != uplimit:
                                diff = pval - uplimit

                                diff_display = units.show(abs(diff),
                                                          resource.unit,
                                                          inf="Unlimited")
                                diff_is_inf = False
                                prev_is_inf = False
                                if uplimit == units.PRACTICALLY_INFINITE:
                                    diff_display = "Unlimited"
                                    diff_is_inf = True
                                if pval == units.PRACTICALLY_INFINITE:
                                    diff_display = "Unlimited"
                                    prev_is_inf = True

                                prev_display = units.show(pval, resource.unit,
                                                          inf="Unlimited")

                                diff_data = {
                                    'prev': pval,
                                    'prev_display': prev_display,
                                    'diff': diff,
                                    'diff_display': diff_display,
                                    'increased': diff < 0,
                                    'diff_is_inf': diff_is_inf,
                                    'prev_is_inf': prev_is_inf,
                                    'operator': '+' if diff < 0 else '-'
                                }

                        except:
                            pass

                    if is_project_limit:
                        d.update(dict(resource=prefix,
                                      p_uplimit=uplimit,
                                      display_p_uplimit=display))

                        if diff_data:
                            d.update(dict(resource=prefix, p_diff=diff_data))

                        if not handled:
                            d.update(dict(resource=prefix, m_uplimit=0,
                                      display_m_uplimit=units.show(0,
                                           resource.unit)))
                    else:
                        d.update(dict(resource=prefix, m_uplimit=uplimit,
                                      display_m_uplimit=display))

                        if diff_data:
                            d.update(dict(resource=prefix, m_diff=diff_data))

                        if not handled:
                            d.update(dict(resource=prefix, p_uplimit=0,
                                      display_p_uplimit=units.show(0,
                                           resource.unit)))

                    if resource_indexes.get(prefix, None) is not None:
                        # already included in policies
                        handled.update(d)
                    else:
                        # keep track of resource dicts
                        append(d)
                        resource_indexes[prefix] = d

        ordered_keys = presentation.RESOURCES['resources_order']

        def resource_order(r):
            if r['str_repr'] in ordered_keys:
                return ordered_keys.index(r['str_repr'])
            else:
                return -1

        policies = sorted(policies, key=resource_order)
        return policies

    def cleaned_resource_policies(self):
        policies = {}
        for d in self.resource_policies:
            if self.instance.pk:
                if not d.get('p_diff', None) and not d.get('m_diff', None):
                    continue

            policies[d["name"]] = {
                "project_capacity": d.get("p_uplimit", 0),
                "member_capacity": d.get("m_uplimit", 0)
            }

        if len(policies.keys()) == 0:
            return {}

        return policies

    def get_api_data(self):
        data = dict(self.cleaned_data)
        is_new = self.instance.id is None
        if isinstance(self.instance, Project):
            data['project_id'] = self.instance.id
        else:
            data['project_id'] = self.instance.chain.id if not is_new else None

        owner_uuid = None
        if self.instance.owner:
            owner_uuid = self.instance.owner.uuid

        user_uuid = self.user.uuid if is_new else owner_uuid
        try:
            object_owner = AstakosUser.objects.get(uuid=user_uuid)
            data['owner'] = object_owner
        except AstakosUser.DoesNotExist:
            pass

        exclude_keys = ['owner', 'comments', 'project_id', 'start_date']

        # is_valid changes instance attributes
        instance = self.instance
        if not is_new:
            instance = Project.objects.get(pk=self.instance.pk)

        for key in [dkey for dkey in data.keys() if not dkey in exclude_keys]:
            if not is_new and \
                   (getattr(instance, key) == data.get(key)):
                del data[key]

        resources = self.cleaned_resource_policies()
        if resources:
            data['resources'] = resources

        if data.get('start_date', None):
            data['start_date'] = date_util.isoformat(data.get('start_date'))
        else:
            del data['start_date']

        if data.get('end_date', None):
            data['end_date'] = date_util.isoformat(data.get('end_date'))

        limit = data.get('limit_on_members_number', None)
        if limit:
            data['max_members'] = data.get('limit_on_members_number')
        else:
            data['max_members'] = units.PRACTICALLY_INFINITE

        data['request_user'] = self.user
        if 'owner' in data:
            data['owner'] = data['owner'].uuid

        return data

    def save(self, commit=True, **kwargs):
        from astakos.api import projects as api
        data = self.get_api_data()
        return api.submit_new_project(data, self.user)


class ProjectModificationForm(ProjectApplicationForm):

    class Meta:
        model = Project
        fields = ('name', 'homepage', 'description',
                  'end_date', 'comments', 'member_join_policy',
                  'member_leave_policy', 'limit_on_members_number')

    def save(self, commit=True, **kwargs):
        from astakos.api import projects as api
        data = self.get_api_data()
        return api.submit_modification(data, self.user, self.instance.uuid)


class ProjectSortForm(forms.Form):
    sorting = forms.ChoiceField(
        label='Sort by',
        choices=(('name', 'Sort by Name'),
                 ('issue_date', 'Sort by Issue date'),
                 ('start_date', 'Sort by Start Date'),
                 ('end_date', 'Sort by End Date'),
                 # ('approved_members_num', 'Sort by Participants'),
                 ('state', 'Sort by Status'),
                 ('member_join_policy__description',
                  'Sort by Member Join Policy'),
                 ('member_leave_policy__description',
                  'Sort by Member Leave Policy'),
                 ('-name', 'Sort by Name'),
                 ('-issue_date', 'Sort by Issue date'),
                 ('-start_date', 'Sort by Start Date'),
                 ('-end_date', 'Sort by End Date'),
                 # ('-approved_members_num', 'Sort by Participants'),
                 ('-state', 'Sort by Status'),
                 ('-member_join_policy__description',
                  'Sort by Member Join Policy'),
                 ('-member_leave_policy__description',
                  'Sort by Member Leave Policy')
                 ),
        required=True
    )


class AddProjectMembersForm(forms.Form):
    q = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'placeholder':
                astakos_messages.ADD_PROJECT_MEMBERS_Q_PLACEHOLDER}),
        label=_('Add members'),
        help_text=_(astakos_messages.ADD_PROJECT_MEMBERS_Q_HELP),
        required=True,)

    def __init__(self, *args, **kwargs):
        project_id = kwargs.pop('project_id', None)
        if project_id:
            self.project = Project.objects.get(id=project_id)
        self.request_user = kwargs.pop('request_user', None)
        super(AddProjectMembersForm, self).__init__(*args, **kwargs)

    def clean(self):
        try:
            accept_membership_project_checks(self.project, self.request_user)
        except ProjectError as e:
            raise forms.ValidationError(e)

        q = self.cleaned_data.get('q') or ''
        users = re.split("\r\n|\n|,", q)
        users = list(u.strip() for u in users if u)
        db_entries = AstakosUser.objects.accepted().filter(email__in=users)
        unknown = list(set(users) - set(u.email for u in db_entries))
        if unknown:
            raise forms.ValidationError(
                _(astakos_messages.UNKNOWN_USERS) % ','.join(unknown))
        self.valid_users = db_entries
        return self.cleaned_data

    def get_valid_users(self):
        """Should be called after form cleaning"""
        return self.valid_users


class ProjectMembersSortForm(forms.Form):
    sorting = forms.ChoiceField(
        label='Sort by',
        choices=(('person__email', 'User Id'),
                 ('person__first_name', 'Name'),
                 ('acceptance_date', 'Acceptance date')
                 ),
        required=True
    )


class ProjectSearchForm(forms.Form):
    q = forms.CharField(max_length=200, label='Search project', required=False)


class ExtendedProfileForm(ProfileForm):
    """
    Profile form that combines `email change` and `password change` user
    actions by propagating submited data to internal EmailChangeForm
    and ExtendedPasswordChangeForm objects.
    """

    password_change_form = None
    email_change_form = None

    password_change = False
    email_change = False

    extra_forms_fields = {
        'email': ['new_email_address'],
        'password': ['old_password', 'new_password1', 'new_password2']
    }

    fields = ('email')
    change_password = forms.BooleanField(initial=False, required=False)
    change_email = forms.BooleanField(initial=False, required=False)

    email_changed = False
    password_changed = False

    def __init__(self, *args, **kwargs):
        session_key = kwargs.get('session_key', None)
        self.fields_list = [
            'email',
            'new_email_address',
            'first_name',
            'last_name',
            'old_password',
            'new_password1',
            'new_password2',
            'change_email',
            'change_password',
        ]

        super(ExtendedProfileForm, self).__init__(*args, **kwargs)
        self.session_key = session_key
        if self.instance.can_change_password():
            self.password_change = True
        else:
            self.fields_list.remove('old_password')
            self.fields_list.remove('new_password1')
            self.fields_list.remove('new_password2')
            self.fields_list.remove('change_password')
            del self.fields['change_password']

        if settings.EMAILCHANGE_ENABLED and self.instance.can_change_email():
            self.email_change = True
        else:
            self.fields_list.remove('new_email_address')
            self.fields_list.remove('change_email')
            del self.fields['change_email']

        self._init_extra_forms()
        self.save_extra_forms = []
        self.success_messages = []
        self.fields.keyOrder = self.fields_list

    def _init_extra_form_fields(self):
        if self.email_change:
            self.fields.update(self.email_change_form.fields)
            self.fields['new_email_address'].required = False
            self.fields['email'].help_text = _(
                'Change the email associated with '
                'your account. This email will '
                'remain active until you verify '
                'your new one.')

        if self.password_change:
            self.fields.update(self.password_change_form.fields)
            self.fields['old_password'].required = False
            self.fields['old_password'].label = _('Password')
            self.fields['old_password'].help_text = _('Change your password.')
            self.fields['old_password'].initial = 'password'
            self.fields['old_password'].widget.render_value = True
            self.fields['new_password1'].required = False
            self.fields['new_password2'].required = False

    def _update_extra_form_errors(self):
        if self.cleaned_data.get('change_password'):
            self.errors.update(self.password_change_form.errors)
        if self.cleaned_data.get('change_email'):
            self.errors.update(self.email_change_form.errors)

    def _init_extra_forms(self):
        self.email_change_form = EmailChangeForm(self.data)
        self.password_change_form = ExtendedPasswordChangeForm(
            user=self.instance,
            data=self.data, session_key=self.session_key)
        self._init_extra_form_fields()

    def is_valid(self):
        password, email = True, True
        profile = super(ExtendedProfileForm, self).is_valid()
        if profile and self.cleaned_data.get('change_password', None):
            self.password_change_form.fields['new_password1'].required = True
            self.password_change_form.fields['new_password2'].required = True
            password = self.password_change_form.is_valid()
            self.save_extra_forms.append('password')
        if profile and self.cleaned_data.get('change_email'):
            self.fields['new_email_address'].required = True
            email = self.email_change_form.is_valid()
            self.save_extra_forms.append('email')

        if not password or not email:
            self._update_extra_form_errors()

        return all([profile, password, email])

    def save(self, request, *args, **kwargs):
        if 'email' in self.save_extra_forms:
            self.email_change_form.save(request, *args, **kwargs)
            self.email_changed = True
        if 'password' in self.save_extra_forms:
            self.password_change_form.save(*args, **kwargs)
            self.password_changed = True
        return super(ExtendedProfileForm, self).save(*args, **kwargs)
