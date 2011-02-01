#
# Bill Allocator - Administration script
#
# Run all the time, and wait for messages from ganeti, then update the database
#
# Copyright 2010 Greek Research and Technology Network
#

import zmq

from db.models import *

#GANETI_ZMQ_PUBLISHER = "tcp://ganeti-master:5801"

def init_publisher(context):
    request = context.socket(zmq.REQ)
    request.connect('tcp://127.0.0.1:6666')
    request.send_json('{ "message" : "hello" }')
    
    message = request.recv_json()

def main():
    context = zmq.Context()
    
    subscriber = context.socket(zmq.SUB)
    subscriber.connect('tcp://127.0.0.1:5801')
    
    # accept all messages
    subscriber.setsockopt(zmq.IDENTITY, "DBController")
    subscriber.setsockopt(zmq.SUBSCRIBE, '')
    
    init_publisher(context)
    
    while True:
        message = sock.recv_json()        
    
    subscriber.close()