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

from pithos.api.test import PithosAPITest, TEST_BLOCK_SIZE
from pithos.api.test.util import get_random_data

from synnefo.lib import join_urls

from urllib import quote

import random


class TestUnicode(PithosAPITest):
    #def setUp(self):
    #    super(TestUnicode, self).setUp()
    #    self.user = 'χρήστης'

    def test_create_container(self):
        cname = 'φάκελος'
        self.create_container(cname)
        url = join_urls(self.pithos_path, self.user, cname)
        r = self.head(url)
        self.assertEqual(r.status_code, 204)

        url = join_urls(self.pithos_path, self.user)
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        containers = r.content.split('\n')
        self.assertTrue('φάκελος' in containers)

    def test_create_object(self):
        cname = 'φάκελος'
        oname = 'αντικείμενο'
        self.create_container(cname)
        odata = self.upload_object(cname, oname)[1]

        url = join_urls(self.pithos_path, self.user, cname, oname)
        r = self.head(url)
        self.assertEqual(r.status_code, 200)

        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, odata)

        url = join_urls(self.pithos_path, self.user, cname)
        r = self.get(url)
        objects = r.content.split('\n')
        self.assertEqual(r.status_code, 200)
        self.assertTrue('αντικείμενο' in objects)

    def test_copy_object(self):
        src_container = 'φάκελος'
        src_object = 'αντικείμενο'
        dest_container = 'αντίγραφα'
        dest_object = 'ασφαλές-αντίγραφο'

        self.create_container(src_container)
        self.upload_object(src_container, src_object)

        self.create_container(dest_container)
        url = join_urls(self.pithos_path, self.user, dest_container,
                        dest_object)
        self.put(url, data='',
                 HTTP_X_COPY_FROM='/%s/%s' % (src_container, src_object))

        # assert destination object exists
        r = self.head(url)
        self.assertEqual(r.status_code, 200)
        r = self.get(url)
        self.assertEqual(r.status_code, 200)

        # assert source object exists
        url = join_urls(self.pithos_path, self.user, src_container,
                        src_object)
        r = self.head(url)
        self.assertEqual(r.status_code, 200)
        r = self.get(url)
        self.assertEqual(r.status_code, 200)

        # list source container objects
        url = join_urls(self.pithos_path, self.user, src_container)
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        self.assertTrue(src_object in objects)
        self.assertTrue(dest_object not in objects)

        # list destination container objects
        url = join_urls(self.pithos_path, self.user, dest_container)
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        self.assertTrue(src_object not in objects)
        self.assertTrue(dest_object in objects)

    def test_move_object(self):
        src_container = 'φάκελος'
        src_object = 'αντικείμενο'
        dest_container = 'αντίγραα'
        dest_object = 'ασφαλές-αντίγραφο'

        self.create_container(src_container)
        self.upload_object(src_container, src_object)

        self.create_container(dest_container)
        url = join_urls(self.pithos_path, self.user, dest_container,
                        dest_object)
        self.put(url, data='',
                 HTTP_X_MOVE_FROM='/%s/%s' % (src_container, src_object))

        # assert destination object exists
        r = self.head(url)
        self.assertEqual(r.status_code, 200)
        r = self.get(url)
        self.assertEqual(r.status_code, 200)

        # assert source object does not exist
        url = join_urls(self.pithos_path, self.user, src_container,
                        src_object)
        r = self.head(url)
        self.assertEqual(r.status_code, 404)
        r = self.get(url)
        self.assertEqual(r.status_code, 404)

        # list source container objects
        url = join_urls(self.pithos_path, self.user, src_container)
        r = self.get(url)
        self.assertEqual(r.status_code, 204)
        objects = r.content.split('\n')
        self.assertTrue(src_object not in objects)
        self.assertTrue(dest_object not in objects)

        # list destination container objects
        url = join_urls(self.pithos_path, self.user, dest_container)
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        self.assertTrue(src_object not in objects)
        self.assertTrue(dest_object in objects)

    def test_delete_object(self):
        self.create_container('φάκελος')
        self.upload_object('φάκελος', 'αντικείμενο')
        url = join_urls(self.pithos_path, self.user, 'φάκελος')
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        self.assertTrue('αντικείμενο' in objects)

        url = join_urls(self.pithos_path, self.user, 'φάκελος', 'αντικείμενο')
        r = self.head(url)
        self.assertEqual(r.status_code, 200)
        r = self.get(url)
        self.assertEqual(r.status_code, 200)

        r = self.delete(url)
        r = self.head(url)
        self.assertEqual(r.status_code, 404)
        r = self.get(url)
        self.assertEqual(r.status_code, 404)
        url = join_urls(self.pithos_path, self.user, 'φάκελος')
        r = self.get(url)
        objects = r.content.split('\n')
        self.assertTrue('αντικείμενο' not in objects)

    def test_delete_container(self):
        self.create_container('φάκελος')
        url = join_urls(self.pithos_path, self.user)
        r = self.get(url)
        containers = r.content.split('\n')
        self.assertTrue('φάκελος' in containers)

        self.upload_object('φάκελος', 'αντικείμενο')
        url = join_urls(self.pithos_path, self.user, 'φάκελος')
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        self.assertTrue('αντικείμενο' in objects)

        url = join_urls(self.pithos_path, self.user, 'φάκελος', 'αντικείμενο')
        r = self.head(url)
        self.assertEqual(r.status_code, 200)
        r = self.get(url)
        self.assertEqual(r.status_code, 200)

        url = join_urls(self.pithos_path, self.user, 'φάκελος')
        r = self.delete(url)
        self.assertEqual(r.status_code, 409)

        url = join_urls(self.pithos_path, self.user, 'φάκελος', 'αντικείμενο')
        r = self.delete(url)
        r = self.head(url)
        self.assertEqual(r.status_code, 404)
        r = self.get(url)
        self.assertEqual(r.status_code, 404)
        url = join_urls(self.pithos_path, self.user, 'φάκελος')
        r = self.get(url)
        objects = r.content.split('\n')
        self.assertTrue('αντικείμενο' not in objects)

        url = join_urls(self.pithos_path, self.user, 'φάκελος')
        r = self.delete(url)
        self.assertEqual(r.status_code, 204)

        url = join_urls(self.pithos_path, self.user)
        r = self.get(url)
        containers = r.content.split('\n')
        self.assertTrue('φάκελος' not in containers)

    def test_account_meta(self):
        url = join_urls(self.pithos_path, self.user)
        headers = {'HTTP_X_ACCOUNT_META_Ποιότητα': 'Ααα'}
        r = self.post(url, content_type='', **headers)
        self.assertEqual(r.status_code, 202)

        meta = self.get_account_meta()
        self.assertTrue('Ποιότητα' in meta)
        self.assertEqual(meta['Ποιότητα'], 'Ααα')

    def test_container_meta(self):
        url = join_urls(self.pithos_path, self.user, 'φάκελος')
        headers = {'HTTP_X_CONTAINER_META_Ποιότητα': 'Ααα'}
        r = self.put(url, data='', **headers)
        self.assertEqual(r.status_code, 201)

        meta = self.get_container_meta('φάκελος')
        self.assertTrue('Ποιότητα' in meta)
        self.assertEqual(meta['Ποιότητα'], 'Ααα')

    def test_object_meta(self):
        self.create_container('φάκελος')
        url = join_urls(self.pithos_path, self.user, 'φάκελος', 'αντικείμενο')
        headers = {'HTTP_X_OBJECT_META_Ποιότητα': 'Ααα'}
        r = self.put(url, data=get_random_data(), **headers)
        self.assertEqual(r.status_code, 201)

        meta = self.get_object_meta('φάκελος', 'αντικείμενο')
        self.assertTrue('Ποιότητα' in meta)
        self.assertEqual(meta['Ποιότητα'], 'Ααα')

    def test_list_meta_filtering(self):
        self.create_container('φάκελος')
        meta = {'ποιότητα': 'Ααα'}
        self.upload_object('φάκελος', 'ο1', **meta)
        self.upload_object('φάκελος', 'ο2')
        self.upload_object('φάκελος', 'ο3')

        meta = {'ποσότητα': 'μεγάλη'}
        self.update_object_meta('φάκελος', 'ο2', meta)

        url = join_urls(self.pithos_path, self.user, 'φάκελος')
        r = self.get('%s?meta=%s' % (url, quote('ποιότητα, ποσότητα')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(objects, ['ο1', 'ο2'])

        r = self.get('%s?meta=%s' % (url, quote('!ποιότητα')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(objects, ['ο2', 'ο3'])

        r = self.get('%s?meta=%s' % (url, quote('!ποιότητα, !ποσότητα')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(objects, ['ο3'])

        meta = {'ποιότητα': 'ΑΒ'}
        self.update_object_meta('φάκελος', 'ο2', meta)
        r = self.get('%s?meta=%s' % (url, quote('ποιότητα=Ααα')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(objects, ['ο1'])

        r = self.get('%s?meta=%s' % (url, quote('ποιότητα!=Ααα')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(objects, ['ο2'])

        meta = {'έτος': '2011'}
        self.update_object_meta('φάκελος', 'ο3', meta)
        meta = {'έτος': '2012'}
        self.update_object_meta('φάκελος', 'ο2', meta)
        r = self.get('%s?meta=%s' % (url, quote('έτος<2012')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(objects, ['ο3'])

        r = self.get('%s?meta=%s' % (url, quote('έτος<=2012')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(objects, ['ο2', 'ο3'])

        r = self.get('%s?meta=%s' % (url, quote('έτος<=2012, έτος!=2011')))
        self.assertEqual(r.status_code, 200)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(objects, ['ο2'])

        r = self.get('%s?meta=%s' % (url, quote('έτος<2012, έτος!=2011')))
        self.assertEqual(r.status_code, 204)
        objects = r.content.split('\n')
        if '' in objects:
            objects.remove('')
        self.assertEquals(objects, [])

    def test_groups(self):
        # create a group
        headers = {'HTTP_X_ACCOUNT_GROUP_γκρουπ': 'chazapis,διογένης'}
        url = join_urls(self.pithos_path, self.user)
        r = self.post(url, **headers)
        self.assertEqual(r.status_code, 202)

        groups = self.get_account_groups()
        self.assertTrue('γκρουπ' in groups)
        self.assertEqual(groups['γκρουπ'], 'chazapis,διογένης')

        # check read access
        self.create_container('φάκελος')
        odata = self.upload_object('φάκελος', 'ο1')[1]

        r = self.head(url, user='διογένης')
        self.assertEqual(r.status_code, 403)
        r = self.get(url, user='διογένης')
        self.assertEqual(r.status_code, 403)

        # share for read
        url = join_urls(self.pithos_path, self.user, 'φάκελος', 'ο1')
        r = self.post(url, content_type='',
                      HTTP_X_OBJECT_SHARING='read=%s:γκρουπ' % self.user)
        self.assertEqual(r.status_code, 202)

        r = self.head(url, user='διογένης')
        self.assertEqual(r.status_code, 200)
        r = self.get(url, user='διογένης')
        self.assertEqual(r.status_code, 200)

        # check write access
        appended_data = get_random_data()
        r = self.post(url, user='διογένης',  data=appended_data,
                      content_type='application/octet-stream',
                      HTTP_CONTENT_LENGTH=str(len(appended_data)),
                      HTTP_CONTENT_RANGE='bytes */*')
        self.assertEqual(r.status_code, 403)

        # share for write
        url = join_urls(self.pithos_path, self.user, 'φάκελος', 'ο1')
        r = self.post(url, content_type='',
                      HTTP_X_OBJECT_SHARING='write=%s:γκρουπ' % self.user)
        self.assertEqual(r.status_code, 202)

        r = self.post(url, user='διογένης', data=appended_data,
                      content_type='application/octet-stream',
                      HTTP_CONTENT_LENGTH=str(len(appended_data)),
                      HTTP_CONTENT_RANGE='bytes */*')
        self.assertEqual(r.status_code, 204)

        r = self.get(url, user='διογένης')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, odata + appended_data)

    def test_manifestation(self):
        self.create_container('κουβάς')
        prefix = 'μέρη/'
        data = ''
        for i in range(5):
            part = '%s%d' % (prefix, i)
            data += self.upload_object('κουβάς', part)[1]

        self.create_container('φάκελος')
        url = join_urls(self.pithos_path, self.user, 'φάκελος', 'άπαντα')
        r = self.put(url, data='', HTTP_X_OBJECT_MANIFEST='κουβάς/%s' % prefix)
        self.assertEqual(r.status_code, 201)

        r = self.head(url)
        self.assertEqual(r.status_code, 200)

        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, data)

        # wrong manifestation
        url = join_urls(self.pithos_path, self.user, 'φάκελος', 'άπαντα')
        r = self.put(url, data='', HTTP_X_OBJECT_MANIFEST='κουβάς/λάθος')
        self.assertEqual(r.status_code, 201)

        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content != data)

    def test_update_from_another_object(self):
        self.create_container('κουβάς')
        initial_data = self.upload_object('κουβάς', 'νέο')[1]
        length = TEST_BLOCK_SIZE + random.randint(1, TEST_BLOCK_SIZE - 1)
        src_data = self.upload_object('κουβάς', 'πηγή', length=length)[1]

        url = join_urls(self.pithos_path, self.user, 'κουβάς', 'νέο')
        r = self.post(url, content_type='', HTTP_CONTENT_RANGE='bytes */*',
                      HTTP_X_SOURCE_OBJECT='/κουβάς/πηγή')
        self.assertEqual(r.status_code, 204)

        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, initial_data + src_data)
