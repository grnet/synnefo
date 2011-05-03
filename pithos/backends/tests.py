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
        
    def tearDown(self):
        # clear fs
        for root, dirs, files in os.walk(self.basepath, topdown=False):
            for name in files: 
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.removedirs(self.basepath)
        
    def test_get_account_meta(self):
        account = 'account1'
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
        "lastLogin": 1223372769275,
        "quota": {"totalFiles": 7, "totalBytes": 429330,"bytesRemaining": 10736988910}
        }
        self.b.update_account_meta(account, meta)
        d = self.b.get_account_meta(account)
        p = os.path.join(self.basepath, account)
        self.assertEquals(d['count'], len(os.listdir(p)))
        self.assertEquals(d['bytes'], os.stat(p).st_size)
        self.assertEquals(d['name'], account)
        exp_len = len(meta)+3
        if meta.has_key('count'):
            exp_len = exp_len - 1
        if meta.has_key('bytes'):
            exp_len = exp_len - 1
        if meta.has_key('name'):
            exp_len = exp_len - 1
        self.assertEquals(len(d), exp_len)
        
    def test_get_non_existing_account_meta(self):
        account = 'account1'
        self.assertRaises(NameError, self.b.get_account_meta, account)
    
    def test_update_account_meta(self):
        account = 'account1'
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
        "lastLogin": 1223372769275,
        "quota": {"totalFiles": 7, "totalBytes": 429330,"bytesRemaining": 10736988910}
        }
        self.b.update_account_meta(account, meta)
        p = os.path.join(self.basepath, account)
        self.assertTrue(os.path.exists(p))
        
        db_meta = self.b.get_account_meta(account)
        for k,v in meta.iteritems():
            self.assertTrue(k in db_meta)
            db_value = db_meta[k]
            if type(v) != types.StringType:
                db_value = json.loads(db_value)
            self.assertEquals(v, db_value)
        
    def test_create_container(self):
        account = 'account1'
        cname = 'container1' 
        self.b.create_container(account, cname)
        fullpath = os.path.join(self.basepath, account, cname)
        self.assertTrue(os.path.exists(fullpath))
    
    def test_create_container_twice(self):
        account = 'account1'
        cname = 'container1'
        self.b.create_container(account, cname)
        self.assertRaises(NameError, self.b.create_container, account, cname)
    
    def test_delete_container(self):
        account = 'account1'
        cname = 'container1'
        self.b.create_container(account, cname)
        self.b.delete_container(account, cname)
        self.assertTrue(not os.path.exists(os.path.join(account, cname)))
        path = os.path.join(account, cname)
        c = self.b.con.execute('select * from metadata where object_id in (select rowid from objects where name = ''?'')', (path,))
        self.assertEqual(c.rowcount, -1)
        
        c = self.b.con.execute('select * from objects where name = ''?''', (path,))
        self.assertEqual(c.rowcount, -1)

    def test_delete_non_exisitng_container(self):
        account = 'account1'
        cname = 'container1'
        self.assertRaises(NameError, self.b.delete_container, account, cname)
    
    def test_delete_non_empty_container(self):
        account = 'account1'
        cname = 'container1'
        self.b.create_container(account, cname)
        self.b.update_object(account, cname, 'object1', 'alkhadlkhalkdhal')
        self.assertRaises(Exception, self.b.delete_container, account, cname)
        
if __name__ == "__main__":
    unittest.main()        