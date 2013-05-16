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
from contextlib import contextmanager

import copy
import datetime
import functools

from snf_django.utils.testing import with_settings, override_settings, assertIn

from django.test import Client
from django.test import TransactionTestCase as TestCase
from django.core import mail
from django.http import SimpleCookie, HttpRequest, QueryDict
from django.utils.importlib import import_module
from django.utils import simplejson as json

from astakos.im.activation_backends import *
from astakos.im.target.shibboleth import Tokens as ShibbolethTokens
from astakos.im.models import *
from astakos.im import functions
from astakos.im import settings as astakos_settings
from astakos.im import forms
from astakos.im import activation_backends

from urllib import quote
from datetime import timedelta

from astakos.im import messages
from astakos.im import auth_providers
from astakos.im import quotas
from astakos.im import resources

from django.conf import settings


# set some common settings
astakos_settings.EMAILCHANGE_ENABLED = True
astakos_settings.RECAPTCHA_ENABLED = False

settings.LOGGING_SETUP['disable_existing_loggers'] = False

# shortcut decorators to override provider settings
# e.g. shibboleth_settings(ENABLED=True) will set
# ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_ENABLED = True in global synnefo settings
prefixes = {'providers': 'AUTH_PROVIDER_',
            'shibboleth': 'ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_',
            'local': 'ASTAKOS_AUTH_PROVIDER_LOCAL_'}
im_settings = functools.partial(with_settings, astakos_settings)
shibboleth_settings = functools.partial(with_settings,
                                        settings,
                                        prefix=prefixes['shibboleth'])
localauth_settings = functools.partial(with_settings, settings,
                                       prefix=prefixes['local'])


class AstakosTestClient(Client):
    pass


class ShibbolethClient(AstakosTestClient):
    """
    A shibboleth agnostic client.
    """
    VALID_TOKENS = filter(lambda x: not x.startswith("_"),
                          dir(ShibbolethTokens))

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


def get_user_client(username, password="password"):
    client = Client()
    client.login(username=username, password=password)
    return client


