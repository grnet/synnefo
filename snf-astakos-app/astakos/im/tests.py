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

from snf_django.utils.testing import with_settings, override_settings

from django.test import TestCase, Client
from django.core import mail
from django.http import SimpleCookie, HttpRequest, QueryDict
from django.utils.importlib import import_module

from astakos.im.activation_backends import *
from astakos.im.target.shibboleth import Tokens as ShibbolethTokens
from astakos.im.models import *
from astakos.im import functions
from astakos.im import settings as astakos_settings
from astakos.im import forms

from urllib import quote
from datetime import timedelta

from astakos.im import messages
from astakos.im import auth_providers
from astakos.im import quotas

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
        client.set_tokens(mail="kpap@grnet.gr", eppn="kpapeppn",
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
        post_data['email'] = 'kpap@grnet.gr'
        r = client.post(signup_url, post_data, follow=True)
        self.assertContains(r, messages.NOTIFICATION_SENT)

        # everything is ok in our db
        self.assertEqual(AstakosUser.objects.count(), 1)
        self.assertEqual(AstakosUserAuthProvider.objects.count(), 1)
        self.assertEqual(PendingThirdPartyUser.objects.count(), 0)

        # provider info stored
        provider = AstakosUserAuthProvider.objects.get(module="shibboleth")
        self.assertEqual(provider.affiliation, 'Test Affiliation')
        self.assertEqual(provider.info, {u'email': u'kpap@grnet.gr',
                                         u'eppn': u'kpapeppn',
                                         u'name': u'Kostas Papadimitriou'})

        # lets login (not activated yet)
        client.set_tokens(mail="kpap@grnet.gr", eppn="kpapeppn",
                          cn="Kostas Papadimitriou", )
        r = client.get("/im/login/shibboleth?", follow=True)
        self.assertContains(r, 'is pending moderation')

        # admin activates our user
        u = AstakosUser.objects.get(username="kpap@grnet.gr")
        functions.activate(u)
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
        existing_user = get_local_user('kpap@grnet.gr')
        existing_inactive = get_local_user('kpap-inactive@grnet.gr')
        existing_inactive.is_active = False
        existing_inactive.save()

        existing_unverified = get_local_user('kpap-unverified@grnet.gr')
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
        signupdata['email'] = 'kpap@grnet.gr'
        signupdata['third_party_token'] = token
        signupdata['provider'] = 'shibboleth'
        del signupdata['id']

        # the email exists to another user
        r = client.post("/im/signup", signupdata)
        self.assertContains(r, "There is already an account with this email "
                               "address")
        # change the case, still cannot create
        signupdata['email'] = 'KPAP@grnet.GR'
        r = client.post("/im/signup", signupdata)
        self.assertContains(r, "There is already an account with this email "
                               "address")
        # inactive user
        signupdata['email'] = 'KPAP-inactive@grnet.GR'
        r = client.post("/im/signup", signupdata)
        self.assertContains(r, "There is already an account with this email "
                               "address")

        # unverified user, this should pass, old entry will be deleted
        signupdata['email'] = 'KAPAP-unverified@grnet.GR'
        r = client.post("/im/signup", signupdata)

        post_data = {'password': 'password',
                     'username': 'kpap@grnet.gr'}
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
        self.assertTrue(r.context['request'].user.email == "kpap@grnet.gr")
        self.assertRedirects(r, '/im/landing')
        self.assertEqual(r.status_code, 200)
        client.logout()
        client.reset_tokens()

        # logged out
        r = client.get("/im/profile", follow=True)
        self.assertFalse(r.context['request'].user.is_authenticated())

        # login with local account also works
        post_data = {'password': 'password',
                     'username': 'kpap@grnet.gr'}
        r = self.client.post('/im/local', post_data, follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue(r.context['request'].user.email == "kpap@grnet.gr")
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
        client.set_tokens(mail="kpap@grnet.gr", eppn="kpapeppninvalid",
                          cn="Kostas Papadimitriou")
        r = client.get("/im/login/shibboleth?", follow=True)
        self.assertFalse(r.context['request'].user.is_authenticated())

        # cannot

        # lets remove local password
        user = AstakosUser.objects.get(username="kpap@grnet.gr",
                                       email="kpap@grnet.gr")
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
                     'username': 'kpap@grnet.gr'}
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
                     'username': 'kpap@grnet.gr'}
        r = self.client.post('/im/local', post_data, follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())

        client.reset_tokens()

        # we cannot take over another shibboleth identifier
        user2 = get_local_user('another@grnet.gr')
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
        settings.ADMINS = (('admin', 'support@cloud.grnet.gr'),)
        settings.SERVER_EMAIL = 'no-reply@grnet.gr'
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
        data = {'email': 'kpap@grnet.gr', 'password1': 'password',
                'password2': 'password', 'first_name': 'Kostas',
                'last_name': 'Mitroglou', 'provider': 'local'}
        r = self.client.post("/im/signup", data)

        # user created
        self.assertEqual(AstakosUser.objects.count(), 1)
        user = AstakosUser.objects.get(username="kpap@grnet.gr",
                                       email="kpap@grnet.gr")
        self.assertEqual(user.username, 'kpap@grnet.gr')
        self.assertEqual(user.has_auth_provider('local'), True)
        self.assertFalse(user.is_active)

        # user (but not admin) gets notified
        self.assertEqual(len(get_mailbox('support@cloud.grnet.gr')), 0)
        self.assertEqual(len(get_mailbox('kpap@grnet.gr')), 1)
        astakos_settings.MODERATION_ENABLED = True

    def test_email_case(self):
        data = {
            'email': 'kPap@grnet.gr',
            'password1': '1234',
            'password2': '1234'
        }

        form = forms.LocalUserCreationForm(data)
        self.assertTrue(form.is_valid())
        user = form.save()
        form.store_user(user, {})

        u = AstakosUser.objects.get()
        self.assertEqual(u.email, 'kPap@grnet.gr')
        self.assertEqual(u.username, 'kpap@grnet.gr')
        u.is_active = True
        u.email_verified = True
        u.save()

        data = {'username': 'kpap@grnet.gr', 'password': '1234'}
        login = forms.LoginForm(data=data)
        self.assertTrue(login.is_valid())

        data = {'username': 'KpaP@grnet.gr', 'password': '1234'}
        login = forms.LoginForm(data=data)
        self.assertTrue(login.is_valid())

        data = {
            'email': 'kpap@grnet.gr',
            'password1': '1234',
            'password2': '1234'
        }
        form = forms.LocalUserCreationForm(data)
        self.assertFalse(form.is_valid())

    @im_settings(HELPDESK=(('support', 'support@synnefo.org'),))
    @im_settings(FORCE_PROFILE_UPDATE=False)
    def test_local_provider(self):
        self.helpdesk_email = astakos_settings.HELPDESK[0][1]
        # enable moderation
        astakos_settings.MODERATION_ENABLED = True

        # create a user
        r = self.client.get("/im/signup")
        self.assertEqual(r.status_code, 200)
        data = {'email': 'kpap@grnet.gr', 'password1': 'password',
                'password2': 'password', 'first_name': 'Kostas',
                'last_name': 'Mitroglou', 'provider': 'local'}
        r = self.client.post("/im/signup", data)

        # user created
        self.assertEqual(AstakosUser.objects.count(), 1)
        user = AstakosUser.objects.get(username="kpap@grnet.gr",
                                       email="kpap@grnet.gr")
        self.assertEqual(user.username, 'kpap@grnet.gr')
        self.assertEqual(user.has_auth_provider('local'), True)
        self.assertFalse(user.is_active)  # not activated
        self.assertFalse(user.email_verified)  # not verified
        self.assertFalse(user.activation_sent)  # activation automatically sent

        # admin gets notified and activates the user from the command line
        self.assertEqual(len(get_mailbox(self.helpdesk_email)), 1)
        r = self.client.post('/im/local', {'username': 'kpap@grnet.gr',
                                           'password': 'password'})
        self.assertContains(r, messages.NOTIFICATION_SENT)
        functions.send_activation(user)

        # user activation fields updated and user gets notified via email
        user = AstakosUser.objects.get(pk=user.pk)
        self.assertTrue(user.activation_sent)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.is_active)
        self.assertEqual(len(get_mailbox('kpap@grnet.gr')), 1)

        # user forgot she got registered and tries to submit registration
        # form. Notice the upper case in email
        data = {'email': 'KPAP@grnet.gr', 'password1': 'password',
                'password2': 'password', 'first_name': 'Kostas',
                'last_name': 'Mitroglou', 'provider': 'local'}
        r = self.client.post("/im/signup", data, follow=True)
        self.assertRedirects(r, reverse('index'))
        self.assertContains(r, messages.NOTIFICATION_SENT)

        user = AstakosUser.objects.get()
        functions.send_activation(user)

        # previous user replaced
        self.assertTrue(user.activation_sent)
        self.assertFalse(user.email_verified)
        self.assertFalse(user.is_active)
        self.assertEqual(len(get_mailbox('KPAP@grnet.gr')), 1)

        # hmmm, email exists; lets request a password change
        r = self.client.get('/im/local/password_reset')
        self.assertEqual(r.status_code, 200)
        data = {'email': 'kpap@grnet.gr'}
        r = self.client.post('/im/local/password_reset', data, follow=True)
        # she can't because account is not active yet
        self.assertContains(r, 'pending activation')

        # moderation is enabled and an activation email has already been sent
        # so user can trigger resend of the activation email
        r = self.client.get('/im/send/activation/%d' % user.pk, follow=True)
        self.assertContains(r, 'has been sent to your email address.')
        self.assertEqual(len(get_mailbox('KPAP@grnet.gr')), 2)

        # also she cannot login
        data = {'username': 'kpap@grnet.gr', 'password': 'password'}
        r = self.client.post('/im/local', data, follow=True)
        self.assertContains(r, 'Resend activation')
        self.assertFalse(r.context['request'].user.is_authenticated())
        self.assertFalse('_pithos2_a' in self.client.cookies)

        # user sees the message and resends activation
        r = self.client.get('/im/send/activation/%d' % user.pk, follow=True)
        self.assertEqual(len(get_mailbox('KPAP@grnet.gr')), 3)

        # switch back moderation setting
        astakos_settings.MODERATION_ENABLED = True
        r = self.client.get(user.get_activation_url(), follow=True)
        self.assertRedirects(r, "/im/landing")
        r = self.client.get('/im/profile', follow=True)
        self.assertTrue(r.context['request'].user.is_authenticated())
        self.assertTrue('_pithos2_a' in self.client.cookies)
        self.assertContains(r, "KPAP@grnet.gr")
        self.assertEqual(len(get_mailbox('KPAP@grnet.gr')), 4)

        user = AstakosUser.objects.get(pk=user.pk)
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
        r = self.client.post('/im/local', {'username': 'kpap@grnet.gr',
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
                                                          'kpap@grnet.gr'})
        self.assertEqual(r.status_code, 302)
        # email sent
        self.assertEqual(len(get_mailbox('KPAP@grnet.gr')), 5)

        # user visits change password link
        r = self.client.get(user.get_password_reset_url())
        r = self.client.post(user.get_password_reset_url(),
                             {'new_password1': 'newpass',
                              'new_password2': 'newpass'})

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
        self.assertContains(r, "Changing password is not")


