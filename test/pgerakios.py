#!/usr/bin/env python
import sys
import os
from commissioning.clients.http import HTTP_API_Client
from commissioning import QuotaholderAPI
from sets import Set
import random
import copy
import inspect
import traceback


def environ_get(key, default_value=''):
    if os.environ.has_key(key):
        return os.environ.get(key)
    else:
        return default_value

#DEFAULT_PORT = "8008"
DEFAULT_PORT = "3536"
DEFAULT_HOST = "127.0.0.1"
QH_HOST = environ_get("TEST_QH_HOST", environ_get("QH_HOST", DEFAULT_HOST))
QH_PORT = environ_get("TEST_QH_PORT", environ_get("QH_PORT", DEFAULT_PORT))
QH_DEBUG = True

assert QH_HOST != None
assert QH_PORT != None

def printf(fmt, *args):
    global QH_DEBUG
    if(QH_DEBUG):
        sys.stderr.write(fmt.format(*args) + "\n")
#        print(fmt.format(*args))
    return 0

def exn(fmt, *args):
    raise Exception(fmt.format(*args))

def cexn(b, fmt, *args):
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
    string = ''
    for x in random.sample(alphabet, random.randint(min, max)):
        string += x
    return string


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)


def find(f, seq):
    for item in seq:
        if f(item):
            return item
    return None

def split(f, seq):
    a = []
    b = []
    for item in seq:
        if f(item):
            a.append(item)
        else:
            b.append(item)
    return (a, b)


class Client(object):
    qh = new_qh_client()
    #clientKey = rand_string()
    clientKey = "test1"
    
    @staticmethod
    def get():
        return Client.qh

    #getPending
    @staticmethod
    def getPending():
        return Client.qh.get_pending_commissions(context={},clientkey=Client.clientKey)

    #
    @staticmethod
    def removePending():
        #TODO: resolve_pending_commissions
        exn("Not implemented")


class Config(object):
    Context = {}
    Flags = 0

    @staticmethod
    def con():
        return Client.get()


