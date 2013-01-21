import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'synnefo.settings'

from django.conf import settings
from unittest import TestCase, main as test_main
from astakos.im.models import (AstakosUser,
                               Project,
                               ProjectDefinition)

_serial = 0
def get_serial():
    global _serial
    serial = _serial + 1
    _serial = serial
    return serial


def mk_rand_user():
    name = "user-%d" % get_serial()
    user = AstakosUser()
    return user


class BasicTestProjects(TestCase):

    @classmethod
    def setUpClass(cls):
        users = {}
        cls.users = users

        for _ in xrange(5):
            user = mk_rand_user()
            users[user.username] = user

    def test_001_create_definition(self):
        pass

    def test_001_create_project(self):
        pass

if __name__ == '__main__':
    test_main()
