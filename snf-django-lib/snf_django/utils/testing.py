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


from contextlib import contextmanager
from django.test import TestCase
from django.utils import simplejson as json
from django.utils.encoding import smart_unicode
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
    ...     assert settings.DEBUG == True

    The special arguemnt ``prefix`` can be set to prefix all setting keys with
    the provided value.

    >>> from django.conf import settings
    >>> from django.core import mail
    >>> with override_settings(settings, CONTACT_EMAILS=['kpap@grnet.gr'],
    ...                        prefix='MYAPP_'):
    ...     from django.core.mail import send_mail
    ...     send_mail("hello", "I love you kpap", settings.DEFAULT_FROM_EMAIL,
    ...               settings.MYAPP_CONTACT_EMAILS)
    ...     assert 'kpap@grnet.gr' in mail.mailbox[0].recipients()

    If you plan to reuse it

    >>> import functools
    >>> from synnefo.util.testing import override_settings
    >>> from django.conf import settings
    >>> myapp_settings = functools.partial(override_settings, prefix='MYAPP_')
    >>> with myapp_settings(CONTACT_EMAILS=['kpap@grnet.gr']):
    ...     assert settings.MYAPP_CONTACT_EMAILS == ['kpap@grnet.gr']

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
        with patch('astakosclient.AstakosClient.authenticate') as m2:
            m2.return_value = {"access": {
                "token": {
                    "expires": "2013-06-19T15:23:59.975572+00:00",
                    "id": "DummyToken",
                    "tenant": {
                        "id": smart_unicode(user, encoding='utf-8'),
                        "name": "Firstname Lastname"
                        }
                    },
                "serviceCatalog": [],
                "user": {
                    "roles_links": [],
                    "id": smart_unicode(user, encoding='utf-8'),
                    "roles": [{"id": 1, "name": "default"}],
                    "name": "Firstname Lastname"}}
                }

            with patch('astakosclient.AstakosClient.service_get_quotas') as m2:
                m2.return_value = {user: {
                    "system": {
                        "pithos.diskspace": {
                            "usage": 0,
                            "limit": 1073741824,  # 1GB
                            "pending": 0
                            }
                        }
                    }
                }
                issue_fun = \
                    "astakosclient.AstakosClient.issue_one_commission"
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
                        users_fun = \
                            'astakosclient.AstakosClient.get_usernames'
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

        def resolve_mock(*args, **kwargs):
            return {"failed": [],
                    "accepted": args[0],
                    "rejected": args[1],
                    }
        astakos.return_value.resolve_commissions.side_effect = resolve_mock
        yield astakos.return_value


class BaseAPITest(TestCase):
    def get(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            with mocked_quotaholder():
                response = self.client.get(url, *args, **kwargs)
        return response

    def head(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            with mocked_quotaholder():
                response = self.client.head(url, *args, **kwargs)
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
        self.assertTrue(response.status_code in [200, 202, 203, 204],
                        msg=response.content)

    def assertSuccess201(self, response):
        self.assertEqual(response.status_code, 201, msg=response.content)

    def assertFault(self, response, status_code, name, msg=''):
        self.assertEqual(response.status_code, status_code,
                         msg=msg)
        fault = json.loads(response.content)
        self.assertEqual(fault.keys(), [name])

    def assertBadRequest(self, response):
        self.assertFault(response, 400, 'badRequest', msg=response.content)

    def assertConflict(self, response):
        self.assertFault(response, 409, 'conflict', msg=response.content)

    def assertItemNotFound(self, response):
        self.assertFault(response, 404, 'itemNotFound', msg=response.content)

    def assertMethodNotAllowed(self, response):
        self.assertFault(response, 405, 'notAllowed', msg=response.content)
        self.assertTrue('Allow' in response)
        try:
            error = json.loads(response.content)
        except ValueError:
            self.assertTrue(False)
        self.assertEqual(error['notAllowed']['message'], 'Method not allowed')


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
