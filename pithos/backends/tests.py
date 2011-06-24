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

import unittest
import os
import types
import json

from simple import SimpleBackend


class TestAccount(unittest.TestCase):
    def setUp(self):
        self.basepath = './test/content'
        self.b = SimpleBackend(self.basepath)
        self.account = 'test'
    
    def tearDown(self):
        containers = [x[0] for x in self.b.list_containers('test', self.account)]
        for container in containers:
            try:
                self.b.delete_container('test', self.account, container)
            except IndexError:
                # container not empty
                for obj in [x[0] for x in self.b.list_objects('test', self.account, container)]:
                    self.b.delete_object('test', self.account, container, obj)
                self.b.delete_container('test', self.account, container)
    
    def test_list_containers(self):
        l1 = ['images', 'movies', 'documents', 'backups']
        for item in l1:
            self.b.put_container('test', self.account, item)
        l2 = [x[0] for x in self.b.list_containers('test', self.account)]
        l1.sort()
        self.assertEquals(l1, l2)
    
    def test_list_containers_with_limit_marker(self):
        l1 = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']
        for item in l1:
            self.b.put_container('test', self.account, item)
        l2 = [x[0] for x in self.b.list_containers('test', self.account, limit=2)]
        self.assertEquals(len(l2), 2)
        self.assertEquals(l1[:2], l2)
    
        l2 = [x[0] for x in self.b.list_containers('test', self.account, limit=2, marker='bananas')]
        self.assertTrue(len(l2) <= 2)
        self.assertEquals(l1[2:4], l2)

        l2 = [x[0] for x in self.b.list_containers('test', self.account, limit=2, marker='oranges')]
        self.assertTrue(len(l2) <= 2)
        self.assertEquals(l1[4:], l2)
    
    def test_get_account_meta(self):
        meta = {
            "name": "test",
            "username": "aaitest@uth.gr",
            "email": "aaitest@uth.gr",
            "fileroot": "http://hostname/gss/rest/aaitest@uth.gr/files",
            "trash": "http://hostname/gss/rest/aaitest@uth.gr/trash",
            "shared": "http://hostname/gss/rest/aaitest@uth.gr/shared",
            "others": "http://hostname/gss/rest/aaitest@uth.gr/others",
            "tags": "http://hostname/gss/rest/aaitest@uth.gr/tags",
            "groups": "http://hostname/gss/rest/aaitest@uth.gr/groups",
            "creationDate": 1223372769275,
            "modificationDate": 1223372769275,
            "lastLogin": 1223372769275}
        self.b.update_account_meta('test', self.account, meta)
        d = self.b.get_account_meta('test', self.account)
        for k,v in meta.iteritems():
            self.assertEquals(unicode(v), d[k])
    
    def test_get_non_existing_account_meta(self):
        meta = self.b.get_account_meta('account1', 'account1')
        self.assertEquals(meta, {'name': 'account1', 'count': 0, 'bytes': 0})
    
    def test_update_account_meta(self):
        meta = {
            "name": "test",
            "username": "aaitest@uth.gr",
            "email": "aaitest@uth.gr",
            "fileroot": "http://hostname/gss/rest/aaitest@uth.gr/files",
            "trash": "http://hostname/gss/rest/aaitest@uth.gr/trash",
            "shared": "http://hostname/gss/rest/aaitest@uth.gr/shared",
            "others": "http://hostname/gss/rest/aaitest@uth.gr/others",
            "tags": "http://hostname/gss/rest/aaitest@uth.gr/tags",
            "groups": "http://hostname/gss/rest/aaitest@uth.gr/groups",
            "creationDate": 1223372769275,
            "modificationDate": 1223372769275,
            "lastLogin": 1223372769275}
        self.b.update_account_meta('test', self.account, meta)
        p = os.path.join(self.basepath, self.account)
        
        db_meta = self.b.get_account_meta('test', self.account)
        for k,v in meta.iteritems():
            self.assertTrue(k in db_meta)
            db_value = db_meta[k]
            self.assertEquals(unicode(v), db_value)

