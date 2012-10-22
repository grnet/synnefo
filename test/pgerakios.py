import sys
import os
from commissioning.clients.http import HTTP_API_Client
from commissioning import QuotaholderAPI
import random 

QH_HOST = environ_get("TEST_QH_HOST", environ_get("QH_HOST", "127.0.0.1"))
QH_PORT = environ_get("TEST_QH_PORT", environ_get("QH_PORT", "8008"))

assert QH_HOST != None
assert QH_PORT != None

printf("Will connect to QH_HOST = {0}", QH_HOST)
printf("            and QH_PORT = {0}", QH_PORT)

QH_URL = "http://{0}:{1}/api/quotaholder/v".format(QH_HOST, QH_PORT)
def new_qh_client():
    """
    Create a new quota holder api client
    """
    class QuotaholderHTTP(HTTP_API_Client):
        api_spec = QuotaholderAPI()

    global QH_URL
    return QuotaholderHTTP(QH_URL)

def rand_string():
   alphabet = 'abcdefghijklmnopqrstuvwxyz'
   min = 5
   max = 15
   string=''
   for x in random.sample(alphabet,random.randint(min,max)):
    string += x
   return string

def printf(fmt, *args):
    print(fmt.format(*args))

class Client(object):
    qh = new_quota_holder_client()
    @staticmethod
    def get(self):
       self.qh


class Config(object):
   @staticmethod
   def con():
      Client.get()


class Entity(Config):

   class EntityState:
      NOT_EXISTS=1
      EXISTS=2

   state = EntityState.NOT_EXISTS
   parent = None 
   entityName = None
   entityKey = None
   context = {}

    @staticmethod
    def getRoot(self):
       e = new Entity()
       e.set("system","",None)
       return e

    @staticmethod
    def split(entityList,rejectedList,op):
       a = []
       b = []
       for e in entityList:
          if(e.entityName in rejectedList):
             b.append(e)
          else:
             a.append(e)
        if(rejectedList != [])
            printf("Rejected entities {0}: {1}",op, rejectedList)
      return (a,b)            

    @staticmethod
    def createMany(entityList):
        inputList = [(e.entityName,e.parent.parentName,e.entityKey,e.parent.entityKey) for e in entityList]
        printf("Creating entities: {0}", inputList)
        rejectedList = self.con().create_entity(context={},create_entity=inputList)
        (ok,notok) = Entity.split(entityList,rejectedList,"create") 
        for e in ok:
           e.setExists(True)
        for e in notok:
           e.setExists(False)
        return r

     @staticmethod
     def releaseMany(entityList):        
        inputList = [(e.entityName,e.entityKey) for e in entityList]
        printf("Releasing entities: {0}", inputList)
        rejectedList = self.con().release_entity(context={},release_entity=inputList)
        (ok,notok) = Entity.split(entityList,rejectedList,"release") 
        for e in ok:
           e.setExists(False)
        for e in notok:
           e.setExists(True)
        return r

    @staticmethod
    def checkMany(entityList):
        inputList = [(e.entityName,e.entityKey) for e in entityList]
        printf("Get entities: {0}", inputList)
        rejectedList = self.con().get_entity(context={},get_entity=inputList)
        if(rejectedList != [])
            printf("Could not find entities : {0}", rejectedList)
        for e in entityList:
           if(e not any(
           if e.entityName in rejectedList: yield e           
        return [for e in entityList:
                    if e.entityName in rejectedList: yield e]


    #release entity implies that each ENTITY in the system has a unique name
    #therefore we don't have to check for equality recursively but we do it anyway.
    def __eq__(self, other):
       if isinstance(other, Entity):
         return self.entityName == other.entityName and (self.parent == other.parent)
       elif isinstance(other,String):
         return self.entityName == other
       else:
         return False 

    def __ne__(self, other):
       return not (self.__eq__(other))

    def resetData(self):
       e.entityName = None
       e.entityKey  = None
       e.parent = None
       e.setExists(False)

    def setData(self,name,password,parent):
       e.entityName = name
       e.entityKey  = password
       e.parent = parent
       self.setExists(False)

    def setExists(self,v): 
       if(v == True): 
         e.state = EntityState.EXISTS
         return True
       else:
         e.state = EntityState.NOT_EXISTS
         return False

    def exists(self):
         return self.state != EntityState.NOT_EXISTS
    
    def checkExists(self):
       self.setExists(self.checkMany([self]) == [self])
       return self.exists()

    def mustExist(self):
       if(not self.exists())
         raise Exception("User {0} does not exist!".format(entityName))

    def mustNotExist(self):
       if(self.exists())
         raise Exception("User {0} already exists!".format(entityName))

    def create(self):
       if((not self.checkExists())):
         self.setExists(self.createMany([self]) == [self])

       self.setData(name,password,parent)
 

    def release():
       self.checkExists


root = Entity.getRoot()
pgerakios = new Entity()
pgerakios.setData("pgerakios","key1",root)

if(pgerakios.checkExists())