class Policy(Config):

    PolicyState = enum('NOT_EXISTS', 'EXISTS', 'DUMMY')

    policies = {}

    @staticmethod
    def names(policyList):
        return [p.policyName for p in policyList]
    
    @staticmethod
    def copy(policy):
        return copy.deepcopy(policy)

    @staticmethod
    def union(policy1,policy2):
        return Policy.copy(policy1)

    @staticmethod
    def get(name,load=False):
        p = Policy.policies.get(name)
        if(p == None):
            p = Policy.newDummy()
            p.policyName = name
            Policy.policies[name] = p
        elif(load == True):
            p.load()        
        return p
    
    
    @staticmethod
    def getMany(names):
        policyList = [Policy.get(name) for name in names]
        for p in policyList:
            p.setDummy(False)
        return policyList

    
    @staticmethod
    def loadManyByName(names):
        policyList = Policy.getMany(names)
        rejected = Policy.loadMany(policyList)
        return split(lambda p: p.policyName not in rejected,policyList)
        

    # Dummy policies are neither loaded nor saved.
    @staticmethod
    def newDummy(**kwargs):
        p = Policy(**kwargs)
        p.exist = Policy.PolicyState.DUMMY
        return p

    @staticmethod
    def splitRejected(policyList, rejectedList):
        (a, b) = split((lambda p: p.policyName not in rejectedList), policyList)
        if(b != []):
            printf("Rejected policies (call to set_limits!!): {0}", [p.policyName for p in b])
        return (a, b)

    @staticmethod
    def splitAccepted(policyList, acceptedList):
        acceptedListNames = [x[0] for x in acceptedList]
        (a, b) = split((lambda p: p.policyName in acceptedListNames), policyList)
        if(b != []):
            printf("Rejected policies (call to get_limits): {0}", b)
        return (a, b)

    @staticmethod
    def saveMany(policyList):
        inputList = [(p.policyName, p.quantity, p.capacity, p.importLimit, p.exportLimit)
                     for p in policyList if(not p.isDummy())]
        if(inputList != []):
            printf("set_limits input list is : {0}",inputList)
            rejectedList = Policy.con().set_limits(context=Policy.Context, set_limits=inputList)
        else:
            printf("EMPTY INPUT LIST")
            for p in policyList:
                printf("Policy list item {0} valid={1} dummy={2}",p.policyName,p.isValid(),p.isDummy())
            rejectedList = inputList
        ok, notok = Policy.splitRejected(policyList, rejectedList)
        for p in ok:
            p.exist = Policy.PolicyState.EXISTS
        for p in notok:
            if(p.exist == Policy.PolicyState.EXISTS):
                p.exist = Policy.PolicyState.NOT_EXISTS
        return notok

    @staticmethod
    def loadMany(policyList):
        inputList = [p.policyName for p in policyList if(not p.isDummy())]
        #printf("get_limits inputList: {0}", inputList)
        if(inputList != []):
            acceptedList = Policy.con().get_limits(context=Policy.Context, get_limits=inputList)
        else:
            acceptedList = []
        (ok, notok) = Policy.splitAccepted(policyList, acceptedList)
        # fill the policy
        for p in ok:
            p.exist = Policy.PolicyState.EXISTS
            g = find((lambda x: x[0] == p.policyName), acceptedList)
            p.quantity = g[1]
            p.capacity = g[2]
            p.importLimit = g[3]
            p.exportLimit = g[4]
        for p in notok:
            if(p.exist == Policy.PolicyState.EXISTS):
                p.exist = Policy.PolicyState.NOT_EXISTS

        return notok
    
    def __str__(self):
        return "Policy({0})".format(self.policyName)

    def reset(self):
        self.set(None, 0, 0, None, None)

    def set(self, name, q, c, i, e):
        self.policyName = name
        self.quantity = q
        self.capacity = c
        self.importLimit = i
        self.exportLimit = e
        self.exist = Policy.PolicyState.NOT_EXISTS

    def __init__(self, **kwargs):
        self.policyName = None
        self.reset()
        self.__dict__.update(kwargs)


    def isDummy(self):
        return self.exist == Policy.PolicyState.DUMMY


    def setDummy(self,v=True):
        if(v):
            self.exist = Policy.PolicyState.DUMMY
        else:
            self.exist = Policy.PolicyState.NOT_EXISTS

    def name(self):
        return self.policyName


    def isValid(self):
        return  self.policyName == None or self.quantity == None or  self.capacity == None or  self.importLimit == None  or self.exportLimit == None


    def setExists(self,v=True):
        if(v):
            self.exist = Policy.PolicyState.EXISTS
        else:
            self.exist = Policy.PolicyState.NOT_EXISTS

    def exists(self):
        return self.exist

    def __eq__(self, other):
        if isinstance(other, Policy):
            return self.policyName == other.policyName
        elif isinstance(other, basestring):
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

    ResourceState = enum('DIRTY', 'LOADED')
    
    @staticmethod
    def loadAllAsDummy(resourceList):
        resourceList = [copy.deepcopy(r) for r in resourceList]
        for r in resourceList:
            r.policy.setDummy(True)
        #
        return Resource.loadMany(resourceList,False)
    
    @staticmethod
    def names(resourceList):
        return [r.resourceName for r in resourceList]
    
    @staticmethod
    def getPolicies(resourceList):
        return [r.policy for r in resourceList]
    
    @staticmethod
    def copy(resource):
        return copy.copy(resource)

    @staticmethod
    def allDirty(resourceList):
        for r in resourceList:
            r.setDirty()

    # When a dummy policy is used, the policy is also loaded by get_quota
    # if it is a normal policy only the resource is loaded but not the corresponding
    @staticmethod
    def loadMany(resourceList0,dirtyOnly=True):
        if(dirtyOnly):
            resourceList = [r for r in resourceList0 if(r.isDirty())]
        else:
            resourceList = resourceList0
        #
        (rl1,rl2) = split((lambda r: r.policy.isDummy()),resourceList)
        #
        iList1 = [(r.entity.entityName, r.resourceName, r.entity.entityKey) for r in rl1]
        if(iList1 == []):
            oList1 = []
        else:
            oList1 = Resource.con().get_quota(context=Resource.Context, get_quota=iList1)
            for e, res, q, c, il, el, i, e, r1, r2, f in oList1:
                res1 = find((lambda r: r.resourceName == res), rl1)
                res1.imported = i
                res1.exported = e
                res1.returned = r1
                res1.released = r2
                res1.flags = f
                res1.policy.quantity = q
                res1.policy.capacity = c
                res1.policy.importLimit = il
                res1.policy.exportLimit = el
                res1.state = Resource.ResourceState.LOADED
        #
        iList2 = [(r.entity.entityName,r.resourceName,r.entity.entityKey) for r in rl2]
        if(iList2 == []):
            oList2 = []
        else:
            oList2 = Resource.con().get_holding(context=Resource.Context,get_holding=iList2)
            for e,res,p,im,ex,ret,rel,f in oList2:
                res1 = find((lambda r: r.resourceName == res), rl2)
                res1.imported = im
                res1.exported = ex
                res1.returned = ret
                res1.released = rel
                res1.flags = f
                res1.state = Resource.ResourceState.LOADED
        #
        rejectedList = [r for r in resourceList if(r.resourceName not in oList1 and r.resourceName not in oList2)]
        return rejectedList

    # set_holding or set_quota (if dummy)
    @staticmethod
    def saveMany(resourceList0,dirtyOnly=True):
        if(dirtyOnly):
            resourceList = [r for r in resourceList0 if(r.isDirty())]
        else:
            resourceList = resourceList0
        #
        (rl1, rl2) = split((lambda r: r.policy.isDummy()), resourceList)
        #
        if(rl1 == []):
            ol1 = []
        else:
            il1 = [(r.entity.entityName, r.resourceName, r.entity.entityKey,r.policy.quantity,
                    r.policy.capacity,r.policy.importLimit,r.policy.exportLimit,Resource.Flags) for r in rl1]
            printf("before call to set_quota: input list {0}",il1)
            #exn("BUG! should not reach this point")
            ol1 = Resource.con().set_quota(context=Resource.Context,set_quota=il1)
            #ListOf(Entity, Resource)
            ol1 = [find(lambda r: r.resourceName == r and r.entity.entityName == e,rl1) for e,r in ol1]
            ol1 = [r.policy for r in ol1]
            
        if(rl2 == []):
            ol2 = []
        else:
            il2 = [(r.entity.entityName,r.resourceName,r.entity.entityKey,r.policy.policyName,Resource.Flags) for r in rl2]
            ol2 = Resource.con().set_holding(context=Resource.Context,set_holding=il2)
            #rejected = ListOf(Entity, Resource, Policy)
            printf("####Rejected list ol2: {0}",ol2)
            ol2 = [find(lambda r: r.resourceName == r and r.entity.entityName == e,rl2) for e,r,p in ol2]
            ol2 = ol1 = [r.policy for r in ol2]

        return ol1+ol2


    def isDirty(self):
        return self.state == Resource.ResourceState.DIRTY

    def setDirty(self,val=True):
        if(val):
            self.state = Resource.ResourceState.DIRTY
        else:
            self.state = Resource.ResourceState.LOADED

    def set(self,**kwargs):
        self.__dict__.update(kwargs)
        self.setDirty()

    def __init__(self,name,entity):
        self.resourceName = name
        self.entity = entity
        self.policy = None
        self.imported = 0
        self.exported = 0
        self.returned = 0
        self.released = 0
        self.flags = 0
        self.state = Resource.ResourceState.DIRTY
        self.setPolicy(Policy.newDummy())

    def __eq__(self, other):
        if isinstance(other, Resource):
            return self.resourceName == other.resourceName
        elif isinstance(other, basestring):
            return self.resourceName == other
        else:
            return False

    def __ne__(self, other):
        return not (self.__eq__(other))


    def name(self):
        return self.resourceName


    def policy(self, query=False):
        if(query):
            self.load()
        return self.policy


    def setPolicy(self, policy):
        self.policy = policy
        self.setDirty(True)

    def quantity(self, query=False):
        if(query):
            self.load()
            #FIXME: Is this correct ?
        return self.policy.quantity


    def load(self,dirtyOnly=True):
        if(not self.policy.isDummy()):
            self.policy.load()
        return Resource.loadMany([self],dirtyOnly) == []

    def save(self,dirtyOnly=True):
        return Resource.saveMany([self],dirtyOnly) == []


