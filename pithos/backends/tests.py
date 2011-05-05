from dummy import BackEnd
import unittest
import os
import types
import json

class TestAccount(unittest.TestCase):
    def setUp(self):
        self.basepath = './test/content'
        self.b = BackEnd(self.basepath)
        self.account = 'account1'
        
    def tearDown(self):
        containers = self.b.list_containers(self.account)
        for container in containers:
            try:
                self.b.delete_container(self.account, container)
            except IndexError: # container not empty
                for obj in self.b.list_objects(self.account, container):
                    self.b.delete_object(self.account, container, obj)
                self.b.delete_container(self.account, container)
    
    def test_list_containers(self):
        l1 = ['images', 'movies', 'documents', 'backups']
        for item in l1:
            self.b.create_container(self.account, item)
        l2 = self.b.list_containers(self.account)
        l1.sort()
        self.assertEquals(l1, l2)
        
    def test_list_containers_with_limit_marker(self):
        l1 = ['apples', 'bananas', 'kiwis', 'oranges', 'pears']
        for item in l1:
            self.b.create_container(self.account, item)
        l2 = self.b.list_containers(self.account, limit=2)
        self.assertEquals(len(l2), 2)
        self.assertEquals(l1[:2], l2)
    
        l2 = self.b.list_containers(self.account, limit=2, marker='bananas')
        self.assertTrue(len(l2) <= 2)
        self.assertEquals(l1[2:4], l2)

        l2 = self.b.list_containers(self.account, limit=2, marker='oranges')
        self.assertTrue(len(l2) <= 2)
        self.assertEquals(l1[4:], l2)
        
    def test_get_account_meta(self):
        meta = {
        "name": "account1",
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
        "lastLogin": 1223372769275
        }
        self.b.update_account_meta(self.account, meta)
        d = self.b.get_account_meta(self.account)
        for k,v in meta.iteritems():
            self.assertEquals(unicode(v), d[k])
            
    def test_get_non_existing_account_meta(self):
        self.assertRaises(NameError, self.b.get_account_meta, 'account2')
    
    def test_update_account_meta(self):
        meta = {
        "name": "account1",
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
        "lastLogin": 1223372769275
        }
        self.b.update_account_meta(self.account, meta)
        p = os.path.join(self.basepath, self.account)
        self.assertTrue(os.path.exists(p))
        
        db_meta = self.b.get_account_meta(self.account)
        for k,v in meta.iteritems():
            self.assertTrue(k in db_meta)
            db_value = db_meta[k]
            self.assertEquals(unicode(v), db_value)