def get_local_user(username, **kwargs):
        try:
            return AstakosUser.objects.get(email=username)
        except:
            user_params = {
                'username': username,
                'email': username,
                'is_active': True,
                'activation_sent': datetime.now(),
                'email_verified': True
            }
            user_params.update(kwargs)
            user = AstakosUser(**user_params)
            user.set_password(kwargs.get('password', 'password'))
            user.renew_verification_code()
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
        astakos_settings.IM_MODULES = ['local', 'shibboleth']
        astakos_settings.MODERATION_ENABLED = True

    @im_settings(FORCE_PROFILE_UPDATE=False)
    def test_create_account(self):

        client = ShibbolethClient()

        # shibboleth views validation
        # eepn required
        r = client.get('/im/login/shibboleth?', follow=True)
        self.assertContains(r, messages.SHIBBOLETH_MISSING_EPPN % {
            'domain': astakos_settings.BASEURL,
            'contact_email': settings.CONTACT_EMAIL
        })
        client.set_tokens(eppn="kpapeppn")

        astakos_settings.SHIBBOLETH_REQUIRE_NAME_INFO = True
        # shibboleth user info required
        r = client.get('/im/login/shibboleth?', follow=True)
        self.assertContains(r, messages.SHIBBOLETH_MISSING_NAME)
        astakos_settings.SHIBBOLETH_REQUIRE_NAME_INFO = False

        # shibboleth logged us in
        client.set_tokens(mail="kpap@synnefo.org", eppn="kpapeppn",
                          cn="Kostas Papadimitriou",
                          ep_affiliation="Test Affiliation")
        r = client.get('/im/login/shibboleth?', follow=True)
        token = PendingThirdPartyUser.objects.get().token
        self.assertRedirects(r, '/im/signup?third_party_token=%s' % token)
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
        r = client.get('/im/shibboleth/signup/%s' % pending_user.username)
        self.assertEqual(r.status_code, 404)

        # this is the signup unique url associated with the pending user
        # created
        r = client.get('/im/signup/?third_party_token=%s' % token)
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
        self.assertEqual(provider.info, {u'email': u'kpap@synnefo.org',
                                         u'eppn': u'kpapeppn',
                                         u'name': u'Kostas Papadimitriou'})

        # login (not activated yet)
        client.set_tokens(mail="kpap@synnefo.org", eppn="kpapeppn",
                          cn="Kostas Papadimitriou", )
        r = client.get("/im/login/shibboleth?", follow=True)
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
        r = client.get("/im/login/shibboleth?", follow=True)
        self.assertRedirects(r, '/im/landing')
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
        r = client.get("/im/login/shibboleth?", follow=True)

        # a new pending user created
        pending_user = PendingThirdPartyUser.objects.get()
        token = pending_user.token
        self.assertEqual(PendingThirdPartyUser.objects.count(), 1)
        pending_key = pending_user.token
        client.reset_tokens()
        self.assertRedirects(r, "/im/signup?third_party_token=%s" % token)

        form = r.context['form']
        signupdata = copy.copy(form.initial)
        signupdata['email'] = 'kpap@synnefo.org'
        signupdata['third_party_token'] = token
        signupdata['provider'] = 'shibboleth'
        signupdata.pop('id', None)

        # the email exists to another user
        r = client.post("/im/signup", signupdata)
        self.assertContains(r, "There is already an account with this email "
                               "address")
        # change the case, still cannot create
        signupdata['email'] = 'KPAP@synnefo.org'
        r = client.post("/im/signup", signupdata)
        self.assertContains(r, "There is already an account with this email "
                               "address")
        # inactive user
        signupdata['email'] = 'KPAP-inactive@synnefo.org'
        r = client.post("/im/signup", signupdata)
        self.assertContains(r, "There is already an account with this email "
                               "address")

        # unverified user, this should pass, old entry will be deleted
        signupdata['email'] = 'KAPAP-unverified@synnefo.org'
        r = client.post("/im/signup", signupdata)

        post_data = {'password': 'password',
                     'username': 'kpap@synnefo.org'}
        r = client.post('/im/local', post_data, follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        client.set_tokens(mail="kpap@shibboleth.gr", eppn="kpapeppn",
                          cn="Kostas Papadimitriou", )
        r = client.get("/im/login/shibboleth?", follow=True)
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
        r = client.get("/im/login/shibboleth?", follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue(r.context['request'].user.email == "kpap@synnefo.org")
        self.assertRedirects(r, '/im/landing')
        self.assertEqual(r.status_code, 200)
        client.logout()
        client.reset_tokens()

        # logged out
        r = client.get("/im/profile", follow=True)
        self.assertFalse(r.context['request'].user.is_authenticated())

        # login with local account also works
        post_data = {'password': 'password',
                     'username': 'kpap@synnefo.org'}
        r = self.client.post('/im/local', post_data, follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue(r.context['request'].user.email == "kpap@synnefo.org")
        self.assertRedirects(r, '/im/landing')
        self.assertEqual(r.status_code, 200)

        # cannot add the same eppn
        client.set_tokens(mail="secondary@shibboleth.gr", eppn="kpapeppn",
                          cn="Kostas Papadimitriou", )
        r = client.get("/im/login/shibboleth?", follow=True)
        self.assertRedirects(r, '/im/landing')
        self.assertTrue(r.status_code, 200)
        self.assertEquals(existing_user.auth_providers.count(), 2)

        # only one allowed by default
        client.set_tokens(mail="secondary@shibboleth.gr", eppn="kpapeppn2",
                          cn="Kostas Papadimitriou", ep_affiliation="affil2")
        prov = auth_providers.get_provider('shibboleth')
        r = client.get("/im/login/shibboleth?", follow=True)
        self.assertContains(r, "Failed to add")
        self.assertRedirects(r, '/im/profile')
        self.assertTrue(r.status_code, 200)
        self.assertEquals(existing_user.auth_providers.count(), 2)
        client.logout()
        client.reset_tokens()

        # cannot login with another eppn
        client.set_tokens(mail="kpap@synnefo.org", eppn="kpapeppninvalid",
                          cn="Kostas Papadimitriou")
        r = client.get("/im/login/shibboleth?", follow=True)
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
        r = client.get("/im/login/shibboleth?", follow=True)
        client.reset_tokens()

        # TODO: this view should use POST
        r = client.get(remove_local_url)
        # 2 providers left
        self.assertEqual(user.auth_providers.count(), 1)
        # cannot remove last provider
        r = client.get(remove_shibbo_url)
        self.assertEqual(r.status_code, 403)
        self.client.logout()

        # cannot login using local credentials (notice we use another client)
        post_data = {'password': 'password',
                     'username': 'kpap@synnefo.org'}
        r = self.client.post('/im/local', post_data, follow=True)
        self.assertFalse(r.context['request'].user.is_authenticated())

        # we can reenable the local provider by setting a password
        r = client.get("/im/password_change", follow=True)
        r = client.post("/im/password_change", {'new_password1': '111',
                                                'new_password2': '111'},
                        follow=True)
        user = r.context['request'].user
        self.assertTrue(user.has_auth_provider('local'))
        self.assertTrue(user.has_auth_provider('shibboleth'))
        self.assertTrue(user.check_password('111'))
        self.assertTrue(user.has_usable_password())
        self.client.logout()

        # now we can login
        post_data = {'password': '111',
                     'username': 'kpap@synnefo.org'}
        r = self.client.post('/im/local', post_data, follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())

        client.reset_tokens()

        # we cannot take over another shibboleth identifier
        user2 = get_local_user('another@synnefo.org')
        user2.add_auth_provider('shibboleth', identifier='existingeppn')
        # login
        client.set_tokens(mail="kpap@shibboleth.gr", eppn="kpapeppn",
                          cn="Kostas Papadimitriou")
        r = client.get("/im/login/shibboleth?", follow=True)
        # try to assign existing shibboleth identifier of another user
        client.set_tokens(mail="kpap_second@shibboleth.gr",
                          eppn="existingeppn", cn="Kostas Papadimitriou")
        r = client.get("/im/login/shibboleth?", follow=True)
        self.assertContains(r, "this account is already assigned")


class TestLocal(TestCase):

    fixtures = ['groups']

    def setUp(self):
        settings.ADMINS = (('admin', 'support@cloud.synnefo.org'),)
        settings.SERVER_EMAIL = 'no-reply@synnefo.org'
        self._orig_moderation = astakos_settings.MODERATION_ENABLED
        settings.ASTAKOS_MODERATION_ENABLED = True

    def tearDown(self):
        settings.ASTAKOS_MODERATION_ENABLED = self._orig_moderation

    def test_no_moderation(self):
        # disable moderation
        astakos_settings.MODERATION_ENABLED = False

        # create a new user
        r = self.client.get("/im/signup")
        self.assertEqual(r.status_code, 200)
        data = {'email': 'kpap@synnefo.org', 'password1': 'password',
                'password2': 'password', 'first_name': 'Kostas',
                'last_name': 'Mitroglou', 'provider': 'local'}
        r = self.client.post("/im/signup", data)

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
        r = self.client.get("/im/signup")
        self.assertEqual(r.status_code, 200)
        data = {'email': 'kpap@synnefo.org', 'password1': 'password',
                'password2': 'password', 'first_name': 'Kostas',
                'last_name': 'Mitroglou', 'provider': 'local'}
        r = self.client.post("/im/signup", data)

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
        r = self.client.post('/im/local', {'username': 'kpap@synnefo.org',
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
        r = self.client.post("/im/signup", data, follow=True)
        self.assertRedirects(r, reverse('index'))
        self.assertContains(r, messages.VERIFICATION_SENT)

        user = AstakosUser.objects.get()
        # previous user replaced
        self.assertTrue(user.activation_sent)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.is_active)
        self.assertEqual(len(get_mailbox('KPAP@synnefo.org')), 1)

        # hmmm, email exists; lets request a password change
        r = self.client.get('/im/local/password_reset')
        self.assertEqual(r.status_code, 200)
        data = {'email': 'kpap@synnefo.org'}
        r = self.client.post('/im/local/password_reset', data, follow=True)
        # she can't because account is not active yet
        self.assertContains(r, 'pending activation')

        # moderation is enabled and an activation email has already been sent
        # so user can trigger resend of the activation email
        r = self.client.get('/im/send/activation/%d' % user.pk, follow=True)
        self.assertContains(r, 'has been sent to your email address.')
        self.assertEqual(len(get_mailbox('KPAP@synnefo.org')), 2)

        # also she cannot login
        data = {'username': 'kpap@synnefo.org', 'password': 'password'}
        r = self.client.post('/im/local', data, follow=True)
        self.assertContains(r, 'Resend activation')
        self.assertFalse(r.context['request'].user.is_authenticated())
        self.assertFalse('_pithos2_a' in self.client.cookies)

        # user sees the message and resends activation
        r = self.client.get('/im/send/activation/%d' % user.pk, follow=True)
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
        self.assertRedirects(r, reverse('index'))
        # user sees that account is pending approval from admins
        self.assertContains(r, messages.NOTIFICATION_SENT)
        self.assertEqual(len(get_mailbox(self.helpdesk_email)), 1)

        user = AstakosUser.objects.get(email="KPAP@synnefo.org")
        result = backend.handle_moderation(user)
        backend.send_result_notifications(result, user)
        self.assertEqual(len(get_mailbox('KPAP@synnefo.org')), 4)
        self.assertEqual(len(get_mailbox(self.helpdesk_email)), 2)

        user = AstakosUser.objects.get(email="KPAP@synnefo.org")
        r = self.client.get('/im/profile', follow=True)
        self.assertFalse(r.context['request'].user.is_authenticated())
        self.assertFalse('_pithos2_a' in self.client.cookies)
        self.assertEqual(len(get_mailbox('KPAP@synnefo.org')), 4)

        user = AstakosUser.objects.get(pk=user.pk)
        r = self.client.post('/im/local', {'username': 'kpap@synnefo.org',
                                           'password': 'password'},
                             follow=True)
        # user activated and logged in, token cookie set
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue('_pithos2_a' in self.client.cookies)
        cookies = self.client.cookies
        self.assertTrue(quote(user.auth_token) in
                        cookies.get('_pithos2_a').value)
        r = self.client.get('/im/logout', follow=True)
        r = self.client.get('/im/')
        # user logged out, token cookie removed
        self.assertFalse(r.context['request'].user.is_authenticated())
        self.assertFalse(self.client.cookies.get('_pithos2_a').value)

        #https://docs.djangoproject.com/en/dev/topics/testing/#persistent-state
        del self.client.cookies['_pithos2_a']

        # user can login
        r = self.client.post('/im/local', {'username': 'kpap@synnefo.org',
                                           'password': 'password'},
                             follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue('_pithos2_a' in self.client.cookies)
        cookies = self.client.cookies
        self.assertTrue(quote(user.auth_token) in
                        cookies.get('_pithos2_a').value)
        self.client.get('/im/logout', follow=True)

        # user forgot password
        old_pass = user.password
        r = self.client.get('/im/local/password_reset')
        self.assertEqual(r.status_code, 200)
        r = self.client.post('/im/local/password_reset', {'email':
                                                          'kpap@synnefo.org'})
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
        r = self.client.post('/im/local', {'username': 'kpap@synnefo.org',
                                           'password': 'password'})
        self.assertContains(r, 'Please enter a correct username and password')
        r = self.client.post('/im/local', {'username': 'kpap@synnefo.org',
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
                                                          'kpap@synnefo.org'})
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
        r = self.client.get('/im/profile', follow=True)
        user = r.context['request'].user
        self.assertTrue(user.is_authenticated())

        # change email is enabled
        r = self.client.get('/im/email_change')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(user.email_change_is_pending())

        # request email change to an existing email fails
        data = {'new_email_address': 'existing@synnefo.org'}
        r = self.client.post('/im/email_change', data)
        self.assertContains(r, messages.EMAIL_USED)

        # proper email change
        data = {'new_email_address': 'kpap@gmail.com'}
        r = self.client.post('/im/email_change', data, follow=True)
        self.assertRedirects(r, '/im/profile')
        self.assertContains(r, messages.EMAIL_CHANGE_REGISTERED)
        change1 = EmailChange.objects.get()

        # user sees a warning
        r = self.client.get('/im/email_change')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, messages.PENDING_EMAIL_CHANGE_REQUEST)
        self.assertTrue(user.email_change_is_pending())

        # link was sent
        self.assertEqual(len(get_mailbox('kpap@synnefo.org')), 0)
        self.assertEqual(len(get_mailbox('kpap@gmail.com')), 1)

        # proper email change
        data = {'new_email_address': 'kpap@yahoo.com'}
        r = self.client.post('/im/email_change', data, follow=True)
        self.assertRedirects(r, '/im/profile')
        self.assertContains(r, messages.EMAIL_CHANGE_REGISTERED)
        self.assertEqual(len(get_mailbox('kpap@synnefo.org')), 0)
        self.assertEqual(len(get_mailbox('kpap@yahoo.com')), 1)
        change2 = EmailChange.objects.get()

        r = self.client.get(change1.get_url())
        self.assertEquals(r.status_code, 302)
        self.client.logout()

        r = self.client.post('/im/local?next=' + change2.get_url(),
                             {'username': 'kpap@synnefo.org',
                              'password': 'password',
                              'next': change2.get_url()},
                             follow=True)
        self.assertRedirects(r, '/im/profile')
        user = r.context['request'].user
        self.assertEquals(user.email, 'kpap@yahoo.com')
        self.assertEquals(user.username, 'kpap@yahoo.com')

        self.client.logout()
        r = self.client.post('/im/local?next=' + change2.get_url(),
                             {'username': 'kpap@synnefo.org',
                              'password': 'password',
                              'next': change2.get_url()},
                             follow=True)
        self.assertContains(r, "Please enter a correct username and password")
        self.assertEqual(user.emailchanges.count(), 0)


class TestAuthProviderViews(TestCase):

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
        r = cl_newuser.get('/im/login/shibboleth?', follow=True)
        pending = Pending.objects.get()
        identifier = pending.third_party_identifier
        signup_data = {'third_party_identifier': identifier,
                       'first_name': 'Academic',
                       'third_party_token': pending.token,
                       'last_name': 'New User',
                       'provider': 'shibboleth'}
        r = cl_newuser.post('/im/signup', signup_data)
        self.assertContains(r, "This field is required", )
        signup_data['email'] = 'olduser@synnefo.org'
        r = cl_newuser.post('/im/signup', signup_data)
        self.assertContains(r, "already an account with this email", )
        signup_data['email'] = 'newuser@synnefo.org'
        r = cl_newuser.post('/im/signup', signup_data, follow=True)
        r = cl_newuser.post('/im/signup', signup_data, follow=True)
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
        r = cl_newuser2.post('/im/signup', signup_data)
        self.assertContains(r, 'There is already an account with this '
                               'email address')
        signup_data['email'] = 'newuser@synnefo.org'
        r = cl_newuser2.post('/im/signup/', signup_data)
        self.assertFalse(academic_users.filter(email='newuser@synnefo.org'))
        r = self.client.get(activation_link, follow=True)
        self.assertEqual(r.status_code, 404)
        newuser = User.objects.get(email="newuser@synnefo.org")
        self.assertTrue(newuser.activation_sent)

        # activation sent, user didn't open verification url so additional
        # registrations invalidate the previous signups.
        self.assertFalse(academic_users.filter(email='newuser@synnefo.org'))
        r = cl_newuser.get('/im/login/shibboleth?', follow=True)
        pending = Pending.objects.get()
        identifier = pending.third_party_identifier
        signup_data = {'third_party_identifier': identifier,
                       'first_name': 'Academic',
                       'third_party_token': pending.token,
                       'last_name': 'New User',
                       'provider': 'shibboleth'}
        signup_data['email'] = 'newuser@synnefo.org'
        r = cl_newuser.post('/im/signup', signup_data)
        self.assertEqual(r.status_code, 302)
        newuser = User.objects.get(email="newuser@synnefo.org")
        self.assertTrue(newuser.activation_sent)
        activation_link = newuser.get_activation_url()
        self.assertTrue(academic_users.get(email='newuser@synnefo.org'))
        r = cl_newuser.get(newuser.get_activation_url(), follow=True)
        self.assertRedirects(r, '/im/landing')
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

        cl_newuser.get('/im/login/shibboleth?', follow=True)
        local = auth.get_provider('local', newuser)
        self.assertEqual(local.get_add_policy, False)
        self.assertEqual(local.get_login_policy, False)
        r = cl_newuser.get(local.get_add_url, follow=True)
        self.assertRedirects(r, '/im/profile')
        self.assertContains(r, 'disabled for your')

        cl_olduser.login(username='olduser@synnefo.org', password="password")
        r = cl_olduser.get('/im/profile', follow=True)
        self.assertEqual(r.status_code, 200)
        r = cl_olduser.get('/im/login/shibboleth?', follow=True)
        self.assertContains(r, 'Your request is missing a unique token')
        cl_olduser.set_tokens(eppn="newusereppn")
        r = cl_olduser.get('/im/login/shibboleth?', follow=True)
        self.assertContains(r, 'is already assigned to another user')
        cl_olduser.set_tokens(eppn="oldusereppn")
        r = cl_olduser.get('/im/login/shibboleth?', follow=True)
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
        login_data = {'username': 'olduser@synnefo.org', 'password': 'password'}
        r = cl_olduser.post('/im/local', login_data, follow=True)
        self.assertContains(r, "href='/im/login/shibboleth'>Academic login")
        Group.objects.all().delete()


class TestAuthProvidersAPI(TestCase):
    """
    Test auth_providers module API
    """

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
        self.client.get('/im/')

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


class TestProjects(TestCase):
    """
    Test projects.
    """
    def setUp(self):
        # astakos resources
        self.astakos_service = Service.objects.create(name="astakos",
                                                      api_url="/astakos/api/")
        self.resource = Resource.objects.create(name="astakos.pending_app",
                                                uplimit=0,
                                                allow_in_projects=False,
                                                service=self.astakos_service)

        # custom service resources
        self.service = Service.objects.create(name="service1",
                                              api_url="http://service.api")
        self.resource = Resource.objects.create(name="service1.resource",
                                                uplimit=100,
                                                service=self.service)
        self.admin = get_local_user("projects-admin@synnefo.org")
        self.admin.uuid = 'uuid1'
        self.admin.save()

        self.user = get_local_user("user@synnefo.org")
        self.member = get_local_user("member@synnefo.org")
        self.member2 = get_local_user("member2@synnefo.org")

        self.admin_client = get_user_client("projects-admin@synnefo.org")
        self.user_client = get_user_client("user@synnefo.org")
        self.member_client = get_user_client("member@synnefo.org")
        self.member2_client = get_user_client("member2@synnefo.org")

        quotas.qh_sync_users(AstakosUser.objects.all())

    @im_settings(PROJECT_ADMINS=['uuid1'])
    def test_application_limit(self):
        # user cannot create a project
        r = self.user_client.get(reverse('project_add'), follow=True)
        self.assertRedirects(r, reverse('project_list'))
        self.assertContains(r, "You are not allowed to create a new project")

        # but admin can
        r = self.admin_client.get(reverse('project_add'), follow=True)
        self.assertRedirects(r, reverse('project_add'))

    @im_settings(PROJECT_ADMINS=['uuid1'])
    def test_allow_in_project(self):
        dfrom = datetime.now()
        dto = datetime.now() + timedelta(days=30)

        # astakos.pending_uplimit allow_in_project flag is False
        # we shouldn't be able to create a project application using this
        # resource.
        application_data = {
            'name': 'project.synnefo.org',
            'homepage': 'https://www.synnefo.org',
            'start_date': dfrom.strftime("%Y-%m-%d"),
            'end_date': dto.strftime("%Y-%m-%d"),
            'member_join_policy': 2,
            'member_leave_policy': 1,
            'service1.resource_uplimit': 100,
            'is_selected_service1.resource': "1",
            'astakos.pending_app_uplimit': 100,
            'is_selected_accounts': "1",
            'user': self.user.pk
        }
        form = forms.ProjectApplicationForm(data=application_data)
        # form is invalid
        self.assertEqual(form.is_valid(), False)

        del application_data['astakos.pending_app_uplimit']
        del application_data['is_selected_accounts']
        form = forms.ProjectApplicationForm(data=application_data)
        self.assertEqual(form.is_valid(), True)

    @im_settings(PROJECT_ADMINS=['uuid1'])
    def test_applications(self):
        # let user have 2 pending applications
        quotas.add_base_quota(self.user, 'astakos.pending_app', 2)

        r = self.user_client.get(reverse('project_add'), follow=True)
        self.assertRedirects(r, reverse('project_add'))

        # user fills the project application form
        post_url = reverse('project_add') + '?verify=1'
        dfrom = datetime.now()
        dto = datetime.now() + timedelta(days=30)
        application_data = {
            'name': 'project.synnefo.org',
            'homepage': 'https://www.synnefo.org',
            'start_date': dfrom.strftime("%Y-%m-%d"),
            'end_date': dto.strftime("%Y-%m-%d"),
            'member_join_policy': 2,
            'member_leave_policy': 1,
            'service1.resource_uplimit': 100,
            'is_selected_service1.resource': "1",
            'user': self.user.pk
        }
        r = self.user_client.post(post_url, data=application_data, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['form'].is_valid(), True)

        # confirm request
        post_url = reverse('project_add') + '?verify=0&edit=0'
        r = self.user_client.post(post_url, data=application_data, follow=True)
        self.assertContains(r, "The project application has been received")
        self.assertRedirects(r, reverse('project_list'))
        self.assertEqual(ProjectApplication.objects.count(), 1)
        app1_id = ProjectApplication.objects.filter().order_by('pk')[0].pk

        # create another one
        application_data['name'] = 'project2.synnefo.org'
        r = self.user_client.post(post_url, data=application_data, follow=True)
        app2_id = ProjectApplication.objects.filter().order_by('pk')[1].pk

        # no more applications (LIMIT is 2)
        r = self.user_client.get(reverse('project_add'), follow=True)
        self.assertRedirects(r, reverse('project_list'))
        self.assertContains(r, "You are not allowed to create a new project")

        # login
        self.admin_client.get(reverse("edit_profile"))
        # admin approves
        r = self.admin_client.post(reverse('project_app_approve',
                                           kwargs={'application_id': app1_id}),
                                   follow=True)
        self.assertEqual(r.status_code, 200)

        # project created
        self.assertEqual(Project.objects.count(), 1)

        # login
        self.member_client.get(reverse("edit_profile"))
        # cannot join app2 (not approved yet)
        join_url = reverse("project_join", kwargs={'chain_id': app2_id})
        r = self.member_client.post(join_url, follow=True)
        self.assertEqual(r.status_code, 403)

        # can join app1
        self.member_client.get(reverse("edit_profile"))
        join_url = reverse("project_join", kwargs={'chain_id': app1_id})
        r = self.member_client.post(join_url, follow=True)
        self.assertEqual(r.status_code, 200)

        memberships = ProjectMembership.objects.all()
        self.assertEqual(len(memberships), 1)
        memb_id = memberships[0].id

        reject_member_url = reverse('project_reject_member',
                                    kwargs={'chain_id': app1_id, 'memb_id':
                                            memb_id})
        accept_member_url = reverse('project_accept_member',
                                    kwargs={'chain_id': app1_id, 'memb_id':
                                            memb_id})

        # only project owner is allowed to reject
        r = self.member_client.post(reject_member_url, follow=True)
        self.assertContains(r, "You do not have the permissions")
        self.assertEqual(r.status_code, 200)

        # user (owns project) rejects membership
        r = self.user_client.post(reject_member_url, follow=True)
        self.assertEqual(ProjectMembership.objects.count(), 0)

        # user rejoins
        self.member_client.get(reverse("edit_profile"))
        join_url = reverse("project_join", kwargs={'chain_id': app1_id})
        r = self.member_client.post(join_url, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ProjectMembership.objects.count(), 1)

        # user (owns project) accepts membership
        r = self.user_client.post(accept_member_url, follow=True)
        self.assertEqual(ProjectMembership.objects.count(), 1)
        membership = ProjectMembership.objects.get()
        self.assertEqual(membership.state, ProjectMembership.ACCEPTED)

        user_quotas = quotas.get_users_quotas([self.member])
        resource = 'service1.resource'
        newlimit = user_quotas[self.member.uuid]['system'][resource]['limit']
        # 100 from initial uplimit + 100 from project
        self.assertEqual(newlimit, 200)

        remove_member_url = reverse('project_remove_member',
                                    kwargs={'chain_id': app1_id, 'memb_id':
                                            membership.id})
        r = self.user_client.post(remove_member_url, follow=True)
        self.assertEqual(r.status_code, 200)

        user_quotas = quotas.get_users_quotas([self.member])
        resource = 'service1.resource'
        newlimit = user_quotas[self.member.uuid]['system'][resource]['limit']
        # 200 - 100 from project
        self.assertEqual(newlimit, 100)


ROOT = '/astakos/api/'
u = lambda url: ROOT + url


class QuotaAPITest(TestCase):
    def test_0(self):
        client = Client()
        # custom service resources
        service1 = Service.objects.create(
            name="service1", api_url="http://service1.api")
        resource11 = {"name": "service1.resource11",
                      "desc": "resource11 desc",
                      "allow_in_projects": True}
        r, _ = resources.add_resource(service1, resource11)
        resources.update_resource(r, 100)
        resource12 = {"name": "service1.resource12",
                      "desc": "resource11 desc",
                      "unit": "bytes"}
        r, _ = resources.add_resource(service1, resource12)
        resources.update_resource(r, 1024)

        # create user
        user = get_local_user('test@grnet.gr')
        quotas.qh_sync_user(user)

        # create another service
        service2 = Service.objects.create(
            name="service2", api_url="http://service2.api")
        resource21 = {"name": "service2.resource21",
                      "desc": "resource11 desc",
                      "allow_in_projects": False}
        r, _ = resources.add_resource(service2, resource21)
        resources.update_resource(r, 3)

        resource_names = [r['name'] for r in
                          [resource11, resource12, resource21]]

        # get resources
        r = client.get(u('resources'))
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        for name in resource_names:
            assertIn(name, body)

        # get quota
        r = client.get(u('quotas'))
        self.assertEqual(r.status_code, 401)

        headers = {'HTTP_X_AUTH_TOKEN': user.auth_token}
        r = client.get(u('quotas/'), **headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        system_quota = body['system']
        assertIn('system', body)
        for name in resource_names:
            assertIn(name, system_quota)

        r = client.get(u('service_quotas'))
        self.assertEqual(r.status_code, 401)

        s1_headers = {'HTTP_X_AUTH_TOKEN': service1.auth_token}
        r = client.get(u('service_quotas'), **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        assertIn(user.uuid, body)

        r = client.get(u('commissions'), **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        self.assertEqual(body, [])

        # issue some commissions
        commission_request = {
            "force": False,
            "auto_accept": False,
            "name": "my commission",
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": 1
                },
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource12['name'],
                    "quantity": 30000
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 413)

        commission_request = {
            "force": False,
            "auto_accept": False,
            "name": "my commission",
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": 1
                },
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource12['name'],
                    "quantity": 100
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)
        body = json.loads(r.content)
        serial = body['serial']
        self.assertEqual(serial, 1)

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)
        body = json.loads(r.content)
        self.assertEqual(body['serial'], 2)

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)
        body = json.loads(r.content)
        self.assertEqual(body['serial'], 3)

        r = client.get(u('commissions'), **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        self.assertEqual(body, [1, 2, 3])

        r = client.get(u('commissions/' + str(serial)), **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        self.assertEqual(body['serial'], serial)
        assertIn('issue_time', body)
        self.assertEqual(body['provisions'], commission_request['provisions'])
        self.assertEqual(body['name'], commission_request['name'])

        r = client.get(u('service_quotas?user=' + user.uuid), **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        user_quota = body[user.uuid]
        system_quota = user_quota['system']
        r11 = system_quota[resource11['name']]
        self.assertEqual(r11['usage'], 3)
        self.assertEqual(r11['pending'], 3)

        # resolve pending commissions
        resolve_data = {
            "accept": [1, 3],
            "reject": [2, 3, 4],
        }
        post_data = json.dumps(resolve_data)

        r = client.post(u('commissions/action'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        self.assertEqual(body['accepted'], [1])
        self.assertEqual(body['rejected'], [2])
        failed = body['failed']
        self.assertEqual(len(failed), 2)

        r = client.get(u('commissions/' + str(serial)), **s1_headers)
        self.assertEqual(r.status_code, 404)

        # auto accept
        commission_request = {
            "auto_accept": True,
            "name": "my commission",
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": 1
                },
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource12['name'],
                    "quantity": 100
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)
        body = json.loads(r.content)
        serial = body['serial']
        self.assertEqual(serial, 4)

        r = client.get(u('commissions/' + str(serial)), **s1_headers)
        self.assertEqual(r.status_code, 404)

        # malformed
        commission_request = {
            "auto_accept": True,
            "name": "my commission",
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                }
            ]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 400)

        commission_request = {
            "auto_accept": True,
            "name": "my commission",
            "provisions": "dummy"}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 400)

        r = client.post(u('commissions'), commission_request,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 400)

        # no holding
        commission_request = {
            "auto_accept": True,
            "name": "my commission",
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": "non existent",
                    "quantity": 1
                },
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource12['name'],
                    "quantity": 100
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 404)

        # release
        commission_request = {
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": -1
                }
            ]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)
        body = json.loads(r.content)
        serial = body['serial']

        accept_data = {'accept': ""}
        post_data = json.dumps(accept_data)
        r = client.post(u('commissions/' + str(serial) + '/action'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 200)

        reject_data = {'reject': ""}
        post_data = json.dumps(accept_data)
        r = client.post(u('commissions/' + str(serial) + '/action'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 404)

        # force
        commission_request = {
            "force": True,
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": 100
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 201)

        commission_request = {
            "force": True,
            "provisions": [
                {
                    "holder": user.uuid,
                    "source": "system",
                    "resource": resource11['name'],
                    "quantity": -200
                }]}

        post_data = json.dumps(commission_request)
        r = client.post(u('commissions'), post_data,
                        content_type='application/json', **s1_headers)
        self.assertEqual(r.status_code, 413)

        r = client.get(u('quotas'), **headers)
        self.assertEqual(r.status_code, 200)
        body = json.loads(r.content)
        system_quota = body['system']
        r11 = system_quota[resource11['name']]
        self.assertEqual(r11['usage'], 102)
        self.assertEqual(r11['pending'], 101)
