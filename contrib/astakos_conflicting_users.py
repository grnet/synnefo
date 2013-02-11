import os
import sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'

from django.conf import settings
from astakos.im.models import AstakosUser

def duplicate_users():
    for u in AstakosUser.objects.filter():
        if AstakosUser.objects.filter(email__iexact=u.email).count() > 1:
            print AstakosUser.objects.filter(email__iexact=u.email).values('pk',
                                                                    'email',
                                                                    'is_active')

if len(sys.argv) == 2:
    pk = int(sys.argv[1])
    user = AstakosUser.objects.get(pk=pk)
    if AstakosUser.objects.filter(email__iexact=user.email).count() == 1:
        print "No duplicate emails found for user %s" % (user)
        exit()
    user = AstakosUser.objects.get(pk=pk)
    print "Deleting user %r" % (user)
    user.delete()
    exit()
else:
    duplicate_users()

