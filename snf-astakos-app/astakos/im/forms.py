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
from urlparse import urljoin
from random import random

from django import forms
from django.utils.translation import ugettext as _
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm,
    PasswordResetForm, PasswordChangeForm,
    SetPasswordForm)
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.template import Context, loader
from django.utils.http import int_to_base36
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_str
from django.conf import settings
from django.forms.models import fields_for_model
from django.db import transaction
from django.utils.encoding import smart_unicode
from django.core import validators
from django.contrib.auth.models import AnonymousUser

from astakos.im.models import (
    AstakosUser, EmailChange, Invitation,
    Resource, PendingThirdPartyUser, get_latest_terms, RESOURCE_SEPARATOR,
    ProjectApplication)
from astakos.im.settings import (
    INVITATIONS_PER_LEVEL, BASEURL, SITENAME, RECAPTCHA_PRIVATE_KEY,
    RECAPTCHA_ENABLED, DEFAULT_CONTACT_EMAIL, LOGGING_LEVEL,
    PASSWORD_RESET_EMAIL_SUBJECT, NEWPASSWD_INVALIDATE_TOKEN,
    MODERATION_ENABLED, PROJECT_MEMBER_JOIN_POLICIES,
    PROJECT_MEMBER_LEAVE_POLICIES)
from astakos.im.widgets import DummyWidget, RecaptchaWidget
from astakos.im.functions import send_change_email, submit_application

from astakos.im.util import reserved_email, get_query, model_to_dict
from astakos.im import auth_providers

import astakos.im.messages as astakos_messages

import logging
import hashlib
import recaptcha.client.captcha as captcha
import re

logger = logging.getLogger(__name__)

DOMAIN_VALUE_REGEX = re.compile(
    r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$',
    re.IGNORECASE)

class StoreUserMixin(object):

    @transaction.commit_on_success
    def store_user(self, user, request):
        user.save()
        self.post_store_user(user, request)
        return user

    def post_store_user(self, user, request):
        """
        Interface method for descendant backends to be able to do stuff within
        the transaction enabled by store_user.
        """
        pass


class LocalUserCreationForm(UserCreationForm, StoreUserMixin):
    """
    Extends the built in UserCreationForm in several ways:

    * Adds email, first_name, last_name, recaptcha_challenge_field, recaptcha_response_field field.
    * The username field isn't visible and it is assigned a generated id.
    * User created is not active.
    """
    recaptcha_challenge_field = forms.CharField(widget=DummyWidget)
    recaptcha_response_field = forms.CharField(
        widget=RecaptchaWidget, label='')

    class Meta:
        model = AstakosUser
        fields = ("email", "first_name", "last_name",
                  "has_signed_terms", "has_signed_terms")

    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """
        request = kwargs.pop('request', None)
        if request:
            self.ip = request.META.get('REMOTE_ADDR',
                                       request.META.get('HTTP_X_REAL_IP', None))

        super(LocalUserCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['email', 'first_name', 'last_name',
                                'password1', 'password2']

        if RECAPTCHA_ENABLED:
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
        if reserved_email(email):
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
        check = captcha.submit(rcf, rrf, RECAPTCHA_PRIVATE_KEY, self.ip)
        if not check.is_valid:
            raise forms.ValidationError(_(astakos_messages.CAPTCHA_VALIDATION_ERR))

    def post_store_user(self, user, request):
        """
        Interface method for descendant backends to be able to do stuff within
        the transaction enabled by store_user.
        """
        user.add_auth_provider('local', auth_backend='astakos')
        user.set_password(self.cleaned_data['password1'])

    def save(self, commit=True):
        """
        Saves the email, first_name and last_name properties, after the normal
        save behavior is complete.
        """
        user = super(LocalUserCreationForm, self).save(commit=False)
        user.renew_token()
        if commit:
            user.save()
            logger.log(LOGGING_LEVEL, 'Created user %s' % user.email)
        return user


class InvitedLocalUserCreationForm(LocalUserCreationForm):
    """
    Extends the LocalUserCreationForm: email is readonly.
    """
    class Meta:
        model = AstakosUser
        fields = ("email", "first_name", "last_name", "has_signed_terms")

    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """
        super(InvitedLocalUserCreationForm, self).__init__(*args, **kwargs)

        #set readonly form fields
        ro = ('email', 'username',)
        for f in ro:
            self.fields[f].widget.attrs['readonly'] = True

    def save(self, commit=True):
        user = super(InvitedLocalUserCreationForm, self).save(commit=False)
        user.set_invitations_level()
        user.email_verified = True
        if commit:
            user.save()
        return user


