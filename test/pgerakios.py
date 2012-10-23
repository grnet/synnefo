#!/usr/bin/python
import sys
import os
from commissioning.clients.http import HTTP_API_Client,init_logger_stderr
from commissioning import QuotaholderAPI
import random 

init_logger_stderr('mylogger', level='INFO')

def environ_get(key, default_value = ''):
    if os.environ.has_key(key):
        return os.environ.get(key)
    else:
        return default_value

QH_HOST = environ_get("TEST_QH_HOST", environ_get("QH_HOST", "127.0.0.1"))
QH_PORT = environ_get("TEST_QH_PORT", environ_get("QH_PORT", "8008"))
QH_DEBUG = True

assert QH_HOST != None
assert QH_PORT != None

def printf(fmt, *args):
    global QH_DEBUG
    if(QH_DEBUG):
       print(fmt.format(*args))
    return 0

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

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)

def find(f, seq):
     """Return first item in sequence where f(item) == True."""
    for item in seq:
        if f(item): 
            return item
    return None

class Client(object):
    
    qh = new_qh_client()
    clientKey = rand_string()

    @staticmethod
    def get():
       return Client.qh

    #getPending
    def getPending():
       #get_pending_commissions
       pass
    
    #
    def removePending():
       #resolve_pending_commissions
       pass


class Config(object):
    
    Context = {}
    Flags = 0

    @staticmethod
    def con():
        return Client.get()

    @staticmethod
    def split(list1,f,list2,g,equalsLeft):
        a = []
        b = []
        list2 = [g(e) for e in list2]
        if(equalsLeft):
            for e in list1:
                if(f(e) in list2):
                   a.append(e)
                else:
                   b.append(e)
        else:                   
            for e in list1:
                if(f(e) in list2):
                   b.append(e)
                else:
                   a.append(e)
        return (a,b)           

     @staticmethod
     def splitRejected(list1,f,list2,g):
        return Config.split(list1,f,list2,g,False)

     @staticmethod
     def splitAccepted(list1,f,list2,g):
        return Config.split(list1,f,list2,g,True)



class Policy(Config):

    PolicyState = enum('NOT_EXISTS','EXISTS','DUMMY')    

    @staticmethod
    def create(policy):
       return Policy.createMany([policy])

    @staticmethod
    def splitRejected(policyList,rejectedList):
        (a,b) =  Config.splitRejected(policyList,(lambda p: p.policyName),
                                      rejectedList,(lambda x: x))
        if(b != [])
            printf("Rejected entities (call to set_limits): {0}", rejectedList)
        return (a,b)

    @staticmethod
    def splitAccepted(policyList,acceptedList):
        (a,b) =  Config.splitAccepted(policyList,(lambda p: p.policyName),
                                      acceptedList,(lambda x: x[0]))
        if(b != [])
            printf("Accepted entities (call to get_limits): {0}", acceptedList)
        return (a,b)


    @staticmethod
    def saveMany(policyList):
        inputList = [(p.policyName,p.quantity,p.capacity,p.importLimit,p.exportLimit) for p if(p.valid() and not p.isDummy()) in policyList)]
        rejectedList = Policy.con().set_limits(context=Policy.Context, set_limits=inputList)
        (ok,notok) = Policy.splitRejected(policyList,rejectedList)
        for p in ok:
           p.exist = PolicyState.EXISTS
        for p in notok:
           if(p.exist == Policy.EXISTS):
              p.exist = PolicyState.NOT_EXISTS
        return notok
    
    @staticmethod
    def loadMany(policyList):
        inputList = [p.policyName for p if(not p.isDummy()) in policyList)]
        acceptedList = Policy.con().get_limits(context=Policy.Context,get_limits=inputList)
        (ok,notok) = Policy.splitAccepted(policyList,acceptedList)
        # fill the policy
        for p in ok:
            p.exist = PolicyState.EXISTS
            g = find((lambda x: x[0]),acceptedList)
            p.quantity = g[1]
            p.capacity = g[2]
            p.importLimit = g[3]
            p.exportLimit = g[4]
       for p in notok:
          if(p.exist == Policy.EXISTS):
             p.exist = PolicyState.NOT_EXISTS
       return notok

    def reset(self):
       self.set(None,None,None,None,None)

    def __init__(self):
       self.reset() 

    def isDummy(self):
       return self.exist == PolicyState.DUMMY

    def setDummy(self):
       self.exist = PolicyState.DUMMY

    def name(self):
       return self.policyName

    def valid(self):
       return self.policyName != None and 
              self.quantity != None and
              self.capacity != None and
              self.importLimit != None and 
              self.exportLimit != None 

    def set(self,name,q,c,i,e):
       self.policyName = name
       self.quantity = q
       self.capacity = c
       self.importLimit = i
       self.exportLimit = e
       self.exist = PolicyState.NOT_EXISTS

    def exists(self): 
       return self.exist

    def __eq__(self, other):
       if isinstance(other, Policy):
         return self.policyName == other.policyName
       elif isinstance(other,String):
         return self.policyName == other
       else:
         return False 

    def __ne__(self, other):
       return not (self.__eq__(other))


    def load(self):
       if(self.isDummy()):
          return True
       else:
          return Policy.loadMany([self]) == []

    def save(self):
       if(self.isDummy()):
          return True
       else:
          return Policy.saveMany([self]) == []
        

