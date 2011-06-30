# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.


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

        # Check whether the invited user has been added to the database
        added_user = SynnefoUser.objects.filter(name = "Test",
                                                uniq = "test@gmail.com")
        self.assertNotEquals(added_user, None)

        # Re-adding an existing invitation
        try:
            invitations.add_invitation(source, u'', "test@gmail.com")
            self.assertTrue(False)
        except invitations.AlreadyInvited:
            self.assertTrue(True)

        # 
