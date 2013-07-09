#!/usr/bin/env python
#coding=utf8

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

from urlparse import urlunsplit, urlsplit
from xml.dom import minidom

from snf_django.utils.testing import with_settings, astakos_user

from pithos.api import settings as pithos_settings
from pithos.api.test.util import is_date, get_random_data

from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls

from django.test import TestCase
from django.conf import settings
from django.utils.http import urlencode

import django.utils.simplejson as json

import random
import threading
import functools


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

return_codes = (400, 401, 403, 404, 503)

TEST_BLOCK_SIZE = 1024
TEST_HASH_ALGORITHM = 'sha256'

BACKEND_DB_CONNECTION = None


def django_to_sqlalchemy():
    """Convert the django default database to sqlalchemy connection string"""

    global BACKEND_DB_CONNECTION
    if BACKEND_DB_CONNECTION:
        return BACKEND_DB_CONNECTION

    # TODO support for more complex configuration
    db = settings.DATABASES['default']
    name = db.get('TEST_NAME', 'test_%s' % db['NAME'])
    if db['ENGINE'] == 'django.db.backends.sqlite3':
        BACKEND_DB_CONNECTION = 'sqlite:///%s' % name
    else:
        d = dict(scheme=django_sqlalchemy_engines.get(db['ENGINE']),
                 user=db['USER'],
                 pwd=db['PASSWORD'],
                 host=db['HOST'].lower(),
                 port=int(db['PORT']) if db['PORT'] != '' else '',
                 name=name)
        BACKEND_DB_CONNECTION = (
            '%(scheme)s://%(user)s:%(pwd)s@%(host)s:%(port)s/%(name)s' % d)
    return BACKEND_DB_CONNECTION


