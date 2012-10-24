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

def exn(fmt, *args):
   raise Exception(fmt.format(*args))

def cexn(b,fmt,*args):
    if(b):
      raise Exception(fmt.format(*args))

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

def split(f,seq):
    a = []
    b = []
    for item in seq:
        if f(item): 
            a.append(item)
        else:
            b.append(item) 
    return (a,b)


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



class Policy(Config):

    PolicyState = enum('NOT_EXISTS','EXISTS','DUMMY')    

    # Dummy policies are neither loaded nor saved.
    @staticmethod
    def newDummy():
       p = Policy()
       p.exist = Policy.PolicyState.DUMMY
       return p

    @staticmethod
    def splitRejected(policyList,rejectedList):
        (a,b) = split((lambda p:p.policyName not in rejectedList),policyList)
        if(b != [])
            printf("Rejected entities (call to set_limits): {0}", rejectedList)
        return (a,b)

    @staticmethod
    def splitAccepted(policyList,acceptedList):
        acceptedListNames =[x[0] for x in acceptedList]
        (a,b) = split((lambda p:p.policyName in acceptedListNames),policyList)
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
      self.imported = None
      self.exported = None
      self.returned = None
      self.released = None
      self.flags = None

    # get_holding is NOT USED!!! We update Policy data as well with get_quota
    @staticmethod 
    def loadMany(resourceList):
       iList1 = [(r.entity.entityName,r.resourceName,r.entity.entityKey) for r in resourceList]
       oList1 = Resource.con().get_quota(context=Resource.Context,get_quota=iList1)
       for e,res,q,c,il,el,p,i,e,r1,r2,f in oList1:
          res1 = find((lambda r: r.resourceName == res),resourceList)
          res1.imported = i
          res1.exported = e
          res1.returned = r1
          res1.released = r2
          res1.flags = f
          res1.policy.quantity = q
          res1.policy.capacity = c
          res1.policy.importLimit = il
          res1.policy.exportLimit = el

        return []

   # set_holding or set_quota (if dummy)
   @staticmethod
   def saveMany(resourceList):
      (rl1,rl2) = split((lambda r: not r.policy.isDummy()),resourceList)
      #
      #
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

    def name(self):
        return self.resourceName
        
    def policy(self,query=False):
       if(query):
          self.load()
        return self.policy

    def setPolicy(self,policy):
        self.policy = policy

    def quantity(self,query=False):
       if(query):
          self.load()
       #FIXME: Is this correct ?
       return self.policy.quantity

    def load(self):
       return loadMany([self]) == []


class Commission(Config):

    CommissionState = enum('NOT_ISSUED','PENDING','ACCEPTED','REJECTED')   

    @staticmethod
    def saveAll(comList):
        inputList = [c.serial for c if(c.isPending()) in comList]
        rejectedList = Commission.con().accept_commission(context=Commission.context,
                                                          clientkey=Commission.ClientKey,
                                                          serials=inputList,reason='ACCEPT')
        for c in inputList:
           c.state = CommissionState.ACCEPTED
      #TODO: not implemented yet because the API does not support this. 
        return [c for c if(c not in inputList) in comList]


   @staticmethod
   def denyAll(comList):
        inputList = [c.serial for c if(c.isPending()) in comList]
        rejectedList = Commission.con().accept_commission(context=Commission.context,
                                                          clientkey=Commission.ClientKey,
                                                          serials=inputList,reason='REJECT')
        for c in inputList:
           c.state = CommissionState.REJECTED
      #TODO: not implemented yet because the API does not support this. 
        return [c for c if(c not in inputList) in comList]


    #Serial : Positive
    # ClientKey : Name
   def __init__(self,target):
      self.clientKey = Client.clientKey
      self.serial = None
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

    def canChange(self):
       self.state == CommissionState.NOT_ISSUED

    def isPending(self):
       self.state == CommissionState.PENDING

    def issue(self):
        prov = [(r.entity.entityName,r.resourceName,q) for r,q in self.resources_quant]
        self.serial = Commission.con().issue_commission(context=Commission.Context,
                                                        target=self.target.entityName,
                                                        clientkey=Client.ClientKey,
                                                        owner=self.target.parent.entityName,
                                                        ownerKey=self.target.parent.entityKey,
                                                        provisions=prov)
        self.state = CommissionState.PENDING
        return True

    def accept(self):
       return Commission.saveAll[self]) == []

    def reject(self):
       return Commission.denyAll[self]) == []

    #TODO: assert that resource.entity is the same as self.entity !!
    def addResource(self,resource,quantity):
        cexn(self.state != CommissionState.NOT_ISSUED,
             "Attempted to add a resource to a commission that has been issued.")
        cexn(resource in [r  for r,q in self.resources_quant],
             "Resource {0} already exists in commission.",resource.resourceName)
        cexn(resource.quantity() < quantity,
             "Insufficient quantity: Resource {0} quantity is {1} but {2} is required.",
             resource.resourceName,resource.quantity(),quantity)
       self.resources_quant.append((resource,quantity))
       return True


