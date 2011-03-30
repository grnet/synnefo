#
# Charger - Administration script
#
# Executed hourly to charge vm usage for each user
#
# Copyright 2010 Greek Research and Technology Network
#

from synnefo.db.models import VirtualMachine

from logic import credits

def periodically_charge():
    """Scan all virtual machines and charge each user"""
    active_vms = VirtualMachine.objects.filter(delete=False)
    
    if not len(active_vms):
        print "No virtual machines found"
        return
    
    for vm in active_vms:
        # Running and Stopped is charged, else the cost is zero
        credits.charge(vm)

# vim: set ts=4 sts=4 sw=4 et ai :