class PithosAPITest(TestCase):
    def setUp(self):
        if (pithos_settings.BACKEND_DB_MODULE ==
                'pithos.backends.lib.sqlalchemy'):
            pithos_settings.BACKEND_DB_CONNECTION = django_to_sqlalchemy()
            pithos_settings.BACKEND_POOL_SIZE = 1

        # Override default block size to spead up tests
        pithos_settings.BACKEND_BLOCK_SIZE = TEST_BLOCK_SIZE
        pithos_settings.BACKEND_HASH_ALGORITHM = TEST_HASH_ALGORITHM

        self.user = 'user'
        self.pithos_path = join_urls(get_service_path(
            pithos_settings.pithos_services, 'object-store'))

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

    def head(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            response = self.client.head(url, *args, **kwargs)
        return response

    def get(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            response = self.client.get(url, *args, **kwargs)
        return response

    def delete(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            response = self.client.delete(url, *args, **kwargs)
        return response

    def post(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            kwargs.setdefault('content_type', 'application/octet-stream')
            response = self.client.post(url, *args, **kwargs)
        return response

    def put(self, url, user='user', *args, **kwargs):
        with astakos_user(user):
            kwargs.setdefault('content_type', 'application/octet-stream')
            response = self.client.put(url, *args, **kwargs)
        return response

    def update_account_meta(self, meta):
        kwargs = dict(
            ('HTTP_X_ACCOUNT_META_%s' % k, str(v)) for k, v in meta.items())
        url = join_urls(self.pithos_path, self.user)
        r = self.post('%s?update=' % url, **kwargs)
        self.assertEqual(r.status_code, 202)
        account_meta = self.get_account_meta()
        (self.assertTrue('X-Account-Meta-%s' % k in account_meta) for
            k in meta.keys())
        (self.assertEqual(account_meta['X-Account-Meta-%s' % k], v) for
            k, v in meta.items())

    def reset_account_meta(self, meta):
        kwargs = dict(
            ('HTTP_X_ACCOUNT_META_%s' % k, str(v)) for k, v in meta.items())
        url = join_urls(self.pithos_path, self.user)
        r = self.post(url, **kwargs)
        self.assertEqual(r.status_code, 202)
        account_meta = self.get_account_meta()
        (self.assertTrue('X-Account-Meta-%s' % k in account_meta) for
            k in meta.keys())
        (self.assertEqual(account_meta['X-Account-Meta-%s' % k], v) for
            k, v in meta.items())

    def delete_account_meta(self, meta):
        transform = lambda k: 'HTTP_%s' % k.replace('-', '_').upper()
        kwargs = dict((transform(k), '') for k, v in meta.items())
        url = join_urls(self.pithos_path, self.user)
        r = self.post('%s?update=' % url, **kwargs)
        self.assertEqual(r.status_code, 202)
        account_meta = self.get_account_meta()
        (self.assertTrue('X-Account-Meta-%s' % k not in account_meta) for
            k in meta.keys())
        return r

    def delete_account_groups(self, groups):
        url = join_urls(self.pithos_path, self.user)
        r = self.post('%s?update=' % url, **groups)
        self.assertEqual(r.status_code, 202)
        return r

    def get_account_info(self, until=None):
        url = join_urls(self.pithos_path, self.user)
        if until is not None:
            parts = list(urlsplit(url))
            parts[3] = urlencode({
                'until': until
            })
            url = urlunsplit(parts)
        r = self.head(url)
        self.assertEqual(r.status_code, 204)
        return r

    def get_account_meta(self, until=None):
        r = self.get_account_info(until=until)
        headers = dict(r._headers.values())
        map(headers.pop,
            [k for k in headers.keys()
                if not k.startswith('X-Account-Meta-')])
        return headers

    def get_account_groups(self, until=None):
        r = self.get_account_info(until=until)
        headers = dict(r._headers.values())
        map(headers.pop,
            [k for k in headers.keys()
                if not k.startswith('X-Account-Group-')])
        return headers

    def get_container_info(self, container, until=None):
        url = join_urls(self.pithos_path, self.user, container)
        if until is not None:
            parts = list(urlsplit(url))
            parts[3] = urlencode({
                'until': until
            })
            url = urlunsplit(parts)
        r = self.head(url)
        self.assertEqual(r.status_code, 204)
        return r

    def get_container_meta(self, container, until=None):
        r = self.get_container_info(container, until=until)
        headers = dict(r._headers.values())
        map(headers.pop,
            [k for k in headers.keys()
                if not k.startswith('X-Container-Meta-')])
        return headers

    def update_container_meta(self, container, meta):
        kwargs = dict(
            ('HTTP_X_CONTAINER_META_%s' % k, str(v)) for k, v in meta.items())
        url = join_urls(self.pithos_path, self.user, container)
        r = self.post('%s?update=' % url, **kwargs)
        self.assertEqual(r.status_code, 202)
        container_meta = self.get_container_meta(container)
        (self.assertTrue('X-Container-Meta-%s' % k in container_meta) for
            k in meta.keys())
        (self.assertEqual(container_meta['X-Container-Meta-%s' % k], v) for
            k, v in meta.items())

    def list_containers(self, format='json', headers={}, **params):
        _url = join_urls(self.pithos_path, self.user)
        parts = list(urlsplit(_url))
        params['format'] = format
        parts[3] = urlencode(params)
        url = urlunsplit(parts)
        _headers = dict(('HTTP_%s' % k.upper(), str(v))
                        for k, v in headers.items())
        r = self.get(url, **_headers)

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

    def delete_container_content(self, cname):
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.delete('%s?delimiter=/' % url)
        self.assertEqual(r.status_code, 204)
        return r

    def delete_container(self, cname):
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.delete(url)
        self.assertEqual(r.status_code, 204)
        return r

    def create_container(self, cname):
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.put(url, data='')
        self.assertTrue(r.status_code in (202, 201))
        return r

    def upload_object(self, cname, oname=None, length=None, verify=True,
                      **meta):
        oname = oname or get_random_data(8)
        length = length or random.randint(TEST_BLOCK_SIZE, 2 * TEST_BLOCK_SIZE)
        data = get_random_data(length=length)
        headers = dict(('HTTP_X_OBJECT_META_%s' % k.upper(), v)
                       for k, v in meta.iteritems())
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.put(url, data=data, **headers)
        if verify:
            self.assertEqual(r.status_code, 201)
        return oname, data, r

    def update_object_data(self, cname, oname=None, length=None,
                           content_type=None, content_range=None,
                           verify=True, **meta):
        oname = oname or get_random_data(8)
        length = length or random.randint(TEST_BLOCK_SIZE, 2 * TEST_BLOCK_SIZE)
        content_type = content_type or 'application/octet-stream'
        data = get_random_data(length=length)
        headers = dict(('HTTP_X_OBJECT_META_%s' % k.upper(), v)
                       for k, v in meta.iteritems())
        if content_range:
            headers['HTTP_CONTENT_RANGE'] = content_range
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.post(url, data=data, content_type=content_type, **headers)
        if verify:
            self.assertEqual(r.status_code, 204)
        return oname, data, r

    def append_object_data(self, cname, oname=None, length=None,
                           content_type=None):
        return self.update_object_data(cname, oname=oname,
                                       length=length,
                                       content_type=content_type,
                                       content_range='bytes */*')

    def create_folder(self, cname, oname=None, **headers):
        oname = oname or get_random_data(8)
        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.put(url, data='', content_type='application/directory',
                     **headers)
        self.assertEqual(r.status_code, 201)
        return oname, r

    def list_objects(self, cname, prefix=None):
        url = join_urls(self.pithos_path, self.user, cname)
        path = '%s?format=json' % url
        if prefix is not None:
            path = '%s&prefix=%s' % (path, prefix)
        r = self.get(path)
        self.assertTrue(r.status_code in (200, 204))
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        return objects

    def get_object_info(self, container, object, version=None, until=None):
        url = join_urls(self.pithos_path, self.user, container, object)
        if until is not None:
            parts = list(urlsplit(url))
            parts[3] = urlencode({
                'until': until
            })
            url = urlunsplit(parts)
        if version:
            url = '%s?version=%s' % (url, version)
        r = self.head(url)
        self.assertEqual(r.status_code, 200)
        return r

    def get_object_meta(self, container, object, version=None, until=None):
        r = self.get_object_info(container, object, version, until=until)
        headers = dict(r._headers.values())
        map(headers.pop,
            [k for k in headers.keys()
                if not k.startswith('X-Object-Meta-')])
        return headers

    def update_object_meta(self, container, object, meta):
        kwargs = dict(
            ('HTTP_X_OBJECT_META_%s' % k, str(v)) for k, v in meta.items())
        url = join_urls(self.pithos_path, self.user, container, object)
        r = self.post('%s?update=' % url, content_type='', **kwargs)
        self.assertEqual(r.status_code, 202)
        object_meta = self.get_object_meta(container, object)
        (self.assertTrue('X-Objecr-Meta-%s' % k in object_meta) for
            k in meta.keys())
        (self.assertEqual(object_meta['X-Object-Meta-%s' % k], v) for
            k, v in meta.items())

    def assert_status(self, status, codes):
        l = [elem for elem in return_codes]
        if isinstance(codes, list):
            l.extend(codes)
        else:
            l.append(codes)
        self.assertTrue(status in l)

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


django_sqlalchemy_engines = {
    'django.db.backends.postgresql_psycopg2': 'postgresql+psycopg2',
    'django.db.backends.postgresql': 'postgresql',
    'django.db.backends.mysql': '',
    'django.db.backends.sqlite3': 'mssql',
    'django.db.backends.oracle': 'oracle'}


def test_concurrently(times=2):
    """
    Add this decorator to small pieces of code that you want to test
    concurrently to make sure they don't raise exceptions when run at the
    same time.  E.g., some Django views that do a SELECT and then a subsequent
    INSERT might fail when the INSERT assumes that the data has not changed
    since the SELECT.
    """
    def test_concurrently_decorator(test_func):
        def wrapper(*args, **kwargs):
            exceptions = []

            def call_test_func():
                try:
                    test_func(*args, **kwargs)
                except Exception, e:
                    exceptions.append(e)
                    raise

            threads = []
            for i in range(times):
                threads.append(threading.Thread())
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if exceptions:
                raise Exception(
                    ('test_concurrently intercepted %s',
                     'exceptions: %s') % (len(exceptions), exceptions))
        return wrapper
    return test_concurrently_decorator
