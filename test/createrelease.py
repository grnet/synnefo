from config import QHTestCase
from config import run_test_case
from config import rand_string
from config import printf
import os

class CreateReleaseListAPITest(QHTestCase):
    #BUG: max empty name <= 72 
    def test_001(self):
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

    def test_002(self):
        entityName = rand_string()
        parentName = "system"
        entityKey = "key1" 
        parentKey = ""

        entityList = self.qh.list_entities(context={},entity=parentName,key=parentKey)
        self.assertFalse(entityName in entityList)


        print("Creating random string: {0}".format(entityName))
        rejected = self.qh.create_entity(context={},
                                        create_entity=[(entityName,parentName,entityKey,parentKey)])
        self.assertEqual(rejected,[])

        entityList = self.qh.list_entities(context={},entity=parentName,key=parentKey)
        self.assertTrue(entityName in entityList)


        print("Releasing random string: {0}".format(entityName))
        rejected = self.qh.release_entity(context={},release_entity=[(entityName,entityKey)])
        self.assertEqual(rejected,[])

        entityList = self.qh.list_entities(context={},entity=parentName,key=parentKey)
        self.assertFalse(entityName in entityList)


if __name__ == "__main__":
    import sys
    printf("Using {0}", sys.executable)
    run_test_case(CreateReleaseListAPITest)