class Commission(Config):
    CommissionState = enum('NOT_ISSUED', 'PENDING', 'ACCEPTED', 'REJECTED')

    @staticmethod
    def saveAll(comList):
        inputList = [c.serial for c in comList if(c.isPending() and c.serial != None)]
        #cexn(inputList==None,"input list is NONE!")
        if(inputList != []):
            rejectedList = Commission.con().accept_commission(context=Commission.Context,
                clientKey=Client.clientKey,
                serials=inputList, reason='ACCEPT')
        else:
            rejectedList = []
        
        if(rejectedList == None):
            rejectedList = []
            
        #TODO: not implemented yet because the API does not support this.
        #cexn(isinstance(rejectedList,NoneType),"rejectedList is NoneType")
        #cexn(isinstance(comList,NoneType),"comList is NoneType")
        
        inputList = [c for c in comList if(c.serial not in rejectedList)]
        for c in inputList:
            c.state = Commission.CommissionState.ACCEPTED

        return [c for c in comList if(c not in inputList)]

    @staticmethod
    def denyAll(comList):
        inputList = [c.serial for c in comList if(c.isPending())]
        rejectedList = Commission.con().accept_commission(context=Commission.Context,
            clientKey=Client.clientKey,
            serials=inputList, reason='REJECT')
        for c in inputList:
            c.state = Commission.CommissionState.REJECTED
            #TODO: not implemented yet because the API does not support this.
        return [c for c in comList if(c not in inputList)]

    def __init__(self, target):
        self.clientKey = Client.clientKey
        self.serial = None
        self.state = Commission.CommissionState.NOT_ISSUED
        self.resources_quant = []
        self.target = target

    def __eq__(self, other):
        if isinstance(other, Commission):
            return self.serial == other.serial
        elif isinstance(other, int):
            return self.serial == other
        else:
            return False

    def __ne__(self, other):
        return not (self.__eq__(other))


    def inverse(self):
        ret = copy.copy(self)
        ret.resources_quant = [(r,-q) for r,q in ret.resources_quant]
        ret.state = Commission.CommissionState.NOT_ISSUED
        return ret

    def canChange(self):
        return self.state == Commission.CommissionState.NOT_ISSUED


    def isPending(self):
        return self.state == Commission.CommissionState.PENDING

    def isFinal(self):
        return (not self.canChange()) and (not self.isPending())

    def issue(self):
        prov = [(r.entity.entityName, r.resourceName, q) for r, q in self.resources_quant if(q != 0)]
        if(prov != []):
            printf("Target is {0} and prov_list= {1}",self.target.entityName,prov)
            cexn(Client.clientKey == None, "Client key has the value NONE")
            self.serial = Commission.con().issue_commission(context=Commission.Context,
                target=self.target.entityName,
                key=self.target.entityKey,
                clientKey=Client.clientKey,
                owner=self.target.parent.entityName,
                ownerKey=self.target.parent.entityKey,
                provisions=prov,
                name="Commission from {0} -> {1}".format([a for a,b,c in prov],self.target.entityName))
        self.state = Commission.CommissionState.PENDING
        return True


    def accept(self,forceIssue=False):
        if(forceIssue):
            self.issue()
        return Commission.saveAll([self]) == []

    def reject(self):
        return Commission.denyAll([self]) == []

        #TODO: assert that resource.entity is the same as self.entity !!


    def addResource(self, resource, quantity):
        cexn(self.state != Commission.CommissionState.NOT_ISSUED,
            "Attempted to add a resource to a commission that has been issued.")
        cexn(resource in [r  for r,q in self.resources_quant],
            "Resource {0} already exists in commission.", resource.resourceName)
        #cexn(resource.quantity < quantity,
            #   "Insufficient quantity: Resource {0} quantity is {1} but {2} is required.",
            #  resource.resourceName, resource.quantity, quantity)
        self.resources_quant.append((resource, quantity))
        return True

    def __str__(self):
        prov = [(r.entity.entityName, r.resourceName, q) for r, q in self.resources_quant if(q != 0)]
        return "Commission(SERIAL={0},PENDING={1},FINAL={2},canChange={3},PROV={4})".format(self.serial,self.isPending(),self.isFinal(),self.canChange(),prov) 

