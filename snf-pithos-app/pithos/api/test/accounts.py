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

from pithos.api.test import (PithosAPITest, AssertMappingInvariant,
                             DATE_FORMATS)

from synnefo.lib import join_urls

import time as _time
import datetime


class AccountHead(PithosAPITest):
    def test_get_account_meta(self):
        cnames = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']

        # create containers
        uploaded_bytes = 0
        for cname in cnames:
            self.create_container(cname)

            # upload object
            name, data, resp = self.upload_object(cname)
            uploaded_bytes += len(data)

        # set account meta
        self.update_account_meta({'foo': 'bar'})

        account_info = self.get_account_info()
        self.assertTrue('X-Account-Meta-Foo' in account_info)
        self.assertEqual(account_info['X-Account-Meta-Foo'], 'bar')

        # list containers
        containers = self.list_containers()
        self.assertEqual(int(account_info['X-Account-Container-Count']),
                         len(containers))
        usage = 0
        for c in containers:
            # list objects
            objects = self.list_objects(c['name'])
            self.assertEqual(c['count'], len(objects))
            csum = sum([o['bytes'] for o in objects])
            self.assertEqual(int(c['bytes']), csum)
            usage += int(c['bytes'])

        self.assertEqual(
            int(account_info['x-account-bytes-used']) + uploaded_bytes,
            usage)

    def test_get_account_meta_until(self):
        self.update_account_meta({'foo': 'bar'})

        account_info = self.get_account_info()
        t = datetime.datetime.strptime(account_info['Last-Modified'],
                                       DATE_FORMATS[2])
        t1 = t + datetime.timedelta(seconds=1)
        until = int(_time.mktime(t1.timetuple()))

        _time.sleep(2)
        self.update_account_meta({'quality': 'AAA'})

        account_info = self.get_account_info()
        t = datetime.datetime.strptime(account_info['Last-Modified'],
                                       DATE_FORMATS[-1])
        last_modified = int(_time.mktime(t.timetuple()))
        assert until < last_modified

        self.assertTrue('X-Account-Meta-Quality' in account_info)
        self.assertTrue('X-Account-Meta-Foo' in account_info)

        account_info = self.get_account_info(until=until)
        self.assertTrue('X-Account-Meta-Quality' not in account_info)
        self.assertTrue('X-Account-Meta-Foo' in account_info)
        self.assertTrue('X-Account-Until-Timestamp' in account_info)
        t = datetime.datetime.strptime(
            account_info['X-Account-Until-Timestamp'], DATE_FORMATS[2])
        self.assertTrue(int(_time.mktime(t1.timetuple())) <= until)

    def test_get_account_meta_until_invalid_date(self):
        self.update_account_meta({'quality': 'AAA'})
        meta = self.get_account_meta(until='-1')
        self.assertTrue('Quality' in meta)