class ThirdPartyUserCreationForm(forms.ModelForm, StoreUserMixin):
    id = forms.CharField(
        widget=forms.HiddenInput(),
        label='',
        required=False
    )
    third_party_identifier = forms.CharField(
        widget=forms.HiddenInput(),
        label=''
    )
    class Meta:
        model = AstakosUser
        fields = ['id', 'email', 'third_party_identifier', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """
        self.request = kwargs.get('request', None)
        if self.request:
            kwargs.pop('request')

        latest_terms = get_latest_terms()
        if latest_terms:
            self._meta.fields.append('has_signed_terms')

        super(ThirdPartyUserCreationForm, self).__init__(*args, **kwargs)

        if latest_terms:
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
        if reserved_email(email):
            raise forms.ValidationError(_(astakos_messages.EMAIL_USED))
        return email

    def clean_has_signed_terms(self):
        has_signed_terms = self.cleaned_data['has_signed_terms']
        if not has_signed_terms:
            raise forms.ValidationError(_(astakos_messages.SIGN_TERMS))
        return has_signed_terms

    def post_store_user(self, user, request):
        pending = PendingThirdPartyUser.objects.get(
                                token=request.POST.get('third_party_token'),
                                third_party_identifier= \
            self.cleaned_data.get('third_party_identifier'))
        return user.add_pending_auth_provider(pending)


    def save(self, commit=True):
        user = super(ThirdPartyUserCreationForm, self).save(commit=False)
        user.set_unusable_password()
        user.renew_token()
        if commit:
            user.save()
            logger.log(LOGGING_LEVEL, 'Created user %s' % user.email)
        return user


class InvitedThirdPartyUserCreationForm(ThirdPartyUserCreationForm):
    """
    Extends the ThirdPartyUserCreationForm: email is readonly.
    """
    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """
        super(
            InvitedThirdPartyUserCreationForm, self).__init__(*args, **kwargs)

        #set readonly form fields
        ro = ('email',)
        for f in ro:
            self.fields[f].widget.attrs['readonly'] = True

    def save(self, commit=True):
        user = super(InvitedThirdPartyUserCreationForm, self).save(commit=False)
        user.set_invitation_level()
        user.email_verified = True
        if commit:
            user.save()
        return user


class ShibbolethUserCreationForm(ThirdPartyUserCreationForm):
    additional_email = forms.CharField(
        widget=forms.HiddenInput(), label='', required=False)

    def __init__(self, *args, **kwargs):
        super(ShibbolethUserCreationForm, self).__init__(*args, **kwargs)
        # copy email value to additional_mail in case user will change it
        name = 'email'
        field = self.fields[name]
        self.initial['additional_email'] = self.initial.get(name, field.initial)
        self.initial['email'] = None


class InvitedShibbolethUserCreationForm(ShibbolethUserCreationForm,
                                        InvitedThirdPartyUserCreationForm):
    pass


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label=_("Email"))
    recaptcha_challenge_field = forms.CharField(widget=DummyWidget)
    recaptcha_response_field = forms.CharField(
        widget=RecaptchaWidget, label='')

    def __init__(self, *args, **kwargs):
        was_limited = kwargs.get('was_limited', False)
        request = kwargs.get('request', None)
        if request:
            self.ip = request.META.get('REMOTE_ADDR',
                                       request.META.get('HTTP_X_REAL_IP', None))

        t = ('request', 'was_limited')
        for elem in t:
            if elem in kwargs.keys():
                kwargs.pop(elem)
        super(LoginForm, self).__init__(*args, **kwargs)

        self.fields.keyOrder = ['username', 'password']
        if was_limited and RECAPTCHA_ENABLED:
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
        check = captcha.submit(rcf, rrf, RECAPTCHA_PRIVATE_KEY, self.ip)
        if not check.is_valid:
            raise forms.ValidationError(_(astakos_messages.CAPTCHA_VALIDATION_ERR))

    def clean(self):
        """
        Override default behavior in order to check user's activation later
        """
        username = self.cleaned_data.get('username')

        if username:
            try:
                user = AstakosUser.objects.get_by_identifier(username)
                if not user.has_auth_provider('local'):
                    provider = auth_providers.get_provider('local')
                    raise forms.ValidationError(
                        _(provider.get_message('NOT_ACTIVE_FOR_USER')))
            except AstakosUser.DoesNotExist:
                pass

        try:
            super(LoginForm, self).clean()
        except forms.ValidationError, e:
            if self.user_cache is None:
                raise
            if not self.user_cache.is_active:
                raise forms.ValidationError(self.user_cache.get_inactive_message())
            if self.request:
                if not self.request.session.test_cookie_worked():
                    raise
        return self.cleaned_data


