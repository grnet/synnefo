#!/usr/bin/env python
#coding=utf8
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

from urlparse import urlunsplit, urlsplit, urlparse
from xml.dom import minidom
from urllib import quote, unquote
from mock import patch, PropertyMock

from snf_django.utils.testing import with_settings, astakos_user

from pithos.api import settings as pithos_settings
from pithos.api.test.util import is_date, get_random_data, get_random_name
from pithos.backends.migrate import initialize_db

from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls

from django.test import TestCase
from django.test.client import Client, MULTIPART_CONTENT, FakePayload
from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings
from django.utils.http import urlencode
from django.utils.encoding import smart_unicode
from django.db.backends.creation import TEST_DATABASE_PREFIX

import django.utils.simplejson as json


import sys
import random
import functools
import time


pithos_test_settings = functools.partial(with_settings, pithos_settings)

DATE_FORMATS = ["%a %b %d %H:%M:%S %Y",
                "%A, %d-%b-%y %H:%M:%S GMT",
                "%a, %d %b %Y %H:%M:%S GMT"]

o_names = ['kate.jpg',
           'kate_beckinsale.jpg',
           'How To Win Friends And Influence People.pdf',
           'moms_birthday.jpg',
           'poodle_strut.mov',
           'Disturbed - Down With The Sickness.mp3',
           'army_of_darkness.avi',
           'the_mad.avi',
           'photos/animals/dogs/poodle.jpg',
           'photos/animals/dogs/terrier.jpg',
           'photos/animals/cats/persian.jpg',
           'photos/animals/cats/siamese.jpg',
           'photos/plants/fern.jpg',
           'photos/plants/rose.jpg',
           'photos/me.jpg']

details = {'container': ('name', 'count', 'bytes', 'last_modified',
                         'x_container_policy'),
           'object': ('name', 'hash', 'bytes', 'content_type',
                      'content_encoding', 'last_modified',)}

TEST_BLOCK_SIZE = 1024
TEST_HASH_ALGORITHM = 'sha256'

print 'backend module:', pithos_settings.BACKEND_DB_MODULE
print 'backend database engine:', settings.DATABASES['default']['ENGINE']
print 'update md5:', pithos_settings.UPDATE_MD5


django_sqlalchemy_engines = {
    'django.db.backends.postgresql_psycopg2': 'postgresql+psycopg2',
    'django.db.backends.postgresql': 'postgresql',
    'django.db.backends.mysql': '',
    'django.db.backends.sqlite3': 'mssql',
    'django.db.backends.oracle': 'oracle'}


def prepare_db_connection():
    """Build pithos backend connection string from django default database"""

    db = settings.DATABASES['default']
    name = db.get('TEST_NAME', TEST_DATABASE_PREFIX + db['NAME'])

    if (pithos_settings.BACKEND_DB_MODULE == 'pithos.backends.lib.sqlalchemy'):
        if db['ENGINE'] == 'django.db.backends.sqlite3':
            db_connection = 'sqlite:///%s' % name
        else:
            d = dict(scheme=django_sqlalchemy_engines.get(db['ENGINE']),
                     user=db['USER'],
                     pwd=db['PASSWORD'],
                     host=db['HOST'].lower(),
                     port=int(db['PORT']) if db['PORT'] != '' else '',
                     name=name)
            db_connection = (
                '%(scheme)s://%(user)s:%(pwd)s@%(host)s:%(port)s/%(name)s' % d)

            # initialize pithos database
            initialize_db(db_connection)
    else:
        db_connection = name
    pithos_settings.BACKEND_DB_CONNECTION = db_connection


def filter_headers(headers, prefix):
    meta = {}
    for k, v in headers.iteritems():
        if not k.startswith(prefix):
            continue
        meta[unquote(k[len(prefix):])] = unquote(v)
    return meta


class PithosTestSuiteRunner(DjangoTestSuiteRunner):
    def setup_test_environment(self, **kwargs):
        pithos_settings.BACKEND_MAPFILE_PREFIX = \
            'snf_test_pithos_app_%s_' % time.time()
        super(PithosTestSuiteRunner, self).setup_test_environment(**kwargs)

    def setup_databases(self, **kwargs):
        old_names, mirrors = super(PithosTestSuiteRunner,
                                   self).setup_databases(**kwargs)
        prepare_db_connection()
        return old_names, mirrors

    def teardown_databases(self, old_config, **kwargs):
        from pithos.api.util import _pithos_backend_pool
        _pithos_backend_pool.shutdown()
        try:
            super(PithosTestSuiteRunner, self).teardown_databases(old_config,
                                                                  **kwargs)
        except Exception as e:
            sys.stderr.write("FAILED to teardown databases: %s\n" % str(e))


