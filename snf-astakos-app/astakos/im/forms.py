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

from django import forms
from django.utils.translation import ugettext as _
from django.contrib.auth.forms import (UserCreationForm, AuthenticationForm,
                                       PasswordResetForm, PasswordChangeForm,
                                       SetPasswordForm)
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.template import Context, loader
from django.utils.http import int_to_base36
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_str
from django.forms.extras.widgets import SelectDateWidget
from django.conf import settings

from astakos.im.models import (AstakosUser, EmailChange, AstakosGroup,
                               Invitation, Membership, GroupKind, Resource,
                               get_latest_terms, RESOURCE_SEPARATOR)
from astakos.im.settings import (INVITATIONS_PER_LEVEL, BASEURL, SITENAME,
                                 RECAPTCHA_PRIVATE_KEY, RECAPTCHA_ENABLED,
                                 DEFAULT_CONTACT_EMAIL, LOGGING_LEVEL,
                                 PASSWORD_RESET_EMAIL_SUBJECT,
                                 NEWPASSWD_INVALIDATE_TOKEN)
from astakos.im.widgets import DummyWidget, RecaptchaWidget
from astakos.im.functions import send_change_email

from astakos.im.util import reserved_email, get_query

import logging
import hashlib
import recaptcha.client.captcha as captcha
from random import random

logger = logging.getLogger(__name__)


class LocalUserCreationForm(UserCreationForm):
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
        request = kwargs.get('request', None)
        if request:
            kwargs.pop('request')
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
            raise forms.ValidationError(_("This field is required"))
        if reserved_email(email):
            raise forms.ValidationError(_("This email is already used"))
        return email

    def clean_has_signed_terms(self):
        has_signed_terms = self.cleaned_data['has_signed_terms']
        if not has_signed_terms:
            raise forms.ValidationError(_('You have to agree with the terms'))
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
            raise forms.ValidationError(
                _('You have not entered the correct words'))

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
        level = user.invitation.inviter.level + 1
        user.level = level
        user.invitations = INVITATIONS_PER_LEVEL.get(level, 0)
        user.email_verified = True
        if commit:
            user.save()
        return user