class TestContainer(unittest.TestCase):
    def setUp(self):
        self.basepath = './test/content'
        self.b = BackEnd(self.basepath)
        self.account = 'account1'
        
    def tearDown(self):
        containers = self.b.list_containers(self.account)
        for container in containers:
            try:
                self.b.delete_container(self.account, container)
            except Exception: # container not empty
                for obj in self.b.list_objects(self.account, container):
                    self.b.delete_object(self.account, container, obj)
                self.b.delete_container(self.account, container)
                
    def test_list_non_existing_account_objects(self):
        self.assertRaises(NameError, self.b.list_objects, 'account2', 'container1')
        
    def test_list_objects(self):
        self.b.create_container(self.account, 'container1')
        objects = self.b.list_objects(self.account, 'container1')
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
            self.b.update_object(self.account, 'container1', item['name'], json.dumps(item))
        objects = self.b.list_objects(self.account, 'container1')
        self.assertEquals(len(l), len(objects))
        
    def test_list_objects_with_limit_marker(self):
        self.b.create_container(self.account, 'container1')
        l = ['gala', 'grannysmith', 'honeycrisp', 'jonagold', 'reddelicious']
        for item in l:
            self.b.update_object(self.account, 'container1', item, item)
        objects = self.b.list_objects(self.account, 'container1', limit=2)
        self.assertEquals(l[:2], objects)
        
        objects = self.b.list_objects(self.account, 'container1', limit=2, marker='grannysmith')
        self.assertEquals(l[2:4], objects)
        
        objects = self.b.list_objects(self.account, 'container1', limit=2, marker='jonagold')
        self.assertEquals(l[4:], objects)
    
    def test_list_pseudo_hierarchical_folders(self):
        self.b.create_container(self.account, 'container1')
        l = ['photos/animals/dogs/poodle.jpg',
             'photos/animals/dogs/terrier.jpg',
             'photos/animals/cats/persian.jpg',
             'photos/animals/cats/siamese.jpg',
             'photos/plants/fern.jpg',
             'photos/plants/rose.jpg',
             'photos/me.jpg'
             ]
        for item in l:
            self.b.update_object(self.account, 'container1', item, item)
        
        objects = self.b.list_objects(self.account, 'container1', prefix='photos/', delimiter='/')
        self.assertEquals(['animals', 'me.jpg', 'plants'], objects)
        
        objects = self.b.list_objects(self.account, 'container1', prefix='photos/animals/', delimiter='/')
        self.assertEquals(['cats', 'dogs'], objects)
        
        self.b.create_container(self.account, 'container2')
        l = ['photos/photo1', 'photos/photo2', 'movieobject', 'videos/movieobj4']
        for item in l:
            self.b.update_object(self.account, 'container2', item, item)
        objects = self.b.list_objects(self.account, 'container2', delimiter='/')
        self.assertEquals(['movieobject', 'photos', 'videos'], objects)    
        
    def test_create_container(self):
        cname = 'container1' 
        self.b.create_container(self.account, cname)
        self.assertTrue(cname in self.b.list_containers(self.account))
        
    def test_create_container_twice(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        self.assertRaises(NameError, self.b.create_container, self.account, cname)
    
    def test_delete_container(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        self.b.delete_container(self.account, cname)
        self.assertTrue(cname not in self.b.list_containers(self.account))

    def test_delete_non_exisitng_container(self):
        cname = 'container1'
        self.assertRaises(NameError, self.b.delete_container, self.account, cname)
    
    def test_delete_non_empty_container(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        self.b.update_object(self.account, cname, 'object1', 'alkhadlkhalkdhal')
        self.assertRaises(Exception, self.b.delete_container, self.account, cname)
        
    def test_get_container_meta(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        meta = self.b.get_container_meta(self.account, cname)
        self.assertEquals(meta['count'], 0)
        
        l = ['photos/photo1', 'photos/photo2', 'movieobject', 'videos/movieobj4']
        for item in l:
            self.b.update_object(self.account, cname, item, item)
        meta = self.b.get_container_meta(self.account, cname)
        self.assertEquals(meta['count'], 4)

class TestObject(unittest.TestCase):
    def setUp(self):
        self.basepath = './test/content'
        self.b = BackEnd(self.basepath)
        self.account = 'account1'
        
    def tearDown(self):
        containers = self.b.list_containers(self.account)
        for container in containers:
            try:
                self.b.delete_container(self.account, container)
            except Exception: # container not empty
                for obj in self.b.list_objects(self.account, container):
                    self.b.delete_object(self.account, container, obj)
                self.b.delete_container(self.account, container)
    
    def test_get_non_existing_object(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        self.assertRaises(NameError, self.b.get_object, self.account, 'cname', 'testobj')
        self.assertRaises(NameError, self.b.get_object, self.account, cname, 'testobj')
    
    def test_get_object(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        input = {'name':'kate_beckinsale.jpg'}
        self.b.update_object(self.account, cname, input['name'], json.dumps(input))
        out = self.b.get_object(self.account, cname, 'kate_beckinsale.jpg')
        self.assertEquals(input, json.loads(out))
    
    def test_update_object(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        input = {'name':'kate_beckinsale.jpg'}
        self.b.update_object(self.account, cname, input['name'], json.dumps(input))
        meta = self.b.get_object_meta(self.account, cname, input['name'])
        self.assertTrue('hash' in meta)
        
    def test_copy_object(self):
        src_cname = 'container1'
        src_obj = 'photos/me.jpg'
        dest_cname = 'container2'
        dest_obj = 'photos/personal/myself.jpg'
        
        # non existing source account
        self.assertRaises(NameError,
                          self.b.copy_object,
                          'account',
                          src_cname,
                          src_obj,
                          dest_cname,
                          dest_obj)
        # non existing source container
        self.assertRaises(NameError,
                          self.b.copy_object,
                          self.account,
                          src_cname,
                          src_obj,
                          dest_cname,
                          dest_obj)
        
        self.b.create_container(self.account, src_cname)
        # non existing source object
        self.assertRaises(NameError,
                          self.b.copy_object,
                          self.account,
                          src_cname,
                          src_obj,
                          dest_cname,
                          dest_obj)
        
        self.b.update_object(self.account, src_cname, src_obj, src_obj)
        # non existing destination container
        self.assertRaises(NameError,
                          self.b.copy_object,
                          self.account,
                          src_cname,
                          src_obj,
                          dest_cname,
                          dest_obj)
        
        self.b.create_container(self.account, dest_cname)
        self.b.update_object_meta(self.account, src_cname, src_obj, {'tag':'sfsfssf'})
        self.b.copy_object(self.account, src_cname, src_obj, dest_cname, dest_obj)
        self.assertTrue(dest_obj.split('/')[-1] in self.b.list_objects(self.account,
                                                                       dest_cname,
                                                                       prefix='photos/personal/',
                                                                       delimiter='/'))
        # TODO: test metadata changes
        meta_tag = self.b.get_object_meta(self.account, dest_cname, dest_obj)['tag']
        self.assertEquals(meta_tag, unicode('sfsfssf'))
        
    def test_delete_non_existing_object(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        name = 'kate_beckinsale.jpg'
        self.assertRaises(NameError, self.b.delete_object, self.account, cname, name)
        
    def test_delete_object(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        name = 'kate_beckinsale.jpg'
        self.b.update_object(self.account, cname, name, name)
        self.assertTrue(name in self.b.list_objects(self.account, cname))
        
        self.b.delete_object(self.account, cname, name)
        self.assertTrue(name not in self.b.list_objects(self.account, cname))
        self.assertRaises(NameError, self.b.delete_object, self.account, cname, name)
        
    def test_get_non_existing_object_meta(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        name = 'kate_beckinsale.jpg'
        self.assertRaises(NameError, self.b.get_object_meta, self.account, cname, name)
        
    def test_get_update_object_meta(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        name = 'kate_beckinsale.jpg'
        self.b.update_object(self.account, cname, name, name)
        
        m1 = {'X-Object-Meta-Meat': 'Bacon',
             'X-Object-Meta-Fruit': 'Bacon',
             'X-Object-Meta-Dairy': 'Bacon'}
        self.b.update_object_meta(self.account, cname, name, m1)
        meta = self.b.get_object_meta(self.account, cname, name)
        for k,v in m1.iteritems():
            self.assertTrue(k in meta)
            self.assertEquals(unicode(v), meta[k])

        m2 = {'X-Object-Meta-Meat': 'Bacon',
             'X-Object-Meta-Fruit': 'Bacon',
             'X-Object-Meta-Veggie': 'Bacon',
             'X-Object-Meta-Dairy': 'Chicken'}
        self.b.update_object_meta(self.account, cname, name, m2)
        meta = self.b.get_object_meta(self.account, cname, name)
        m1.update(m2)
        for k,v in m1.iteritems():
            self.assertTrue(k in meta)
            self.assertEquals(unicode(v), meta[k])

    def test_update_non_existing_object_meta(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        name = 'kate_beckinsale.jpg'
        self.assertRaises(NameError, self.b.update_object_meta, self.account, cname, name, {})
    
if __name__ == "__main__":
    unittest.main()        