#!/usr/bin/env python
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'

import astakos
from astakos.im.models import AstakosUser as A


def user_filter(user):
    return A.objects.filter(email__iexact=user.email).count() > 1

all_users = list(A.objects.all())
userlist = [(str(u.pk) + ': ' + str(u.email)) for u in
            filter(user_filter, all_users)]

sys.stderr.write("id: email\n")
print "\n".join(userlist)
