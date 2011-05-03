from dummy import BackEnd
import unittest
import os
import types
import json

class TestBackend(unittest.TestCase):
    def setUp(self):
        self.basepath = './test/content'
        log_file = './test_backend.log'
        self.b = BackEnd(self.basepath, log_file)
        self.account = 'account1'
        
    def tearDown(self):
        # clear fs
        for root, dirs, files in os.walk(self.basepath, topdown=False):
            for name in files: 
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.removedirs(self.basepath)
        
    def test_get_account_meta(self):
        self.b.update_account_meta(self.account, {})
        d = self.b.get_account_meta(self.account)
        p = os.path.join(self.basepath, self.account)
        self.assertEquals(d['count'], len(os.listdir(p)))
        self.assertEquals(d['bytes'], os.stat(p).st_size)
        self.assertEquals(d['name'], self.account)
        
        c = self.b.con.execute('select m.name, m.value from metadata m, objects o where o.rowid = m.object_id and o.name = ''?''', (p,))
        rows = c.fetchall()
        self.assertEquals(len(d), len(rows)+3)
    
    def test_get_non_existing_account_meta(self):
        self.assertRaises(NameError, self.b.get_account_meta, 'account2')
    
    def test_update_account_meta(self):
        meta = {
        #"name": "aaitest",
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
        "lastLogin": 1223372769275,
        "quota": {"totalFiles": 7, "totalBytes": 429330,"bytesRemaining": 10736988910}
        }
        self.b.update_account_meta(self.account, meta)
        p = os.path.join(self.basepath, self.account)
        self.assertTrue(os.path.exists(p))
        
        db_meta = self.b.get_account_meta(self.account)
        for k,v in meta.iteritems():
            self.assertTrue(k in db_meta)
            db_value = db_meta[k]
            if type(v) != types.StringType:
                db_value = json.loads(db_value)
            self.assertEquals(v, db_value)
        
    def test_create_container(self):
        cname = 'container1' 
        self.b.create_container(self.account, cname)
        fullpath = os.path.join(self.basepath, self.account, cname)
        self.assertTrue(os.path.exists(fullpath))
    
    def test_create_container_twice(self):
        cname = 'container1'
        self.b.create_container(self.account, cname)
        self.assertRaises(NameError, self.b.create_container, self.account, cname)
        
    def test_create_container(self):
        cname = 'container1' 
        self.b.create_container(self.account, cname)
        fullpath = os.path.join(self.basepath, self.account, cname)
        self.assertTrue(os.path.exists(fullpath))
        
#def suite():
#    suite = unittest.TestSuite()
#    suite.addTest(unittest.makeSuite(TestBackend))
#    return suite

if __name__ == "__main__":
    unittest.main()        