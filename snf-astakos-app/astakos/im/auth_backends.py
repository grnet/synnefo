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

from django.contrib.auth.backends import ModelBackend
from django.core.validators import email_re

from astakos.im.models import AstakosUser


class TokenBackend(ModelBackend):
    """
    AuthenticationBackend used to authenticate using token instead
    """
    def authenticate(self, email=None, auth_token=None):
        try:
            user = AstakosUser.objects.get(email=email, is_active=True)
            if user.auth_token == auth_token:
                return user
        except AstakosUser.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return AstakosUser.objects.get(pk=user_id)
        except AstakosUser.DoesNotExist:
            return None


class EmailBackend(ModelBackend):
    """
    If the ``username`` parameter is actually an email uses email to authenticate
    the user else tries the username.

    Used from ``astakos.im.forms.LoginForm`` to authenticate.
    """
    def authenticate(self, username=None, password=None):
        #If username is an email address, then try to pull it up
        if email_re.search(username):
            try:
                user = AstakosUser.objects.get(email=username, is_active=True)
            except AstakosUser.DoesNotExist:
                return None
        else:
            #We have a non-email address username we
            #should try username
            try:
                user = AstakosUser.objects.get(username=username)
            except AstakosUser.DoesNotExist:
                return None
        if user.check_password(password):
            return user

    def get_user(self, user_id):
        try:
            return AstakosUser.objects.get(pk=user_id)
        except AstakosUser.DoesNotExist:
            return None
