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

import datetime

from django.test import TestCase, Client
from django.conf import settings
from django.core import mail

from astakos.im.target.shibboleth import Tokens as ShibbolethTokens
from astakos.im.models import *
from astakos.im import functions
from astakos.im import settings as astakos_settings

from urllib import quote

from astakos.im import messages

class ShibbolethClient(Client):
    """
    A shibboleth agnostic client.
    """
    VALID_TOKENS = filter(lambda x: not x.startswith("_"), dir(ShibbolethTokens))

    def __init__(self, *args, **kwargs):
        self.tokens = kwargs.pop('tokens', {})
        super(ShibbolethClient, self).__init__(*args, **kwargs)

    def set_tokens(self, **kwargs):
        for key, value in kwargs.iteritems():
            key = 'SHIB_%s' % key.upper()
            if not key in self.VALID_TOKENS:
                raise Exception('Invalid shibboleth token')

            self.tokens[key] = value

    def unset_tokens(self, *keys):
        for key in keys:
            key = 'SHIB_%s' % param.upper()
            if key in self.tokens:
                del self.tokens[key]

    def reset_tokens(self):
        self.tokens = {}

    def get_http_token(self, key):
        http_header = getattr(ShibbolethTokens, key)
        return http_header

    def request(self, **request):
        """
        Transform valid shibboleth tokens to http headers
        """
        for token, value in self.tokens.iteritems():
            request[self.get_http_token(token)] = value

        for param in request.keys():
            key = 'SHIB_%s' % param.upper()
            if key in self.VALID_TOKENS:
                request[self.get_http_token(key)] = request[param]
                del request[param]

        return super(ShibbolethClient, self).request(**request)


def get_local_user(username, **kwargs):
        try:
            return AstakosUser.objects.get(email=username)
        except:
            user_params = {
                'username': username,
                'email': username,
                'is_active': True,
                'activation_sent': datetime.now(),
                'email_verified': True,
                'provider': 'local'
            }
            user_params.update(kwargs)
            user = AstakosUser(**user_params)
            user.set_password(kwargs.get('password', 'password'))
            user.save()
            user.add_auth_provider('local', auth_backend='astakos')
            if kwargs.get('is_active', True):
                user.is_active = True
            else:
                user.is_active = False
            user.save()
            return user


def get_mailbox(email):
    mails = []
    for sent_email in mail.outbox:
        for recipient in sent_email.recipients():
            if email in recipient:
                mails.append(sent_email)
    return mails


