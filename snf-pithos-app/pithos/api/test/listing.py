# Copyright 2011-2012 GRNET S.A. All rights reserved.
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

from pithos.api.test import PithosAPITest

from synnefo.lib import join_urls

import django.utils.simplejson as json


class ListSharing(PithosAPITest):
    def _build_structure(self, user=None):
        user = user or self.user
        for i in range(2):
            cname = 'c%d' % i
            self.create_container(cname, user=user)
            self.upload_object(cname, 'obj', user=user)
            self.create_folder(cname, 'f1', user=user)
            self.create_folder(cname, 'f1/f2', user=user)
            self.upload_object(cname, 'f1/f2/obj', user=user)

        # share /c0/f1 path
        url = join_urls(self.pithos_path, user, 'c0', 'f1')
        r = self.post(url, user=user, content_type='',
                      HTTP_CONTENT_RANGE='bytes */*',
                      HTTP_X_OBJECT_SHARING='read=*')
        self.assertEqual(r.status_code, 202)
        r = self.get(url)

    def test_list_share_with_me(self):
        self._build_structure('alice')
        url = join_urls(self.pithos_path)
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        allowed_accounts = r.content.split('\n')
        if '' in allowed_accounts:
            allowed_accounts.remove('')
        self.assertEqual(allowed_accounts, ['alice'])

        r = self.get('%s?format=json' % url)
        self.assertEqual(r.status_code, 200)
        allowed_accounts = json.loads(r.content)
        self.assertEqual([i['name'] for i in allowed_accounts], ['alice'])

        url = join_urls(url, 'alice')
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        allowed_containers = r.content.split('\n')
        if '' in allowed_containers:
            allowed_containers.remove('')
        self.assertEqual(allowed_containers, ['c0'])

        r = self.get('%s?format=json' % url)
        self.assertEqual(r.status_code, 200)
        allowed_containers = json.loads(r.content)
        self.assertEqual([i['name'] for i in allowed_containers], ['c0'])

        url = join_urls(url, 'c0')
        r = self.get('%s?delimiter=/&shared=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        shared_objects = [i.get('name', i.get('subdir')) for i in
                          json.loads(r.content)]
        self.assertEqual(shared_objects, ['f1', 'f1/'])

        r = self.get('%s?delimiter=/&prefix=f1&shared=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        shared_objects = [i.get('name', i.get('subdir')) for i in
                          json.loads(r.content)]
        self.assertEqual(shared_objects, ['f1/f2', 'f1/f2/'])

        r = self.get('%s?delimiter=/&prefix=f1/f2&shared=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        shared_objects = [i.get('name', i.get('subdir')) for i in
                          json.loads(r.content)]
        self.assertEqual(shared_objects, ['f1/f2/obj'])

    def test_list_shared_by_me(self):
        self._build_structure()
        url = join_urls(self.pithos_path, self.user)
        r = self.get('%s?shared=' % url)
        self.assertEqual(r.status_code, 200)
        shared_containers = r.content.split('\n')
        if '' in shared_containers:
            shared_containers.remove('')
        self.assertEqual(shared_containers, ['c0'])

        r = self.get('%s?shared=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        shared_containers = json.loads(r.content)
        self.assertEqual([i['name'] for i in shared_containers], ['c0'])

        url = join_urls(url, 'c0')
        r = self.get('%s?delimiter=/&shared=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        shared_objects = [i.get('name', i.get('subdir')) for i in
                          json.loads(r.content)]
        self.assertEqual(shared_objects, ['f1', 'f1/'])

        r = self.get('%s?delimiter=/&prefix=f1&shared=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        shared_objects = [i.get('name', i.get('subdir')) for i in
                          json.loads(r.content)]
        self.assertEqual(shared_objects, ['f1/f2', 'f1/f2/'])

        r = self.get('%s?delimiter=/&prefix=f1/f2&shared=&format=json' % url)
        self.assertEqual(r.status_code, 200)
        shared_objects = [i.get('name', i.get('subdir')) for i in
                          json.loads(r.content)]
        self.assertEqual(shared_objects, ['f1/f2/obj'])
