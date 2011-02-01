#
# Bill Allocator - Administration script
#
# Run all the time, and wait for messages from ganeti, then update the database
#
# Copyright 2010 Greek Research and Technology Network
#

import zmq

from db.models import *

def main():
    context = zmq.Context()
    
    subscriber = context.socket(zmq.SUB)
    subscriber.connect('tcp://127.0.0.1:5801')
    
    # accept all messages
    subscriber.setsockopt(zmq.IDENTITY, "DBController")
    subscriber.setsockopt(zmq.SUBSCRIBE, '')
    
    while True:
        message = sock.recv()
        
        # do something
        if message == 'start':
            print "start"
        elif message == 'stop':
            print "stop"
    
    subscriber.close()