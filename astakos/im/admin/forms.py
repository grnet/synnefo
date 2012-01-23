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

class AdminProfileForm(forms.ModelForm):
    """
    Subclass of ``ModelForm`` for permiting user to edit his/her profile.
    Most of the fields are readonly since the user is not allowed to change them.
    
    The class defines a save method which sets ``is_verified`` to True so as the user
    during the next login will not to be redirected to profile page.
    """
    class Meta:
        model = AstakosUser
    
    def __init__(self, *args, **kwargs):
        super(AdminProfileForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        ro_fields = ('username','date_joined', 'auth_token', 'last_login', 'email')
        if instance and instance.id:
            for field in ro_fields:
                if isinstance(self.fields[field].widget, forms.CheckboxInput):
                    self.fields[field].widget.attrs['disabled'] = True
                self.fields[field].widget.attrs['readonly'] = True