class AccountGet(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)
        cnames = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']

        # create containers
        uploaded_bytes = 0
        for cname in cnames:
            self.create_container(cname)

            # upload object
            name, data, resp = self.upload_object(cname)
            uploaded_bytes += len(data)

    def test_list(self):
        #list containers: row format
        containers = self.list_containers(format=None)
        self.assertEquals(containers,
                          ['apples', 'bananas', 'kiwis', 'oranges', 'pears'])

    def test_list_shared(self):
        # upload and publish object
        oname, data, resp = self.upload_object('apples')
        url = join_urls(self.pithos_path, self.user, 'apples', oname)
        r = self.post(url, content_type='', HTTP_X_OBJECT_PUBLIC='true')
        self.assertEqual(r.status_code, 202)

        # upload and share object
        other, data, resp = self.upload_object('bananas')
        url = join_urls(self.pithos_path, self.user, 'bananas', other)
        r = self.post(url, content_type='', HTTP_X_OBJECT_SHARING='read=alice')
        self.assertEqual(r.status_code, 202)

        url = join_urls(self.pithos_path, self.user)

        # list shared containers
        r = self.get('%s?public=' % url)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEqual(objects, ['apples'])

        # list shared containers
        r = self.get('%s?shared=' % url)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEqual(objects, ['bananas'])

        # list public and shared containers
        r = self.get('%s?public=&shared=' % url)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEqual(objects, ['apples', 'bananas'])

        # assert forbidden public container listing
        r = self.get('%s?public=' % url, user='alice')
        self.assertEqual(r.status_code, 403)

        # assert forbidden shared & public container listing
        r = self.get('%s?public=&shared=' % url, user='alice')
        self.assertEqual(r.status_code, 403)

    def test_list_with_limit(self):
        containers = self.list_containers(format=None, limit=2)
        self.assertEquals(len(containers), 2)
        self.assertEquals(containers, ['apples', 'bananas'])

    def test_list_with_marker(self):
        containers = self.list_containers(format=None, limit=2,
                                          marker='bananas')
        self.assertEquals(containers, ['kiwis', 'oranges'])

        containers = self.list_containers(format=None, limit=2,
                                          marker='oranges')
        self.assertEquals(containers, ['pears'])

    def test_list_json_with_marker(self):
        containers = self.list_containers(format='json', limit=2,
                                          marker='bananas')
        self.assert_extended(containers, 'json', 'container', 2)
        self.assertEqual(containers[0]['name'], 'kiwis')
        self.assertEqual(containers[1]['name'], 'oranges')

        containers = self.list_containers(format='json', limit=2,
                                          marker='oranges')
        self.assert_extended(containers, 'json', 'container', 1)
        self.assertEqual(containers[0]['name'], 'pears')

    def test_list_xml_with_marker(self):
        xml = self.list_containers(format='xml', limit=2, marker='bananas')
        self.assert_extended(xml, 'xml', 'container', 2)
        nodes = xml.getElementsByTagName('name')
        self.assertTrue(len(nodes) <= 2)
        names = [n.childNodes[0].data for n in nodes]
        self.assertEqual(names, ['kiwis', 'oranges'])

        xml = self.list_containers(format='xml', limit=2, marker='oranges')
        self.assert_extended(xml, 'xml', 'container', 1)
        nodes = xml.getElementsByTagName('name')
        self.assertTrue(len(nodes) <= 2)
        names = [n.childNodes[0].data for n in nodes]
        self.assertEqual(names, ['pears'])

    def test_if_modified_since(self):
        account_info = self.get_account_info()
        last_modified = account_info['Last-Modified']
        t1 = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t1_formats = map(t1.strftime, DATE_FORMATS)

        # Check not modified
        url = join_urls(self.pithos_path, self.user)
        for t in t1_formats:
            r = self.get(url, HTTP_IF_MODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 304)

        # modify account: add container
        _time.sleep(1)
        self.create_container('c1')

        # Check modified
        for t in t1_formats:
            r = self.get(url, HTTP_IF_MODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(
                r.content.split('\n')[:-1],
                ['apples', 'bananas', 'c1', 'kiwis', 'oranges', 'pears'])

        account_info = self.get_account_info()
        last_modified = account_info['Last-Modified']
        t2 = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t2_formats = map(t2.strftime, DATE_FORMATS)

        # modify account: update account meta
        _time.sleep(1)
        self.update_account_meta({'foo': 'bar'})

        # Check modified
        for t in t2_formats:
            r = self.get(url, HTTP_IF_MODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(
                r.content.split('\n')[:-1],
                ['apples', 'bananas', 'c1', 'kiwis', 'oranges', 'pears'])

    def test_if_modified_since_invalid_date(self):
        url = join_urls(self.pithos_path, self.user)
        r = self.get(url, HTTP_IF_MODIFIED_SINCE='Monday')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.content.split('\n')[:-1],
            ['apples', 'bananas', 'kiwis', 'oranges', 'pears'])

    def test_if_not_modified_since(self):
        url = join_urls(self.pithos_path, self.user)
        account_info = self.get_account_info()
        last_modified = account_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])

        # Check unmodified
        t1 = t + datetime.timedelta(seconds=1)
        t1_formats = map(t1.strftime, DATE_FORMATS)
        for t in t1_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(
                r.content.split('\n')[:-1],
                ['apples', 'bananas', 'kiwis', 'oranges', 'pears'])

        # modify account: add container
        _time.sleep(2)
        self.create_container('c1')

        account_info = self.get_account_info()
        last_modified = account_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t2 = t - datetime.timedelta(seconds=1)
        t2_formats = map(t2.strftime, DATE_FORMATS)

        # Check modified
        for t in t2_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 412)

        # modify account: update account meta
        _time.sleep(1)
        self.update_account_meta({'foo': 'bar'})

        account_info = self.get_account_info()
        last_modified = account_info['Last-Modified']
        t = datetime.datetime.strptime(last_modified, DATE_FORMATS[-1])
        t3 = t - datetime.timedelta(seconds=1)
        t3_formats = map(t3.strftime, DATE_FORMATS)

        # Check modified
        for t in t3_formats:
            r = self.get(url, HTTP_IF_UNMODIFIED_SINCE=t)
            self.assertEqual(r.status_code, 412)

    def test_if_unmodified_since_invalid_date(self):
        url = join_urls(self.pithos_path, self.user)
        r = self.get(url, HTTP_IF_UNMODIFIED_SINCE='Monday')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.content.split('\n')[:-1],
            ['apples', 'bananas', 'kiwis', 'oranges', 'pears'])


