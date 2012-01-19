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
from django.conf import settings

from astakos.im.models import User

openid_providers = (
('Google','https://www.google.com/accounts/o8/id'),
('Yahoo', 'http://yahoo.com/'),
('AOL','http://openid.aol.com/%s/'),
('OpenID', None),
('MyOpenID','http://%s.myopenid.com/'),
('LiveJournal', 'http://%s.livejournal.com/'),
('Flickr', 'http://flickr.com/%s/'),
('Technorati', 'http://technorati.com/people/technorati/%s/'),
('Wordpress', 'http://%s.wordpress.com/'),
('Blogger', 'http://%s.blogspot.com/'),
('Verisign', 'http://%s.pip.verisignlabs.com/'),
('Vidoop', 'http://%s.myvidoop.com/'),
('ClaimID','http://claimid.com/%s')    
)

class RegisterForm(forms.Form):
    uniq = forms.CharField(widget=forms.widgets.TextInput())
    provider = forms.CharField(widget=forms.TextInput(),
                                label=u'Identity Provider')
    email = forms.EmailField(widget=forms.TextInput(),
                             label=_('Email address'))
    realname = forms.CharField(widget=forms.TextInput(),
                                label=u'Real Name')
    
    def __init__(self, *args, **kwargs):
        super(forms.Form, self).__init__(*args, **kwargs)
        
        #set readonly form fields
        self.fields['provider'].widget.attrs['readonly'] = True
    
    def clean_uniq(self):
        """
        Validate that the uniq is alphanumeric and is not already
        in use.
        
        """
        try:
            user = User.objects.get(uniq__iexact=self.cleaned_data['uniq'])
        except User.DoesNotExist:
            return self.cleaned_data['uniq']
        raise forms.ValidationError(_("A user with that uniq already exists."))

class ShibbolethRegisterForm(RegisterForm):
    pass

class TwitterRegisterForm(RegisterForm):
    pass

class OpenidRegisterForm(RegisterForm):
    openidurl = forms.ChoiceField(widget=forms.Select,
                                  choices=((url, l) for l, url in openid_providers))

class LocalRegisterForm(RegisterForm):
    """ local signup form"""
    password = forms.CharField(widget=forms.PasswordInput(render_value=False),
                                label=_('Password'))
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False),
                                label=_('Confirm Password'))
    
    def __init__(self, *args, **kwargs):
        super(LocalRegisterForm, self).__init__(*args, **kwargs)
    
    def clean_uniq(self):
        """
        Validate that the uniq is alphanumeric and is not already
        in use.
        
        """
        try:
            user = User.objects.get(uniq__iexact=self.cleaned_data['uniq'])
        except User.DoesNotExist:
            return self.cleaned_data['uniq']
        raise forms.ValidationError(_("A user with that uniq already exists."))
    
    def clean(self):
        """
        Verifiy that the values entered into the two password fields
        match. Note that an error here will end up in
        ``non_field_errors()`` because it doesn't apply to a single
        field.
        
        """
        if 'password' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return self.cleaned_data

class InvitedRegisterForm(RegisterForm):
    inviter = forms.CharField(widget=forms.TextInput(),
                                label=_('Inviter Real Name'))
    
    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        
        #set readonly form fields
        self.fields['uniq'].widget.attrs['readonly'] = True
        self.fields['inviter'].widget.attrs['readonly'] = True
        self.fields['provider'].widget.attrs['provider'] = True

class InvitedLocalRegisterForm(LocalRegisterForm, InvitedRegisterForm):
    pass

class InvitedOpenidRegisterForm(OpenidRegisterForm, InvitedRegisterForm):
    pass

class InvitedTwitterRegisterForm(TwitterRegisterForm, InvitedRegisterForm):
    pass

class InvitedShibbolethRegisterForm(ShibbolethRegisterForm, InvitedRegisterForm):
    pass
