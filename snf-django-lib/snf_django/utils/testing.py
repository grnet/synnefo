# Copyright 2011-2013 GRNET S.A. All rights reserved.
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
from django.test import TestCase
from django.utils import simplejson as json
from synnefo.util import text
from mock import patch


@contextmanager
def override_settings(settings, **kwargs):
    """
    Helper context manager to override django settings within the provided
    context.

    All keyword arguments provided are set to the django settings object and
    get reverted/removed when the manager exits.

    >>> from synnefo.util.testing import override_settings
    >>> from django.conf import settings
    >>> with override_settings(settings, DEBUG=True):
    >>>     assert settings.DEBUG == True

    The special arguemnt ``prefix`` can be set to prefix all setting keys with
    the provided value.

    >>> from django.conf import settings
    >>> from django.core import mail
    >>> with override_settings(settings, CONTACT_EMAILS=['kpap@grnet.gr'],
    >>>                        prefix='MYAPP_'):
    >>>     from django.core.mail import send_mail
    >>>     send_mail("hello", "I love you kpap", settings.DEFAULT_FROM_EMAIL,
    >>>               settings.MYAPP_CONTACT_EMAILS)
    >>>     assert 'kpap@grnet.gr' in mail.mailbox[0].recipients()

    If you plan to reuse it

    >>> import functools
    >>> from synnefo.util.testing import override_settings
    >>> from django.conf import settings
    >>> myapp_settings = functools.partial(override_settings, prefix='MYAPP_')
    >>> with myapp_settings(CONTACT_EMAILS=['kpap@grnet.gr'])
    >>>     assert settings.MYAPP_CONTACT_EMAILS == ['kpap@grnet.gr']

    """

    _prefix = kwargs.get('prefix', '')
    prefix = lambda key: '%s%s' % (_prefix, key)

    oldkeys = [k for k in dir(settings) if k.upper() == k]
    oldsettings = dict([(k, getattr(settings, k)) for k in oldkeys])

    toremove = []
    for key, value in kwargs.iteritems():
        key = prefix(key)
        if not hasattr(settings, key):
            toremove.append(key)
        setattr(settings, key, value)

    yield

    # Remove keys that didn't exist
    for key in toremove:
        delattr(settings, key)

    # Remove keys that added during the execution of the context
    if kwargs.get('reset_changes', True):
        newkeys = [k for k in dir(settings) if k.upper() == k]
        for key in newkeys:
            if not key in oldkeys:
                delattr(settings, key)

    # Revert old keys
    for key in oldkeys:
        if key == key.upper():
            setattr(settings, key, oldsettings.get(key))


def with_settings(settings, prefix='', **override):
    def wrapper(func):
        def inner(*args, **kwargs):
            with override_settings(settings, prefix=prefix, **override):
                ret = func(*args, **kwargs)
            return ret
        return inner
    return wrapper

serial = 0


@contextmanager
def astakos_user(user):
    """
    Context manager to mock astakos response.

    usage:
    with astakos_user("user@user.com"):
        .... make api calls ....

    """
    with patch("snf_django.lib.api.get_token") as get_token:
        get_token.return_value = "DummyToken"
        with patch('astakosclient.AstakosClient.get_user_info') as m:
            m.return_value = {"uuid": text.udec(user, 'utf8')}
            with patch('astakosclient.AstakosClient.get_quotas') as m2:
                m2.return_value = {
                    "system": {
                        "pithos.diskspace": {
                            "usage": 0,
                            "limit": 1073741824,  # 1GB
                            "pending": 0
                        }
                    }
                }
                issue_fun = "astakosclient.AstakosClient.issue_one_commission"
                with patch(issue_fun) as m3:
                    serials = []
                    append = serials.append

                    def get_serial(*args, **kwargs):
                        global serial
                        serial += 1
                        append(serial)
                        return serial

                    m3.side_effect = get_serial
                    resolv_fun = \
                        'astakosclient.AstakosClient.resolve_commissions'
                    with patch(resolv_fun) as m4:
                        m4.return_value = {'accepted': serials,
                                           'rejected': [],
                                           'failed': []}
                        users_fun = 'astakosclient.AstakosClient.get_usernames'
                        with patch(users_fun) as m5:

                            def get_usernames(*args, **kwargs):
                                uuids = args[-1]
                                return dict((uuid, uuid) for uuid in uuids)

                            m5.side_effect = get_usernames
                            yield


serial = 0


@contextmanager
def mocked_quotaholder(success=True):
    with patch("synnefo.quotas.Quotaholder.get") as astakos:
        global serial
        serial += 10

        def foo(*args, **kwargs):
            return (len(astakos.return_value.issue_one_commission.mock_calls) +
                    serial)
        astakos.return_value.issue_one_commission.side_effect = foo
        astakos.return_value.resolve_commissions.return_value = {"failed": []}
        yield astakos.return_value


class BaseAPITest(TestCase):
    def get(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            with mocked_quotaholder():
                response = self.client.get(url, *args, **kwargs)
        return response

    def delete(self, url, user='user'):
        with astakos_user(user):
            with mocked_quotaholder() as m:
                self.mocked_quotaholder = m
                response = self.client.delete(url)
        return response

    def post(self, url, user='user', params={}, ctype='json', *args, **kwargs):
        if ctype == 'json':
            content_type = 'application/json'
        with astakos_user(user):
            with mocked_quotaholder() as m:
                self.mocked_quotaholder = m
                response = self.client.post(url, params,
                                            content_type=content_type,
                                            *args, **kwargs)
        return response

    def put(self, url, user='user', params={}, ctype='json', *args, **kwargs):
        if ctype == 'json':
            content_type = 'application/json'
        with astakos_user(user):
            with mocked_quotaholder() as m:
                self.mocked_quotaholder = m
                response = self.client.put(url, params,
                                           content_type=content_type,
                                           *args, **kwargs)
        return response

    def assertSuccess(self, response):
        self.assertTrue(response.status_code in [200, 202, 203, 204])

    def assertFault(self, response, status_code, name):
        self.assertEqual(response.status_code, status_code)
        fault = json.loads(response.content)
        self.assertEqual(fault.keys(), [name])

    def assertBadRequest(self, response):
        self.assertFault(response, 400, 'badRequest')

    def assertItemNotFound(self, response):
        self.assertFault(response, 404, 'itemNotFound')

    def assertMethodNotAllowed(self, response):
        self.assertFault(response, 400, 'badRequest')
        try:
            error = json.loads(response.content)
        except ValueError:
            self.assertTrue(False)
        self.assertEqual(error['badRequest']['message'], 'Method not allowed')


# Imitate unittest assertions new in Python 2.7

class _AssertRaisesContext(object):
    """
    A context manager used to implement TestCase.assertRaises* methods.
    Adapted from unittest2.
    """

    def __init__(self, expected):
        self.expected = expected

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is None:
            try:
                exc_name = self.expected.__name__
            except AttributeError:
                exc_name = str(self.expected)
            raise AssertionError(
                "%s not raised" % (exc_name,))
        if not issubclass(exc_type, self.expected):
            # let unexpected exceptions pass through
            return False
        self.exception = exc_value  # store for later retrieval
        return True


def assertRaises(excClass):
    return _AssertRaisesContext(excClass)


def assertGreater(x, y):
    assert x > y


def assertIn(x, y):
    assert x in y