class TestContainer(unittest.TestCase):
    def setUp(self):
        self.basepath = './test/content'
        self.b = SimpleBackend(self.basepath)
        self.account = 'test'
    
    def tearDown(self):
        containers = [x[0] for x in self.b.list_containers('test', self.account)]
        for container in containers:
            try:
                self.b.delete_container('test', self.account, container)
            except IndexError: # container not empty
                for obj in [x[0] for x in self.b.list_objects('test', self.account, container)]:
                    self.b.delete_object('test', self.account, container, obj)
                self.b.delete_container('test', self.account, container)
    
    def test_list_non_existing_account_objects(self):
        self.assertRaises(NameError, self.b.list_objects, 'test', 'test', 'container1')
    
    def test_list_objects(self):
        self.b.put_container('test', self.account, 'container1')
        objects = [x[0] for x in self.b.list_objects('test', self.account, 'container1')]
        self.assertEquals(len([]), len(objects))
        l = [
            {'name':'kate_beckinsale.jpg'},
            {'name':'How To Win Friends And Influence People.pdf'},
            {'name':'moms_birthday.jpg'},
            {'name':'poodle_strut.mov'},
            {'name':'Disturbed - Down With The Sickness.mp3'},
            {'name':'army_of_darkness.avi'},
            {'name':'the_mad.avi'}
        ]
        for item in l:
            self.b.update_object_hashmap('test', self.account, 'container1', item['name'], 0, [])
        objects = [x[0] for x in self.b.list_objects('test', self.account, 'container1')]
        self.assertEquals(len(l), len(objects))
    
    def test_list_objects_with_limit_marker(self):
        self.b.put_container('test', self.account, 'container1')
        l = ['gala', 'grannysmith', 'honeycrisp', 'jonagold', 'reddelicious']
        for item in l:
            self.b.update_object_hashmap('test', self.account, 'container1', item, 0, [])
        objects = [x[0] for x in self.b.list_objects('test', self.account, 'container1', limit=2)]
        self.assertEquals(l[:2], objects)
        
        objects = [x[0] for x in self.b.list_objects('test', self.account, 'container1', limit=2, marker='grannysmith')]
        self.assertEquals(l[2:4], objects)
        
        objects = [x[0] for x in self.b.list_objects('test', self.account, 'container1', limit=2, marker='jonagold')]
        self.assertEquals(l[4:], objects)
    
    def test_list_pseudo_hierarchical_folders(self):
        self.b.put_container('test', self.account, 'container1')
        l = ['photos/animals/dogs/poodle.jpg',
             'photos/animals/dogs/terrier.jpg',
             'photos/animals/cats/persian.jpg',
             'photos/animals/cats/siamese.jpg',
             'photos/plants/fern.jpg',
             'photos/plants/rose.jpg',
             'photos/me.jpg'
             ]
        for item in l:
            self.b.update_object_hashmap('test', self.account, 'container1', item, 0, [])
        
        objects = [x[0] for x in self.b.list_objects('test', self.account, 'container1', prefix='photos/', delimiter='/')]
        self.assertEquals(['photos/animals/', 'photos/me.jpg', 'photos/plants/'], objects)
        
        objects = [x[0] for x in self.b.list_objects('test', self.account, 'container1', prefix='photos/animals/', delimiter='/')]
        self.assertEquals(['photos/animals/cats/', 'photos/animals/dogs/'], objects)
        
        self.b.put_container('test', self.account, 'container2')
        l = ['photos/photo1', 'photos/photo2', 'movieobject', 'videos', 'videos/movieobj4']
        for item in l:
            self.b.update_object_hashmap('test', self.account, 'container2', item, 0, [])
        objects = [x[0] for x in self.b.list_objects('test', self.account, 'container2', delimiter='/')]
        self.assertEquals(['movieobject', 'photos/', 'videos', 'videos/'], objects)
    
    def test_put_container(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        self.assertTrue(cname in [x[0] for x in self.b.list_containers('test', self.account)])
    
    def test_put_container_twice(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        self.assertRaises(NameError, self.b.put_container, 'test', self.account, cname)
    
    def test_delete_container(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        self.b.delete_container('test', self.account, cname)
        self.assertTrue(cname not in [x[0] for x in self.b.list_containers('test', self.account)])
    
    def test_delete_non_exisitng_container(self):
        cname = 'container1'
        self.assertRaises(NameError, self.b.delete_container, 'test', self.account, cname)
    
    def test_delete_non_empty_container(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        self.b.update_object_hashmap('test', self.account, cname, 'object1', 0, [])
        self.assertRaises(IndexError, self.b.delete_container, 'test', self.account, cname)
    
    def test_get_container_meta(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        meta = self.b.get_container_meta('test', self.account, cname)
        self.assertEquals(meta['count'], 0)
        
        l = ['photos/photo1', 'photos/photo2', 'movieobject', 'videos/movieobj4']
        for item in l:
            self.b.update_object_hashmap('test', self.account, cname, item, 0, [])
        meta = self.b.get_container_meta('test', self.account, cname)
        self.assertEquals(meta['count'], 4)

class TestObject(unittest.TestCase):
    def setUp(self):
        self.basepath = './test/content'
        self.b = SimpleBackend(self.basepath)
        self.account = 'test'
    
    def tearDown(self):
        containers = [x[0] for x in self.b.list_containers('test', self.account)]
        for container in containers:
            try:
                self.b.delete_container('test', self.account, container)
            except IndexError: # container not empty
                for obj in [x[0] for x in self.b.list_objects('test', self.account, container)]:
                    self.b.delete_object('test', self.account, container, obj)
                self.b.delete_container('test', self.account, container)
    
    def test_get_non_existing_object(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        self.assertRaises(NameError, self.b.get_object_hashmap, 'test', self.account, 'cname', 'testobj')
        self.assertRaises(NameError, self.b.get_object_hashmap, 'test', self.account, cname, 'testobj')
    
    def test_get_object(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        input = {'name':'kate_beckinsale.jpg'}
        data = json.dumps(input)
        hash = self.b.put_block(data)
        self.b.update_object_hashmap('test', self.account, cname, input['name'], len(data), [hash])
        size, hashmap = self.b.get_object_hashmap('test', self.account, cname, 'kate_beckinsale.jpg')
        self.assertEquals(len(data), size)
        self.assertEquals(hash, hashmap[0])
        self.assertEquals(input, json.loads(self.b.get_block(hash)))
    
#     def test_update_object(self):
#         cname = 'container1'
#         self.b.put_container('test', self.account, cname)
#         input = {'name':'kate_beckinsale.jpg'}
#         self.b.update_object('test', self.account, cname, input['name'], json.dumps(input))
#         meta = self.b.get_object_meta('test', self.account, cname, input['name'])
    
    def test_copy_object(self):
        src_cname = 'container1'
        src_obj = 'photos/me.jpg'
        dest_cname = 'container2'
        dest_obj = 'photos/personal/myself.jpg'
        
        # non existing source account
        self.assertRaises(NameError,
                          self.b.copy_object,
                          'test',
                          'test',
                          src_cname,
                          src_obj,
                          dest_cname,
                          dest_obj)
        # non existing source container
        self.assertRaises(NameError,
                          self.b.copy_object,
                          'test',
                          self.account,
                          src_cname,
                          src_obj,
                          dest_cname,
                          dest_obj)
        
        self.b.put_container('test', self.account, src_cname)
        # non existing source object
        self.assertRaises(NameError,
                          self.b.copy_object,
                          'test',
                          self.account,
                          src_cname,
                          src_obj,
                          dest_cname,
                          dest_obj)
        
        self.b.update_object_hashmap('test', self.account, src_cname, src_obj, 0, [])
        # non existing destination container
        self.assertRaises(NameError,
                          self.b.copy_object,
                          'test',
                          self.account,
                          src_cname,
                          src_obj,
                          dest_cname,
                          dest_obj)
        
        self.b.put_container('test', self.account, dest_cname)
        self.b.update_object_meta('test', self.account, src_cname, src_obj, {'tag':'sfsfssf'})
        self.b.copy_object('test', self.account, src_cname, src_obj, dest_cname, dest_obj)
        self.assertTrue(dest_obj in [x[0] for x in self.b.list_objects('test',
                                                                        self.account,
                                                                        dest_cname,
                                                                        prefix='photos/personal/',
                                                                        delimiter='/')])
        # TODO: test metadata changes
        meta_tag = self.b.get_object_meta('test', self.account, dest_cname, dest_obj)['tag']
        self.assertEquals(meta_tag, unicode('sfsfssf'))
    
    def test_delete_non_existing_object(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        name = 'kate_beckinsale.jpg'
        self.assertRaises(NameError, self.b.delete_object, 'test', self.account, cname, name)
    
    def test_delete_object(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        name = 'kate_beckinsale.jpg'
        self.b.update_object_hashmap('test', self.account, cname, name, 0, [])
        self.assertTrue(name in [x[0] for x in self.b.list_objects('test', self.account, cname)])
        
        self.b.delete_object('test', self.account, cname, name)
        self.assertTrue(name not in [x[0] for x in self.b.list_objects('test', self.account, cname)])
        self.assertRaises(NameError, self.b.delete_object, 'test', self.account, cname, name)
    
    def test_get_non_existing_object_meta(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        name = 'kate_beckinsale.jpg'
        self.assertRaises(NameError, self.b.get_object_meta, 'test', self.account, cname, name)
    
    def test_get_update_object_meta(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        name = 'kate_beckinsale.jpg'
        self.b.update_object_hashmap('test', self.account, cname, name, 0, [])
        
        m1 = {'X-Object-Meta-Meat': 'Bacon',
             'X-Object-Meta-Fruit': 'Bacon',
             'X-Object-Meta-Dairy': 'Bacon'}
        self.b.update_object_meta('test', self.account, cname, name, m1)
        meta = self.b.get_object_meta('test', self.account, cname, name)
        for k,v in m1.iteritems():
            self.assertTrue(k in meta)
            self.assertEquals(unicode(v), meta[k])
        
        m2 = {'X-Object-Meta-Meat': 'Bacon',
             'X-Object-Meta-Fruit': 'Bacon',
             'X-Object-Meta-Veggie': 'Bacon',
             'X-Object-Meta-Dairy': 'Chicken'}
        self.b.update_object_meta('test', self.account, cname, name, m2)
        meta = self.b.get_object_meta('test', self.account, cname, name)
        m1.update(m2)
        for k,v in m1.iteritems():
            self.assertTrue(k in meta)
            self.assertEquals(unicode(v), meta[k])
    
    def test_update_non_existing_object_meta(self):
        cname = 'container1'
        self.b.put_container('test', self.account, cname)
        name = 'kate_beckinsale.jpg'
        self.assertRaises(NameError, self.b.update_object_meta, 'test', self.account, cname, name, {})

if __name__ == "__main__":
    unittest.main()