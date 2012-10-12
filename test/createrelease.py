from kkconfig import unittest
from kkconfig import new_quota_holder_client
from kkconfig import rand_string
from kkconfig import printf
import os

class CreateReleaseListAPITest(unittest.TestCase):
    def setUp(self):
        self.qh = new_quota_holder_client()

    def tearDown(self):
        del self.qh

    #BUG: empty entity worked ...
    #BUG: max empty name 
    def test_001(self):
        string_length = 10
        entityName = rand_string()
        parentName = "system"
        entityKey = "key1" 
        parentKey = ""
        printf("Creating random string: {0}", entityName)
        rejected = self.qh.create_entity(context={},
                                        create_entity=[(entityName,parentName,entityKey,parentKey)])
        self.assertEqual(rejected,[])
        printf("Releasing random string: {0}", entityName)
        rejected = self.qh.release_entity(context={},release_entity=[(entityName,entityKey)])
        self.assertEqual(rejected,[])



if __name__ == "__main__":
    unittest.main()