class ThirdPartyUserCreationForm(forms.ModelForm):
    class Meta:
        model = AstakosUser
        fields = ("email", "first_name", "last_name",
                  "third_party_identifier", "has_signed_terms")

    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """
        self.request = kwargs.get('request', None)
        if self.request:
            kwargs.pop('request')
        super(ThirdPartyUserCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['email', 'first_name', 'last_name',
                                'third_party_identifier']
        if get_latest_terms():
            self.fields.keyOrder.append('has_signed_terms')
        #set readonly form fields
        ro = ["third_party_identifier"]
        for f in ro:
            self.fields[f].widget.attrs['readonly'] = True

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
            raise forms.ValidationError(_("This field is required"))
        return email

    def clean_has_signed_terms(self):
        has_signed_terms = self.cleaned_data['has_signed_terms']
        if not has_signed_terms:
            raise forms.ValidationError(_('You have to agree with the terms'))
        return has_signed_terms

    def save(self, commit=True):
        user = super(ThirdPartyUserCreationForm, self).save(commit=False)
        user.set_unusable_password()
        user.renew_token()
        user.provider = get_query(self.request).get('provider')
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
        user = super(
            InvitedThirdPartyUserCreationForm, self).save(commit=False)
        level = user.invitation.inviter.level + 1
        user.level = level
        user.invitations = INVITATIONS_PER_LEVEL.get(level, 0)
        user.email_verified = True
        if commit:
            user.save()
        return user


class ShibbolethUserCreationForm(ThirdPartyUserCreationForm):
    additional_email = forms.CharField(
        widget=forms.HiddenInput(), label='', required=False)

    def __init__(self, *args, **kwargs):
        super(ShibbolethUserCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder.append('additional_email')
        # copy email value to additional_mail in case user will change it
        name = 'email'
        field = self.fields[name]
        self.initial['additional_email'] = self.initial.get(name,
                                                            field.initial)

    def clean_email(self):
        email = self.cleaned_data['email']
        for user in AstakosUser.objects.filter(email=email):
            if user.provider == 'shibboleth':
                raise forms.ValidationError(_("This email is already associated with another shibboleth account."))
            elif not user.is_active:
                raise forms.ValidationError(_("This email is already associated with an inactive account. \
                                              You need to wait to be activated before being able to switch to a shibboleth account."))
        super(ShibbolethUserCreationForm, self).clean_email()
        return email


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
        if 'username' in self.cleaned_data:
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
            raise forms.ValidationError(
                _('You have not entered the correct words'))

    def clean(self):
        super(LoginForm, self).clean()
        if self.user_cache and self.user_cache.provider not in ('local', ''):
            raise forms.ValidationError(_('Local login is not the current authentication method for this account.'))
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
            user.renew_token()
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
    Extends PasswordResetForm by overriding save method:
    passes a custom from_email in send_mail.

    Since Django 1.3 this is useless since ``django.contrib.auth.views.reset_password``
    accepts a from_email argument.
    """
    def clean_email(self):
        email = super(ExtendedPasswordResetForm, self).clean_email()
        try:
            user = AstakosUser.objects.get(email=email, is_active=True)
            if not user.has_usable_password():
                raise forms.ValidationError(
                    _("This account has not a usable password."))
        except AstakosUser.DoesNotExist:
            raise forms.ValidationError(_('That e-mail address doesn\'t have an associated user account. Are you sure you\'ve registered?'))
        return email

    def save(
        self, domain_override=None, email_template_name='registration/password_reset_email.html',
            use_https=False, token_generator=default_token_generator, request=None):
        """
        Generates a one-use only link for resetting password and sends to the user.
        """
        for user in self.users_cache:
            url = reverse('django.contrib.auth.views.password_reset_confirm',
                          kwargs={'uidb36': int_to_base36(user.id),
                                  'token': token_generator.make_token(user)
                                  }
                          )
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
            raise forms.ValidationError(_(u'This email address is already in use. Please supply a different email address.'))
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
            raise forms.ValidationError(_('You have to agree with the terms'))
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
            raise forms.ValidationError(
                _('There is already invitation for this email.'))
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
        super(ExtendedPasswordChangeForm, self).__init__(user, *args, **kwargs)

    def save(self, commit=True):
        if NEWPASSWD_INVALIDATE_TOKEN or self.cleaned_data.get('renew'):
            self.user.renew_token()
        return super(ExtendedPasswordChangeForm, self).save(commit=commit)


class AstakosGroupCreationForm(forms.ModelForm):
    kind = forms.ModelChoiceField(
        queryset=GroupKind.objects.all(),
        label="",
        widget=forms.HiddenInput()
    )
    name = forms.URLField()
    moderation_enabled = forms.BooleanField(
        help_text="Check if you want to approve members participation manually",
        required=False,
        initial=True
    )
    max_participants = forms.IntegerField(
        required=False, min_value=1
    )

    class Meta:
        model = AstakosGroup

    def __init__(self, *args, **kwargs):
        #update QueryDict
        args = list(args)
        qd = args.pop(0).copy()
        members_unlimited = qd.pop('members_unlimited', False)
        members_uplimit = qd.pop('members_uplimit', None)