class PithosTestClient(Client):
    def _get_path(self, parsed):
        # If there are parameters, add them
        if parsed[3]:
            return unquote(parsed[2] + ";" + parsed[3])
        else:
            return unquote(parsed[2])

    def copy(self, path, data={}, content_type=MULTIPART_CONTENT,
             follow=False, **extra):
        """
        Send a resource to the server using COPY.
        """
        parsed = urlparse(path)
        r = {
            'CONTENT_TYPE':    'text/html; charset=utf-8',
            'PATH_INFO':       self._get_path(parsed),
            'QUERY_STRING':    urlencode(data, doseq=True) or parsed[4],
            'REQUEST_METHOD': 'COPY',
            'wsgi.input':      FakePayload('')
        }
        r.update(extra)

        response = self.request(**r)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response

    def move(self, path, data={}, content_type=MULTIPART_CONTENT,
             follow=False, **extra):
        """
        Send a resource to the server using MOVE.
        """
        parsed = urlparse(path)
        r = {
            'CONTENT_TYPE':    'text/html; charset=utf-8',
            'PATH_INFO':       self._get_path(parsed),
            'QUERY_STRING':    urlencode(data, doseq=True) or parsed[4],
            'REQUEST_METHOD': 'MOVE',
            'wsgi.input':      FakePayload('')
        }
        r.update(extra)

        response = self.request(**r)
        if follow:
            response = self._handle_redirects(response, **extra)
        return response