class Entity(Config):
    # static  field (in some sense --- if it is assigned it will create a new binding)
    EntityState = enum('NOT_EXISTS', 'EXISTS')
    systemName = "system"
    systemKey = ""

    allEntities = {}

    @staticmethod
    def get(name="",f=None):
        #printf("System name {0} ==> get name {1}",Entity.systemName,name)
        # If system has not been added to hierarchy add it now
        if( Entity.allEntities.get(Entity.systemName) == None):
            Entity.allEntities[Entity.systemName] = Entity().set(Entity.systemName,"",None)
        # If name is empty, then translate it to system
        if(name == ""):
            name = Entity.systemName
        # find entity named name
        e = Entity.allEntities.get(name)
        #otherwise, create a new one
        if(e == None):
            printf("calling f for name {0}",name)
            if(f == None):
                if(name == Entity.systemName):
                    e =  Entity().set("system","",None)
                else:
                    exn("Invalid callback function")
            else:
                e = f()
            Entity.allEntities[name] = e
            
        #printf("Getting object with name {0} and type {1} and its name is {2}",name,type(e),e.entityName)
        return e

    @staticmethod
    def list():
        return [v for k, v in Entity.allEntities.iteritems() if(v!=None)]

    @staticmethod
    def split(entityList, rejectedList, op):
        (a, b) = split((lambda e: e.entityName not in rejectedList), entityList)
        if(rejectedList != []):
            printf("Rejected entities (call to {0}): {1}", op, rejectedList)
        return (a, b)

    @staticmethod
    def saveMany(entityList):
        inputList = [(e.entityName, e.parent.entityName, e.entityKey, e.parent.entityKey) for e in entityList]
        printf("Creating entities: {0}", inputList)
        rejectedList = Entity.con().create_entity(context=Entity.Context, create_entity=inputList)
        (ok, notok) = Entity.split(entityList, rejectedList, "create")
        printf("\n")
        for e in ok:
            e.state = Entity.EntityState.EXISTS
        for e in notok:
            e.state = Entity.EntityState.NOT_EXISTS
        return notok

    @staticmethod
    def deleteMany(entityList,force=False):
        if(entityList == []):
            return []
        #
        if(force):
            resourceList = []
            for e in entityList:
                for r in e.getResources():
                    r.policy.setDummy(True)
                    r.policy.quantity = 0
                    r.policy.capacity = 0
                    resourceList.append(r)
            if(resourceList != []):
                printf("----> REMOVING ALL RESOURCES !!!")
                Resource.saveMany(resourceList,False)
                printf("----> REMOVING ALL RESOURCES DONE.")
            
        inputList = [(e.entityName, e.entityKey) for e in entityList]
        printf("Releasing entities: {0}", inputList)
        rejectedList = Entity.con().release_entity(context=Entity.Context, release_entity=inputList)
        (ok, notok) = Entity.split(entityList, rejectedList, "release")
        printf("\n")
        for e in ok:
            e.state = Entity.EntityState.NOT_EXISTS
        for e in notok:
            e.state = Entity.EntityState.EXISTS
        return notok

    @staticmethod
    def checkMany(entityList):
        inputList = [(e.entityName, e.entityKey) for e in entityList]
        printf("Get entities: {0}", inputList)
        acceptedList = Entity.con().get_entity(context=Entity.Context, get_entity=inputList)
        rejectedList = [e.entityName for e in entityList if e.entityName not in [n for n, k in acceptedList]]
        (ok, notok) = Entity.split(entityList, rejectedList, "get_entity")
        printf("\n")
        for name,parentName in acceptedList:
            e = find((lambda e: e.entityName == name),entityList)
            #if(e.parent != None and parentName !=  e.parent.entityName):
            #    exn("Parent of {0} is {1} and not {2}.",e.entityName,parentName,e.parent.parentName)
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
        elif isinstance(other, basestring):
            return self.entityName == other
        else:
            return False

    def __ne__(self, other):
        return not (self.__eq__(other))

    def __init__(self):
        self.set(None, None, None)
        self._commissions = []
        self._resources = []

    def _check(self):
    #       cexn(self != Entity.allEntities.get(self.entityName),"Entity {0} does not exist in global dict",self.entityName)
        pass

    def getChildren(self):
        list = Entity.con().list_entities(context=Entity.Context,entity=self.entityName,key=self.entityKey)
        return [Entity.get(e,lambda: Entity().set(e,"",self)) for e in list]

    def reset(self):
        self.set(None, None, None)

    def set(self, name, password, parent):
        cexn(parent == None and name != "system" and name != None, "Entity.get of a non-existent entity with name {0} and no parent.", name)
        self.entityName = name
        self.entityKey = password
        self.parent = parent
        self.state = Entity.EntityState.NOT_EXISTS
        return self

    def exists(self, query=False):
        self._check()
        if(query):
            self.checkMany([self])
        return self.state != self.EntityState.NOT_EXISTS

    def create(self, query=False):
        self._check()
        if(not self.exists(query)):
            self.saveMany([self])
        return self.exists()

    def release(self, query=False):
        self._check()
        if(self.exists(query)):
            self.deleteMany([self])
        return not self.exists()

    def addResourceWith(self,name,**kwargs):
        p = Policy.newDummy(quantity=0,capacity=10)
        return self.addResource(name,p)

    # Resource-related API
    def addResource(self,name,policy=None):
        r1 = Resource(name,self)
        if(isinstance(policy,Policy)):
            r1.policy = policy
        self._resources.append(r1)
        return r1

    def markAllResourcesAsDirty(self):
        Resource.allDirty(self._resources)

    # save dirty only
    def saveResources(self,all=False):
        Resource.saveMany(self._resources,not all)

    def getResource(self,name ,query=False):
        r1 = self.getResources(query)
        return find((lambda r: r.resourceName == name),r1)

    # list and load resources
    def getResources(self, query=False):
        self._check()
        if(query):
            resourceList = Entity.con().list_resources(context=Entity.Context,
                entity=self.entityName,
                key=self.entityKey)
            ret = []
            for r in resourceList:
                r1 = Resource(r,self)
                ret.append(r1)
            Resource.loadMany(ret)
            self._resources = ret + [r for r in self._resources if(r not in ret)]

        return self._resources

    # Commission-related API
    # self = target entity
    def addCommission(self):
        q = Commission(self)
        self._commissions.append(q)
        return q

    def getCommissions(self):
        return self._commissions

    def issueAllCommissions(self):
        valid = [c for c in self.commissions() if(c.canChange())]
        for c in valid:
            c.issue()
        return valid

    def commitAllCommissions(self, accept=True):
        self.issueAll()
        valid = [c for c in self.commissions() if(c.isPending())]
        if(accept):
            return Commission.saveAll(valid) == []
        else:
            return Commission.denyAll(valid) == []


    def clearFinished(self):
        self.commissions = [c for c in self.commissions() if(c.canChange())]

