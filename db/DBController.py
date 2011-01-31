#
# Run all the time, and wait for messages from ganeti, then update the database
#

import zmq

from db.models import *

def main():
    context = zmq.Context()
    
    sock = context.socket(zmq.SUB)
    sock.connect('tcp://127.0.0.1:6666')
    
    # accept all messages
    sock.setsockopt(zmq.SUBSCRIBE, '')
    
    while True:
        message = sock.recv()
        
        # do something
        if message == 'start':
            all_machines = VirtualMachine.objects.all()
            for vm in all_machines:
                vm.state = 1
                vm.save()
                print "Changed stated of vm with name %s to RUNNING" % ( vm.name, )
        elif message == 'stop':
            all_machines = VirtualMachine.objects.all()
            for vm in all_machines:
                vm.state = 0
                vm.save()
                print "Changed stated of vm with name %s to STOPPED" % ( vm.name, )
        elif message == 'quit':
            print "Killing the bigeye"
            break
    
    sock.close()