class UserActionsTests(TestCase):

    def test_email_change(self):
        # to test existing email validation
        get_local_user('existing@grnet.gr')

        # local user
        user = get_local_user('kpap@grnet.gr')

        # login as kpap
        self.client.login(username='kpap@grnet.gr', password='password')
        r = self.client.get('/im/profile', follow=True)
        user = r.context['request'].user
        self.assertTrue(user.is_authenticated())

        # change email is enabled
        r = self.client.get('/im/email_change')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(user.email_change_is_pending())

        # request email change to an existing email fails
        data = {'new_email_address': 'existing@grnet.gr'}
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
        self.assertEqual(len(get_mailbox('kpap@grnet.gr')), 0)
        self.assertEqual(len(get_mailbox('kpap@gmail.com')), 1)

        # proper email change
        data = {'new_email_address': 'kpap@yahoo.com'}
        r = self.client.post('/im/email_change', data, follow=True)
        self.assertRedirects(r, '/im/profile')
        self.assertContains(r, messages.EMAIL_CHANGE_REGISTERED)
        self.assertEqual(len(get_mailbox('kpap@grnet.gr')), 0)
        self.assertEqual(len(get_mailbox('kpap@yahoo.com')), 1)
        change2 = EmailChange.objects.get()

        r = self.client.get(change1.get_url())
        self.assertEquals(r.status_code, 302)
        self.client.logout()

        r = self.client.post('/im/local?next=' + change2.get_url(),
                             {'username': 'kpap@grnet.gr',
                              'password': 'password',
                              'next': change2.get_url()},
                             follow=True)
        self.assertRedirects(r, '/im/profile')
        user = r.context['request'].user
        self.assertEquals(user.email, 'kpap@yahoo.com')
        self.assertEquals(user.username, 'kpap@yahoo.com')

        self.client.logout()
        r = self.client.post('/im/local?next=' + change2.get_url(),
                             {'username': 'kpap@grnet.gr',
                              'password': 'password',
                              'next': change2.get_url()},
                             follow=True)
        self.assertContains(r, "Please enter a correct username and password")
        self.assertEqual(user.emailchanges.count(), 0)