#########################################################################################################

class ResourceHolder(Entity):

    root = Entity.get("pgerakios", lambda: Entity().set("pgerakios","key1",Entity.get("system")))
    resourceDefaults ={
                     "pithos" : 1000,
                     "cyclades_vm" : 1000,
                     "cyclades_cpu" : 1000,
                     "cyclades_mem" : 1000
                   }
    
    @staticmethod
    def getResourceNames():
        return [name for name in ResourceHolder.resourceDefaults]
    
    @staticmethod
    def getResourceDefaultValues():
        return ResourceHolder.resourceNames

    def __init__(self):
        #super(Entity,self).__init__()
        Entity.__init__(self)
        printf("INIT of ResourceHolder invoked for {0}",self.entityName)
        #self.commission = Commission(self)
        for r in ResourceHolder.getResourceNames():
            self.addResource(r)


    def loadResources(self):
        self.getResource(True)

#    def newCommission(self):
#        self.commission = Commission(self)
#        return self.commission
#
#    def commit(self):
#        return self.commission.issue() and self.commission.accept()
#
#    def reject(self):
#        return self.issue() and self.commission.reject()

    def release(self):
#        # If there is a committed commission, then undo changes
#        if(not self.commission.canChange()):
#            # commit the inverse stuff (send stuff back to groups)
#            self.commission = self.commission.inverse()
#            b = self.commit()
#            self.newCommission()
#            if(not b):
#                return False
#        # Remove entity
        return super(ResourceHolder,self).release()