#         max_participants = None if members_unlimited else members_uplimit
#         qd['max_participants']= max_participants.pop(0) if max_participants else None
        
        #substitue QueryDict
        args.insert(0, qd)
        
        super(AstakosGroupCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['kind', 'name', 'homepage', 'desc',
                                'issue_date', 'expiration_date',
                                'moderation_enabled', 'max_participants']
        def add_fields((k, v)):
            self.fields[k] = forms.IntegerField(
                required=False,
                widget=forms.HiddenInput(),
                min_value=1
            )
        map(add_fields,
            ((k, v) for k,v in qd.iteritems() if k.endswith('_uplimit'))
        )
        
        def add_fields((k, v)):
            self.fields[k] = forms.BooleanField(
                required=False,
                widget=forms.HiddenInput()
            )
        map(add_fields,
            ((k, v) for k,v in qd.iteritems() if k.startswith('is_selected_'))
        )
    
    def policies(self):
        self.clean()
        policies = []
        append = policies.append
        for name, uplimit in self.cleaned_data.iteritems():
            subs = name.split('_uplimit')
            if len(subs) == 2:
                prefix, suffix = subs
                s, sep, r = prefix.partition(RESOURCE_SEPARATOR)
                resource = Resource.objects.get(service__name=s, name=r)
                
                # keep only resource limits for selected resource groups
                if self.cleaned_data.get(
                    'is_selected_%s' % resource.group, True
                ):
                    append(dict(service=s, resource=r, uplimit=uplimit))
        return policies

class AstakosGroupCreationSummaryForm(forms.ModelForm):
    kind = forms.ModelChoiceField(
        queryset=GroupKind.objects.all(),
        label="",
        widget=forms.HiddenInput()
    )
    name = forms.URLField()
    moderation_enabled = forms.BooleanField(
        help_text="Check if you want to approve members participation manually",
        required=False,
        initial=True
    )
    max_participants = forms.IntegerField(
        required=False, min_value=1
    )

    class Meta:
        model = AstakosGroup

    def __init__(self, *args, **kwargs):
        #update QueryDict
        args = list(args)
        qd = args.pop(0).copy()
        members_unlimited = qd.pop('members_unlimited', False)
        members_uplimit = qd.pop('members_uplimit', None)
#         max_participants = None if members_unlimited else members_uplimit
#         qd['max_participants']= max_participants.pop(0) if max_participants else None
        
        #substitue QueryDict
        args.insert(0, qd)
        
        super(AstakosGroupCreationSummaryForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['kind', 'name', 'homepage', 'desc',
                                'issue_date', 'expiration_date',
                                'moderation_enabled', 'max_participants']
        def add_fields((k, v)):
            self.fields[k] = forms.IntegerField(
                required=False,
                widget=forms.TextInput(),
                min_value=1
            )
        map(add_fields,
            ((k, v) for k,v in qd.iteritems() if k.endswith('_uplimit'))
        )
        
        def add_fields((k, v)):
            self.fields[k] = forms.BooleanField(
                required=False,
                widget=forms.HiddenInput()
            )
        map(add_fields,
            ((k, v) for k,v in qd.iteritems() if k.startswith('is_selected_'))
        )
        for f in self.fields.values():
            f.widget = forms.HiddenInput()

    def clean(self):
        super(AstakosGroupCreationSummaryForm, self).clean()
        self.cleaned_data['policies'] = []
        append = self.cleaned_data['policies'].append
        tbd = [f for f in self.fields if f.startswith('is_selected_')]
        for name, uplimit in self.cleaned_data.iteritems():
            subs = name.split('_uplimit')
            if len(subs) == 2:
                tbd.append(name)
                prefix, suffix = subs
                s, sep, r = prefix.partition(RESOURCE_SEPARATOR)
                resource = Resource.objects.get(service__name=s, name=r)
                
                # keep only resource limits for selected resource groups
                if self.cleaned_data.get(
                    'is_selected_%s' % resource.group, True
                ):
                    append(dict(service=s, resource=r, uplimit=uplimit))
        for name in tbd:
            self.cleaned_data.pop(name, None)
        return self.cleaned_data

class AstakosGroupUpdateForm(forms.ModelForm):
    class Meta:
        model = AstakosGroup
        fields = ('homepage', 'desc')


class AddGroupMembersForm(forms.Form):
    q = forms.CharField(
        max_length=800, widget=forms.Textarea, label=_('Add users'),
        help_text=_('Add comma separated user emails, eg. user1@user.com, user2@user.com'),
        required=True)

    def clean(self):
        q = self.cleaned_data.get('q') or ''
        users = q.split(',')
        users = list(u.strip() for u in users if u)
        db_entries = AstakosUser.objects.filter(email__in=users)
        unknown = list(set(users) - set(u.email for u in db_entries))
        if unknown:
            raise forms.ValidationError(
                _('Unknown users: %s' % ','.join(unknown)))
        self.valid_users = db_entries
        return self.cleaned_data

    def get_valid_users(self):
        """Should be called after form cleaning"""
        try:
            return self.valid_users
        except:
            return ()


class AstakosGroupSearchForm(forms.Form):
    q = forms.CharField(max_length=200, label='Search group')


class TimelineForm(forms.Form):
#    entity = forms.CharField(
#        widget=forms.HiddenInput(), label='')
    entity = forms.ModelChoiceField(
        queryset=AstakosUser.objects.filter(is_active=True)
    )
    resource = forms.ModelChoiceField(
        queryset=Resource.objects.all()
    )
    start_date = forms.DateTimeField()
    end_date = forms.DateTimeField()
    details = forms.BooleanField(required=False, label="Detailed Listing")
    operation = forms.ChoiceField(
        label='Charge Method',
        choices=(('', '-------------'),
                 ('charge_usage', 'Charge Usage'),
                 ('charge_traffic', 'Charge Traffic'), )
    )

    def clean(self):
        super(TimelineForm, self).clean()
        d = self.cleaned_data
        if 'resource' in d:
            d['resource'] = str(d['resource'])
        if 'start_date' in d:
            d['start_date'] = d['start_date'].strftime(
                "%Y-%m-%dT%H:%M:%S.%f")[:24]
        if 'end_date' in d:
            d['end_date'] = d['end_date'].strftime("%Y-%m-%dT%H:%M:%S.%f")[:24]
        if 'entity' in d:
            d['entity'] = d['entity'].email
        return d


class AstakosGroupSortForm(forms.Form):
    sort_by = forms.ChoiceField(label='Sort by',
                                choices=(('groupname', 'Name'),
                                         ('kindname', 'Type'),
                                         ('issue_date', 'Issue Date'),
                                         ('expiration_date',
                                          'Expiration Date'),
                                         ('approved_members_num',
                                          'Participants'),
                                         ('is_enabled', 'Status'),
                                         ('moderation_enabled', 'Moderation'),
                                         ('membership_status',
                                          'Enrollment Status')
                                         ),
                                required=False)


class MembersSortForm(forms.Form):
    sort_by = forms.ChoiceField(label='Sort by',
                                choices=(('person__email', 'User Id'),
                                         ('person__first_name', 'Name'),
                                         ('date_joined', 'Status')
                                         ),
                                required=False)


class PickResourceForm(forms.Form):
    resource = forms.ModelChoiceField(
        queryset=Resource.objects.select_related().all()
    )
    resource.widget.attrs["onchange"] = "this.form.submit()"


class ExtendedSetPasswordForm(SetPasswordForm):
    """
    Extends SetPasswordForm by enabling user
    to optionally renew also the token.
    """
    if not NEWPASSWD_INVALIDATE_TOKEN:
        renew = forms.BooleanField(label='Renew token', required=False,
                                   initial=True,
                                   help_text='Unsetting this may result in security risk.')

    def __init__(self, user, *args, **kwargs):
        super(ExtendedSetPasswordForm, self).__init__(user, *args, **kwargs)

    def save(self, commit=True):
        if NEWPASSWD_INVALIDATE_TOKEN or self.cleaned_data.get('renew'):
            if isinstance(self.user, AstakosUser):
                self.user.renew_token()
        return super(ExtendedSetPasswordForm, self).save(commit=commit)
