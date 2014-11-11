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

        self.user = get_local_user('user@synnefo.org',
                                   has_signed_terms=False,
                                   date_signed_terms=None)
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
