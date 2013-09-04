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

import astakos.im.messages as astakos_messages

from astakos.im.models import ApprovalTerms
from astakos.im.tests.common import *

from django.core import urlresolvers
from django.utils.translation import ugettext as _

import os


class TestViews(TestCase):

    def test_user_views(self):
        user = get_local_user('user@synnefo.org')
        r = self.client.get(reverse('api_access'), follow=True)
        self.assertRedirects(r, reverse_with_next('api_access'))

        self.client.login(username='user@synnefo.org', password='password')
        r = self.client.get(reverse('api_access'), follow=True)
        self.assertEqual(r.status_code, 200)

        r = self.client.get(reverse('api_access_config'))
        self.assertContains(r, user.auth_token)


class TestApprovalTerms(TestCase):
    def tearDown(self):
        os.remove('terms')

        ApprovalTerms.objects.get(location='terms').delete()

    def test_approval_terms(self):
        r = self.client.get(reverse('latest_terms'), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, _(astakos_messages.NO_APPROVAL_TERMS))

        r = self.client.post(reverse('latest_terms'), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, _(astakos_messages.NO_APPROVAL_TERMS))

        # add terms
        f = open('terms', 'w+')
        f.write('This are some terms')
        f.close()

        terms = ApprovalTerms(location='terms')
        terms.save()

        self.user = get_local_user('user@synnefo.org')
        self.assertTrue(not self.user.signed_terms)
        self.assertTrue(self.user.date_signed_terms is None)
        self.user_client = get_user_client(self.user.username)

        r = self.client.get(reverse('latest_terms'))
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'im/approval_terms.html')
        # assert there is no form
        self.assertNotContains(r, 'I agree with the terms')

        r = self.client.post(reverse('latest_terms'), follow=False)
        self.assertEqual(r.status_code, 302)
        # assert redirect to login
        self.assertTrue('Location' in r)
        self.assertTrue(r['Location'].find(reverse('login')) != -1)

        r = self.user_client.get(reverse('latest_terms'), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'im/approval_terms.html')
        # assert there is form
        self.assertContains(r, 'I agree with the terms')

        r = self.user_client.post(reverse('latest_terms'), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertFormError(r, 'approval_terms_form', 'has_signed_terms',
                             _(astakos_messages.SIGN_TERMS))

        r = self.user_client.post(reverse('latest_terms'),
                                  {'has_signed_terms': True},
                                  follow=True)
        self.assertEqual(r.status_code, 200)

        user = AstakosUser.objects.get(username=self.user.username)
        self.assertTrue(user.signed_terms)