class Resource(Config):   

    def set(self, name, entity):
      self.resourceName = name 
      self.entity = entity
      self.policy = None 
      self.Imported = None
      self.Exported = None
      self.Returned = None
      self.Released = None
      self.Flags = None


   # get_holding or get_quota (if dummy)
    @staticmethod 
    def loadMany(resourceList):

       resourceList1 = filter((lambda r: r.policy.exists()),resourceList)
       resourceList2 = filter((lambda r: not r.policy.exists()),resourceList)
       policies1 = [r.policy() for r in resourceList1]
      # get_holding
      pass

   # set_holding or set_quota (if dummy)
   @staticmethod
   def saveMany(resourceList):
      pass

    
   def __init__(self):
       self.set(None,None,None)

   def __eq__(self, other):
       if isinstance(other, Resource):
         return self.resourceName == other.resourceName
       elif isinstance(other,String):
         return self.resourceName == other
       else:
         return False 

    def __ne__(self, other):
       return not (self.__eq__(other))

    def name():
        return self.resourceName
        
    def policy():
        return self.policy

    def setPolicy(self,policy):
        self.policy = policy



class Commission(Config):

    CommissionState = enum('NOT_ISSUED','PENDING','ACCEPTED','REJECTED')    

    #Serial : Positive
    # ClientKey : Name
    # 
   def __init__(self,entity,target):
      self.clientKey = Client.clientKey
      self.serial = None
      self.entity = entity
      self.state = CommissionState.NOT_ISSUED
      self.resources_quant = []
      self.target = target

    def __eq__(self, other):
       if isinstance(other, Commission):
         return self.serial == other.serial
       elif isinstance(other,Int):
         return self.serial == other
       else:
         return False 

    def __ne__(self, other):
       return not (self.__eq__(other))

    def issue(self):
       pass

    def accept(self):
       pass

    def reject(self):
       pass

    #TODO: assert that resource.entity is the same as self.entity !!
    def addResource(self,resource,quantity):
       self.resources_quant.append((resource,quantity))


class Entity(Config):
    # static  field (in some sense --- if it is assigned it will create a new binding)
    EntityState = enum('NOT_EXISTS','EXISTS')    
    #state = EntityState.NOT_EXISTS
    #parent = None 
    #entityName = None
    #entityKey = None
    #context = {}

    @staticmethod
    def getRoot():
        e = Entity()
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
            if(rejectedList != []):
                printf("Rejected entities (call to {0}): {1}",op, rejectedList)
        return (a,b)            

    @staticmethod
    def saveMany(entityList):
        inputList = [(e.entityName,e.parent.entityName,e.entityKey,e.parent.entityKey) for e in entityList]
        printf("Creating entities: {0}", inputList)
        rejectedList = Entity.con().create_entity(context=Entity.Context,create_entity=inputList)
        (ok,notok) = Entity.split(entityList,rejectedList,"create") 
        printf("\n")
        for e in ok:
            e.setExists(True)
        for e in notok:
            e.setExists(False)
        return notok

    @staticmethod
    def deleteMany(entityList):        
        inputList = [(e.entityName,e.entityKey) for e in entityList]
        printf("Releasing entities: {0}", inputList)
        rejectedList = Entity.con().release_entity(context=Entity.Context,release_entity=inputList)
        (ok,notok) = Entity.split(entityList,rejectedList,"release") 
        printf("\n")
        for e in ok:
           e.setExists(False)
        for e in notok:
           e.setExists(True)
        return notok

    @staticmethod
    def checkMany(entityList):
        inputList = [(e.entityName,e.entityKey) for e in entityList]
        printf("Get entities: {0}", inputList)
        acceptedList = Entity.con().get_entity(context=Entity.Context,get_entity=inputList)
        rejectedList = [e.entityName for e in entityList if e.entityName not in [n for n,k in acceptedList]] 
        (ok,notok) = Entity.split(entityList,rejectedList,"get_entity") 
        printf("\n")
        for e in ok:
           e.setExists(True)
        for e in notok:
           e.setExists(False)
        return notok

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

    def __init__(self):
       self.set(None,None,None)
       self.commissions = []

    def reset(self):
       self.set(None,None,None)

    def set(self,name,password,parent):
       self.entityName = name
       self.entityKey  = password
       self.parent = parent
       self.setExists(False)

    def setExists(self,v): 
       if(v == True): 
         self.state = self.EntityState.EXISTS
         return True
       else:
         self.state = self.EntityState.NOT_EXISTS
         return False

    def exists(self):
         q.return self.state != self.EntityState.NOT_EXISTS
    
   # def mustExist(self):
   #    if(not self.checkExists()):
   #         raise Exception("User {0} does not exist!".format(entityName))

   # def mustNotExist(self):
   #    if(self.checkExists()):
   #         raise Exception("User {0} already exists!".format(entityName))

    def checkExists(self):
       self.checkMany([self])
       return self.exists()

    def create(self):
       if(not self.checkExists()):
          self.saveMany([self])
       return self.exists()

    def release(self):
       if(self.checkExists()):
          self.deleteMany([self])
       return self.exists()

    # list and load resources
    def getResources(self):
        resourceList = Entity.con().list_resources(Entity.Context,self.entityName,self.entityKey)
        ret = []
        for r in resourceList:
           r1 = Resource()
           r1.set(self,r)
           ret.append(r1)
        Resource.loadMany(ret)
        return ret

     def createCommission(self,targetEntity):
        q = Commission(self,target,targetEntity)
        self.commissions.append(q)
        return q

    def getCommissions(self):
        return self.commissions()
    
# Main program 
root = Entity.getRoot()
pgerakios = Entity()
pgerakios.set("pgerakios","key1",root)
pgerakios.create()

e = Entity()
e.set(rand_string(),"key1",pgerakios)
e.create()
e.release()


