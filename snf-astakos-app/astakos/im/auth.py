# Copyright 2013 GRNET S.A. All rights reserved.
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

import datetime
from astakos.im import models
from astakos.im import functions


def _finalize_astakosuser_object(user, has_signed_terms=False):
    user.fix_username()
    if has_signed_terms:
        user.has_signed_terms = True
        user.date_signed_terms = datetime.datetime.now()

    user.renew_verification_code()
    project = functions.make_base_project(user.username)
    user.base_project = project
    user.uuid = project.uuid
    user.renew_token()
    user.save()


def set_local_auth(user):
    user.add_auth_provider('local', auth_backend='astakos')


def make_user(email, first_name="", last_name="", password=None,
              has_signed_terms=False):
    # delete previously unverified accounts
    models.AstakosUser.objects.unverified_namesakes(email).delete()

    user = models.AstakosUser(
        email=email, first_name=first_name, last_name=last_name,
        is_active=False)
    if password is None:
        user.set_unusable_password()
    else:
        user.set_password(password)

    user.date_joined = datetime.datetime.now()
    _finalize_astakosuser_object(user, has_signed_terms)
    return user


def make_local_user(email, **kwargs):
    user = make_user(email, **kwargs)
    set_local_auth(user)
    return user


def extend_superuser(user):
    extended_user = models.AstakosUser(user_ptr_id=user.pk)
    extended_user.__dict__.update(user.__dict__)
    _finalize_astakosuser_object(extended_user, has_signed_terms=True)
    set_local_auth(extended_user)
    return extended_user


def fix_superusers():
    admins = models.User.objects.filter(is_superuser=True)
    fixed = []
    for u in admins:
        try:
            models.AstakosUser.objects.get(user_ptr=u.pk)
        except models.AstakosUser.DoesNotExist:
            fixed.append(extend_superuser(u))
    return fixed
