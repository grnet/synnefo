from django.test import TestCase
from django.test.client import Client

import invitations
from synnefo.db.models import SynnefoUser


class InvitationsTestCase(TestCase):

    token = '46e427d657b20defe352804f0eb6f8a2'

    def setUp(self):
        self.client = Client()

    def test_add_invitation(self):
        source = SynnefoUser.objects.filter(auth_token = self.token)[0]
        invitations.add_invitation(source, "Test", "test@gmail.com")

        added_user = SynnefoUser.objects.filter(name = "Test",
                                                uniq = "test@gmail.com")

        self.assertNotEquals(added_user, None)

        invitations.add_invitation(source, u'', "test@gmail.com")
