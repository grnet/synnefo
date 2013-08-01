#!/usr/bin/env python

import os
import sys
from time import sleep

os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'

import astakos
from astakos.im.models import AstakosUser as A


def user_filter(user):
    return A.objects.filter(email__iexact=user.email).count() > 1

argv = sys.argv
argc = len(sys.argv)

if argc < 2:
    print "Usage: ./delete_astakos_users.py <id>..."
    raise SystemExit()

id_list = [int(x) for x in argv[1:]]

print ""
print "This will permanently delete the following users:\n"
print "id: email"
print "--  -----"

users = A.objects.filter(id__in=id_list)
for user in users:
    print "%s: %s" % (user.id, user.email)

print "\nExecute? (yes/no): ",
line = raw_input().rstrip()
if line != 'yes':
    print "\nCancelled"
    raise SystemExit()

print "\nConfirmed."
sleep(2)
for user in users:
    print "deleting %s: %s" % (user.id, user.email)
    user.delete()
