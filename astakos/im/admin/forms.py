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

from astakos.im.models import AstakosUser
from astakos.im.forms import LocalUserCreationForm

import logging

class AdminProfileForm(forms.ModelForm):
    """
    Subclass of ``ModelForm`` for permiting user to edit his/her profile.
    Most of the fields are readonly since the user is not allowed to change them.
    
    The class defines a save method which sets ``is_verified`` to True so as the user
    during the next login will not to be redirected to profile page.
    """
    quota = forms.CharField(label=_('Quota (GiB)'))
    
    class Meta:
        model = AstakosUser
        fields = ('email', 'first_name', 'last_name', 'is_superuser',
                  'affiliation',  'is_active', 'invitations', 'quota',
                  'auth_token', 'auth_token_created', 'auth_token_expires',
                  'date_joined', 'updated')
    
    def __init__(self, *args, **kwargs):
        super(AdminProfileForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        ro_fields = ('date_joined', 'auth_token', 'auth_token_created',
                     'auth_token_expires', 'updated', 'email')
        if instance and instance.id:
            for field in ro_fields:
                self.fields[field].widget.attrs['readonly'] = True
        user = kwargs['instance']
        if user:
            quota = lambda x: int(x) / 1024 ** 3
            self.fields['quota'].widget.attrs['value'] = quota(user.quota)
    
    def save(self, commit=True):
        user = super(AdminProfileForm, self).save(commit=False)
        quota = lambda x: int(x or 0) * (1024 ** 3)
        user.quota = quota(self.cleaned_data['quota'])
        user.save()

class AdminUserCreationForm(LocalUserCreationForm):
    class Meta:
        model = AstakosUser
        fields = ("email", "first_name", "last_name", "is_superuser",
                  "is_active", "affiliation")
    
    def __init__(self, *args, **kwargs):
        """
        Changes the order of fields, and removes the username field.
        """
        super(AdminUserCreationForm, self).__init__(*args, **kwargs)
        self.fields.keyOrder = ['email', 'first_name', 'last_name',
                                'is_superuser', 'is_active', 'affiliation',
                                'password1', 'password2']
    
    def save(self, commit=True):
        user = super(AdminUserCreationForm, self).save(commit=False)
        user.renew_token()
        if commit:
            user.save()
        logging.info('Created user %s', user)
        return user