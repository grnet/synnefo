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

from django import forms
from django.utils.translation import ugettext as _
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.conf import settings
from django.core.validators import email_re
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.template import Context, loader
from django.utils.http import int_to_base36

from hashlib import new as newhasher

from astakos.im.models import AstakosUser
from astakos.im.util import get_current_site

import logging

class LocalUserCreationForm(UserCreationForm):
    """
    Extends the built in UserCreationForm in several ways:
    
    * Adds email, first_name and last_name field.
    * The username field isn't visible and it is assigned a generated id.
    * User created is not active. 
    """
    
    class Meta:
        model = AstakosUser
        fields = ("email", "first_name", "last_name")
    
    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """
        super(LocalUserCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['email', 'first_name', 'last_name',
                                'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if not email:
            raise forms.ValidationError(_("This field is required"))
        try:
            AstakosUser.objects.get(email = email)
            raise forms.ValidationError(_("Email is reserved"))
        except AstakosUser.DoesNotExist:
            return email
    
    def save(self, commit=True):
        """
        Saves the email, first_name and last_name properties, after the normal
        save behavior is complete.
        """
        user = super(LocalUserCreationForm, self).save(commit=False)
        user.renew_token()
        if commit:
            user.save()
        logging.info('Created user %s', user)
        return user

class InvitedLocalUserCreationForm(LocalUserCreationForm):
    """
    Extends the LocalUserCreationForm: adds an inviter readonly field.
    """
    
    inviter = forms.CharField(widget=forms.TextInput(), label=_('Inviter Real Name'))
    
    class Meta:
        model = AstakosUser
        fields = ("email", "first_name", "last_name")
    
    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """
        super(InvitedLocalUserCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['email', 'inviter', 'first_name',
                                'last_name', 'password1', 'password2']
        #set readonly form fields
        self.fields['inviter'].widget.attrs['readonly'] = True
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['username'].widget.attrs['readonly'] = True
    
    def save(self, commit=True):
        user = super(InvitedLocalUserCreationForm, self).save(commit=False)
        level = user.invitation.inviter.level + 1
        user.level = level
        user.invitations = settings.INVITATIONS_PER_LEVEL[level]
        if commit:
            user.save()
        return user

class LoginForm(AuthenticationForm):
    username = forms.EmailField(label=_("Email"))

class ProfileForm(forms.ModelForm):
    """
    Subclass of ``ModelForm`` for permiting user to edit his/her profile.
    Most of the fields are readonly since the user is not allowed to change them.
    
    The class defines a save method which sets ``is_verified`` to True so as the user
    during the next login will not to be redirected to profile page.
    """
    class Meta:
        model = AstakosUser
        exclude = ('is_active', 'is_superuser', 'is_staff', 'is_verified', 'groups', 'user_permissions')
    
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        ro_fields = ('username','date_joined', 'updated', 'auth_token',
                     'auth_token_created', 'auth_token_expires', 'invitations',
                     'level', 'last_login', 'email', )
        if instance and instance.id:
            for field in ro_fields:
                if isinstance(self.fields[field].widget, forms.CheckboxInput):
                    self.fields[field].widget.attrs['disabled'] = True
                self.fields[field].widget.attrs['readonly'] = True
    
    def save(self, commit=True):
        user = super(ProfileForm, self).save(commit=False)
        user.is_verified = True
        if commit:
            user.save()
        return user

class ThirdPartyUserCreationForm(ProfileForm):
    class Meta:
        model = AstakosUser
        fields = ('email', 'last_name', 'first_name', 'affiliation', 'provider', 'third_party_identifier')
    
    def __init__(self, *args, **kwargs):
        super(ThirdPartyUserCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['email']
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if not email:
            raise forms.ValidationError(_("This field is required"))
        try:
            user = AstakosUser.objects.get(email = email)
            raise forms.ValidationError(_("Email is reserved"))
        except AstakosUser.DoesNotExist:
            return email
    
    def save(self, commit=True):
        user = super(ThirdPartyUserCreationForm, self).save(commit=False)
        user.verified = False
        user.renew_token()
        if commit:
            user.save()
        logging.info('Created user %s', user)
        return user

class InvitedThirdPartyUserCreationForm(ThirdPartyUserCreationForm):
    def __init__(self, *args, **kwargs):
        super(InvitedThirdPartyUserCreationForm, self).__init__(*args, **kwargs)
        #set readonly form fields
        self.fields['email'].widget.attrs['readonly'] = True

class FeedbackForm(forms.Form):
    """
    Form for writing feedback.
    """
    feedback_msg = forms.CharField(widget=forms.Textarea(),
                                label=u'Message', required=False)
    feedback_data = forms.CharField(widget=forms.Textarea(),
                                label=u'Data', required=False)

class SendInvitationForm(forms.Form):
    """
    Form for sending an invitations
    """
    
    email = forms.EmailField(required = True, label = 'Email address')
    first_name = forms.EmailField(label = 'First name')
    last_name = forms.EmailField(label = 'Last name')

class ExtendedPasswordResetForm(PasswordResetForm):
    """
    Extends PasswordResetForm by overriding save method:
    passes a custom from_email in send_mail.
    
    Since Django 1.3 this is useless since ``django.contrib.auth.views.reset_password``
    accepts a from_email argument.
    """
    def save(self, domain_override=None, email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator, request=None):
        """
        Generates a one-use only link for resetting password and sends to the user.
        """
        for user in self.users_cache:
            site_name, sitedomain = get_current_site(request, use_https=use_https)
            t = loader.get_template(email_template_name)
            c = {
                'email': user.email,
                'domain': sitedomain.split('://')[-1],
                'site_name': site_name,
                'uid': int_to_base36(user.id),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': use_https and 'https' or 'http',
            }
            from_email = settings.DEFAULT_FROM_EMAIL % site_name
            send_mail(_("Password reset on %s") % site_name,
                t.render(Context(c)), from_email, [user.email])