class Group(ResourceHolder):

    systemGroupName = "group"
    systemGroupKey  = "group"
    initializedSystem = False
    
    _systemGroupName = "system_group"
    _systemGroupPass = "system_group"

    @staticmethod
    def listGroups():
        return Group.getGroupRoot().getChildren()

    @staticmethod
    def getGroupRoot():
        def createRoot():
            e = Entity().set(Group.systemGroupName,Group.systemGroupKey,ResourceHolder.root)
            if(e.exists(True) == False):
                printf("Group {0} does not exist. Creating {0}.",e.entityName,e.entityName)
                e.create()
            return e
        return  Entity.get(Group.systemGroupName,createRoot)

    @staticmethod
    def systemGroup():
        system = Group.get(Group._systemGroupName,Group._systemGroupPass,
                           # Optional arguments
                           group_pithos=ResourceHolder.resourceDefaults["pithos"],
                           group_cyclades_vm=ResourceHolder.resourceDefaults["cyclades_vm"],
                           group_cyclades_mem=ResourceHolder.resourceDefaults["cyclades_mem"],
                           group_cyclades_cpu=ResourceHolder.resourceDefaults["cyclades_cpu"],
                           user_pithos=0,user_cyclades_vm=0,
                           user_cyclades_mem=0, user_cyclades_cpu=0                      
                          )
        cexn(not isinstance(system,Group),"Not instance of Group!")
        return system
        
    

    @staticmethod
    def get(name,key,**kwargs):
        #printf("@@-1 len of kwargs : {0}", len(kwargs.items()))        
        def groupCreate():
            #printf("@@0 len of kwargs : {0}", len(kwargs.items()))
            g = Group(name,key,Group.getGroupRoot(),**kwargs)
            printf("Creating group {0} with type {1}",name,type(g))
            return g
        ret = Entity.get(name,groupCreate)
        cexn(not isinstance(ret,Group),"Not instance of Group!")
        return ret    
    
    def policyName(self,isGroup,resourceName):
        ret = "group.{0}.{1}.".format(self.entityName,resourceName)
        if(isGroup):
            return ret + "groupPolicy"
        else:
            return ret + "userPolicy"

    def getUserPolicyFor(self,resourceName):
            return self.userResourcePolicies[resourceName]
            
    def __init__(self, name, password, parent, **kwargs):
        #printf("@@1 len of kwargs : {0}", len(kwargs.items()))
        ResourceHolder.__init__(self)
        ResourceHolder.set(self,name, password, parent)
        printf("INIT of Group invoked for {0}",self.entityName)
        self.users = []
        self.userResourcePolicies = {}
        #load group and user policies
        self.userResourcePolicies = {}
        self.commission = None
        
        #printf(" !!!! {0} !!!!", [r.resourceName for r in self.getResources()])
        
        def isSystemGroup():
            return self.entityName == Group._systemGroupName
        
        if(isSystemGroup() and Group.initializedSystem):
            exn("group {0} has already been initialized", Group._systemGroupName)
                
        # create entity if it does not exist        
        if(self.exists(True) == False):
            printf("Group {0} does not exist. Creating {0}.",self.entityName,self.entityName)
            self.create()
        
        #
        def getGroupPolicyFor(resourceName):
            return self.getResource(resourceName).policy
        
        def getUserPolicyFor(resourceName):
            return self.userResourcePolicies[resourceName]
                        
        def parseArgs():
            userArgs={}
            groupArgs={}
            resourceNames = Set([])
            #printf("len of kwargs : {0}", len(kwargs.items()))
            for prefixedResourceName,value in kwargs.items():
                #printf("Prefixed resourcename: {0}",prefixedResourceName)
                tmp = prefixedResourceName.split("_")
                prefix = tmp[0]
                resourceName = "_".join(tmp[1:])
                #prefix,resourceName = tuple(tmp[0],"".join(tmp[1:]))
                #printf("Prefixed resource name {0} ---> resource name {1}",prefixedResourceName,resourceName)
                if(prefix == "group"):
                    groupArgs[resourceName] = value 
                elif(prefix == "user"):
                    userArgs[resourceName] = value
                else:
                    exn("Unknown prefix " + prefix)
                resourceNames.add(resourceName)
                #
            return (groupArgs,userArgs,resourceNames)
            
        def makePolicyNames(resourceNames):
            policyNames = []
            for r in resourceNames:
                #printf("Making resource name {0}", r)
                policyNames.append(self.policyName(True,r))
                policyNames.append(self.policyName(False,r))
            return policyNames

        def fillResources(list):
            (group,user) = split(lambda p: p.policyName.endswith("groupPolicy"),list)
            groupRes = []
            for p in user:
                resourceName = p.policyName.split(".")[2]
                self.userResourcePolicies[resourceName] = p
                p.setDummy(False)
            for p in group:
                resourceName = p.policyName.split(".")[2]
                r = self.getResource(resourceName)
                #cexn(r.policy.policyName != p.policyName, "Bad policy name {0} {1}",r.policy.policyName , p.policyName)
                r.policy.policyName = p.policyName 
                r.policy = p
                p.setDummy(False)
                groupRes.append(r)
            return groupRes
                
        def parseResourceNames(policyList):
            group = []
            user = []
            for policyName in policyList:
                g,entityName,resourceName,postfix = tuple(policyName.split("."))
                if(postfix == "groupPolicy"):
                    group.append(resourceName)
                elif(postfix == "userPolicy"):
                    user.append(resourceName)
                else:
                    exn("bad postfix")                                                    
            return (group,user)
        
        #if(self.isSystemGroup()):
        #   for r in self.getResources():
        #      r.policy.quantity = ResourceHolder.getResourceDefaultValues()[r.resourceName]
        #      r.policy.capacity = 0
        #      r.policy.setDummy(False)
                 
        # Step 1: 
        # find resourceNames that must be overwritten -> specified in Args
        # the remaining resourceNames will be loaded
        # if some the remaining do not exist they will be saved
        groupArgs, userArgs, resourceNames = parseArgs()
        allResourceNames = Set([r.resourceName for r in self.getResources()])
        notInitResources = allResourceNames.difference(resourceNames)
        
                         
        #Step 2: load init policies
        notInitPolicyNames = makePolicyNames(notInitResources)
        printf("notInitPolicyNames: {0}  --- resourceNames : {1} --- allResourceNames: {2}",notInitPolicyNames,resourceNames,allResourceNames)
        (ok,notok) = Policy.loadManyByName(notInitPolicyNames)
        cexn(notok != [], "There exist some unspecified policies for {0} that were not specified in the constructor arguments and do not already exist: {1}",self.entityName,Policy.names(notok))
        # link resources to policies
        #if(self.isSystemGroup()):
                   
        fillResources(ok)
                           
        #        
        initPolicyNames = makePolicyNames(resourceNames)
        initPolicies = Policy.getMany(initPolicyNames)
        
        #        
        for policy in initPolicies:
            def get():
                g,entityName,resourceName,postfix = tuple(policy.policyName.split("."))
                if(postfix == "groupPolicy"):
                    return groupArgs[resourceName]
                elif(postfix == "userPolicy"):
                    return userArgs[resourceName]
                else:
                    exn("get exn")            
            if(isSystemGroup()):
                policy.capacity = 0
                policy.quantity = get()
            # otherwise groups and users have initially zero quantity
            else:
                policy.capacity = get()
                policy.quantity = 0

        
        # Save policies --- maybe some of the do not exist!        
        cexn(Policy.saveMany(initPolicies) != [],"Could not save all policies")
        printf("Saved policies : {0}",Policy.names(initPolicies))
        saveResources = fillResources(initPolicies)
        if(saveResources != []):
            cexn(Resource.saveMany(saveResources) != [] , "Could not save all resources")
            printf("Saved resources : {0}",Resource.names(saveResources))
           
        # system is now initialized
        if(isSystemGroup()):
            Group.initializedSystem = True
            

    def drawSystemResources(self,**kwargs):
        c = self.addCommission()
        system = Group.systemGroup()
        default = Set([])
        for resourceName,quantity in kwargs:            
            default.add(resourceName)
            r = copy.copy(system.getResource(resourceName))
            #r.resourceName = r.resourceName + ".groupPolicy"
            printf("#1 REQUESTING  {0} from system.{1}",quantity,r.resourceName)
            c.addResource(r,quantity)
        remaining = Set(system.getResourceNames()).difference(default)
        for resourceName in remaining: 
            sysRes = copy.copy(system.getResource(resourceName))
            #sysRes.resourceName = sysRes.resourceName + ".groupPolicy"
            r = self.getResource(resourceName) 
            printf("#2 REQUESTING  {0} from system.{1}",r.policy.capacity,sysRes.resourceName)
            c.addResource(sysRes,r.policy.capacity)        
        return  c.accept(True)

    def release(self):
        #
        qs = [q for q in self._commissions if(q.isFinal() and all(q > -1 for r,q in q.resources_quant))]
        qs = [q.inverse() for q in qs]        
        for q in qs:
            q.accept(True)
        #
        ResourceHolder.release(self)

    #def drawResources(self,**kwargs):
    #    for r in self.getResources():
    #        self.commission.addResource(r,r.policy.quantity)
    #    #
    #    return self.commit() 
    
    