class TestAuthProviderViews(TestCase):

    @shibboleth_settings(CREATION_GROUPS_POLICY=['academic-login'])
    @shibboleth_settings(AUTOMODERATE_POLICY=True)
    @im_settings(IM_MODULES=['shibboleth', 'local'])
    @im_settings(MODERATION_ENABLED=True)
    @im_settings(FORCE_PROFILE_UPDATE=False)
    def test_user(self):
        Profile = AuthProviderPolicyProfile
        Pending = PendingThirdPartyUser
        User = AstakosUser

        User.objects.create(email="newuser@grnet.gr")
        get_local_user("olduser@grnet.gr")
        cl_olduser = ShibbolethClient()
        get_local_user("olduser2@grnet.gr")
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
        self.assertFalse(academic_users.filter(email='newuser@grnet.gr'))
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
        signup_data['email'] = 'olduser@grnet.gr'
        r = cl_newuser.post('/im/signup', signup_data)
        self.assertContains(r, "already an account with this email", )
        signup_data['email'] = 'newuser@grnet.gr'
        r = cl_newuser.post('/im/signup', signup_data, follow=True)
        r = cl_newuser.post('/im/signup', signup_data, follow=True)
        self.assertEqual(r.status_code, 404)
        newuser = User.objects.get(email="newuser@grnet.gr")
        activation_link = newuser.get_activation_url()
        self.assertTrue(academic_users.get(email='newuser@grnet.gr'))

        # new non-academic user
        signup_data = {'first_name': 'Non Academic',
                       'last_name': 'New User',
                       'provider': 'local',
                       'password1': 'password',
                       'password2': 'password'}
        signup_data['email'] = 'olduser@grnet.gr'
        r = cl_newuser2.post('/im/signup', signup_data)
        self.assertContains(r, 'There is already an account with this '
                               'email address')
        signup_data['email'] = 'newuser@grnet.gr'
        r = cl_newuser2.post('/im/signup/', signup_data)
        self.assertFalse(academic_users.filter(email='newuser@grnet.gr'))
        r = self.client.get(activation_link, follow=True)
        self.assertEqual(r.status_code, 400)
        newuser = User.objects.get(email="newuser@grnet.gr")
        self.assertFalse(newuser.activation_sent)
        r = self.client.get(newuser.get_activation_url(), follow=True)
        self.assertContains(r, "pending moderation")

        self.assertFalse(academic_users.filter(email='newuser@grnet.gr'))
        r = cl_newuser.get('/im/login/shibboleth?', follow=True)
        pending = Pending.objects.get()
        identifier = pending.third_party_identifier
        signup_data = {'third_party_identifier': identifier,
                       'first_name': 'Academic',
                       'third_party_token': pending.token,
                       'last_name': 'New User',
                       'provider': 'shibboleth'}
        signup_data['email'] = 'newuser@grnet.gr'
        r = cl_newuser.post('/im/signup', signup_data)
        newuser = User.objects.get(email="newuser@grnet.gr")
        self.assertTrue(newuser.activation_sent)
        activation_link = newuser.get_activation_url()
        self.assertTrue(academic_users.get(email='newuser@grnet.gr'))
        r = cl_newuser.get(newuser.get_activation_url(), follow=True)
        self.assertRedirects(r, '/im/landing')
        newuser = User.objects.get(email="newuser@grnet.gr")
        self.assertEqual(newuser.is_active, True)
        self.assertEqual(newuser.email_verified, True)
        cl_newuser.logout()

        # cannot reactivate if suspended
        newuser.is_active = False
        newuser.save()
        r = cl_newuser.get(newuser.get_activation_url())
        newuser = User.objects.get(email="newuser@grnet.gr")
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

        cl_olduser.login(username='olduser@grnet.gr', password="password")
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

        user = User.objects.get(email="olduser@grnet.gr")
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
        login_data = {'username': 'olduser@grnet.gr', 'password': 'password'}
        r = cl_olduser.post('/im/local', login_data, follow=True)
        self.assertContains(r, "href='/im/login/shibboleth'>Academic login")