class ShibbolethTests(TestCase):
    """
    Testing shibboleth authentication.
    """

    fixtures = ['groups']

    def setUp(self):
        self.client = ShibbolethClient()
        settings.ASTAKOS_IM_MODULES = ['local', 'shibboleth']

    def test_create_account(self):
        client = ShibbolethClient()

        # shibboleth views validation
        # eepn required
        r = client.get('/im/login/shibboleth?', follow=True)
        self.assertContains(r, messages.SHIBBOLETH_MISSING_EPPN)
        client.set_tokens(eppn="kpapeppn")
        # shibboleth user info required
        r = client.get('/im/login/shibboleth?', follow=True)
        self.assertContains(r, messages.SHIBBOLETH_MISSING_NAME)

        # shibboleth logged us in
        client.set_tokens(mail="kpap@grnet.gr", eppn="kpapeppn", cn="1", )
        r = client.get('/im/login/shibboleth?')

        # astakos asks if we want to add shibboleth
        self.assertContains(r, "Already have an account?")

        # a new pending user created
        pending_user = PendingThirdPartyUser.objects.get(
            third_party_identifier="kpapeppn")
        self.assertEqual(PendingThirdPartyUser.objects.count(), 1)
        token = pending_user.token
        # from now on no shibboleth headers are sent to the server
        client.reset_tokens()

        # we choose to signup as a new user
        r = client.get('/im/shibboleth/signup/%s' % pending_user.username)
        self.assertEqual(r.status_code, 404)

        r = client.get('/im/shibboleth/signup/%s' % token)
        form = r.context['form']
        post_data = {'email': 'kpap@grnet.gr',
                     'third_party_identifier': pending_user.third_party_identifier,
                     'first_name': 'Kostas',
                     'third_party_token': token,
                     'last_name': 'Mitroglou',
                     'additional_email': 'kpap@grnet.gr',
                     'provider': 'shibboleth'
                    }
        r = client.post('/im/signup', post_data)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(AstakosUser.objects.count(), 1)
        self.assertEqual(PendingThirdPartyUser.objects.count(), 0)
        self.assertEqual(AstakosUserAuthProvider.objects.count(), 1)


        client.set_tokens(mail="kpap@grnet.gr", eppn="kpapeppn", cn="1", )
        r = client.get("/im/login/shibboleth?", follow=True)
        self.assertContains(r, "Your request is pending activation")
        r = client.get("/im/profile", follow=True)
        self.assertRedirects(r, 'http://testserver/im/?next=%2Fim%2Fprofile')

        u = AstakosUser.objects.get()
        functions.activate(u)
        self.assertEqual(u.is_active, True)

        r = client.get("/im/login/shibboleth?")
        self.assertRedirects(r, '/im/profile')

    def test_existing(self):
        existing_user = get_local_user('kpap@grnet.gr')

        client = ShibbolethClient()
        # shibboleth logged us in, notice that we use different email
        client.set_tokens(mail="kpap@shibboleth.gr", eppn="kpapeppn", cn="1", )
        r = client.get("/im/login/shibboleth?")
        # astakos asks if we want to switch a local account to shibboleth
        self.assertContains(r, "Already have an account?")

        # a new pending user created
        pending_user = PendingThirdPartyUser.objects.get()
        self.assertEqual(PendingThirdPartyUser.objects.count(), 1)
        pending_key = pending_user.token
        client.reset_tokens()

        # we choose to add shibboleth to an our existing account
        # we get redirected to login page with the pending token set
        r = client.get('/im/login?key=%s' % pending_key)
        post_data = {'password': 'password',
                     'username': 'kpap@grnet.gr',
                     'key': pending_key}
        r = client.post('/im/local', post_data, follow=True)
        self.assertContains(r, "Your new login method has been added")

        user = AstakosUser.objects.get(username="kpap@grnet.gr",
                                       email="kpap@grnet.gr")
        self.assertTrue(user.has_auth_provider('shibboleth'))
        self.assertTrue(user.has_auth_provider('local', auth_backend='astakos'))
        client.logout()

        # again ???? show her a message
        r = client.get('/im/login?key=%s' % pending_key)
        post_data = {'password': 'password',
                     'username': 'kpap@grnet.gr',
                     'key': pending_key}
        r = self.client.post('/im/local', post_data, follow=True)
        self.assertContains(r, "Account method assignment failed")
        self.client.logout()
        client.logout()

        # look Ma, i can login with both my shibboleth and local account
        client.set_tokens(mail="kpap@shibboleth.gr", eppn="kpapeppn", cn="1")
        r = client.get("/im/login/shibboleth?", follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue(r.context['request'].user.email == "kpap@grnet.gr")
        r = client.get("/im/profile")
        self.assertEquals(r.status_code,200)
        client.logout()
        client.reset_tokens()
        r = client.get("/im/profile", follow=True)
        self.assertFalse(r.context['request'].user.is_authenticated())

        post_data = {'password': 'password',
                     'username': 'kpap@grnet.gr'}
        r = self.client.post('/im/local', post_data, follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        r = self.client.get("/im/profile")
        self.assertEquals(r.status_code,200)

        r = client.post('/im/local', post_data, follow=True)
        client.set_tokens(mail="secondary@shibboleth.gr", eppn="kpapeppn", cn="1", )
        r = client.get("/im/login/shibboleth?", follow=True)
        client.reset_tokens()

        client.logout()
        client.set_tokens(mail="kpap@grnet.gr", eppn="kpapeppninvalid", cn="1")
        r = client.get("/im/login/shibboleth?", follow=True)
        self.assertFalse(r.context['request'].user.is_authenticated())

        user2 = get_local_user('kpap@grnet.gr')


class LocalUserTests(TestCase):

    fixtures = ['groups']

    def setUp(self):
        from django.conf import settings
        settings.ADMINS = (('admin', 'support@cloud.grnet.gr'),)
        settings.SERVER_EMAIL = 'no-reply@grnet.gr'

    def test_invitations(self):
        return

    def test_local_provider(self):
        r = self.client.get("/im/signup")
        self.assertEqual(r.status_code, 200)

        data = {'email':'kpap@grnet.gr', 'password1':'password',
                'password2':'password', 'first_name': 'Kostas',
                'last_name': 'Mitroglou', 'provider': 'local'}
        r = self.client.post("/im/signup", data)
        self.assertEqual(AstakosUser.objects.count(), 1)
        user = AstakosUser.objects.get(username="kpap@grnet.gr",
                                       email="kpap@grnet.gr")
        self.assertEqual(user.username, 'kpap@grnet.gr')
        self.assertEqual(user.has_auth_provider('local'), True)
        self.assertFalse(user.is_active)

        # admin gets notified
        self.assertEqual(len(get_mailbox('support@cloud.grnet.gr')), 1)
        # and sends user activation email
        functions.send_activation(user)

        # user activation fields updated
        user = AstakosUser.objects.get(pk=user.pk)
        self.assertTrue(user.activation_sent)
        self.assertFalse(user.email_verified)
        # email sent to user
        self.assertEqual(len(get_mailbox('kpap@grnet.gr')), 1)

        # user forgot she got registered and tries to submit registration
        # form. Notice the upper case in email
        data = {'email':'KPAP@grnet.gr', 'password1':'password',
                'password2':'password', 'first_name': 'Kostas',
                'last_name': 'Mitroglou', 'provider': 'local'}
        r = self.client.post("/im/signup", data)
        self.assertContains(r, messages.EMAIL_USED)

        # hmmm, email exists; lets get the password
        r = self.client.get('/im/local/password_reset')
        self.assertEqual(r.status_code, 200)
        r = self.client.post('/im/local/password_reset', {'email':
                                                          'kpap@grnet.gr'})
        # she can't because account is not active yet
        self.assertContains(r, "doesn&#39;t have an associated user account")

        # moderation is enabled so no automatic activation can be send
        r = self.client.get('/im/send/activation/%d' % user.pk)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(len(get_mailbox('kpap@grnet.gr')), 1)
        # also she cannot login
        r = self.client.post('/im/local', {'username': 'kpap@grnet.gr',
                                                 'password': 'password'})
        self.assertContains(r, 'You have not followed the activation link')
        self.assertNotContains(r, 'Resend activation')
        self.assertFalse(r.context['request'].user.is_authenticated())
        self.assertFalse('_pithos2_a' in self.client.cookies)

        # lets disable moderation
        astakos_settings.MODERATION_ENABLED = False
        r = self.client.post('/im/local/password_reset', {'email':
                                                          'kpap@grnet.gr'})
        self.assertContains(r, "doesn&#39;t have an associated user account")
        r = self.client.post('/im/local', {'username': 'kpap@grnet.gr',
                                                 'password': 'password'})
        self.assertContains(r, 'You have not followed the activation link')
        self.assertContains(r, 'Resend activation')
        self.assertFalse(r.context['request'].user.is_authenticated())
        self.assertFalse('_pithos2_a' in self.client.cookies)
        # user sees the message and resends activation
        r = self.client.get('/im/send/activation/%d' % user.pk)
        # email sent
        self.assertEqual(len(get_mailbox('kpap@grnet.gr')), 2)

        # switch back moderation setting
        astakos_settings.MODERATION_ENABLED = True
        # lets activate the user
        r = self.client.get(user.get_activation_url(), follow=True)
        self.assertRedirects(r, "/im/profile")
        self.assertContains(r, "kpap@grnet.gr")
        self.assertEqual(len(get_mailbox('kpap@grnet.gr')), 3)

        user = AstakosUser.objects.get(pk=user.pk)
        # user activated and logged in, token cookie set
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue('_pithos2_a' in self.client.cookies)
        cookies = self.client.cookies
        self.assertTrue(quote(user.auth_token) in cookies.get('_pithos2_a').value)
        r = self.client.get('/im/logout', follow=True)
        r = self.client.get('/im/')
        # user logged out, token cookie removed
        self.assertFalse(r.context['request'].user.is_authenticated())
        self.assertFalse(self.client.cookies.get('_pithos2_a').value)
        # https://docs.djangoproject.com/en/dev/topics/testing/#persistent-state
        del self.client.cookies['_pithos2_a']

        # user can login
        r = self.client.post('/im/local', {'username': 'kpap@grnet.gr',
                                           'password': 'password'},
                                          follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue('_pithos2_a' in self.client.cookies)
        cookies = self.client.cookies
        self.assertTrue(quote(user.auth_token) in cookies.get('_pithos2_a').value)
        self.client.get('/im/logout', follow=True)

        # user forgot password
        old_pass = user.password
        r = self.client.get('/im/local/password_reset')
        self.assertEqual(r.status_code, 200)
        r = self.client.post('/im/local/password_reset', {'email':
                                                          'kpap@grnet.gr'})
        self.assertEqual(r.status_code, 302)
        # email sent
        self.assertEqual(len(get_mailbox('kpap@grnet.gr')), 4)

        # user visits change password link
        r = self.client.get(user.get_password_reset_url())
        r = self.client.post(user.get_password_reset_url(),
                            {'new_password1':'newpass',
                             'new_password2':'newpass'})

        user = AstakosUser.objects.get(pk=user.pk)
        self.assertNotEqual(old_pass, user.password)

        # old pass is not usable
        r = self.client.post('/im/local', {'username': 'kpap@grnet.gr',
                                           'password': 'password'})
        self.assertContains(r, 'Please enter a correct username and password')
        r = self.client.post('/im/local', {'username': 'kpap@grnet.gr',
                                           'password': 'newpass'},
                                           follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.client.logout()

        # tests of special local backends
        user = AstakosUser.objects.get(pk=user.pk)
        user.auth_providers.filter(module='local').update(auth_backend='ldap')
        user.save()

        # non astakos local backends do not support password reset
        r = self.client.get('/im/local/password_reset')
        self.assertEqual(r.status_code, 200)
        r = self.client.post('/im/local/password_reset', {'email':
                                                          'kpap@grnet.gr'})
        # she can't because account is not active yet
        self.assertContains(r, "Password change for this account is not"
                                " supported")