#    def makeSystem(self):
#        if( self.entityName != Group.systemGroupName):
#            exn("Only system entity can invoke this function")
#        elif(Group.initializedSystem):
#            exn("group {0} already exists",Group.systemGroupName)
#        #
#        for r in self.getResources():
#            r.policy.quantity = ResourceHolder.getResourceDefaultValues()[r.resourceName]
#        self.saveResources(True)
#        #
#        Group.initializedSystem = True
#        
#    def savePolicyQuantities(self,**kwargs):
#        if(self.isSystemGroup() and Group.initializedSystem and len(kwargs.items)>0):
#            exn("Already initialized group " + Group.systemName)
#        #
#        policies = []
#        for prefixedResourceName,capacity in kwargs.items():
#            prefix,resourceName = tuple(prefixedResourceName.split("_"))
#            if(prefix == "group"):
#                p = self.getGroupPolicyFor(resourceName)
#                p.policyName = self.policyName(True,resourceName)                 
#            elif(prefix == "user"):
#                p = self.getUserPolicyFor(resourceName)
#                p.policyName = self.policyName(False,resourceName)
#            else:
#                exn("Unknown prefix " + prefix)
#            if(self.isSystemGroup()):                
#                p.capacity = 0
#                p.quantity = capacity
#            else:
#                p.capacity = capacity
#                p.quantity = 0                
#            p.setDummy(False)                        
#            policies.append(p)
#        #
#        Policy.saveMany(policies)

#    def saveGroupPolicyQuantities(self,**kwargs):
#        policies = []
#        for resourceName,capacity in kwargs.items():
#            p = self.getResource(resourceName).policy
#            p.capacity = capacity
#            p.quantity = 0
#            p.setDummy(False)
#            p.policyName = self.policyName(True,resourceName) 
#            policies.append(r.policy)
#        #
#        Policy.saveMany(policies)
#        
#    def saveUserPolicyQuantities(self,**kwargs):
#        policies = []
#        for resourceName,capacity in kwargs.items():
#            p = self.getUserPolicyFor(resourceName)
#            p.capacity = capacity
#            p.quantity = 0
#            p.setDummy(False)            
#            #p.policyName =  "group."  + self.entityName             
#            policies.append(p)
#        b = Policy.saveMany(policies)
#        for p in policies:
#            p.setDummy(True)
#        return b


class User(ResourceHolder):

    systemUserName = "group"
    systemUserKey  = "group"
    
    #userRoot =   Entity.get("user",lambda: User().set("user","user",ResourceHolder.root))

    @staticmethod
    def listUsers():
        return User.userRoot.getChildren()

    @staticmethod
    def getUserRoot():
        def createRoot():
            e = Entity().set(User.systemUserName,User.systemUserKey,ResourceHolder.root)
            if(e.exists(True) == False):
                printf("Group {0} does not exist. Creating {0}.",e.entityName,e.entityName)
                e.create()
            return e
            
        e = Entity.get(User.systemUserName,createRoot)
        #if(not e.exists()):
        #    e.create(True)
        return e
        
    @staticmethod
    def get(name,key):
        def userCreate():
            u = User(name,key,User.getUserRoot())
            printf("Creating user {0} with type {1}",name,type(u))
            return u
        return  Entity.get(name,userCreate)

    def __init__(self,name,password,parent):
        #super(ResourceHolder,self).__init__()
        ResourceHolder.__init__(self)
        ResourceHolder.set(self,name, password, parent)
        
        # create entity if it does not exist        
        if(self.exists(True) == False):
            printf("User {0} does not exist. Creating {0}.",self.entityName,self.entityName)            
            self.create()
        
        self.latestCommission = None
        self.groups = []

        self.resourceMap = {}
        self.groupMap = {}
        
        #load policies
        self.loadPolicies()

    def reload(self):
        # order does matter!
        self.clearFinished()
        self.reject()
        self.loadResources()
        self.loadPolicies()

    def loadPolicies(self):
        dict = {}
        for r in self.getResources():
            dict[r.resourceName] = r.policy
            
        for g in self.groups:
            for r in self.getResourceNames():
                p = g.getUserPolicyFor(r.resourceName)
                if(dict[r.name] == None):
                    dict[r.name] = Policy.copy(p)
                else:
                    dict[r.name] = Policy.union(dict[r.name],p)

        # Change user policy to dummy !!! its a copy of the group policy so
        # we can modify its fields
        for r in  self.getResources():
            p = dict.get(r.resourceName)
            p.setDummy(True)
            r.setPolicy(p)

    # 
    def _joinGroup(self,group):
        self.groups.append(group)
        group.users.append(self)
        self.groupMap[group] = {}
        #
        for r in self.getResources():
            groupUserPolicy = group.getUserPolicyFor(r.resourceName)
            printf("join group ==> Resource entity: {0} with name {1}",r.entity.entityName,groupUserPolicy.name())
            #
            #self.commission.addResource(group.getResource(r.resourceName),groupUserPolicy.quantity)
            # set the new policy but do NOT SAVE
            r.setPolicy(Policy.union(groupUserPolicy,r.policy))
       
    def joinGroup(self,group):
        self.joinGroups([group])
        Resource.saveMany(self.getResources(),False)
                
    def joinGroups(self,groupList):
        for group in groupList:
            self._joinGroup(group)
        Resource.saveMany(self.getResources(),False)


    def _addLatestCommission(self,resource,quantity):
        if(self.latestCommission == None):
            self.latestCommission = self.addCommission()
        self.latestCommission.addResource(resource, quantity)
    
            
    def drawResources(self,**kwargs):
        for prefixedName,quantity in kwargs.items():
            #printf("prefixedName = {0}")            
            tmp = prefixedName.split("_")
            group = tmp[0]
            resourceName = "_".join(tmp[1:])
            #group,resourceName = tuple(prefixedName.split("_"))
            self._addLatestCommission(Group.get(group,"").getResource(resourceName),quantity)
        #
    
    def finalizeCommission(self,accept=True):
        if(self.latestCommission == None):
            return True
        elif(self.latestCommission.canChange()):
            self.latestCommission.issue()
        #    
        if(self.latestCommission.isPending()):
            if(accept):
                b = self.latestCommission.accept()
            else:
                b = self.latestCommission.reject()
            self.latestCommission = None
            return b
        else:
            exn("Should not reach this point")
                        
    def commit(self):
        return self.finalizeCommission(True)
        
    def reject(self):
        return self.finalizeCommission(False)
        
    def _leaveGroups(self,groupList):
        #Must DO before anything else:
        self.reject()

        #TODO:  revert commissions  revert policies !!!         
        # remove bindings
        self.groups = [g for g in self.groups if(g not in groupList)]                            
        for g in groupList:
            g.users = [u for u in g.users if(self != u)]
            
        
        qs = [q for q in self._commissions if(q.isFinal() and all(q > -1 for r,q in q.resources_quant))]
        # Invert prior commissions!
        #printf("COMMS_LEN {0}  after {1}",len(self._commissions),len(qs))
        #for q in self._commissions:
        #    printf("COMM {0} ", q)
        
        qs = [q.inverse() for q in qs]        
        # ok remove resource 
        for q in qs:
            q.accept(True)
        
        
        
    def leaveGroup(self,group):
        self._leaveGroups([group])
    
    def release(self):
        if(not self.commission.isFinal()):
            self.reject()
        self._leaveGroups(self.groups)
        ResourceHolder.release(self)


