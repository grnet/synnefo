from config import QHTestCase
from config import run_test_case
from config import rand_string
from config import printf
import os

class CreateReleaseListAPITest(QHTestCase):
  
    def setUp(self):
        super(CreateReleaseListAPITest,self).setUp()
        self.parentName = "pgerakios"
        self.parentKey = "key1"


    #BUG: max empty name <= 72 
    def test_001(self):
        entityName = rand_string()
        entityKey = "key1" 
        parentName = self.parentName 
        parentKey = self.parentKey 
        printf("Creating random string: {0}", entityName)
        rejected = self.qh.create_entity(context={},
                                        create_entity=[(entityName,parentName,entityKey,parentKey)])
        self.assertEqual(rejected,[])
        printf("Releasing random string: {0}", entityName)
        rejected = self.qh.release_entity(context={},release_entity=[(entityName,entityKey)])
        self.assertEqual(rejected,[])

    # Test create, list and release
    def test_002(self):
        entityName = rand_string()
        entityKey = "key1" 
        parentName = self.parentName 
        parentKey =  self.parentKey

        entityList = self.qh.list_entities(context={},entity=parentName,key=parentKey)
        printf("check 1: is entity name {0} in list [{1}] ? {2}",entityName,entityList,entityName in entityList)
        self.assertFalse(entityName in entityList)


        print("Creating random string: {0}".format(entityName))
        rejected = self.qh.create_entity(context={},
                                        create_entity=[(entityName,parentName,entityKey,parentKey)])
        self.assertEqual(rejected,[])

        entityList = self.qh.list_entities(context={},entity=parentName,key=parentKey)
        printf("check 2: is entity name {0} in list [{1}] ? {2}",entityName,entityList,entityName in entityList)
        self.assertTrue(entityName in entityList)


        print("Releasing random string: {0}".format(entityName))
        rejected = self.qh.release_entity(context={},release_entity=[(entityName,entityKey)])
        self.assertEqual(rejected,[])

        entityList = self.qh.list_entities(context={},entity=parentName,key=parentKey)
        printf("check 3: is entity name {0} in list [{1}] ? {2}",entityName,entityList,entityName in entityList)
        self.assertFalse(entityName in entityList)


    # Test create,set key and release
    def test_003(self):
        entityName = rand_string()
        entityKey  = rand_string()
        entityKey2 = rand_string()
        parentName = self.parentName 
        parentKey  = self.parentKey
        # 
        printf("Creating random string: {0} ---> parent = {1}", entityName,self.parentName)
        rejected = self.qh.create_entity(context={},
                                        create_entity=[(entityName,parentName,entityKey,parentKey)])
        #
        rejected = self.qh.set_entity_key(context={},set_entity_key=[(entityName,entityKey,entityKey2)])
        self.assertEqual(rejected,[])
        #
        rejected = self.qh.set_entity_key(context={},set_entity_key=[(entityName,entityKey2,entityKey)])
        self.assertEqual(rejected,[])
        #
        print("Releasing random string: {0}".format(entityName))
        rejected = self.qh.release_entity(context={},release_entity=[(entityName,entityKey)])
        self.assertEqual(rejected,[])
        #

if __name__ == "__main__":
    import sys
    printf("Using {0}", sys.executable)
    run_test_case(CreateReleaseListAPITest)