class Entity(Config):
    # static  field (in some sense --- if it is assigned it will create a new binding)
    EntityState = enum('NOT_EXISTS','EXISTS')   

    allEntities = {}

    @staticmethod
    def get(name="",key="",parent=None):
        e = Entity.allEntities.get(name)
        if(e == None):
            e = Entity()
            if(name == "system" or name == ""):
                e.set("system","",None)
            else:
                cexn(parent == None,"Entity.get of a non-existent entity with name {0} and no parent.",name)
                cexn(not isinstance(parent,Entity),"Entity.get parent of {0} is not an Entity!",name)
                e.set(name,key,parent)
            Entity.allEntities[name] = e
       return e

    @staticmethod
    def list():
       return [v for k,v in Entity.allEntities.iteritems()]

    @staticmethod
    def split(entityList,rejectedList,op):
       (a,b) = split((lambda e: e.entityName not in rejectedList),entityList)
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
           e.state = Entity.EntityState.NOT_EXISTS
        for e in notok:
           e.state = Entity.EntityState.EXISTS
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
           e.state = Entity.EntityState.EXISTS
        for e in notok:
           e.state = Entity.EntityState.NOT_EXISTS
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
       self.resources = []
    
    def _check(self):
#       cexn(self != Entity.allEntities.get(self.entityName),"Entity {0} does not exist in global dict",self.entityName)
        pass

    def reset(self):
       self.set(None,None,None)

    def set(self,name,password,parent):
       self.entityName = name
       self.entityKey  = password
       self.parent = parent
       self.setExists(False)

    def exists(self,query=False):
        self._check()
        if(query):
          self.checkMany([self])
        return self.state != self.EntityState.NOT_EXISTS
    
    def create(self,query=False):
       self._check()
       if(not self.exists(query)):
          self.saveMany([self])
       return self.exists()

    def release(self,query=False):
       self._check()
       if(self.exists(query)):
          self.deleteMany([self])
       return not self.exists()

    # list and load resources
    def resources(self,query=False):
        self._check()
        if(query):
            resourceList = Entity.con().list_resources(context=Entity.Context,
                                                       entity=self.entityName,
                                                       key=self.entityKey)
            self.resources = []
            for r in resourceList:
                r1 = Resource()
                r1.set(r,self)
                self.resources.append(r1)
            Resource.loadMany(self.resources)

        return self.resources

     # self = target Entity 
     # 
     def commission(self):
        q = Commission(self)
        self.commissions.append(q)
        return q

    def commissions(self):
        return self.commissions()

    def issueAll(self):
       valid = [c for c in self.commissions() if(c.canChange())]
       for c in valid:
          c.issue()
       return valid

    def commitAll(self,accept=True):
       self.issueAll()
       valid = [c for c in self.commissions() if(c.isPending())]
       if(accept):
          return Commissions.saveAll(valid) == []
       else:
          return Commissions.denyAll(valid) == []


    
# Main program 
root = Entity.get()
pgerakios = Entity.get("pgerakios","key1",root)
pgerakios.create()

# Transfer resources
e = Entity.get(rand_string(),"key1",pgerakios)
e.create()

q = e.commission()
r = pgerakios.resources()
q.addResource(r[0],10)
q.addResource(r[5],20)

e.commitAll(False)


#







e.release()