class AccountPost(PithosAPITest):
    def setUp(self):
        PithosAPITest.setUp(self)
        cnames = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']

        # create containers
        uploaded_bytes = 0
        for cname in cnames:
            self.create_container(cname)

            # upload object
            name, data, resp = self.upload_object(cname)
            uploaded_bytes += len(data)

        # set account meta
        self.update_account_meta({'foo': 'bar'})

    def test_update_meta(self):
        url = join_urls(self.pithos_path, self.user)
        with AssertMappingInvariant(self.get_account_groups):
            initial = self.get_account_meta()

            meta = {'test': 'tost', 'ping': 'pong'}
            kwargs = dict(('HTTP_X_ACCOUNT_META_%s' % k, str(v))
                          for k, v in meta.items())
            r = self.post('%s?update=' % url, **kwargs)
            self.assertEqual(r.status_code, 202)

            meta.update(initial)
            account_meta = self.get_account_meta()
            (self.assertTrue(k in account_meta) for k in meta.keys())
            (self.assertEqual(account_meta[k], v) for k, v in meta.items())

    def test_reset_meta(self):
        url = join_urls(self.pithos_path, self.user)
        with AssertMappingInvariant(self.get_account_groups):
            meta = {'test': 'tost', 'ping': 'pong'}
            self.update_account_meta(meta)

            new_meta = {'test': 'test33'}
            kwargs = dict((
                'HTTP_X_ACCOUNT_META_%s' % k, str(v)
            ) for k, v in new_meta.items())
            r = self.post(url, **kwargs)
            self.assertEqual(r.status_code, 202)

            account_meta = self.get_account_meta()
            (self.assertTrue(k in account_meta) for k in new_meta.keys())
            (self.assertEqual(account_meta[k], v) for k, v in new_meta.items())

            (self.assertTrue(k not in account_meta) for k in meta.keys())

    def test_delete_meta(self):
        url = join_urls(self.pithos_path, self.user)
        with AssertMappingInvariant(self.get_account_groups):
            meta = {'test': 'tost', 'ping': 'pong'}
            self.update_account_meta(meta)

            kwargs = dict(
                ('HTTP_X_ACCOUNT_META_%s' % k, '') for k, v in meta.items())
            r = self.post('%s?update=' % url, **kwargs)
            self.assertEqual(r.status_code, 202)

            account_meta = self.get_account_meta()

            (self.assertTrue(k not in account_meta) for k in meta.keys())

    def test_set_account_groups(self):
        url = join_urls(self.pithos_path, self.user)
        with AssertMappingInvariant(self.get_account_meta):
            pithosdevs = ['verigak', 'gtsouk', 'chazapis']
            r = self.post('%s?update=' % url,
                          HTTP_X_ACCOUNT_GROUP_PITHOSDEV=','.join(pithosdevs))
            self.assertEqual(r.status_code, 202)

            account_groups = self.get_account_groups()
            self.assertTrue('Pithosdev' in self.get_account_groups())
            self.assertEqual(account_groups['Pithosdev'],
                             ','.join(sorted(pithosdevs)))

            clientdevs = ['pkanavos', 'mvasilak']
            r = self.post('%s?update=' % url,
                          HTTP_X_ACCOUNT_GROUP_CLIENTSDEV=','.join(clientdevs))
            self.assertEqual(r.status_code, 202)

            account_groups = self.get_account_groups()
            self.assertTrue('Pithosdev' in account_groups)
            self.assertTrue('Clientsdev' in account_groups)
            self.assertEqual(account_groups['Pithosdev'],
                             ','.join(sorted(pithosdevs)))
            self.assertEqual(account_groups['Clientsdev'],
                             ','.join(sorted(clientdevs)))

            clientdevs = ['mvasilak']
            r = self.post('%s?update=' % url,
                          HTTP_X_ACCOUNT_GROUP_CLIENTSDEV=''.join(clientdevs))
            self.assertEqual(r.status_code, 202)

            account_groups = self.get_account_groups()
            self.assertTrue('Pithosdev' in account_groups)
            self.assertTrue('Clientsdev' in account_groups)
            self.assertEqual(account_groups['Pithosdev'],
                             ','.join(sorted(pithosdevs)))
            self.assertEqual(account_groups['Clientsdev'],
                             ','.join(sorted(clientdevs)))

    def test_reset_account_groups(self):
        url = join_urls(self.pithos_path, self.user)
        with AssertMappingInvariant(self.get_account_meta):
            groups = {'pithosdev': ['verigak', 'gtsouk', 'chazapis'],
                      'clientsdev': ['pkanavos', 'mvasilak']}
            headers = dict(('HTTP_X_ACCOUNT_GROUP_%s' % k, ','.join(v))
                           for k, v in groups.iteritems())
            r = self.post('%s?update=' % url, **headers)
            self.assertEqual(r.status_code, 202)

            groups = {'pithosdev': ['verigak',
                                    'gtsouk',
                                    'chazapis',
                                    'papagian']}
            headers = dict(('HTTP_X_ACCOUNT_GROUP_%s' % k, ','.join(v))
                           for k, v in groups.iteritems())
            account_meta = self.get_account_meta()
            headers.update(dict(('HTTP_X_ACCOUNT_META_%s' %
                                k.upper().replace('-', '_'), v) for
                                k, v in account_meta.iteritems()))
            r = self.post(url, **headers)
            self.assertEqual(r.status_code, 202)

            account_groups = self.get_account_groups()
            self.assertTrue('Pithosdev' in account_groups)
            self.assertTrue('Clientsdev' not in account_groups)
            self.assertEqual(account_groups['Pithosdev'],
                             ','.join(sorted(groups['pithosdev'])))

    def test_delete_account_groups(self):
        url = join_urls(self.pithos_path, self.user)
        with AssertMappingInvariant(self.get_account_meta):
            groups = {'pithosdev': ['verigak', 'gtsouk', 'chazapis'],
                      'clientsdev': ['pkanavos', 'mvasilak']}
            headers = dict(('HTTP_X_ACCOUNT_GROUP_%s' % k, ','.join(v))
                           for k, v in groups.iteritems())
            self.post('%s?update=' % url, **headers)

            kwargs = dict(('HTTP_X_ACCOUNT_GROUP_%s' % k, '')
                          for k, v in groups.items())
            r = self.post('%s?update=' % url, **kwargs)
            self.assertEqual(r.status_code, 202)

            account_groups = self.get_account_groups()
            self.assertTrue('Pithosdev' not in account_groups)
            self.assertTrue('Clientsdev' not in account_groups)