class ProfileForm(forms.ModelForm):
    """
    Subclass of ``ModelForm`` for permiting user to edit his/her profile.
    Most of the fields are readonly since the user is not allowed to change
    them.

    The class defines a save method which sets ``is_verified`` to True so as the
    user during the next login will not to be redirected to profile page.
    """
    renew = forms.BooleanField(label='Renew token', required=False)

    class Meta:
        model = AstakosUser
        fields = ('email', 'first_name', 'last_name', 'auth_token',
                  'auth_token_expires')

    def __init__(self, *args, **kwargs):
        self.session_key = kwargs.pop('session_key', None)
        super(ProfileForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        ro_fields = ('email', 'auth_token', 'auth_token_expires')
        if instance and instance.id:
            for field in ro_fields:
                self.fields[field].widget.attrs['readonly'] = True

    def save(self, commit=True):
        user = super(ProfileForm, self).save(commit=False)
        user.is_verified = True
        if self.cleaned_data.get('renew'):
            user.renew_token(
                flush_sessions=True,
                current_key=self.session_key
            )
        if commit:
            user.save()
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

    email = forms.EmailField(required=True, label='Email address')
    first_name = forms.EmailField(label='First name')
    last_name = forms.EmailField(label='Last name')


class ExtendedPasswordResetForm(PasswordResetForm):
    """
    Extends PasswordResetForm by overriding

    save method: to pass a custom from_email in send_mail.
    clean_email: to handle local auth provider checks
    """
    def clean_email(self):
        email = super(ExtendedPasswordResetForm, self).clean_email()
        try:
            user = AstakosUser.objects.get_by_identifier(email)

            if not user.is_active:
                raise forms.ValidationError(_(astakos_messages.ACCOUNT_INACTIVE))

            if not user.has_usable_password():
                raise forms.ValidationError(_(astakos_messages.UNUSABLE_PASSWORD))

            if not user.can_change_password():
                raise forms.ValidationError(_(astakos_messages.AUTH_PROVIDER_CANNOT_CHANGE_PASSWORD))
        except AstakosUser.DoesNotExist, e:
            raise forms.ValidationError(_(astakos_messages.EMAIL_UNKNOWN))
        return email

    def save(
        self, domain_override=None, email_template_name='registration/password_reset_email.html',
            use_https=False, token_generator=default_token_generator, request=None):
        """
        Generates a one-use only link for resetting password and sends to the user.
        """
        for user in self.users_cache:
            url = user.astakosuser.get_password_reset_url(token_generator)
            url = urljoin(BASEURL, url)
            t = loader.get_template(email_template_name)
            c = {
                'email': user.email,
                'url': url,
                'site_name': SITENAME,
                'user': user,
                'baseurl': BASEURL,
                'support': DEFAULT_CONTACT_EMAIL
            }
            from_email = settings.SERVER_EMAIL
            send_mail(_(PASSWORD_RESET_EMAIL_SUBJECT),
                      t.render(Context(c)), from_email, [user.email])


class EmailChangeForm(forms.ModelForm):

    class Meta:
        model = EmailChange
        fields = ('new_email_address',)

    def clean_new_email_address(self):
        addr = self.cleaned_data['new_email_address']
        if AstakosUser.objects.filter(email__iexact=addr):
            raise forms.ValidationError(_(astakos_messages.EMAIL_USED))
        return addr

    def save(self, email_template_name, request, commit=True):
        ec = super(EmailChangeForm, self).save(commit=False)
        ec.user = request.user
        activation_key = hashlib.sha1(
            str(random()) + smart_str(ec.new_email_address))
        ec.activation_key = activation_key.hexdigest()
        if commit:
            ec.save()
        send_change_email(ec, request, email_template_name=email_template_name)


class SignApprovalTermsForm(forms.ModelForm):

    class Meta:
        model = AstakosUser
        fields = ("has_signed_terms",)

    def __init__(self, *args, **kwargs):
        super(SignApprovalTermsForm, self).__init__(*args, **kwargs)

    def clean_has_signed_terms(self):
        has_signed_terms = self.cleaned_data['has_signed_terms']
        if not has_signed_terms:
            raise forms.ValidationError(_(astakos_messages.SIGN_TERMS))
        return has_signed_terms


class InvitationForm(forms.ModelForm):

    username = forms.EmailField(label=_("Email"))

    def __init__(self, *args, **kwargs):
        super(InvitationForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Invitation
        fields = ('username', 'realname')

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            Invitation.objects.get(username=username)
            raise forms.ValidationError(_(astakos_messages.INVITATION_EMAIL_EXISTS))
        except Invitation.DoesNotExist:
            pass
        return username


class ExtendedPasswordChangeForm(PasswordChangeForm):
    """
    Extends PasswordChangeForm by enabling user
    to optionally renew also the token.
    """
    if not NEWPASSWD_INVALIDATE_TOKEN:
        renew = forms.BooleanField(label='Renew token', required=False,
                                   initial=True,
                                   help_text='Unsetting this may result in security risk.')

    def __init__(self, user, *args, **kwargs):
        self.session_key = kwargs.pop('session_key', None)
        super(ExtendedPasswordChangeForm, self).__init__(user, *args, **kwargs)

    def save(self, commit=True):
        try:
            if NEWPASSWD_INVALIDATE_TOKEN or self.cleaned_data.get('renew'):
                self.user.renew_token()
            self.user.flush_sessions(current_key=self.session_key)
        except AttributeError:
            # if user model does has not such methods
            pass
        return super(ExtendedPasswordChangeForm, self).save(commit=commit)

class ExtendedSetPasswordForm(SetPasswordForm):
    """
    Extends SetPasswordForm by enabling user
    to optionally renew also the token.
    """
    if not NEWPASSWD_INVALIDATE_TOKEN:
        renew = forms.BooleanField(
            label='Renew token',
            required=False,
            initial=True,
            help_text='Unsetting this may result in security risk.')

    def __init__(self, user, *args, **kwargs):
        super(ExtendedSetPasswordForm, self).__init__(user, *args, **kwargs)

    @transaction.commit_on_success()
    def save(self, commit=True):
        try:
            self.user = AstakosUser.objects.get(id=self.user.id)
            if NEWPASSWD_INVALIDATE_TOKEN or self.cleaned_data.get('renew'):
                self.user.renew_token()
            #self.user.flush_sessions()
            if not self.user.has_auth_provider('local'):
                self.user.add_auth_provider('local', auth_backend='astakos')

        except BaseException, e:
            logger.exception(e)
        return super(ExtendedSetPasswordForm, self).save(commit=commit)




app_name_label       =  "Project name"
app_name_placeholder = _("myproject.mylab.ntua.gr")
app_name_validator   =  validators.RegexValidator(
                            DOMAIN_VALUE_REGEX,
                            _(astakos_messages.DOMAIN_VALUE_ERR),
                            'invalid')
app_name_help        =  _("""
        The Project's name should be in a domain format.
        The domain shouldn't neccessarily exist in the real
        world but is helpful to imply a structure.
        e.g.: myproject.mylab.ntua.gr or
        myservice.myteam.myorganization""")
app_name_widget      =  forms.TextInput(
                            attrs={'placeholder': app_name_placeholder})


app_home_label       =  "Homepage URL"
app_home_placeholder =  'http://myteam.myinstitution.org/myproject/'
app_home_help        =  _("""
        URL pointing at your project's site.
        e.g.: http://myteam.myinstitution.org/myproject.
        Leave blank if there is no website.""")
app_home_widget      =  forms.TextInput(
                            attrs={'placeholder': app_home_placeholder})

app_desc_label       =  _("Description")
app_desc_help        =  _("""
        Please provide a short but descriptive abstract of your Project,
        so that anyone searching can quickly understand
        what this Project is about.""")

app_comment_label    =  _("Comments for review (private)")
app_comment_help     =  _("""
        Write down any comments you may have for the reviewer
        of this application (e.g. background and rationale to
        support your request).
        The comments are strictly for the review process
        and will not be published.""")

app_start_date_label =  _("Start date")
app_start_date_help  =  _("""
        Provide a date when your need your project to be created,
        and members to be able to join and get resources.
        This date is only a hint to help prioritize reviews.""")

app_end_date_label   =  _("Termination date")
app_end_date_help    =  _("""
        At this date, the project will be automatically terminated
        and its resource grants revoked from all members.
        Unless you know otherwise,
        it is best to start with a conservative estimation.
        You can always re-apply for an extension, if you need.""")

join_policy_label    =  _("Joining policy")
leave_policy_label   =  _("Leaving policy")

max_members_label    =  _("Maximum member count")
max_members_help     =  _("""
        Specify the maximum number of members this project may have,
        including the owner. Beyond this number, no new members
        may join the project and be granted the project resources.
        Unless you certainly for otherwise,
        it is best to start with a conservative limit.
        You can always request a raise when you need it.""")

join_policies = PROJECT_MEMBER_JOIN_POLICIES.iteritems()
leave_policies = PROJECT_MEMBER_LEAVE_POLICIES.iteritems()

class ProjectApplicationForm(forms.ModelForm):

    name = forms.CharField(
        label     = app_name_label,
        help_text = app_name_help,
        widget    = app_name_widget,
        validators = [app_name_validator])

    homepage = forms.URLField(
        label     = app_home_label,
        help_text = app_home_help,   
        widget    = app_home_widget,
        required  = False)

    description = forms.CharField(
        label     = app_desc_label,
        help_text = app_desc_help,
        widget    = forms.Textarea,
        required  = False)

    comments = forms.CharField(
        label     = app_comment_label,
        help_text = app_comment_help,
        widget    = forms.Textarea,
        required  = False)

    start_date = forms.DateTimeField(
        label     = app_start_date_label,
        help_text = app_start_date_help,
        required  = False)

    end_date = forms.DateTimeField(
        label     = app_end_date_label,
        help_text = app_end_date_help)

    member_join_policy  = forms.ChoiceField(
        label     = join_policy_label,
        choices   = join_policies)

    member_leave_policy = forms.ChoiceField(
        label     = leave_policy_label,
        choices   = leave_policies)

    limit_on_members_number = forms.IntegerField(
        label     = max_members_label,
        help_text = max_members_help,
        required  = False)

    class Meta:
        model = ProjectApplication
        #include = ( 'name', 'homepage', 'description',
        #            'start_date', 'end_date', 'comments')

        fields = ( 'name', 'homepage', 'description',
                    'start_date', 'end_date', 'comments',
                    'member_join_policy', 'member_leave_policy',
                    'limit_on_members_number')

    def __init__(self, *args, **kwargs):
        self.precursor_application = kwargs.get('instance')
        super(ProjectApplicationForm, self).__init__(*args, **kwargs)

    def clean(self):
        userid = self.data.get('user', None)
        self.user = None
        if userid:
            try:
                self.user = AstakosUser.objects.get(id=userid)
            except AstakosUser.DoesNotExist:
                pass
        if not self.user:
            raise forms.ValidationError(_(astakos_messages.NO_APPLICANT))
        super(ProjectApplicationForm, self).clean()
        return self.cleaned_data

    @property
    def resource_policies(self):
        policies = []
        append = policies.append
        for name, value in self.data.iteritems():
            if not value:
                continue
            uplimit = value
            if name.endswith('_uplimit'):
                subs = name.split('_uplimit')
                prefix, suffix = subs
                s, sep, r = prefix.partition(RESOURCE_SEPARATOR)
                resource = Resource.objects.get(service__name=s, name=r)

                # keep only resource limits for selected resource groups
                if self.data.get(
                    'is_selected_%s' % resource.group, "0"
                 ) == "1":
                    d = model_to_dict(resource)
                    if uplimit:
                        d.update(dict(service=s, resource=r, uplimit=uplimit))
                    else:
                        d.update(dict(service=s, resource=r, uplimit=None))
                    append(d)

        return policies


    def save(self, commit=True):
        application = super(ProjectApplicationForm, self).save(commit=False)
        applicant = self.user
        comments = self.cleaned_data.pop('comments', None)
        return submit_application(
            application,
            self.resource_policies,
            applicant,
            comments,
            self.precursor_application
        )

class ProjectSortForm(forms.Form):
    sorting = forms.ChoiceField(
        label='Sort by',
        choices=(('name', 'Sort by Name'),
                 ('issue_date', 'Sort by Issue date'),
                 ('start_date', 'Sort by Start Date'),
                 ('end_date', 'Sort by End Date'),
#                  ('approved_members_num', 'Sort by Participants'),
                 ('state', 'Sort by Status'),
                 ('member_join_policy__description', 'Sort by Member Join Policy'),
                 ('member_leave_policy__description', 'Sort by Member Leave Policy'),
                 ('-name', 'Sort by Name'),
                 ('-issue_date', 'Sort by Issue date'),
                 ('-start_date', 'Sort by Start Date'),
                 ('-end_date', 'Sort by End Date'),
#                  ('-approved_members_num', 'Sort by Participants'),
                 ('-state', 'Sort by Status'),
                 ('-member_join_policy__description', 'Sort by Member Join Policy'),
                 ('-member_leave_policy__description', 'Sort by Member Leave Policy')
        ),
        required=True
    )

class AddProjectMembersForm(forms.Form):
    q = forms.CharField(
        max_length=800, widget=forms.Textarea, label=_('Add members'),
        help_text=_(astakos_messages.ADD_PROJECT_MEMBERS_Q_HELP),
        required=True)

    def clean(self):
        q = self.cleaned_data.get('q') or ''
        users = q.split(',')
        users = list(u.strip() for u in users if u)
        db_entries = AstakosUser.objects.filter(email__in=users)
        unknown = list(set(users) - set(u.email for u in db_entries))
        if unknown:
            raise forms.ValidationError(_(astakos_messages.UNKNOWN_USERS) % ','.join(unknown))
        self.valid_users = db_entries
        return self.cleaned_data

    def get_valid_users(self):
        """Should be called after form cleaning"""
        try:
            return self.valid_users
        except:
            return ()

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

