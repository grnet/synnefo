#!/usr/bin/env python
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'

import astakos
from astakos.im.models import AstakosUser as A


def user_filter(user):
    return A.objects.filter(email__iexact=user.email).count() > 1

all_users = list(A.objects.all())
userlist = [(str(u.pk) + ': ' + str(u.email) + '(' + str(u.is_active) + ', ' +
             str(u.date_joined) + ')') for u in filter(user_filter, all_users)]

sys.stderr.write("id email (is_active, creation date)\n")
print "\n".join(userlist)
