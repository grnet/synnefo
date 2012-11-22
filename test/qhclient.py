#!/usr/bin/python
from commissioning.clients.http import main, HTTP_API_Client
from commissioning import QuotaholderAPI


class QuotaholderHTTP(HTTP_API_Client):
    api_spec = QuotaholderAPI()


QH_URL='http://localhost:8008/api/quotaholder/v'
qh = QuotaholderHTTP(QH_URL)

def calls():
   for x in qh.api_spec.input_canonicals:
      print x

def help():
   for call, spec in qh.api_spec.input_canonicals.items():
      print call
      print spec.tostring(multiline=1)


def simple_create(name,root,key):
    rejected = qh.create_entity(context={},create_entity=[(name,root,key,"")])
    if rejected == []:
        for r in rejected:
            print ("Rejected " + r)
        False
    else:
        True


#if simple_create("pgerakios","system","key1"):
#    print "User pgerakios was created"
#else:
#    print "Failed to create user pgerakios"

#def create_entity      OK
#def set_entity_key     OK
#def list_entities      OK
#def get_entity         OK --- what's the point ?
#def get_limits
#def set_limits         BUG
#def get_holding
#def set_holding
#def list_resources     BUG
#def get_quota
#def set_quota
#def issue_commission
#def accept_commission
#def reject_commission
#def get_pending_commissions
#def resolve_pending_commissions
#def release_entity
#def get_timeline

for r in qh.set_entity_key(context={},set_entity_key=[("pgerakios","key1","key2")]):
    print "rejected " + r + " set_entity_key1 "

for r in qh.set_entity_key(context={},set_entity_key=[("pgerakios","key2","key1")]):
    print "rejected " + r + " set_entity_key2"

for e in qh.list_entities(context={},entity="system",key=""):
    print ("Entity " + e)

for e in qh.get_entity(context={},get_entity=[("pgerakios","key1")]):
    print "Eeee "  + e[0]

for e in qh.list_resources(context={},entity="pgerakios",key="key1"):
    print "Entity " + e

for e,r in qh.set_quota(context={},set_limits=[("pgerakios","resource1","key1",1,100,10,10,0)]):
    print "set_quota: rejected Entity " + e +  " resource " + r

for p in qh.set_limits(context={},set_limits=[("pgerakios_resource1",1,100,10,10)]):
    print "Policy " + p

#set_holding =   ListOf(Entity, Resource, Key, Policy, Flags)


#BUG: resource2 does not exist
for e,r,p in qh.set_holding(context={},set_limits=[("pgerakios","resource2","key1","policy1",0)]):
    print "set_holding: rejected entity: " + e +  " resource: " + r + " with policy: " + p


#for e in qh.get_quota(context={},get_quota=[("pgerakios","key1")]):
#    print "Entity " + e

#{'context': {}, funcname: data}

#        try:
#            entity = entity.__getattribute__(field)
#        except AttributeError:
#            continue
#        owner = 'system'
#        key = ENTITY_KEY
#        ownerkey = ''
#        args = entity, owner, key, ownerkey
#        append(args)
