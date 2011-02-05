#
# Charger - Administration script
#
# Executed hourly to charge vm usage for each user
#
# Copyright 2010 Greek Research and Technology Network
#

from db.models import *

from datetime import datetime

def stop_virtual_machine(vm):
    """Send message to stop a virtual machine instance"""
    
    # send the message to ganeti
    
    return

def charge():
    """Scan all virtual machines and charge each user"""
    all_vms = VirtualMachine.objects.all()
    
    if len(all_vms) == 0:
        print "No virtual machines found"
    
    for vm in all_vms:
        cost = 0
        
        # Running and Stopped is charged, else the cost is zero
        if vm.state == 'PE_VM_RUNNING':
            cost = vm.flavor.cost_active
        elif vm.state == 'PE_VM_STOPPED':
            cost = vm.flavor.cost_inactive
          
        user_credits = vm.owner.charge_credits(cost)        
        vm.charged = datetime.now()
        
        # update the values in the database
        vm.save()
        vm.owner.save()
        
        if user_credits <= 0:
            stop_virtual_machine(vm)