# Main program

try:
     
    pgerakios = Entity.get("pgerakios",lambda: Entity("pgerakios","key1",Entity.get("system")))
    if(pgerakios.exists(True) == False):
        pgerakios.create()
       
    #
    # Group1
    printf("Step 1")
    group1 = Group.get("group1","group1",
                       # Optional arguments
                       group_pithos=10,group_cyclades_vm=8,
                       group_cyclades_mem=9,group_cyclades_cpu=12,
                       user_pithos=2,user_cyclades_vm=2,
                       user_cyclades_mem=1, user_cyclades_cpu=3                      
                      )
    
    printf("Type of group1 : {0}, exists ? {1} ", type(group1), group1.exists(True))
    
    
    for e in ResourceHolder.root.getChildren():
        printf("{0} child Entity {1}",ResourceHolder.root.entityName,e.entityName)
    
    
    if(not isinstance(group1,Group)):
        exn("Not instance of group")

    printf("PENDING: {0}",Client.getPending())

    printf("Step 2  name : {0}",group1.entityName)
    #["pithos","cyclades.vm","cyclades.cpu","cyclades.mem"]
    group1.drawSystemResources()

    printf("Group1 resources BEGIN")
    for r in group1.getResources(True):
        printf("Group {0} resource {1} = {2}",
               group1.entityName,r.resourceName,r.quantity())
    printf("Group1 resources END")    

    printf("Step 3 ")
    user1 = User.get("prodromos", "key1")

    cexn(user1.exists(True) == False,"User does not exist!!")
    
    printf("User1 resources BEGIN")
    for r in user1.getResources(True):
        printf("User {0} resource {1} = {2} ",user1.entityName,r.resourceName,r.quantity())
    printf("User1 resources END")    
 
    
    printf("Step 4 ")
    
    user1.joinGroup(group1)
    
    user1.drawResources(group1_pithos=2,group1_cyclades_vm=2,
                        group1_cyclades_mem=1, group1_cyclades_cpu=3)
        
    #
    printf("User1 resources BEGIN")
    for r in user1.getResources(False):
        printf("User {0} resource {1} = {2}",user1.entityName,r.resourceName,r.quantity())
    printf("User1 resources END")    
    
    #exn("End of story")
    
    printf("Step 5")
    cexn(user1.commit() == False,"Commit failed")
    

    
    printf("User1 resources BEGIN")
    for r in user1.getResources(True):
        printf("User {0} resource {1} = {2}",user1.entityName,r.resourceName,r.quantity())
    printf("User1 resources END")    
    
    
    # TODO:
    #release resources
    printf("Step 6")
    user1.leaveGroup(group1)
    printf("Step 7")
    group1.release()
    printf("Step 8")
 
 #Let finally take care of this   
#    printf("Step 6")
    #user1.release()
#    group1.release()

finally:
    #raw_input("Press any to terminate program other than Ctrl+C")
    no = ["system","pgerakios","group","user"]
    entityList = [e for e in Entity.list() if(e.entityName not in no)]    
    Entity.deleteMany(entityList,True)



#exit(0)
#
#
## Main program
#root = Entity.get()
##TODO: implement Entity.get recursively !! using get_entity !!!!
## TODO: correct Entity.checkAll
#pgerakios = Entity.get("pgerakios", "key1", root)
#pgerakios.create()
#
#try:
#    # Transfer resources
#    e = Entity.get(rand_string(), "key1", pgerakios)
#    e.create()
#
#    p = Policy.newDummy(quantity=0,capacity=10)
#    r1 = e.addResource("CPU",p)
#
#    r2 =e.addResourceWith("MEMORY",quantity=0,capacity=25)
#    rl1 = e.getResources(False)
#    for r in rl1:
#        printf("Resources of e before : {0}", r.resourceName)
#
#    e.saveResources()
#    rl2 = e.getResources(True)
#
#    for r in rl2:
#        printf("r is {0}",r)
#        printf("dict of r : {0}", r.__dict__)
#        printf("Resources of e after : {0}", r.resourceName)
#
#
#    e1 = Entity.get(rand_string(), "key1", pgerakios)
#    e1.create()
#    rl3 = e1.getResources(True)
#    q= e1.addCommission()
#    q.addResource(r1,3)
#    q.addResource(r1,4)
#    e1.commitAllCommissions(False)
#    rl4 = e1.getResources(True)
#
#    for r in rl3:
#        printf("Resources of e1 before : {0}", r.resourceName)
#    for r in rl4:
#        printf("Resources of e1 after : {0}", r.resourceName)
#
#finally:
#    for e in Entity.list():
#        if(e.entityName != "system" and e.entityName != "pgerakios"):
#            e.release()












