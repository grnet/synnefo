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

import datetime
from astakos.im import models
from astakos.im import functions


def _finalize_astakosuser_object(user, has_signed_terms=False):
    user.fix_username()
    if has_signed_terms:
        user.has_signed_terms = True
        user.date_signed_terms = datetime.datetime.now()

    user.renew_verification_code()
    user.uuid = functions.new_uuid()
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
