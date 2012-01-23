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

from django import forms
from django.utils.translation import ugettext as _
from django.contrib.auth.forms import UserCreationForm
from django.conf import settings
from hashlib import new as newhasher

from astakos.im.models import AstakosUser
from astakos.im.util import get_or_create_user

import logging

class UniqueUserEmailField(forms.EmailField):
    """
    An EmailField which only is valid if no User has that email.
    """
    def validate(self, value):
        super(forms.EmailField, self).validate(value)
        try:
            AstakosUser.objects.get(email = value)
            raise forms.ValidationError("Email already exists")
        except AstakosUser.MultipleObjectsReturned:
            raise forms.ValidationError("Email already exists")
        except AstakosUser.DoesNotExist:
            pass

class ExtendedUserCreationForm(UserCreationForm):
    """
    Extends the built in UserCreationForm in several ways:
    
    * Adds an email field, which uses the custom UniqueUserEmailField.
    * The username field isn't visible and it is assigned the email value.
    * first_name and last_name fields are added.
    """
    
    username = forms.CharField(required = False, max_length = 30)
    email = UniqueUserEmailField(required = True, label = 'Email address')
    first_name = forms.CharField(required = False, max_length = 30)
    last_name = forms.CharField(required = False, max_length = 30)
    
    class Meta:
        model = AstakosUser
        fields = ("username",)
    
    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """
        super(ExtendedUserCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['email', 'first_name', 'last_name',
                                'password1', 'password2']
    
    def clean(self, *args, **kwargs):
        """
        Normal cleanup + username generation.
        """
        cleaned_data = super(ExtendedUserCreationForm, self).clean(*args, **kwargs)
        if cleaned_data.has_key('email'):
            cleaned_data['username'] = cleaned_data['email']
        return cleaned_data
        
    def save(self, commit=True):
        """
        Saves the email, first_name and last_name properties, after the normal
        save behavior is complete.
        """
        user = super(ExtendedUserCreationForm, self).save(commit=False)
        user.renew_token()
        user.save()
        logging.info('Created user %s', user)
        return user

class InvitedExtendedUserCreationForm(UserCreationForm):
    """
    Extends the built in UserCreationForm in several ways:
    
    * Adds an email field, which uses the custom UniqueUserEmailField.
    * The username field isn't visible and it is assigned the email value.
    * first_name and last_name fields are added.
    """
    
    username = forms.CharField(required = False, max_length = 30)
    email = UniqueUserEmailField(required = True, label = 'Email address')
    first_name = forms.CharField(required = False, max_length = 30)
    last_name = forms.CharField(required = False, max_length = 30)
    inviter = forms.CharField(widget=forms.TextInput(), label=_('Inviter Real Name'))
    
    class Meta:
        model = AstakosUser
        fields = ("username",)
    
    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """
        super(InvitedExtendedUserCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['email', 'inviter', 'first_name', 'last_name',
                                'password1', 'password2']
        #set readonly form fields
        self.fields['inviter'].widget.attrs['readonly'] = True
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['username'].widget.attrs['readonly'] = True
    
    def clean(self, *args, **kwargs):
        """
        Normal cleanup + username generation.
        """
        cleaned_data = super(UserCreationForm, self).clean(*args, **kwargs)
        if cleaned_data.has_key('email'):
            cleaned_data['username'] = cleaned_data['email']
        return cleaned_data
        
    def save(self, commit=True):
        """
        Saves the email, first_name and last_name properties, after the normal
        save behavior is complete.
        """
        user = super(InvitedExtendedUserCreationForm, self).save(commit=False)
        user.renew_token()
        user.save()
        logging.info('Created user %s', user)
        return user

class ProfileForm(forms.ModelForm):
    """
    Subclass of ``ModelForm`` for permiting user to edit his/her profile.
    Most of the fields are readonly since the user is not allowed to change them.
    
    The class defines a save method which sets ``is_verified`` to True so as the user
    during the next login will not to be redirected to profile page.
    """
    class Meta:
        model = AstakosUser
        exclude = ('groups', 'user_permissions')
    
    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        ro_fields = ('username','date_joined', 'updated', 'auth_token',
                     'auth_token_created', 'auth_token_expires', 'invitations',
                     'level', 'last_login', 'email', 'is_active', 'is_superuser',
                     'is_staff')
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


class FeedbackForm(forms.Form):
    """
    Form for writing feedback.
    """
    feedback_msg = forms.CharField(widget=forms.Textarea(),
                                label=u'Message', required=False)
    feedback_data = forms.CharField(widget=forms.Textarea(),
                                label=u'Data', required=False)
    