class TestAuthProvidersAPI(TestCase):
    """
    Test auth_providers module API
    """

    @im_settings(IM_MODULES=['local', 'shibboleth'])
    def test_create(self):
        user = AstakosUser.objects.create(email="kpap@grnet.gr")
        user2 = AstakosUser.objects.create(email="kpap2@grnet.gr")

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
    @shibboleth_settings(ADD_GROUPS_POLICY=['group1', 'group2'])
    @shibboleth_settings(CREATION_GROUPS_POLICY=['group-create', 'group1',
                                                 'group2'])
    @localauth_settings(ADD_GROUPS_POLICY=['localgroup'])
    @localauth_settings(CREATION_GROUPS_POLICY=['localgroup-create',
                                                'group-create'])
    def test_add_groups(self):
        user = AstakosUser.objects.create(email="kpap@grnet.gr")
        provider = auth.get_provider('shibboleth', user, 'test123')
        provider.add_to_user()
        user = AstakosUser.objects.get()
        self.assertItemsEqual(user.groups.values_list('name', flat=True),
                              [u'group1', u'group2', u'group-create'])

        local = auth.get_provider('local', user)
        local.add_to_user()
        provider = user.get_auth_provider('shibboleth')
        self.assertEqual(provider.get_add_groups_policy, ['group1', 'group2'])
        provider.remove_from_user()
        user = AstakosUser.objects.get()
        self.assertEqual(len(user.get_auth_providers()), 1)
        self.assertItemsEqual(user.groups.values_list('name', flat=True),
                              [u'group-create', u'localgroup'])

        local = user.get_auth_provider('local')
        self.assertRaises(Exception, local.remove_from_user)
        provider = auth.get_provider('shibboleth', user, 'test123')
        provider.add_to_user()
        user = AstakosUser.objects.get()
        self.assertItemsEqual(user.groups.values_list('name', flat=True),
                              [u'group-create', u'group1', u'group2',
                               u'localgroup'])



    @im_settings(IM_MODULES=['local', 'shibboleth'])
    def test_policies(self):
        group_old, created = Group.objects.get_or_create(name='olduser')

        astakos_settings.MODERATION_ENABLED = True
        settings.ASTAKOS_AUTH_PROVIDER_SHIBBOLETH_CREATION_GROUPS_POLICY = \
            ['academic-user']
        settings.ASTAKOS_AUTH_PROVIDER_GOOGLE_ADD_GROUPS_POLICY = \
            ['google-user']

        user = AstakosUser.objects.create(email="kpap@grnet.gr")
        user.groups.add(group_old)
        user.add_auth_provider('local')

        user2 = AstakosUser.objects.create(email="kpap2@grnet.gr")
        user2.add_auth_provider('shibboleth', identifier='shibid')

        user3 = AstakosUser.objects.create(email="kpap3@grnet.gr")
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
        user = get_local_user('kpap@grnet.gr')
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
        user = get_local_user('kpap@grnet.gr')
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
        user = get_local_user('kpap@grnet.gr')
        user.add_auth_provider('shibboleth', identifier='1234')
        user.add_auth_provider('shibboleth', identifier='12345')

        provider = auth_providers.get_provider('shibboleth')
        self.assertEqual(provider.get_template('login'),
                         'im/auth/shibboleth_login.html')
        provider = auth_providers.get_provider('google')
        self.assertEqual(provider.get_template('login'),
                         'im/auth/generic_login.html')


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
    def test_applications(self):
        # let user have 2 pending applications
        self.user.add_resource_policy('astakos.pending_app', 2)
        quotas.qh_sync_users(AstakosUser.objects.all())

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
            'is_selected_service1.resource': 1,
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

        self.assertEqual(ProjectMembership.objects.count(), 1)

        reject_member_url = reverse('project_reject_member',
                                    kwargs={'chain_id': app1_id, 'user_id':
                                            self.member.pk})
        accept_member_url = reverse('project_accept_member',
                                    kwargs={'chain_id': app1_id, 'user_id':
                                            self.member.pk})

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
                                    kwargs={'chain_id': app1_id, 'user_id':
                                            self.member.pk})
        r = self.user_client.post(remove_member_url, follow=True)
        self.assertEqual(r.status_code, 200)

        user_quotas = quotas.get_users_quotas([self.member])
        resource = 'service1.resource'
        newlimit = user_quotas[self.member.uuid]['system'][resource]['limit']
        # 200 - 100 from project
        self.assertEqual(newlimit, 100)
