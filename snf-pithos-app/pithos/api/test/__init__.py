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
from urllib import quote, unquote

from snf_django.utils.testing import with_settings, astakos_user

from pithos.api import settings as pithos_settings
from pithos.api.test.util import is_date, get_random_data, get_random_name
from pithos.backends.migrate import initialize_db

from synnefo.lib.services import get_service_path
from synnefo.lib import join_urls

from django.test import TestCase
from django.test.simple import DjangoTestSuiteRunner
from django.conf import settings
from django.utils.http import urlencode
from django.db.backends.creation import TEST_DATABASE_PREFIX

import django.utils.simplejson as json

import random
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


def prepate_db_connection():
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
    def setup_databases(self, **kwargs):
        old_names, mirrors = super(PithosTestSuiteRunner,
                                   self).setup_databases(**kwargs)
        prepate_db_connection()
        return old_names, mirrors


class PithosAPITest(TestCase):
    def setUp(self):
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

    def head(self, url, user='user', data={}, follow=False, **extra):
        with astakos_user(user):
            extra = dict((quote(k), quote(v)) for k, v in extra.items())
            response = self.client.head(url, data, follow, **extra)
        return response

    def get(self, url, user='user', data={}, follow=False, **extra):
        with astakos_user(user):
            extra = dict((quote(k), quote(v)) for k, v in extra.items())
            response = self.client.get(url, data, follow, **extra)
        return response

    def delete(self, url, user='user', data={}, follow=False, **extra):
        with astakos_user(user):
            extra = dict((quote(k), quote(v)) for k, v in extra.items())
            response = self.client.delete(url, data, follow, **extra)
        return response

    def post(self, url, user='user', data={},
             content_type='application/octet-stream', follow=False, **extra):
        with astakos_user(user):
            extra = dict((quote(k), quote(v)) for k, v in extra.items())
            response = self.client.post(url, data, content_type, follow,
                                        **extra)
        return response

    def put(self, url, user='user', data={},
            content_type='application/octet-stream', follow=False, **extra):
        with astakos_user(user):
            extra = dict((quote(k), quote(v)) for k, v in extra.items())
            response = self.client.put(url, data, content_type, follow,
                                       **extra)
        return response

    def update_account_meta(self, meta, user=None):
        user = user or self.user
        kwargs = dict(
            ('HTTP_X_ACCOUNT_META_%s' % k, str(v)) for k, v in meta.items())
        url = join_urls(self.pithos_path, user)
        r = self.post('%s?update=' % url, user=user, **kwargs)
        self.assertEqual(r.status_code, 202)
        account_meta = self.get_account_meta()
        (self.assertTrue(k in account_meta) for k in meta.keys())
        (self.assertEqual(account_meta[k], v) for k, v in meta.items())

    def delete_account_meta(self, meta, user=None):
        user = user or self.user
        transform = lambda k: 'HTTP_X_ACCOUNT_META_%s' % k.replace('-', '_').upper()
        kwargs = dict((transform(k), '') for k, v in meta.items())
        url = join_urls(self.pithos_path, user)
        r = self.post('%s?update=' % url, user=user, **kwargs)
        self.assertEqual(r.status_code, 202)
        account_meta = self.get_account_meta()
        (self.assertTrue(k not in account_meta) for k in meta.keys())
        return r

    def delete_account_groups(self, groups, user=None):
        user = user or self.user
        url = join_urls(self.pithos_path, user)
        transform = lambda k: 'HTTP_X_ACCOUNT_GROUP_%s' % k.replace('-', '_').upper()
        kwargs = dict((transform(k), '') for k, v in groups.items())
        r = self.post('%s?update=' % url, user=user, **kwargs)
        self.assertEqual(r.status_code, 202)
        account_groups = self.get_account_groups()
        (self.assertTrue(k not in account_groups) for k in groups.keys())
        return r

    def get_account_info(self, until=None, user=None):
        user = user or self.user
        url = join_urls(self.pithos_path, user)
        if until is not None:
            parts = list(urlsplit(url))
            parts[3] = urlencode({
                'until': until
            })
            url = urlunsplit(parts)
        r = self.head(url, user=user)
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

    def get_container_info(self, container, until=None, user=None):
        user = user or self.user
        url = join_urls(self.pithos_path, user, container)
        if until is not None:
            parts = list(urlsplit(url))
            parts[3] = urlencode({
                'until': until
            })
            url = urlunsplit(parts)
        r = self.head(url, user=user)
        self.assertEqual(r.status_code, 204)
        return r

    def get_container_meta(self, container, until=None, user=None):
        prefix = 'X-Container-Meta-'
        r = self.get_container_info(container, until=until, user=user)
        headers = dict(r._headers.values())
        return filter_headers(headers, prefix)

    def update_container_meta(self, container, meta, user=None):
        user = user or self.user
        kwargs = dict(
            ('HTTP_X_CONTAINER_META_%s' % k, str(v)) for k, v in meta.items())
        url = join_urls(self.pithos_path, user, container)
        r = self.post('%s?update=' % url, user=user, **kwargs)
        self.assertEqual(r.status_code, 202)
        container_meta = self.get_container_meta(container)
        (self.assertTrue('X-Container-Meta-%s' % k in container_meta) for
            k in meta.keys())
        (self.assertEqual(container_meta['X-Container-Meta-%s' % k], v) for
            k, v in meta.items())

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

    def delete_container_content(self, cname, user=None):
        user = user or self.user
        url = join_urls(self.pithos_path, user, cname)
        r = self.delete('%s?delimiter=/' % url, user=user)
        self.assertEqual(r.status_code, 204)
        return r

    def delete_container(self, cname, user=None):
        user = user or self.user
        url = join_urls(self.pithos_path, user, cname)
        r = self.delete(url, user=user)
        self.assertEqual(r.status_code, 204)
        return r

    def create_container(self, cname=None, user=None):
        cname = cname or get_random_name()
        user = user or self.user
        url = join_urls(self.pithos_path, user, cname)
        r = self.put(url, user=user, data='')
        self.assertTrue(r.status_code in (202, 201))
        return cname, r

    def upload_object(self, cname, oname=None, length=None, verify=True,
                      user=None, **meta):
        oname = oname or get_random_name()
        length = length or random.randint(TEST_BLOCK_SIZE, 2 * TEST_BLOCK_SIZE)
        user = user or self.user
        data = get_random_data(length=length)
        headers = dict(('HTTP_X_OBJECT_META_%s' % k.upper(), v)
                       for k, v in meta.iteritems())
        url = join_urls(self.pithos_path, user, cname, oname)
        r = self.put(url, user=user, data=data, **headers)
        if verify:
            self.assertEqual(r.status_code, 201)
        return oname, data, r

    def update_object_data(self, cname, oname=None, length=None,
                           content_type=None, content_range=None,
                           verify=True, user=None, **meta):
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
        if verify:
            self.assertEqual(r.status_code, 204)
        return oname, data, r

    def append_object_data(self, cname, oname=None, length=None,
                           content_type=None, user=None):
        return self.update_object_data(cname, oname=oname,
                                       length=length,
                                       content_type=content_type,
                                       content_range='bytes */*',
                                       user=user)

    def create_folder(self, cname, oname=None, user=None, **headers):
        user = user or self.user
        oname = oname or get_random_name()
        url = join_urls(self.pithos_path, user, cname, oname)
        r = self.put(url, user=user, data='',
                     content_type='application/directory', **headers)
        self.assertEqual(r.status_code, 201)
        return oname, r

    def list_objects(self, cname, prefix=None, user=None):
        user = user or self.user
        url = join_urls(self.pithos_path, user, cname)
        path = '%s?format=json' % url
        if prefix is not None:
            path = '%s&prefix=%s' % (path, prefix)
        r = self.get(path, user=user)
        self.assertTrue(r.status_code in (200, 204))
        try:
            objects = json.loads(r.content)
        except:
            self.fail('json format expected')
        return objects

    def get_object_info(self, container, object, version=None, until=None,
                        user=None):
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
        self.assertEqual(r.status_code, 200)
        return r

    def get_object_meta(self, container, object, version=None, until=None,
                        user=None):
        prefix = 'X-Object-Meta-'
        r = self.get_object_info(container, object, version, until=until,
                                 user=user)
        headers = dict(r._headers.values())
        return filter_headers(headers, prefix)

    def update_object_meta(self, container, object, meta, user=None):
        user = user or self.user
        kwargs = dict(
            ('HTTP_X_OBJECT_META_%s' % k, str(v)) for k, v in meta.items())
        url = join_urls(self.pithos_path, user, container, object)
        r = self.post('%s?update=' % url, user=user, content_type='', **kwargs)
        self.assertEqual(r.status_code, 202)
        object_meta = self.get_object_meta(container, object)
        (self.assertTrue('X-Objecr-Meta-%s' % k in object_meta) for
            k in meta.keys())
        (self.assertEqual(object_meta['X-Object-Meta-%s' % k], v) for
            k, v in meta.items())

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
