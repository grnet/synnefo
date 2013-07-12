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

import urlparse
import urllib

from astakos.im.tests.common import *

ui_url = lambda url: '/' + astakos_settings.BASE_PATH + '/ui/%s' % url


class ShibbolethTests(TestCase):
    """
    Testing shibboleth authentication.
    """

    def setUp(self):
        self.client = ShibbolethClient()
        astakos_settings.IM_MODULES = ['local', 'shibboleth']
        astakos_settings.MODERATION_ENABLED = True

    def tearDown(self):
        AstakosUser.objects.all().delete()

    @im_settings(FORCE_PROFILE_UPDATE=False)
    def test_create_account(self):

        client = ShibbolethClient()

        # shibboleth views validation
        # eepn required
        r = client.get(ui_url('login/shibboleth?'), follow=True)
        self.assertContains(r, messages.SHIBBOLETH_MISSING_EPPN % {
            'domain': astakos_settings.BASE_HOST,
            'contact_email': settings.CONTACT_EMAIL
        })
        client.set_tokens(eppn="kpapeppn")

        astakos_settings.SHIBBOLETH_REQUIRE_NAME_INFO = True
        # shibboleth user info required
        r = client.get(ui_url('login/shibboleth?'), follow=True)
        self.assertContains(r, messages.SHIBBOLETH_MISSING_NAME)
        astakos_settings.SHIBBOLETH_REQUIRE_NAME_INFO = False

        # shibboleth logged us in
        client.set_tokens(mail="kpap@synnefo.org", eppn="kpapeppn",
                          cn="Kostas Papadimitriou",
                          ep_affiliation="Test Affiliation")
        r = client.get(ui_url('login/shibboleth?'), follow=True)
        token = PendingThirdPartyUser.objects.get().token
        self.assertRedirects(r, ui_url('signup?third_party_token=%s' % token))
        self.assertEqual(r.status_code, 200)

        # a new pending user created
        pending_user = PendingThirdPartyUser.objects.get(
            third_party_identifier="kpapeppn")
        self.assertEqual(PendingThirdPartyUser.objects.count(), 1)
        # keep the token for future use
        token = pending_user.token
        # from now on no shibboleth headers are sent to the server
        client.reset_tokens()

        # this is the old way, it should fail, to avoid pending user take over
        r = client.get(ui_url('shibboleth/signup/%s' % pending_user.username))
        self.assertEqual(r.status_code, 404)

        # this is the signup unique url associated with the pending user
        # created
        r = client.get(ui_url('signup/?third_party_token=%s' % token))
        identifier = pending_user.third_party_identifier
        post_data = {'third_party_identifier': identifier,
                     'first_name': 'Kostas',
                     'third_party_token': token,
                     'last_name': 'Mitroglou',
                     'provider': 'shibboleth'}

        signup_url = reverse('signup')

        # invlid email
        post_data['email'] = 'kpap'
        r = client.post(signup_url, post_data)
        self.assertContains(r, token)

        # existing email
        existing_user = get_local_user('test@test.com')
        post_data['email'] = 'test@test.com'
        r = client.post(signup_url, post_data)
        self.assertContains(r, messages.EMAIL_USED)
        existing_user.delete()

        # and finally a valid signup
        post_data['email'] = 'kpap@synnefo.org'
        r = client.post(signup_url, post_data, follow=True)
        self.assertContains(r, messages.VERIFICATION_SENT)

        # entires commited as expected
        self.assertEqual(AstakosUser.objects.count(), 1)
        self.assertEqual(AstakosUserAuthProvider.objects.count(), 1)
        self.assertEqual(PendingThirdPartyUser.objects.count(), 0)

        # provider info stored
        provider = AstakosUserAuthProvider.objects.get(module="shibboleth")
        self.assertEqual(provider.affiliation, 'Test Affiliation')
        self.assertEqual(provider.info['email'], u'kpap@synnefo.org')
        self.assertEqual(provider.info['eppn'], u'kpapeppn')
        self.assertEqual(provider.info['name'], u'Kostas Papadimitriou')
        self.assertTrue('headers' in provider.info)

        # login (not activated yet)
        client.set_tokens(mail="kpap@synnefo.org", eppn="kpapeppn",
                          cn="Kostas Papadimitriou")
        r = client.get(ui_url("login/shibboleth?"), follow=True)
        self.assertContains(r, 'is pending moderation')

        # admin activates the user
        u = AstakosUser.objects.get(username="kpap@synnefo.org")
        backend = activation_backends.get_backend()
        activation_result = backend.verify_user(u, u.verification_code)
        activation_result = backend.accept_user(u)
        self.assertFalse(activation_result.is_error())
        backend.send_result_notifications(activation_result, u)
        self.assertEqual(u.is_active, True)

        # we see our profile
        r = client.get(ui_url("login/shibboleth?"), follow=True)
        self.assertRedirects(r, ui_url('landing'))
        self.assertEqual(r.status_code, 200)

    def test_existing(self):
        """
        Test adding of third party login to an existing account
        """

        # this is our existing user
        existing_user = get_local_user('kpap@synnefo.org')
        existing_inactive = get_local_user('kpap-inactive@synnefo.org')
        existing_inactive.is_active = False
        existing_inactive.save()

        existing_unverified = get_local_user('kpap-unverified@synnefo.org')
        existing_unverified.is_active = False
        existing_unverified.activation_sent = None
        existing_unverified.email_verified = False
        existing_unverified.is_verified = False
        existing_unverified.save()

        client = ShibbolethClient()
        # shibboleth logged us in, notice that we use different email
        client.set_tokens(mail="kpap@shibboleth.gr", eppn="kpapeppn",
                          cn="Kostas Papadimitriou", )
        r = client.get(ui_url("login/shibboleth?"), follow=True)

        # a new pending user created
        pending_user = PendingThirdPartyUser.objects.get()
        token = pending_user.token
        self.assertEqual(PendingThirdPartyUser.objects.count(), 1)
        pending_key = pending_user.token
        client.reset_tokens()
        self.assertRedirects(r, ui_url("signup?third_party_token=%s" % token))

        form = r.context['login_form']
        signupdata = copy.copy(form.initial)
        signupdata['email'] = 'kpap@synnefo.org'
        signupdata['third_party_token'] = token
        signupdata['provider'] = 'shibboleth'
        signupdata.pop('id', None)

        # the email exists to another user
        r = client.post(ui_url("signup"), signupdata)
        self.assertContains(r, "There is already an account with this email "
                               "address")
        # change the case, still cannot create
        signupdata['email'] = 'KPAP@synnefo.org'
        r = client.post(ui_url("signup"), signupdata)
        self.assertContains(r, "There is already an account with this email "
                               "address")
        # inactive user
        signupdata['email'] = 'KPAP-inactive@synnefo.org'
        r = client.post(ui_url("signup"), signupdata)
        self.assertContains(r, "There is already an account with this email "
                               "address")

        # unverified user, this should pass, old entry will be deleted
        signupdata['email'] = 'KAPAP-unverified@synnefo.org'
        r = client.post(ui_url("signup"), signupdata)

        post_data = {'password': 'password',
                     'username': 'kpap@synnefo.org'}
        r = client.post(ui_url('local'), post_data, follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        client.set_tokens(mail="kpap@shibboleth.gr", eppn="kpapeppn",
                          cn="Kostas Papadimitriou", )
        r = client.get(ui_url("login/shibboleth?"), follow=True)
        self.assertContains(r, "enabled for this account")
        client.reset_tokens()

        user = existing_user
        self.assertTrue(user.has_auth_provider('shibboleth'))
        self.assertTrue(user.has_auth_provider('local',
                                               auth_backend='astakos'))
        client.logout()

        # look Ma, i can login with both my shibboleth and local account
        client.set_tokens(mail="kpap@shibboleth.gr", eppn="kpapeppn",
                          cn="Kostas Papadimitriou")
        r = client.get(ui_url("login/shibboleth?"), follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue(r.context['request'].user.email == "kpap@synnefo.org")
        self.assertRedirects(r, ui_url('landing'))
        self.assertEqual(r.status_code, 200)
        client.logout()
        client.reset_tokens()

        # logged out
        r = client.get(ui_url("profile"), follow=True)
        self.assertFalse(r.context['request'].user.is_authenticated())

        # login with local account also works
        post_data = {'password': 'password',
                     'username': 'kpap@synnefo.org'}
        r = self.client.post(ui_url('local'), post_data, follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue(r.context['request'].user.email == "kpap@synnefo.org")
        self.assertRedirects(r, ui_url('landing'))
        self.assertEqual(r.status_code, 200)

        # cannot add the same eppn
        client.set_tokens(mail="secondary@shibboleth.gr", eppn="kpapeppn",
                          cn="Kostas Papadimitriou", )
        r = client.get(ui_url("login/shibboleth?"), follow=True)
        self.assertRedirects(r, ui_url('landing'))
        self.assertTrue(r.status_code, 200)
        self.assertEquals(existing_user.auth_providers.count(), 2)

        # only one allowed by default
        client.set_tokens(mail="secondary@shibboleth.gr", eppn="kpapeppn2",
                          cn="Kostas Papadimitriou", ep_affiliation="affil2")
        prov = auth_providers.get_provider('shibboleth')
        r = client.get(ui_url("login/shibboleth?"), follow=True)
        self.assertContains(r, "Failed to add")
        self.assertRedirects(r, ui_url('profile'))
        self.assertTrue(r.status_code, 200)
        self.assertEquals(existing_user.auth_providers.count(), 2)
        client.logout()
        client.reset_tokens()

        # cannot login with another eppn
        client.set_tokens(mail="kpap@synnefo.org", eppn="kpapeppninvalid",
                          cn="Kostas Papadimitriou")
        r = client.get(ui_url("login/shibboleth?"), follow=True)
        self.assertFalse(r.context['request'].user.is_authenticated())

        # cannot

        # lets remove local password
        user = AstakosUser.objects.get(username="kpap@synnefo.org",
                                       email="kpap@synnefo.org")
        remove_local_url = user.get_auth_provider('local').get_remove_url
        remove_shibbo_url = user.get_auth_provider('shibboleth',
                                                   'kpapeppn').get_remove_url
        client.set_tokens(mail="kpap@shibboleth.gr", eppn="kpapeppn",
                          cn="Kostas Papadimtriou")
        r = client.get(ui_url("login/shibboleth?"), follow=True)
        client.reset_tokens()

        # only POST is allowed (for CSRF protection)
        r = client.get(remove_local_url, follow=True)
        self.assertEqual(r.status_code, 405)

        r = client.post(remove_local_url, follow=True)
        # 2 providers left
        self.assertEqual(user.auth_providers.count(), 1)
        # cannot remove last provider
        r = client.post(remove_shibbo_url)
        self.assertEqual(r.status_code, 403)
        self.client.logout()

        # cannot login using local credentials (notice we use another client)
        post_data = {'password': 'password',
                     'username': 'kpap@synnefo.org'}
        r = self.client.post(ui_url('local'), post_data, follow=True)
        self.assertFalse(r.context['request'].user.is_authenticated())

        # we can reenable the local provider by setting a password
        r = client.get(ui_url("password_change"), follow=True)
        r = client.post(ui_url("password_change"), {'new_password1': '111',
                                                'new_password2': '111'},
                        follow=True)
        user = r.context['request'].user
        self.assertTrue(user.has_auth_provider('local'))
        self.assertTrue(user.has_auth_provider('shibboleth'))
        self.assertTrue(user.check_password('111'))
        self.assertTrue(user.has_usable_password())

        # change password via profile form
        r = client.post(ui_url("profile"), {
            'old_password': '111',
            'new_password': '',
            'new_password2': '',
            'change_password': 'on',
        }, follow=False)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context['profile_form'].is_valid())

        self.client.logout()

        # now we can login
        post_data = {'password': '111',
                     'username': 'kpap@synnefo.org'}
        r = self.client.post(ui_url('local'), post_data, follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())

        client.reset_tokens()

        # we cannot take over another shibboleth identifier
        user2 = get_local_user('another@synnefo.org')
        user2.add_auth_provider('shibboleth', identifier='existingeppn')
        # login
        client.set_tokens(mail="kpap@shibboleth.gr", eppn="kpapeppn",
                          cn="Kostas Papadimitriou")
        r = client.get(ui_url("login/shibboleth?"), follow=True)
        # try to assign existing shibboleth identifier of another user
        client.set_tokens(mail="kpap_second@shibboleth.gr",
                          eppn="existingeppn", cn="Kostas Papadimitriou")
        r = client.get(ui_url("login/shibboleth?"), follow=True)
        self.assertContains(r, "is already in use")


class TestLocal(TestCase):

    def setUp(self):
        settings.ADMINS = (('admin', 'support@cloud.synnefo.org'),)
        settings.SERVER_EMAIL = 'no-reply@synnefo.org'
        self._orig_moderation = astakos_settings.MODERATION_ENABLED
        settings.ASTAKOS_MODERATION_ENABLED = True

    def tearDown(self):
        settings.ASTAKOS_MODERATION_ENABLED = self._orig_moderation
        AstakosUser.objects.all().delete()

    def test_no_moderation(self):
        # disable moderation
        astakos_settings.MODERATION_ENABLED = False

        # create a new user
        r = self.client.get(ui_url("signup"))
        self.assertEqual(r.status_code, 200)
        data = {'email': 'kpap@synnefo.org', 'password1': 'password',
                'password2': 'password', 'first_name': 'Kostas',
                'last_name': 'Mitroglou', 'provider': 'local'}
        r = self.client.post(ui_url("signup"), data)

        # user created
        self.assertEqual(AstakosUser.objects.count(), 1)
        user = AstakosUser.objects.get(username="kpap@synnefo.org",
                                       email="kpap@synnefo.org")
        self.assertEqual(user.username, 'kpap@synnefo.org')
        self.assertEqual(user.has_auth_provider('local'), True)
        self.assertFalse(user.is_active)

        # user (but not admin) gets notified
        self.assertEqual(len(get_mailbox('support@cloud.synnefo.org')), 0)
        self.assertEqual(len(get_mailbox('kpap@synnefo.org')), 1)
        astakos_settings.MODERATION_ENABLED = True

    def test_email_case(self):
        data = {
            'email': 'kPap@synnefo.org',
            'password1': '1234',
            'password2': '1234'
        }

        form = forms.LocalUserCreationForm(data)
        self.assertTrue(form.is_valid())
        user = form.save()
        form.store_user(user, {})

        u = AstakosUser.objects.get()
        self.assertEqual(u.email, 'kPap@synnefo.org')
        self.assertEqual(u.username, 'kpap@synnefo.org')
        u.is_active = True
        u.email_verified = True
        u.save()

        data = {'username': 'kpap@synnefo.org', 'password': '1234'}
        login = forms.LoginForm(data=data)
        self.assertTrue(login.is_valid())

        data = {'username': 'KpaP@synnefo.org', 'password': '1234'}
        login = forms.LoginForm(data=data)
        self.assertTrue(login.is_valid())

        data = {
            'email': 'kpap@synnefo.org',
            'password1': '1234',
            'password2': '1234'
        }
        form = forms.LocalUserCreationForm(data)
        self.assertFalse(form.is_valid())

    @im_settings(HELPDESK=(('support', 'support@synnefo.org'),),
                 FORCE_PROFILE_UPDATE=False, MODERATION_ENABLED=True)
    def test_local_provider(self):
        self.helpdesk_email = astakos_settings.HELPDESK[0][1]

        # create a user
        r = self.client.get(ui_url("signup"))
        self.assertEqual(r.status_code, 200)
        data = {'email': 'kpap@synnefo.org', 'password1': 'password',
                'password2': 'password', 'first_name': 'Kostas',
                'last_name': 'Mitroglou', 'provider': 'local'}
        r = self.client.post(ui_url("signup"), data)

        # user created
        self.assertEqual(AstakosUser.objects.count(), 1)
        user = AstakosUser.objects.get(username="kpap@synnefo.org",
                                       email="kpap@synnefo.org")
        self.assertEqual(user.username, 'kpap@synnefo.org')
        self.assertEqual(user.has_auth_provider('local'), True)
        self.assertFalse(user.is_active)  # not activated
        self.assertFalse(user.email_verified)  # not verified
        self.assertTrue(user.activation_sent)  # activation automatically sent
        self.assertFalse(user.moderated)
        self.assertFalse(user.email_verified)

        # admin gets notified and activates the user from the command line
        self.assertEqual(len(get_mailbox('kpap@synnefo.org')), 1)
        r = self.client.post(ui_url('local'), {'username': 'kpap@synnefo.org',
                                           'password': 'password'},
                             follow=True)
        self.assertContains(r, messages.VERIFICATION_SENT)
        backend = activation_backends.get_backend()

        user = AstakosUser.objects.get(username="kpap@synnefo.org")
        backend.send_user_verification_email(user)

        # user activation fields updated and user gets notified via email
        user = AstakosUser.objects.get(pk=user.pk)
        self.assertTrue(user.activation_sent)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.is_active)
        self.assertEqual(len(get_mailbox('kpap@synnefo.org')), 2)

        # user forgot she got registered and tries to submit registration
        # form. Notice the upper case in email
        data = {'email': 'KPAP@synnefo.org', 'password1': 'password',
                'password2': 'password', 'first_name': 'Kostas',
                'last_name': 'Mitroglou', 'provider': 'local'}
        r = self.client.post(ui_url("signup"), data, follow=True)
        self.assertRedirects(r, reverse('login'))
        self.assertContains(r, messages.VERIFICATION_SENT)

        user = AstakosUser.objects.get()
        # previous user replaced
        self.assertTrue(user.activation_sent)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.is_active)
        self.assertEqual(len(get_mailbox('KPAP@synnefo.org')), 1)

        # hmmm, email exists; lets request a password change
        r = self.client.get(ui_url('local/password_reset'))
        self.assertEqual(r.status_code, 200)
        data = {'email': 'kpap@synnefo.org'}
        r = self.client.post(ui_url('local/password_reset'), data, follow=True)
        # she can't because account is not active yet
        self.assertContains(r, 'pending activation')

        # moderation is enabled and an activation email has already been sent
        # so user can trigger resend of the activation email
        r = self.client.get(ui_url('send/activation/%d' % user.pk),
                            follow=True)
        self.assertContains(r, 'has been sent to your email address.')
        self.assertEqual(len(get_mailbox('KPAP@synnefo.org')), 2)

        # also she cannot login
        data = {'username': 'kpap@synnefo.org', 'password': 'password'}
        r = self.client.post(ui_url('local'), data, follow=True)
        self.assertContains(r, 'Resend activation')
        self.assertFalse(r.context['request'].user.is_authenticated())
        self.assertFalse('_pithos2_a' in self.client.cookies)

        # user sees the message and resends activation
        r = self.client.get(ui_url('send/activation/%d' % user.pk),
                            follow=True)
        self.assertEqual(len(get_mailbox('KPAP@synnefo.org')), 3)

        # logged in user cannot activate another account
        tmp_user = get_local_user("test_existing_user@synnefo.org")
        tmp_client = Client()
        tmp_client.login(username="test_existing_user@synnefo.org",
                         password="password")
        r = tmp_client.get(user.get_activation_url(), follow=True)
        self.assertContains(r, messages.LOGGED_IN_WARNING)

        r = self.client.get(user.get_activation_url(), follow=True)
        # previous code got invalidated
        self.assertEqual(r.status_code, 404)

        user = AstakosUser.objects.get(pk=user.pk)
        self.assertEqual(len(get_mailbox(self.helpdesk_email)), 0)
        r = self.client.get(user.get_activation_url(), follow=True)
        self.assertRedirects(r, reverse('login'))
        # user sees that account is pending approval from admins
        self.assertContains(r, messages.NOTIFICATION_SENT)
        self.assertEqual(len(get_mailbox(self.helpdesk_email)), 1)

        user = AstakosUser.objects.get(email="KPAP@synnefo.org")
        result = backend.handle_moderation(user)
        backend.send_result_notifications(result, user)
        self.assertEqual(len(get_mailbox('KPAP@synnefo.org')), 4)
        self.assertEqual(len(get_mailbox(self.helpdesk_email)), 2)

        user = AstakosUser.objects.get(email="KPAP@synnefo.org")
        r = self.client.get(ui_url('profile'), follow=True)
        self.assertFalse(r.context['request'].user.is_authenticated())
        self.assertFalse('_pithos2_a' in self.client.cookies)
        self.assertEqual(len(get_mailbox('KPAP@synnefo.org')), 4)

        user = AstakosUser.objects.get(pk=user.pk)
        r = self.client.post(ui_url('local'), {'username': 'kpap@synnefo.org',
                                               'password': 'password'},
                             follow=True)
        # user activated and logged in, token cookie set
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue('_pithos2_a' in self.client.cookies)
        cookies = self.client.cookies
        self.assertTrue(quote(user.auth_token) in
                        cookies.get('_pithos2_a').value)
        r = self.client.get(ui_url('logout'), follow=True)
        r = self.client.get(ui_url(''), follow=True)
        self.assertRedirects(r, ui_url('login'))
        # user logged out, token cookie removed
        self.assertFalse(r.context['request'].user.is_authenticated())
        self.assertFalse(self.client.cookies.get('_pithos2_a').value)

        #https://docs.djangoproject.com/en/dev/topics/testing/#persistent-state
        del self.client.cookies['_pithos2_a']

        # user can login
        r = self.client.post(ui_url('local'), {'username': 'kpap@synnefo.org',
                                               'password': 'password'},
                             follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue('_pithos2_a' in self.client.cookies)
        cookies = self.client.cookies
        self.assertTrue(quote(user.auth_token) in
                        cookies.get('_pithos2_a').value)
        self.client.get(ui_url('logout'), follow=True)

        # user forgot password
        old_pass = user.password
        r = self.client.get(ui_url('local/password_reset'))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(ui_url('local/password_reset'),
                             {'email': 'kpap@synnefo.org'})
        self.assertEqual(r.status_code, 302)
        # email sent
        self.assertEqual(len(get_mailbox('KPAP@synnefo.org')), 5)

        # user visits change password link
        user = AstakosUser.objects.get(pk=user.pk)
        r = self.client.get(user.get_password_reset_url())
        r = self.client.post(user.get_password_reset_url(),
                             {'new_password1': 'newpass',
                              'new_password2': 'newpass'})

        user = AstakosUser.objects.get(pk=user.pk)
        self.assertNotEqual(old_pass, user.password)

        # old pass is not usable
        r = self.client.post(ui_url('local'), {'username': 'kpap@synnefo.org',
                                               'password': 'password'})
        self.assertContains(r, 'Please enter a correct username and password')
        r = self.client.post(ui_url('local'), {'username': 'kpap@synnefo.org',
                                               'password': 'newpass'},
                             follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.client.logout()

        # tests of special local backends
        user = AstakosUser.objects.get(pk=user.pk)
        user.auth_providers.filter(module='local').update(auth_backend='ldap')
        user.save()

        # non astakos local backends do not support password reset
        r = self.client.get(ui_url('local/password_reset'))
        self.assertEqual(r.status_code, 200)
        r = self.client.post(ui_url('local/password_reset'),
                             {'email': 'kpap@synnefo.org'})
        # she can't because account is not active yet
        self.assertContains(r, "Changing password is not")


class UserActionsTests(TestCase):

    def test_email_change(self):
        # to test existing email validation
        get_local_user('existing@synnefo.org')

        # local user
        user = get_local_user('kpap@synnefo.org')

        # login as kpap
        self.client.login(username='kpap@synnefo.org', password='password')
        r = self.client.get(ui_url('profile'), follow=True)
        user = r.context['request'].user
        self.assertTrue(user.is_authenticated())

        # change email is enabled
        r = self.client.get(ui_url('email_change'))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(user.email_change_is_pending())

        # request email change to an existing email fails
        data = {'new_email_address': 'existing@synnefo.org'}
        r = self.client.post(ui_url('email_change'), data)
        self.assertContains(r, messages.EMAIL_USED)

        # proper email change
        data = {'new_email_address': 'kpap@gmail.com'}
        r = self.client.post(ui_url('email_change'), data, follow=True)
        self.assertRedirects(r, ui_url('profile'))
        self.assertContains(r, messages.EMAIL_CHANGE_REGISTERED)
        change1 = EmailChange.objects.get()

        # user sees a warning
        r = self.client.get(ui_url('email_change'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, messages.PENDING_EMAIL_CHANGE_REQUEST)
        self.assertTrue(user.email_change_is_pending())

        # link was sent
        self.assertEqual(len(get_mailbox('kpap@synnefo.org')), 0)
        self.assertEqual(len(get_mailbox('kpap@gmail.com')), 1)

        # proper email change
        data = {'new_email_address': 'kpap@yahoo.com'}
        r = self.client.post(ui_url('email_change'), data, follow=True)
        self.assertRedirects(r, ui_url('profile'))
        self.assertContains(r, messages.EMAIL_CHANGE_REGISTERED)
        self.assertEqual(len(get_mailbox('kpap@synnefo.org')), 0)
        self.assertEqual(len(get_mailbox('kpap@yahoo.com')), 1)
        change2 = EmailChange.objects.get()

        r = self.client.get(change1.get_url())
        self.assertEquals(r.status_code, 404)
        self.client.logout()

        invalid_client = Client()
        r = invalid_client.post(ui_url('local?'),
                                {'username': 'existing@synnefo.org',
                                 'password': 'password'})
        r = invalid_client.get(change2.get_url(), follow=True)
        self.assertEquals(r.status_code, 403)

        r = self.client.post(ui_url('local?next=' + change2.get_url()),
                             {'username': 'kpap@synnefo.org',
                              'password': 'password',
                              'next': change2.get_url()},
                             follow=True)
        self.assertRedirects(r, ui_url('profile'))
        user = r.context['request'].user
        self.assertEquals(user.email, 'kpap@yahoo.com')
        self.assertEquals(user.username, 'kpap@yahoo.com')

        self.client.logout()
        r = self.client.post(ui_url('local?next=' + change2.get_url()),
                             {'username': 'kpap@synnefo.org',
                              'password': 'password',
                              'next': change2.get_url()},
                             follow=True)
        self.assertContains(r, "Please enter a correct username and password")
        self.assertEqual(user.emailchanges.count(), 0)

        AstakosUser.objects.all().delete()
        Group.objects.all().delete()


class TestAuthProviderViews(TestCase):

    def tearDown(self):
        AstakosUser.objects.all().delete()

    @shibboleth_settings(CREATION_GROUPS_POLICY=['academic-login'],
                         AUTOMODERATE_POLICY=True)
    @im_settings(IM_MODULES=['shibboleth', 'local'], MODERATION_ENABLED=True,
                 FORCE_PROFILE_UPDATE=False)
    def test_user(self):
        Profile = AuthProviderPolicyProfile
        Pending = PendingThirdPartyUser
        User = AstakosUser

        User.objects.create(email="newuser@synnefo.org")
        get_local_user("olduser@synnefo.org")
        cl_olduser = ShibbolethClient()
        get_local_user("olduser2@synnefo.org")
        ShibbolethClient()
        cl_newuser = ShibbolethClient()
        cl_newuser2 = Client()

        academic_group, created = Group.objects.get_or_create(
            name='academic-login')
        academic_users = academic_group.user_set
        assert created
        policy_only_academic = Profile.objects.add_policy('academic_strict',
                                                          'shibboleth',
                                                          academic_group,
                                                          exclusive=True,
                                                          login=False,
                                                          add=False)

        # new academic user
        self.assertFalse(academic_users.filter(email='newuser@synnefo.org'))
        cl_newuser.set_tokens(eppn="newusereppn")
        r = cl_newuser.get(ui_url('login/shibboleth?'), follow=True)
        pending = Pending.objects.get()
        identifier = pending.third_party_identifier
        signup_data = {'third_party_identifier': identifier,
                       'first_name': 'Academic',
                       'third_party_token': pending.token,
                       'last_name': 'New User',
                       'provider': 'shibboleth'}
        r = cl_newuser.post(ui_url('signup'), signup_data)
        self.assertContains(r, "This field is required", )
        signup_data['email'] = 'olduser@synnefo.org'
        r = cl_newuser.post(ui_url('signup'), signup_data)
        self.assertContains(r, "already an account with this email", )
        signup_data['email'] = 'newuser@synnefo.org'
        r = cl_newuser.post(ui_url('signup'), signup_data, follow=True)
        r = cl_newuser.post(ui_url('signup'), signup_data, follow=True)
        self.assertEqual(r.status_code, 404)
        newuser = User.objects.get(email="newuser@synnefo.org")
        activation_link = newuser.get_activation_url()
        self.assertTrue(academic_users.get(email='newuser@synnefo.org'))

        # new non-academic user
        signup_data = {'first_name': 'Non Academic',
                       'last_name': 'New User',
                       'provider': 'local',
                       'password1': 'password',
                       'password2': 'password'}
        signup_data['email'] = 'olduser@synnefo.org'
        r = cl_newuser2.post(ui_url('signup'), signup_data)
        self.assertContains(r, 'There is already an account with this '
                               'email address')
        signup_data['email'] = 'newuser@synnefo.org'
        r = cl_newuser2.post(ui_url('signup/'), signup_data)
        self.assertFalse(academic_users.filter(email='newuser@synnefo.org'))
        r = self.client.get(activation_link, follow=True)
        self.assertEqual(r.status_code, 404)
        newuser = User.objects.get(email="newuser@synnefo.org")
        self.assertTrue(newuser.activation_sent)

        # activation sent, user didn't open verification url so additional
        # registrations invalidate the previous signups.
        self.assertFalse(academic_users.filter(email='newuser@synnefo.org'))
        r = cl_newuser.get(ui_url('login/shibboleth?'), follow=True)
        pending = Pending.objects.get()
        identifier = pending.third_party_identifier
        signup_data = {'third_party_identifier': identifier,
                       'first_name': 'Academic',
                       'third_party_token': pending.token,
                       'last_name': 'New User',
                       'provider': 'shibboleth'}
        signup_data['email'] = 'newuser@synnefo.org'
        r = cl_newuser.post(ui_url('signup'), signup_data)
        self.assertEqual(r.status_code, 302)
        newuser = User.objects.get(email="newuser@synnefo.org")
        self.assertTrue(newuser.activation_sent)
        activation_link = newuser.get_activation_url()
        self.assertTrue(academic_users.get(email='newuser@synnefo.org'))
        r = cl_newuser.get(newuser.get_activation_url(), follow=True)
        self.assertRedirects(r, ui_url('landing'))
        newuser = User.objects.get(email="newuser@synnefo.org")
        self.assertEqual(newuser.is_active, True)
        self.assertEqual(newuser.email_verified, True)
        cl_newuser.logout()

        # cannot reactivate if suspended
        newuser.is_active = False
        newuser.save()
        r = cl_newuser.get(newuser.get_activation_url())
        newuser = User.objects.get(email="newuser@synnefo.org")
        self.assertFalse(newuser.is_active)

        # release suspension
        newuser.is_active = True
        newuser.save()

        cl_newuser.get(ui_url('login/shibboleth?'), follow=True)
        local = auth.get_provider('local', newuser)
        self.assertEqual(local.get_add_policy, False)
        self.assertEqual(local.get_login_policy, False)
        r = cl_newuser.get(local.get_add_url, follow=True)
        self.assertRedirects(r, ui_url('profile'))
        self.assertContains(r, 'disabled for your')

        cl_olduser.login(username='olduser@synnefo.org', password="password")
        r = cl_olduser.get(ui_url('profile'), follow=True)
        self.assertEqual(r.status_code, 200)
        r = cl_olduser.get(ui_url('login/shibboleth?'), follow=True)
        self.assertContains(r, 'Your request is missing a unique token')
        cl_olduser.set_tokens(eppn="newusereppn")
        r = cl_olduser.get(ui_url('login/shibboleth?'), follow=True)
        self.assertContains(r, 'already in use')
        cl_olduser.set_tokens(eppn="oldusereppn")
        r = cl_olduser.get(ui_url('login/shibboleth?'), follow=True)
        self.assertContains(r, 'Academic login enabled for this account')

        user = User.objects.get(email="olduser@synnefo.org")
        shib_provider = user.get_auth_provider('shibboleth', 'oldusereppn')
        local_provider = user.get_auth_provider('local')
        self.assertEqual(shib_provider.get_remove_policy, True)
        self.assertEqual(local_provider.get_remove_policy, True)

        policy_only_academic = Profile.objects.add_policy('academic_strict2',
                                                          'shibboleth',
                                                          academic_group,
                                                          remove=False)
        user.groups.add(academic_group)
        shib_provider = user.get_auth_provider('shibboleth', 'oldusereppn')
        local_provider = user.get_auth_provider('local')
        self.assertEqual(shib_provider.get_remove_policy, False)
        self.assertEqual(local_provider.get_remove_policy, True)
        self.assertEqual(local_provider.get_login_policy, False)

        cl_olduser.logout()
        login_data = {'username': 'olduser@synnefo.org',
                      'password': 'password'}
        r = cl_olduser.post(ui_url('local'), login_data, follow=True)
        self.assertContains(r, "login/shibboleth'>Academic login")
        Group.objects.all().delete()


class TestAuthProvidersAPI(TestCase):
    """
    Test auth_providers module API
    """

    def tearDown(self):
        Group.objects.all().delete()

    @im_settings(IM_MODULES=['local', 'shibboleth'])
    def test_create(self):
        user = AstakosUser.objects.create(email="kpap@synnefo.org")
        user2 = AstakosUser.objects.create(email="kpap2@synnefo.org")

        module = 'shibboleth'
        identifier = 'SHIB_UUID'
        provider_params = {
            'affiliation': 'UNIVERSITY',
            'info': {'age': 27}
        }
        provider = auth.get_provider(module, user2, identifier,
                                     **provider_params)
        provider.add_to_user()
        provider = auth.get_provider(module, user, identifier,
                                     **provider_params)
        provider.add_to_user()
        user.email_verified = True
        user.save()
        self.assertRaises(Exception, provider.add_to_user)
        provider = user.get_auth_provider(module, identifier)
        self.assertEqual(user.get_auth_provider(
            module, identifier)._instance.info.get('age'), 27)

        module = 'local'
        identifier = None
        provider_params = {'auth_backend': 'ldap', 'info':
                          {'office': 'A1'}}
        provider = auth.get_provider(module, user, identifier,
                                     **provider_params)
        provider.add_to_user()
        self.assertFalse(provider.get_add_policy)
        self.assertRaises(Exception, provider.add_to_user)

        shib = user.get_auth_provider('shibboleth',
                                      'SHIB_UUID')
        self.assertTrue(shib.get_remove_policy)

        local = user.get_auth_provider('local')
        self.assertTrue(local.get_remove_policy)

        local.remove_from_user()
        self.assertFalse(shib.get_remove_policy)
        self.assertRaises(Exception, shib.remove_from_user)

        provider = user.get_auth_providers()[0]
        self.assertRaises(Exception, provider.add_to_user)

    @im_settings(IM_MODULES=['local', 'shibboleth'])
    @shibboleth_settings(ADD_GROUPS_POLICY=['group1', 'group2'],
                         CREATION_GROUPS_POLICY=['group-create', 'group1',
                                                 'group2'])
    @localauth_settings(ADD_GROUPS_POLICY=['localgroup'],
                        CREATION_GROUPS_POLICY=['localgroup-create',
                                                'group-create'])
    def test_add_groups(self):
        user = AstakosUser.objects.create(email="kpap@synnefo.org")
        provider = auth.get_provider('shibboleth', user, 'test123')
        provider.add_to_user()
        user = AstakosUser.objects.get()
        self.assertEqual(sorted(user.groups.values_list('name', flat=True)),
                              sorted([u'group1', u'group2', u'group-create']))

        local = auth.get_provider('local', user)
        local.add_to_user()
        provider = user.get_auth_provider('shibboleth')
        self.assertEqual(provider.get_add_groups_policy, ['group1', 'group2'])
        provider.remove_from_user()
        user = AstakosUser.objects.get()
        self.assertEqual(len(user.get_auth_providers()), 1)
        self.assertEqual(sorted(user.groups.values_list('name', flat=True)),
                              sorted([u'group-create', u'localgroup']))

        local = user.get_auth_provider('local')
        self.assertRaises(Exception, local.remove_from_user)
        provider = auth.get_provider('shibboleth', user, 'test123')
        provider.add_to_user()
        user = AstakosUser.objects.get()
        self.assertEqual(sorted(user.groups.values_list('name', flat=True)),
                              sorted([u'group-create', u'group1', u'group2',
                               u'localgroup']))
        Group.objects.all().delete()



    @im_settings(IM_MODULES=['local', 'shibboleth'])
    def test_policies(self):
        group_old, created = Group.objects.get_or_create(name='olduser')

        astakos_settings.MODERATION_ENABLED = True
        settings.ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_CREATION_GROUPS_POLICY = \
            ['academic-user']
        settings.ASTAKOS_AUTH_PROVIDER_GOOGLE_ADD_GROUPS_POLICY = \
            ['google-user']

        user = AstakosUser.objects.create(email="kpap@synnefo.org")
        user.groups.add(group_old)
        user.add_auth_provider('local')

        user2 = AstakosUser.objects.create(email="kpap2@synnefo.org")
        user2.add_auth_provider('shibboleth', identifier='shibid')

        user3 = AstakosUser.objects.create(email="kpap3@synnefo.org")
        user3.groups.add(group_old)
        user3.add_auth_provider('local')
        user3.add_auth_provider('shibboleth', identifier='1234')

        self.assertTrue(user2.groups.get(name='academic-user'))
        self.assertFalse(user2.groups.filter(name='olduser').count())

        local = auth_providers.get_provider('local')
        self.assertTrue(local.get_add_policy)

        academic_group = Group.objects.get(name='academic-user')
        AuthProviderPolicyProfile.objects.add_policy('academic', 'shibboleth',
                                                     academic_group,
                                                     exclusive=True,
                                                     add=False,
                                                     login=False)
        AuthProviderPolicyProfile.objects.add_policy('academic', 'shibboleth',
                                                     academic_group,
                                                     exclusive=True,
                                                     login=False,
                                                     add=False)
        # no duplicate entry gets created
        self.assertEqual(academic_group.authpolicy_profiles.count(), 1)

        self.assertEqual(user2.authpolicy_profiles.count(), 0)
        AuthProviderPolicyProfile.objects.add_policy('academic', 'shibboleth',
                                                     user2,
                                                     remove=False)
        self.assertEqual(user2.authpolicy_profiles.count(), 1)

        local = auth_providers.get_provider('local', user2)
        google = auth_providers.get_provider('google', user2)
        shibboleth = auth_providers.get_provider('shibboleth', user2)
        self.assertTrue(shibboleth.get_login_policy)
        self.assertFalse(shibboleth.get_remove_policy)
        self.assertFalse(local.get_add_policy)
        self.assertFalse(local.get_add_policy)
        self.assertFalse(google.get_add_policy)

        user2.groups.remove(Group.objects.get(name='academic-user'))
        self.assertTrue(local.get_add_policy)
        self.assertTrue(google.get_add_policy)
        user2.groups.add(Group.objects.get(name='academic-user'))

        AuthProviderPolicyProfile.objects.add_policy('academic', 'shibboleth',
                                                     user2,
                                                     exclusive=True,
                                                     add=True)
        self.assertTrue(local.get_add_policy)
        self.assertTrue(google.get_add_policy)

        settings.ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_AUTOMODERATE_POLICY = True
        self.assertFalse(local.get_automoderate_policy)
        self.assertFalse(google.get_automoderate_policy)
        self.assertTrue(shibboleth.get_automoderate_policy)

        for s in ['SHIBBOLETH_CREATION_GROUPS_POLICY',
                  'GOOGLE_ADD_GROUPS_POLICY']:
            delattr(settings, 'ASTAKOS_AUTH_PROVIDER_%s' % s)


    @shibboleth_settings(CREATE_POLICY=True)
    @im_settings(IM_MODULES=['local', 'shibboleth'])
    def test_create_http(self):
        # this should be wrapped inside a transaction
        user = AstakosUser(email="test@test.com")
        user.save()
        provider = auth_providers.get_provider('shibboleth', user,
                                               'test@academia.test')
        provider.add_to_user()
        user.get_auth_provider('shibboleth', 'test@academia.test')
        provider = auth_providers.get_provider('local', user)
        provider.add_to_user()
        user.get_auth_provider('local')

        settings.ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_CREATE_POLICY = False
        user = AstakosUser(email="test2@test.com")
        user.save()
        provider = auth_providers.get_provider('shibboleth', user,
                                               'test@shibboleth.com',
                                               **{'info': {'name':
                                                                'User Test'}})
        self.assertFalse(provider.get_create_policy)
        settings.ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_CREATE_POLICY = True
        self.assertTrue(provider.get_create_policy)
        academic = provider.add_to_user()

    @im_settings(IM_MODULES=['local', 'shibboleth'])
    @shibboleth_settings(LIMIT_POLICY=2)
    def test_policies(self):
        user = get_local_user('kpap@synnefo.org')
        user.add_auth_provider('shibboleth', identifier='1234')
        user.add_auth_provider('shibboleth', identifier='12345')

        # default limit is 1
        local = user.get_auth_provider('local')
        self.assertEqual(local.get_add_policy, False)

        settings.ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_LIMIT_POLICY = 3
        academic = user.get_auth_provider('shibboleth',
                                          identifier='1234')
        self.assertEqual(academic.get_add_policy, False)
        newacademic = auth_providers.get_provider('shibboleth', user,
                                                  identifier='123456')
        self.assertEqual(newacademic.get_add_policy, True)
        user.add_auth_provider('shibboleth', identifier='123456')
        self.assertEqual(academic.get_add_policy, False)
        settings.ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_LIMIT_POLICY = 1

    @im_settings(IM_MODULES=['local', 'shibboleth'])
    @shibboleth_settings(LIMIT_POLICY=2)
    def test_messages(self):
        user = get_local_user('kpap@synnefo.org')
        user.add_auth_provider('shibboleth', identifier='1234')
        user.add_auth_provider('shibboleth', identifier='12345')
        provider = auth_providers.get_provider('shibboleth')
        self.assertEqual(provider.get_message('title'), 'Academic')
        settings.ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_TITLE = 'New title'
        # regenerate messages cache
        provider = auth_providers.get_provider('shibboleth')
        self.assertEqual(provider.get_message('title'), 'New title')
        self.assertEqual(provider.get_message('login_title'),
                         'New title LOGIN')
        self.assertEqual(provider.get_login_title_msg, 'New title LOGIN')
        self.assertEqual(provider.get_module_icon,
                         settings.MEDIA_URL + 'im/auth/icons/shibboleth.png')
        self.assertEqual(provider.get_module_medium_icon,
                         settings.MEDIA_URL +
                         'im/auth/icons-medium/shibboleth.png')

        settings.ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_TITLE = None
        provider = auth_providers.get_provider('shibboleth', user, '12345')
        self.assertEqual(provider.get_method_details_msg,
                         'Account: 12345')
        provider = auth_providers.get_provider('shibboleth', user, '1234')
        self.assertEqual(provider.get_method_details_msg,
                         'Account: 1234')

        provider = auth_providers.get_provider('shibboleth', user, '1234')
        self.assertEqual(provider.get_not_active_msg,
                         "'Academic login' is disabled.")

    @im_settings(IM_MODULES=['local', 'shibboleth'])
    @shibboleth_settings(LIMIT_POLICY=2)
    def test_templates(self):
        user = get_local_user('kpap@synnefo.org')
        user.add_auth_provider('shibboleth', identifier='1234')
        user.add_auth_provider('shibboleth', identifier='12345')

        provider = auth_providers.get_provider('shibboleth')
        self.assertEqual(provider.get_template('login'),
                         'im/auth/shibboleth_login.html')
        provider = auth_providers.get_provider('google')
        self.assertEqual(provider.get_template('login'),
                         'im/auth/generic_login.html')


class TestActivationBackend(TestCase):

    def setUp(self):
        # dummy call to pass through logging middleware
        self.client.get(ui_url(''))

    @im_settings(RE_USER_EMAIL_PATTERNS=['.*@synnefo.org'])
    @shibboleth_settings(AUTOMODERATE_POLICY=True)
    def test_policies(self):
        backend = activation_backends.get_backend()

        # email matches RE_USER_EMAIL_PATTERNS
        user1 = get_local_user('kpap@synnefo.org', moderated=False,
                               is_active=False, email_verified=False)
        backend.handle_verification(user1, user1.verification_code)
        self.assertEqual(user1.accepted_policy, 'email')

        # manually moderated
        user2 = get_local_user('kpap@synnefo-bad.org', moderated=False,
                               is_active=False, email_verified=False)

        backend.handle_verification(user2, user2.verification_code)
        self.assertEqual(user2.moderated, False)
        backend.handle_moderation(user2)
        self.assertEqual(user2.moderated, True)
        self.assertEqual(user2.accepted_policy, 'manual')

        # autoaccept due to provider automoderate policy
        user3 = get_local_user('kpap2@synnefo-bad.org', moderated=False,
                               is_active=False, email_verified=False)
        user3.auth_providers.all().delete()
        user3.add_auth_provider('shibboleth', identifier='shib123')
        backend.handle_verification(user3, user3.verification_code)
        self.assertEqual(user3.moderated, True)
        self.assertEqual(user3.accepted_policy, 'auth_provider_shibboleth')

    @im_settings(MODERATION_ENABLED=False,
                 MANAGERS=(('Manager',
                            'manager@synnefo.org'),),
                 HELPDESK=(('Helpdesk',
                            'helpdesk@synnefo.org'),),
                 ADMINS=(('Admin', 'admin@synnefo.org'), ))
    def test_without_moderation(self):
        backend = activation_backends.get_backend()
        form = backend.get_signup_form('local')
        self.assertTrue(isinstance(form, forms.LocalUserCreationForm))

        user_data = {
            'email': 'kpap@synnefo.org',
            'first_name': 'Kostas Papas',
            'password1': '123',
            'password2': '123'
        }
        form = backend.get_signup_form('local', user_data)
        user = form.save(commit=False)
        form.store_user(user)
        self.assertEqual(user.is_active, False)
        self.assertEqual(user.email_verified, False)

        # step one, registration
        result = backend.handle_registration(user)
        user = AstakosUser.objects.get()
        self.assertEqual(user.is_active, False)
        self.assertEqual(user.email_verified, False)
        self.assertTrue(user.verification_code)
        self.assertEqual(result.status, backend.Result.PENDING_VERIFICATION)
        backend.send_result_notifications(result, user)
        self.assertEqual(len(get_mailbox('kpap@synnefo.org')), 1)
        self.assertEqual(len(mail.outbox), 1)

        # step two, verify email (automatically
        # moderates/accepts user, since moderation is disabled)
        user = AstakosUser.objects.get()
        valid_code = user.verification_code

        # test invalid code
        result = backend.handle_verification(user, valid_code)
        backend.send_result_notifications(result, user)
        self.assertEqual(len(get_mailbox('manager@synnefo.org')), 1)
        self.assertEqual(len(get_mailbox('helpdesk@synnefo.org')), 1)
        self.assertEqual(len(get_mailbox('admin@synnefo.org')), 1)
        # verification + activated + greeting = 3
        self.assertEqual(len(mail.outbox), 3)
        user = AstakosUser.objects.get()
        self.assertEqual(user.is_active, True)
        self.assertEqual(user.moderated, True)
        self.assertTrue(user.moderated_at)
        self.assertEqual(user.email_verified, True)
        self.assertTrue(user.activation_sent)

    @im_settings(MODERATION_ENABLED=True,
                 MANAGERS=(('Manager',
                            'manager@synnefo.org'),),
                 HELPDESK=(('Helpdesk',
                            'helpdesk@synnefo.org'),),
                 ADMINS=(('Admin', 'admin@synnefo.org'), ))
    def test_with_moderation(self):

        backend = activation_backends.get_backend()
        form = backend.get_signup_form('local')
        self.assertTrue(isinstance(form, forms.LocalUserCreationForm))

        user_data = {
            'email': 'kpap@synnefo.org',
            'first_name': 'Kostas Papas',
            'password1': '123',
            'password2': '123'
        }
        form = backend.get_signup_form(provider='local',
                                       initial_data=user_data)
        user = form.save(commit=False)
        form.store_user(user)
        self.assertEqual(user.is_active, False)
        self.assertEqual(user.email_verified, False)

        # step one, registration
        result = backend.handle_registration(user)
        user = AstakosUser.objects.get()
        self.assertEqual(user.is_active, False)
        self.assertEqual(user.email_verified, False)
        self.assertTrue(user.verification_code)
        self.assertEqual(result.status, backend.Result.PENDING_VERIFICATION)
        backend.send_result_notifications(result, user)
        self.assertEqual(len(get_mailbox('kpap@synnefo.org')), 1)
        self.assertEqual(len(mail.outbox), 1)

        # step two, verifying email
        user = AstakosUser.objects.get()
        valid_code = user.verification_code
        invalid_code = user.verification_code + 'invalid'

        # test invalid code
        result = backend.handle_verification(user, invalid_code)
        self.assertEqual(result.status, backend.Result.ERROR)
        backend.send_result_notifications(result, user)
        user = AstakosUser.objects.get()
        self.assertEqual(user.is_active, False)
        self.assertEqual(user.moderated, False)
        self.assertEqual(user.moderated_at, None)
        self.assertEqual(user.email_verified, False)
        self.assertTrue(user.activation_sent)

        # test valid code
        user = AstakosUser.objects.get()
        result = backend.handle_verification(user, valid_code)
        backend.send_result_notifications(result, user)
        self.assertEqual(len(get_mailbox('manager@synnefo.org')), 1)
        self.assertEqual(len(get_mailbox('helpdesk@synnefo.org')), 1)
        self.assertEqual(len(get_mailbox('admin@synnefo.org')), 1)
        self.assertEqual(len(mail.outbox), 2)
        user = AstakosUser.objects.get()
        self.assertEqual(user.moderated, False)
        self.assertEqual(user.moderated_at, None)
        self.assertEqual(user.email_verified, True)
        self.assertTrue(user.activation_sent)

        # test code reuse
        result = backend.handle_verification(user, valid_code)
        self.assertEqual(result.status, backend.Result.ERROR)
        user = AstakosUser.objects.get()
        self.assertEqual(user.is_active, False)
        self.assertEqual(user.moderated, False)
        self.assertEqual(user.moderated_at, None)
        self.assertEqual(user.email_verified, True)
        self.assertTrue(user.activation_sent)

        # valid code on verified user
        user = AstakosUser.objects.get()
        valid_code = user.verification_code
        result = backend.handle_verification(user, valid_code)
        self.assertEqual(result.status, backend.Result.ERROR)

        # step three, moderation user
        user = AstakosUser.objects.get()
        result = backend.handle_moderation(user)
        backend.send_result_notifications(result, user)

        user = AstakosUser.objects.get()
        self.assertEqual(user.is_active, True)
        self.assertEqual(user.moderated, True)
        self.assertTrue(user.moderated_at)
        self.assertEqual(user.email_verified, True)
        self.assertTrue(user.activation_sent)


class TestWebloginRedirect(TestCase):

    @with_settings(settings, COOKIE_DOMAIN='.astakos.synnefo.org')
    def test_restricts_domains(self):
        get_local_user('user1@synnefo.org')

        # next url construct helpers
        weblogin = lambda nxt: reverse('weblogin') + '?next=%s' % nxt
        weblogin_quoted = lambda nxt: reverse('weblogin') + '?next=%s' % \
            urllib.quote_plus(nxt)

        # common cases
        invalid_domain = weblogin("https://www.invaliddomain.synnefo.org")
        invalid_scheme = weblogin("customscheme://localhost")
        invalid_scheme_with_valid_domain = \
                weblogin("http://www.invaliddomain.com")
        valid_scheme = weblogin("pithos://localhost/")
        # to be used in assertRedirects
        valid_scheme_quoted = weblogin_quoted("pithos://localhost/")

        # not authenticated, redirects to login which contains next param with
        # additional nested quoted next params
        r = self.client.get(valid_scheme, follow=True)
        login_redirect = reverse('login') + '?next=' + \
            urllib.quote_plus("http://testserver" + valid_scheme_quoted)
        self.assertRedirects(r, login_redirect)

        # authenticate client
        self.client.login(username="user1@synnefo.org", password="password")

        # valid scheme
        r = self.client.get(valid_scheme, follow=True)
        url = r.redirect_chain[1][0]
        # scheme preserved
        self.assertTrue(url.startswith('pithos://localhost/'))
        # redirect contains token param
        params = urlparse.urlparse(url.replace('pithos', 'https'),
                                   scheme='https').query
        params = urlparse.parse_qs(params)
        self.assertEqual(params['token'][0],
                         AstakosUser.objects.get().auth_token)
        # does not contain uuid
        # reverted for 0.14.2 to support old pithos desktop clients
        #self.assertFalse('uuid' in params)

        # invalid cases
        r = self.client.get(invalid_scheme, follow=True)
        self.assertEqual(r.status_code, 403)

        r = self.client.get(invalid_scheme_with_valid_domain, follow=True)
        self.assertEqual(r.status_code, 403)

        r = self.client.get(invalid_domain, follow=True)
        self.assertEqual(r.status_code, 403)