class PithosAPITest(TestCase):
    def create_patch(self, name, new_callable=None):
        patcher = patch(name, new_callable=new_callable)
        thing = patcher.start()
        self.addCleanup(patcher.stop)
        return thing

    def setUp(self):
        self.client = PithosTestClient()

        # Override default block size to spead up tests
        pithos_settings.BACKEND_BLOCK_SIZE = TEST_BLOCK_SIZE
        pithos_settings.BACKEND_HASH_ALGORITHM = TEST_HASH_ALGORITHM

        self.user = 'user'
        self.pithos_path = join_urls(get_service_path(
            pithos_settings.pithos_services, 'object-store'))

        # patch astakosclient.AstakosClient.validate_token
        mock_validate_token = self.create_patch(
            'astakosclient.AstakosClient.validate_token')
        mock_validate_token.return_value = {
            'access': {
                'user': {'id': smart_unicode(self.user, encoding='utf-8')}}
            }

        # patch astakosclient.AstakosClient.get_token
        mock_get_token = self.create_patch(
            'astakosclient.AstakosClient.get_token')
        mock_get_token.return_value = {'access_token': 'valid_token'}

        # patch astakosclient.AstakosClient.api_oa2_auth
        mock_api_oauth2_auth = self.create_patch(
            'astakosclient.AstakosClient.oauth2_url',
            new_callable=PropertyMock)
        mock_api_oauth2_auth.return_value = '/astakos/oauth2/'

        mock_service_get_quotas = self.create_patch(
            'astakosclient.AstakosClient.service_get_quotas')
        mock_service_get_quotas.return_value = {
            self.user: {
                "system": {
                    "pithos.diskspace": {
                        "usage": 0,
                        "limit": 1073741824,  # 1GB
                        "pending": 0}}}}

    def tearDown(self):
        #delete additionally created metadata
        meta = self.get_account_meta()
        self.delete_account_meta(meta)

        #delete additionally created groups
        groups = self.get_account_groups()
        self.delete_account_groups(groups)

        self._clean_account()

    def _clean_account(self):
        for c in self.list_containers():
            self.delete_container_content(c['name'])
            self.delete_container(c['name'])

    def head(self, url, user='user', token='DummyToken', data={}, follow=False,
             **extra):
        with astakos_user(user):
            extra = dict((quote(k), quote(v)) for k, v in extra.items())
            if token:
                extra['HTTP_X_AUTH_TOKEN'] = token
            response = self.client.head(url, data, follow, **extra)
        return response

    def get(self, url, user='user', token='DummyToken', data={}, follow=False,
            **extra):
        with astakos_user(user):
            extra = dict((quote(k), quote(v)) for k, v in extra.items())
            if token:
                extra['HTTP_X_AUTH_TOKEN'] = token
            response = self.client.get(url, data, follow, **extra)
        return response

    def delete(self, url, user='user', token='DummyToken', data={},
               follow=False, **extra):
        with astakos_user(user):
            extra = dict((quote(k), quote(v)) for k, v in extra.items())
            if token:
                extra['HTTP_X_AUTH_TOKEN'] = token
            response = self.client.delete(url, data, follow, **extra)
        return response

    def post(self, url, user='user', token='DummyToken', data={},
             content_type='application/octet-stream', follow=False, **extra):
        with astakos_user(user):
            extra = dict((quote(k), quote(v)) for k, v in extra.items())
            if token:
                extra['HTTP_X_AUTH_TOKEN'] = token
            response = self.client.post(url, data, content_type, follow,
                                        **extra)
        return response

    def put(self, url, user='user', token='DummyToken', data={},
            content_type='application/octet-stream', follow=False,
            quote_extra=True, **extra):
        with astakos_user(user):
            if quote_extra:
                extra = dict((quote(k), quote(v)) for k, v in extra.items())
            if token:
                extra['HTTP_X_AUTH_TOKEN'] = token
            response = self.client.put(url, data, content_type, follow,
                                       **extra)
        return response

    def copy(self, url, user='user', token='DummyToken', data={},
             content_type='application/octet-stream', follow=False, **extra):
        with astakos_user(user):
            extra = dict((quote(k), quote(v)) for k, v in extra.items())
            if token:
                extra['HTTP_X_AUTH_TOKEN'] = token
            response = self.client.copy(url, data, content_type, follow,
                                        **extra)
        return response

    def move(self, url, user='user', token='DummyToken', data={},
             content_type='application/octet-stream', follow=False, **extra):
        with astakos_user(user):
            extra = dict((quote(k), quote(v)) for k, v in extra.items())
            if token:
                extra['HTTP_X_AUTH_TOKEN'] = token
            response = self.client.move(url, data, content_type, follow,
                                        **extra)
        return response

    def update_account_meta(self, meta, user=None, verify_status=True):
        user = user or self.user
        kwargs = dict(
            ('HTTP_X_ACCOUNT_META_%s' % k, str(v)) for k, v in meta.items())
        url = join_urls(self.pithos_path, user)
        r = self.post('%s?update=' % url, user=user, **kwargs)
        if verify_status:
            self.assertEqual(r.status_code, 202)
        account_meta = self.get_account_meta(user=user)
        (self.assertTrue('X-Account-Meta-%s' % k in account_meta) for
            k in meta.keys())
        (self.assertEqual(account_meta['X-Account-Meta-%s' % k], v) for
            k, v in meta.items())

    def reset_account_meta(self, meta, user=None, verify_status=True):
        user = user or self.user
        kwargs = dict(
            ('HTTP_X_ACCOUNT_META_%s' % k, str(v)) for k, v in meta.items())
        url = join_urls(self.pithos_path, user)
        r = self.post(url, user=user, **kwargs)
        if verify_status:
            self.assertEqual(r.status_code, 202)
        account_meta = self.get_account_meta(user=user)
        (self.assertTrue('X-Account-Meta-%s' % k in account_meta) for
            k in meta.keys())
        (self.assertEqual(account_meta['X-Account-Meta-%s' % k], v) for
            k, v in meta.items())

    def delete_account_meta(self, meta, user=None, verify_status=True):
        user = user or self.user
        transform = lambda k: 'HTTP_%s' % k.replace('-', '_').upper()
        kwargs = dict((transform(k), '') for k, v in meta.items())
        url = join_urls(self.pithos_path, user)
        r = self.post('%s?update=' % url, user=user, **kwargs)
        if verify_status:
            self.assertEqual(r.status_code, 202)
        account_meta = self.get_account_meta(user=user)
        (self.assertTrue('X-Account-Meta-%s' % k not in account_meta) for
            k in meta.keys())
        return r

    def delete_account_groups(self, groups, user=None, verify_status=True):
        user = user or self.user
        url = join_urls(self.pithos_path, user)
        r = self.post('%s?update=' % url, user=user, **groups)
        if verify_status:
            self.assertEqual(r.status_code, 202)
        account_groups = self.get_account_groups()
        (self.assertTrue(k not in account_groups) for k in groups.keys())
        return r

    def get_account_info(self, until=None, user=None, verify_status=True):
        user = user or self.user
        url = join_urls(self.pithos_path, user)
        if until is not None:
            parts = list(urlsplit(url))
            parts[3] = urlencode({
                'until': until
            })
            url = urlunsplit(parts)
        r = self.head(url, user=user)
        if verify_status:
            self.assertEqual(r.status_code, 204)
        return r

    def get_account_meta(self, until=None, user=None):
        prefix = 'X-Account-Meta-'
        r = self.get_account_info(until=until, user=user)
        headers = dict(r._headers.values())
        return filter_headers(headers, prefix)

    def get_account_groups(self, until=None, user=None):
        prefix = 'X-Account-Group-'
        r = self.get_account_info(until=until, user=user)
        headers = dict(r._headers.values())
        return filter_headers(headers, prefix)

    def get_container_info(self, container, until=None, user=None,
                           verify_status=True):
        user = user or self.user
        url = join_urls(self.pithos_path, user, container)
        if until is not None:
            parts = list(urlsplit(url))
            parts[3] = urlencode({
                'until': until
            })
            url = urlunsplit(parts)
        r = self.head(url, user=user)
        if verify_status:
            self.assertEqual(r.status_code, 204)
        return r

    def get_container_meta(self, container, until=None, user=None):
        prefix = 'X-Container-Meta-'
        r = self.get_container_info(container, until=until, user=user)
        headers = dict(r._headers.values())
        return filter_headers(headers, prefix)

    def update_container_meta(self, container, meta=None, user=None,
                              verify_status=True):
        user = user or self.user
        meta = meta or {get_random_name(): get_random_name()}
        kwargs = dict(
            ('HTTP_X_CONTAINER_META_%s' % k, str(v)) for k, v in meta.items())
        url = join_urls(self.pithos_path, user, container)
        r = self.post('%s?update=' % url, user=user, **kwargs)
        if verify_status:
            self.assertEqual(r.status_code, 202)
        container_meta = self.get_container_meta(container, user=user)
        (self.assertTrue('X-Container-Meta-%s' % k in container_meta) for
            k in meta.keys())
        (self.assertEqual(container_meta['X-Container-Meta-%s' % k], v) for
            k, v in meta.items())
        return r

    def list_containers(self, format='json', headers={}, user=None, **params):
        user = user or self.user
        _url = join_urls(self.pithos_path, user)
        parts = list(urlsplit(_url))
        params['format'] = format
        parts[3] = urlencode(params)
        url = urlunsplit(parts)
        _headers = dict(('HTTP_%s' % k.upper(), str(v))
                        for k, v in headers.items())
        r = self.get(url, user=user, **_headers)

        if format is None:
            containers = r.content.split('\n')
            if '' in containers:
                containers.remove('')
            return containers
        elif format == 'json':
            try:
                containers = json.loads(r.content)
            except:
                self.fail('json format expected')
            return containers
        elif format == 'xml':
            return minidom.parseString(r.content)

    def delete_container_content(self, cname, user=None, verify_status=True):
        user = user or self.user
        url = join_urls(self.pithos_path, user, cname)
        r = self.delete('%s?delimiter=/' % url, user=user)
        if verify_status:
            self.assertEqual(r.status_code, 204)
        return r

    def delete_container(self, cname, user=None, verify_status=True):
        user = user or self.user
        url = join_urls(self.pithos_path, user, cname)
        r = self.delete(url, user=user)
        if verify_status:
            self.assertEqual(r.status_code, 204)
        return r

    def delete_object(self, cname, oname, user=None, verify_status=True):
        user = user or self.user
        url = join_urls(self.pithos_path, user, cname, oname)
        r = self.delete(url, user=user)
        if verify_status:
            self.assertEqual(r.status_code, 204)
        return r

    def create_container(self, cname=None, user=None, verify_status=True):
        cname = cname or get_random_name()
        user = user or self.user
        url = join_urls(self.pithos_path, user, cname)
        r = self.put(url, user=user, data='')
        if verify_status:
            self.assertTrue(r.status_code in (202, 201))
        return cname, r

    def upload_object(self, cname, oname=None, length=None, verify_status=True,
                      user=None, **meta):
        oname = oname or get_random_name()
        length = length or random.randint(TEST_BLOCK_SIZE, 2 * TEST_BLOCK_SIZE)
        user = user or self.user
        data = get_random_data(length=length)
        headers = dict(('HTTP_X_OBJECT_META_%s' % k.upper(), v)
                       for k, v in meta.iteritems())
        url = join_urls(self.pithos_path, user, cname, oname)
        r = self.put(url, user=user, data=data, **headers)
        if verify_status:
            self.assertEqual(r.status_code, 201)
        return oname, data, r

    def update_object_data(self, cname, oname=None, length=None,
                           content_type=None, content_range=None,
                           verify_status=True, user=None, **meta):
        oname = oname or get_random_name()
        length = length or random.randint(TEST_BLOCK_SIZE, 2 * TEST_BLOCK_SIZE)
        content_type = content_type or 'application/octet-stream'
        user = user or self.user
        data = get_random_data(length=length)
        headers = dict(('HTTP_X_OBJECT_META_%s' % k.upper(), v)
                       for k, v in meta.iteritems())
        if content_range:
            headers['HTTP_CONTENT_RANGE'] = content_range
        url = join_urls(self.pithos_path, user, cname, oname)
        r = self.post(url, user=user, data=data, content_type=content_type,
                      **headers)
        if verify_status:
            self.assertEqual(r.status_code, 204)
        return oname, data, r

    def append_object_data(self, cname, oname=None, length=None,
                           content_type=None, user=None):
        return self.update_object_data(cname, oname=oname,
                                       length=length,
                                       content_type=content_type,
                                       content_range='bytes */*',
                                       user=user)

    def create_folder(self, cname, oname=None, user=None, verify_status=True,
                      **headers):
        user = user or self.user
        oname = oname or get_random_name()
        url = join_urls(self.pithos_path, user, cname, oname)
        r = self.put(url, user=user, data='',
                     content_type='application/directory', **headers)
        if verify_status:
            self.assertEqual(r.status_code, 201)
        return oname, r

    def list_objects(self, cname, prefix=None, user=None, verify_status=True):
        user = user or self.user
        url = join_urls(self.pithos_path, user, cname)
        path = '%s?format=json' % url
        if prefix is not None:
            path = '%s&prefix=%s' % (path, prefix)
        r = self.get(path, user=user)
        if verify_status:
            self.assertTrue(r.status_code in (200, 204))
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        return objects

    def get_object_info(self, container, object, version=None, until=None,
                        user=None, verify_status=True):
        user = user or self.user
        url = join_urls(self.pithos_path, user, container, object)
        if until is not None:
            parts = list(urlsplit(url))
            parts[3] = urlencode({
                'until': until
            })
            url = urlunsplit(parts)
        if version:
            url = '%s?version=%s' % (url, version)
        r = self.head(url, user=user)
        if verify_status:
            self.assertEqual(r.status_code, 200)
        return r

    def get_object_meta(self, container, object, version=None, until=None,
                        user=None):
        prefix = 'X-Object-Meta-'
        user = user or self.user
        r = self.get_object_info(container, object, version, until=until,
                                 user=user)
        headers = dict(r._headers.values())
        return filter_headers(headers, prefix)

    def update_object_meta(self, container, object, meta=None, user=None,
                           verify_status=True):
        user = user or self.user
        meta = meta or {get_random_name(): get_random_name()}
        kwargs = dict(
            ('HTTP_X_OBJECT_META_%s' % k, str(v)) for k, v in meta.items())
        url = join_urls(self.pithos_path, user, container, object)
        r = self.post('%s?update=' % url, user=user, content_type='', **kwargs)
        if verify_status:
            self.assertEqual(r.status_code, 202)
        object_meta = self.get_object_meta(container, object, user=user)
        (self.assertTrue('X-Objecr-Meta-%s' % k in object_meta) for
            k in meta.keys())
        (self.assertEqual(object_meta['X-Object-Meta-%s' % k], v) for
            k, v in meta.items())
        return r

    def assert_extended(self, data, format, type, size=10000):
        if format == 'xml':
            self._assert_xml(data, type, size)
        elif format == 'json':
            self._assert_json(data, type, size)

    def _assert_json(self, data, type, size):
        convert = lambda s: s.lower()
        info = [convert(elem) for elem in details[type]]
        self.assertTrue(len(data) <= size)
        for item in info:
            for i in data:
                if 'subdir' in i.keys():
                    continue
                self.assertTrue(item in i.keys())

    def _assert_xml(self, data, type, size):
        convert = lambda s: s.lower()
        info = [convert(elem) for elem in details[type]]
        try:
            info.remove('content_encoding')
        except ValueError:
            pass
        xml = data
        entities = xml.getElementsByTagName(type)
        self.assertTrue(len(entities) <= size)
        for e in entities:
            for item in info:
                self.assertTrue(e.getElementsByTagName(item))


class AssertMappingInvariant(object):
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.map = self.callable(*self.args, **self.kwargs)
        return self.map

    def __exit__(self, type, value, tb):
        map = self.callable(*self.args, **self.kwargs)
        for k, v in self.map.items():
            if is_date(v):
                continue

            assert(k in map), '%s not in map' % k
            assert v == map[k]


class AssertUUidInvariant(object):
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        self.map = self.callable(*self.args, **self.kwargs)
        assert('x-object-uuid' in self.map)
        self.uuid = self.map['x-object-uuid']
        return self.map

    def __exit__(self, type, value, tb):
        map = self.callable(*self.args, **self.kwargs)
        assert('x-object-uuid' in self.map)
        uuid = map['x-object-uuid']
        assert(uuid == self.uuid)
